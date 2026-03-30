from pathlib import Path

import h5py
import numpy as np
import xarray as xr

from ..tallies import BaseTally


class TMCStatePoint:
    """
    Wrapper for TMC statepoint providing an OpenMC StatePoint-like interface.

    Parameters
    ----------
    path : str or Path
        Path to the TMC statepoint NetCDF/HDF5 file.
    """

    def __init__(self, path):
        self.path = Path(path).resolve()
        # We won't keep one global ds; we'll open per-tally groups as needed.
        self._tallies = None

    @property
    def tallies(self):
        """Dictionary of tallies, indexed by tally ID (mimics openmc.StatePoint.tallies)."""
        if self._tallies is None:
            self._tallies = {}
            # Discover tally groups via h5py
            with h5py.File(self.path, "r") as f:
                for group_name in f.keys():
                    if not group_name.startswith("tally_"):
                        continue
                    # Open this group as an xarray Dataset
                    ds = xr.open_dataset(
                        self.path,
                        group=group_name,
                        engine="h5netcdf",
                    )
                    if "mean" not in ds:
                        continue
                    da_mean = ds["mean"]
                    da_mc_std = ds["mc_std"] if "mc_std" in ds else None

                    tally_id = da_mean.attrs.get("tally_id")
                    if tally_id is None:
                        # Fallback: parse id from group name
                        try:
                            tally_id = int(group_name.split("_", 1)[1])
                        except Exception:
                            continue

                    self._tallies[tally_id] = TMCTally(da_mean, da_mc_std, parent_ds=ds)
        return self._tallies

    def get_tally(self, tally_id=None, name=None):
        """
        Get a tally by ID or name (mimics openmc.StatePoint.get_tally).

        Parameters
        ----------
        tally_id : int, optional
            Tally ID
        name : str, optional
            Tally name

        Returns
        -------
        TMCTally
            The requested tally
        """
        if tally_id is not None:
            try:
                return self.tallies[tally_id]
            except KeyError:
                raise ValueError(f"No tally with id '{tally_id}' found")
        elif name is not None:
            for tally in self.tallies.values():
                if tally.name == name:
                    return tally
            raise ValueError(f"No tally with name '{name}' found")
        else:
            raise ValueError("Must specify either 'tally_id' or 'name'")

    def close(self):
        """No persistent open Dataset to close, but keep for API symmetry."""
        # If you decide to cache per-group ds objects, close them here.
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self):
        n_tallies = len(self.tallies)
        # Try to infer "realizations" (or more generally TMC size along first dim)
        n_realizations = 0
        if self.tallies:
            any_tally = next(iter(self.tallies.values()))
            tmc_dims = any_tally._tmc_dims
            if tmc_dims:
                # product of TMC dims sizes
                sz = 1
                for d in tmc_dims:
                    sz *= any_tally._da.sizes[d]
                n_realizations = sz
        return f"<TMCStatePoint: {n_realizations} TMC combinations, {n_tallies} tallies>"


class TMCTally(BaseTally):
    """
    Wrapper for a single TMC tally providing an OpenMC Tally-like interface.

    Parameters
    ----------
    mean_da : xarray.DataArray
        The DataArray containing the TMC mean values for this tally.
    mc_std_da : xarray.DataArray, optional
        The DataArray containing the MC std dev per run/combo.
    parent_ds : xarray.Dataset, optional
        Parent dataset (group) containing metadata attributes.
    """

    def __init__(self, mean_da, mc_std_da=None, parent_ds=None):
        super().__init__(mean_da=mean_da, mc_std_da=mc_std_da, parent_ds=parent_ds)

        # Identify TMC dimensions: "perturbation" and "realization" for sequential, "perturbation_*" for matrix
        self._tmc_dims = [
            d for d in self._da.dims
            if d in ("perturbation", "realization") or d.startswith("perturbation_")
        ]

    @property
    def tmc_dims(self):
        """Names of TMC dimensions (realization / perturbation_*)."""
        return tuple(self._tmc_dims)

    @property
    def mean(self):
        """
        TMC mean across all TMC dimensions (realization / perturbation_*).
        """
        if not self._tmc_dims:
            return self._da.values
        return self._da.mean(dim=self._tmc_dims).values

    @property
    def std_dev(self):
        """
        TMC standard deviation across all TMC dimensions.

        This is the propagated parametric uncertainty from the ensemble,
        not the MC sampling error within each run.
        """
        if not self._tmc_dims:
            return np.zeros_like(self._da.values)
        return self._da.std(dim=self._tmc_dims).values

    @property
    def per_realization_mean(self):
        """
        Raw mean value for each TMC point (all TMC dims retained).
        Shape: (TMC dims..., filters..., nuclide, score).
        """
        return self._da.values

    @property
    def per_realization_std_dev(self):
        """
        Monte Carlo standard deviation for each run/combo.

        This is the statistical uncertainty from particle sampling within each
        individual OpenMC run, shaped like self._da.
        """
        if self._da_mc_std is not None:
            return self._da_mc_std.values
        return np.zeros_like(self._da.values)

    @property
    def per_perturbation_mean(self):
        """
        Mean value for each perturbation type (averaging over all realizations).

        For sequential mode: shape (n_perturbations, filters..., nuclide, score)
          - Averages over realizations, keeping separate perturbation results

        For matrix mode: shape (n_perturbations, filters..., nuclide, score)
          - Averages over all perturbation_i dimensions (all realization grids)
          - Returns one value per perturbation type

        For diagonal mode: returns overall mean (single realization dimension)
        """
        dims = tuple(self._da.dims)
        has_pert = "perturbation" in dims
        has_real = "realization" in dims

        if has_pert and has_real:
            # Sequential mode: average over realizations only
            result = self._da.mean(dim="realization")
            return result.values
        elif has_pert:
            # Edge case: perturbation dim exists but no realization dim
            return self._da.values
        else:
            # Matrix mode: average over all perturbation_i dimensions
            pert_dims = [d for d in self._tmc_dims if d.startswith("perturbation_")]
            if pert_dims:
                # Average over all perturbation dimensions (all realization grids)
                result = self._da.mean(dim=pert_dims)
                # Result shape: (filters..., nuclide, score)
                # Expand to add perturbation axis: (n_perturbations, filters..., nuclide, score)
                n_perturbations = len(pert_dims)
                # Repeat the result for each perturbation
                result_expanded = np.tile(result.values, (n_perturbations,) + (1,) * (result.ndim))
                return result_expanded
            else:
                # Diagonal or other: collapse all TMC dims
                return self.mean

    @property
    def per_perturbation_std_dev(self):
        """
        Standard deviation for each perturbation type (across all realizations).

        For sequential mode: shape (n_perturbations, filters..., nuclide, score)
          - Std deviation across realizations, keeping separate perturbation results

        For matrix mode: shape (n_perturbations, filters..., nuclide, score)
          - Std deviation over all perturbation_i dimensions (all realization grids)
          - Returns one value per perturbation type

        For diagonal mode: returns overall std_dev (single realization dimension)
        """
        dims = tuple(self._da.dims)
        has_pert = "perturbation" in dims
        has_real = "realization" in dims

        if has_pert and has_real:
            # Sequential mode: std over realizations only
            result = self._da.std(dim="realization")
            return result.values
        elif has_pert:
            # Edge case: perturbation dim exists but no realization dim
            return np.zeros_like(self._da.values)
        else:
            # Matrix mode: std over all perturbation_i dimensions
            pert_dims = [d for d in self._tmc_dims if d.startswith("perturbation_")]
            if pert_dims:
                # Std over all perturbation dimensions (all realization grids)
                result = self._da.std(dim=pert_dims)
                # Result shape: (filters..., nuclide, score)
                # Expand to add perturbation axis: (n_perturbations, filters..., nuclide, score)
                n_perturbations = len(pert_dims)
                # Repeat the result for each perturbation
                result_expanded = np.tile(result.values, (n_perturbations,) + (1,) * (result.ndim))
                return result_expanded
            else:
                # Diagonal or other: collapse all TMC dims
                return self.std_dev

    @property
    def perturbation_dims(self):
        """Names of perturbation dimensions in matrix mode (e.g. 'perturbation_0', ...)."""
        return tuple(d for d in self._tmc_dims if d.startswith("perturbation_"))

    def __repr__(self):
        return f"<TMCTally {self.id}: '{self.name}', shape={self.shape}>"
