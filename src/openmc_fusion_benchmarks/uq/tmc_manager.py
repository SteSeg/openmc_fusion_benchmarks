from typing import List, Callable
from pathlib import Path
import openmc
import numpy as np
import json
import copy
import xarray as xr
import inspect
import itertools


class TMCManager:
    def __init__(self, base_model: openmc.Model, perturbations: List[Callable],
                realizations:int, seed: int | None = None, 
                rng: np.random.Generator | None = None):

        if rng is not None and seed is not None:
            raise ValueError("Pass either seed or rng, not both.")

        if rng is None:
            if seed is None:
                seed = 123456  # or from config
            self.master_rng = np.random.default_rng(seed)
        else:
            self.master_rng = rng
        
        if rng is not None:
            self.rng = rng
        else:
            self.rng = np.random.default_rng(seed)

        self.base_model = base_model
        self.realizations = realizations
        
        # perturbations is a list of factories: factory(rng) -> perturb(model)
        # call each factory once to get a closure perturb(model) -> model
        perts = []
        for factory in perturbations:
            base_seed = int(self.master_rng.integers(0, 2**31))
            perturb = factory(base_seed)
            perts.append(perturb)
        
        self.perturbations = perts

    def run(self, cwd='.', *args, **kwargs):

        cwd = Path(cwd).resolve()

        # Prepare TMC manifest file
        manifest = cwd / "tmc_manifest.jsonl"
        manifest.parent.mkdir(parents=True, exist_ok=True)

        # Open TMC manifest for folder structure
        with manifest.open("a") as f_manifest:

            # Run TMC engine in matrix combined perturbations mode
            for idx_tuple in itertools.product(range(self.realizations), repeat=len(self.perturbations)):
                # idx_tuple length == p, e.g. (0, 2) for this p=2 example

                # Copy base model
                perturbed_model = copy.deepcopy(self.base_model)

                # Apply each perturbation with its corresponding realization index

                # Might need idx as argument for reproducibility, i.e.:
                # for perturb, ridx in zip(self.perturbations, idx_tuple):
                #     perturbed_model = perturb(perturbed_model, ridx, self.rng)

                for pert, ridx in zip(self.perturbations, idx_tuple):
                    perturbed_model = pert(perturbed_model, ridx)

                    # Create run directory
                    s = ".".join(map(str, idx_tuple))
                    run_dir = cwd / "tmc" / f"perturbation_{s}"
                    run_dir.mkdir(parents=True, exist_ok=True)

                    # Run model
                    # sp_path = perturbed_model.run(cwd=run_dir, *args, **kwargs)

                    print(s)  # delete later
                    sp_path = run_dir / "model.xml"  # delete later
                    perturbed_model.export_to_model_xml(str(sp_path))  # delete later

                    sp_path = Path(sp_path).resolve()

                    # Store statepoint path in manifest
                    rec = {
                            "combo_index": s,
                            "indices": list(idx_tuple),  # [i0, i1, ..., i_{p-1}]
                            "statepoint": str(sp_path.relative_to(cwd)),
                        }
                    f_manifest.write(json.dumps(rec) + "\n")

    def _process_tmc(self, manifest_path="tmc_manifest.jsonl"):
        manifest_path = Path(manifest_path).resolve()
        tmc_dir = manifest_path.parent

        # xarray will write NetCDF (HDF5-backed); extension is up to you
        tmc_statepoint = tmc_dir / f"tmc_statepoint.{int(self.realizations)}.h5"

        # ---- 1. Read TMC manifest ----
        records = []
        with manifest_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                records.append(rec)

        # Sort for deterministic order
        records.sort(key=lambda r: (r["perturbation"], r["realization"]))
        n_realizations = len(records)
        if n_realizations == 0:
            raise RuntimeError("TMC manifest is empty; no runs to process")

        # ---- 2. Use first statepoint as reference to determine shape & metadata ----
        first_sp_path = Path(records[0]["statepoint"]).resolve()
        tally_names = {}  # key: tally id, value: tally name
        tally_shapes = {}  # key: tally id, value: nd_shape
        tally_filters = {}  # key: tally id, value: list of filters
        tally_axisinfo = {}  # key: tally id, value: axis_info dict

        with openmc.StatePoint(str(first_sp_path)) as sp0:
            for tally in sp0.tallies.values():
                tid = tally.id

                filters = tally.filters
                filter_bins = [f.num_bins for f in filters]
                n_nuclides = max(len(tally.nuclides), 1)
                n_scores = len(tally.scores)

                flat_shape = tally.mean.shape  # (prod_bins, n_nuclides, n_scores)
                nd_shape = tuple(filter_bins) + (n_nuclides, n_scores)

                assert flat_shape[0] == np.prod(filter_bins)
                assert flat_shape[1] == n_nuclides
                assert flat_shape[2] == n_scores

                tally_names[tid]  = tally.name
                tally_shapes[tid]  = nd_shape
                tally_filters[tid] = filters

                axis_info = {
                    "sample_axis": 0,
                    "filter_axes": [
                        {"name": type(f).__name__, "num_bins": f.num_bins}
                        for f in filters
                    ],
                    "nuclide_axis": len(filter_bins) + 1,
                    "score_axis":   len(filter_bins) + 2,
                    "nuclides":     [str(n) for n in tally.nuclides] if tally.nuclides else ["total"],
                    "scores":       list(tally.scores),
                }

                tally_axisinfo[tid] = axis_info

        # ---- 3. Allocate TMC arrays, one per tally ----
        tmc_data = {}  # key: tally id, value: ndarray (n_samples, ...)
        tmc_mc_std = {}  # key: tally id, value: MC std_dev per realization

        for tid, nd_shape in tally_shapes.items():
            tmc_data[tid] = np.empty((n_realizations,) + nd_shape, dtype=float)
            tmc_mc_std[tid] = np.empty((n_realizations,) + nd_shape, dtype=float)

        # ---- 4. Fill arrays by looping over all statepoints ----
        for i, rec in enumerate(records):
            sp_path = Path(rec["statepoint"]).resolve()
            with openmc.StatePoint(str(sp_path)) as sp:
                for tid, arr in tmc_data.items():
                    # assumes same tally IDs exist in every statepoint
                    tally = sp.tallies[tid]
                    mean_flat = tally.mean
                    std_flat = tally.std_dev
                    nd_shape = tally_shapes[tid]
                    mean_nd = mean_flat.reshape(nd_shape)
                    std_nd = std_flat.reshape(nd_shape)
                    arr[i, ...] = mean_nd
                    tmc_mc_std[tid][i, ...] = std_nd

        # ---- 5. Build xarray Dataset and write to disk ----
        ds = xr.Dataset()
        sample_coord = np.arange(n_realizations)

        for tid, arr in tmc_data.items():
            nd_shape = tally_shapes[tid]
            filters = tally_filters[tid]
            
            # Build dimension names following OpenMC conventions
            # Make nuclide and score dimensions unique per tally to avoid conflicts
            filter_dims = []
            for f in filters:
                # Use filter type name without "Filter" suffix, lowercase
                filter_type = type(f).__name__.replace("Filter", "").lower()
                filter_dims.append(filter_type)
            
            dims = ("realization",) + tuple(filter_dims) + (f"nuclide_{tid}", f"score_{tid}")

            # Use tally name if available, otherwise fall back to ID
            tally_name = tally_names[tid] or f"tally_{tid}"
            
            da = xr.DataArray(
                arr,
                dims=dims,
                coords={"realization": sample_coord},
                name=tally_name,
            )
            
            # Create corresponding MC std_dev DataArray
            da_mc_std = xr.DataArray(
                tmc_mc_std[tid],
                dims=dims,
                coords={"realization": sample_coord},
                name=f"{tally_name}_mc_std",
            )

            # Attach tally metadata
            da.attrs["tally_id"] = tid
            da.attrs["tally_name"] = tally_names[tid]
            da_mc_std.attrs["tally_id"] = tid
            da_mc_std.attrs["tally_name"] = tally_names[tid]

            # Attach axis info as attrs; serialize non-scalar things to JSON strings
            axisinfo = tally_axisinfo[tid]
            for k, v in axisinfo.items():
                # scalars are fine
                if isinstance(v, (int, float, bool, str, np.number)):
                    da.attrs[k] = v
                else:
                    # lists, dicts, numpy arrays -> JSON string
                    if isinstance(v, np.ndarray):
                        to_dump = v.tolist()
                    else:
                        to_dump = v
                    da.attrs[k] = json.dumps(to_dump)
            
            # Copy axis info to MC std DataArray
            for k, v in axisinfo.items():
                if isinstance(v, (int, float, bool, str, np.number)):
                    da_mc_std.attrs[k] = v
                else:
                    if isinstance(v, np.ndarray):
                        to_dump = v.tolist()
                    else:
                        to_dump = v
                    da_mc_std.attrs[k] = json.dumps(to_dump)

            ds[da.name] = da
            ds[da_mc_std.name] = da_mc_std

        # If you have netcdf4/h5netcdf installed, you can also specify engine explicitly:
        # ds.to_netcdf(tmc_statepoint, engine="h5netcdf")
        ds.to_netcdf(tmc_statepoint)
        
        # Store path for later retrieval
        self.tmc_statepoint_path = tmc_statepoint

    def get_tmc_statepoint(self, path=None):
        """
        Load and return a TMCStatePoint wrapper for the TMC results.
        
        Parameters
        ----------
        path : str or Path, optional
            Path to the TMC statepoint file. If not provided, uses the path
            from the last run() call.
            
        Returns
        -------
        TMCStatePoint
            Wrapper object providing OpenMC StatePoint-like interface to TMC data.
        """
        if path is None:
            if not hasattr(self, 'tmc_statepoint_path'):
                raise RuntimeError("No TMC statepoint path available. Either run TMC first or provide path.")
            path = self.tmc_statepoint_path
        else:
            path = Path(path).resolve()
            
        return TMCStatePoint(path)


class TMCStatePoint:
    """
    Wrapper for TMC statepoint providing OpenMC StatePoint-like interface.
    
    Parameters
    ----------
    path : str or Path
        Path to the TMC statepoint NetCDF/HDF5 file.
    """
    
    def __init__(self, path):
        self.path = Path(path).resolve()
        self._ds = xr.open_dataset(self.path)
        self._tallies = None
        
    @property
    def tallies(self):
        """Dictionary of tallies, indexed by tally ID (mimics openmc.StatePoint.tallies)."""
        if self._tallies is None:
            self._tallies = {}
            for var_name in self._ds.data_vars:
                # Skip MC std arrays (they're accessed via the main tally)
                if var_name.endswith('_mc_std'):
                    continue
                da = self._ds[var_name]
                tally_id = da.attrs.get('tally_id')
                if tally_id is not None:
                    self._tallies[tally_id] = TMCTally(da, parent_ds=self._ds)
        return self._tallies
    
    def get_tally(self, tally_id=None, name=None):
        """
        Get a tally by ID or name (mimics openmc.StatePoint.get_tally).
        
        Parameters
        ----------
        id : int, optional
            Tally ID
        name : str, optional
            Tally name
            
        Returns
        -------
        TMCTally
            The requested tally
        """
        if tally_id is not None:
            return self.tallies[tally_id]
        elif name is not None:
            for tally in self.tallies.values():
                if tally.name == name:
                    return tally
            raise ValueError(f"No tally with name '{name}' found")
        else:
            raise ValueError("Must specify either 'id' or 'name'")
    
    def close(self):
        """Close the underlying NetCDF file."""
        self._ds.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *args):
        self.close()
        
    def __repr__(self):
        n_tallies = len(self.tallies)
        n_realizations = self._ds.dims.get('realization', 0)
        return f"<TMCStatePoint: {n_realizations} realizations, {n_tallies} tallies>"


class TMCTally:
    """
    Wrapper for a single TMC tally providing OpenMC Tally-like interface.
    
    Parameters
    ----------
    data_array : xarray.DataArray
        The DataArray containing the TMC tally data
    parent_ds : xarray.Dataset, optional
        Parent dataset containing MC uncertainty data
    """
    
    def __init__(self, data_array, parent_ds=None):
        self._da = data_array
        self._parent_ds = parent_ds
        
    @property
    def id(self):
        """Tally ID."""
        return self._da.attrs.get('tally_id')
    
    @property
    def name(self):
        """Tally name."""
        return self._da.attrs.get('tally_name')
    
    @property
    def mean(self):
        """TMC mean: mean value across all realizations."""
        return self._da.mean(dim='realization').values
    
    @property
    def std_dev(self):
        """TMC standard deviation: propagated parametric uncertainty across realizations."""
        return self._da.std(dim='realization').values
    
    @property
    def realization_means(self):
        """Mean value for each individual realization (shape: n_realizations x ...)."""
        return self._da.values
    
    @property
    def realization_stds(self):
        """
        Monte Carlo standard deviation for each individual realization.
        
        This is the statistical uncertainty from particle sampling within each
        individual OpenMC run (shape: n_realizations x ...).
        """
        # Get the corresponding MC std DataArray from the parent dataset
        mc_std_name = f"{self._da.name}_mc_std"
        if hasattr(self._da, '_parent_ds') and mc_std_name in self._da._parent_ds:
            return self._da._parent_ds[mc_std_name].values
        # Fallback: try to find it in the same file
        try:
            ds = xr.open_dataset(self._da.encoding.get('source', ''))
            if mc_std_name in ds:
                return ds[mc_std_name].values
        except:
            pass
        # If not found, return zeros as fallback
        return np.zeros_like(self._da.values)
    
    @property
    def data(self):
        """Full TMC data array (all realizations)."""
        return self._da.values
    
    @property
    def scores(self):
        """List of score names."""
        scores_json = self._da.attrs.get('scores')
        if scores_json:
            return json.loads(scores_json)
        return []
    
    @property
    def nuclides(self):
        """List of nuclide names."""
        nuclides_json = self._da.attrs.get('nuclides')
        if nuclides_json:
            return json.loads(nuclides_json)
        return []
    
    @property
    def filters(self):
        """List of filter information (type and number of bins)."""
        filters_json = self._da.attrs.get('filter_axes')
        if filters_json:
            return json.loads(filters_json)
        return []
    
    @property
    def realizations(self):
        """Number of TMC realizations."""
        return self._da.sizes.get('realization', 0)
    
    @property
    def shape(self):
        """Shape of the data array."""
        return self._da.shape
    
    @property
    def dims(self):
        """Dimension names."""
        return self._da.dims
    
    def get_slice(self, scores=None, nuclides=None, **filter_kwargs):
        """
        Get a slice of the TMC data with optional filtering.
        
        Parameters
        ----------
        scores : list of str, optional
            Score names to select
        nuclides : list of str, optional
            Nuclide names to select
        **filter_kwargs : optional
            Additional dimension filters (e.g., energy=slice(0, 10))
            
        Returns
        -------
        xarray.DataArray
            Filtered TMC data
        """
        da = self._da
        
        # Apply filter dimension selections
        if filter_kwargs:
            da = da.sel(**filter_kwargs)
            
        # Apply score selection
        if scores is not None:
            all_scores = self.scores
            score_indices = [all_scores.index(s) for s in scores]
            da = da.isel(score=score_indices)
            
        # Apply nuclide selection
        if nuclides is not None:
            all_nuclides = self.nuclides
            nuclide_indices = [all_nuclides.index(n) for n in nuclides]
            da = da.isel(nuclide=nuclide_indices)
            
        return da
    
    def __repr__(self):
        return f"<TMCTally {self.id}: '{self.name}', shape={self.shape}>"