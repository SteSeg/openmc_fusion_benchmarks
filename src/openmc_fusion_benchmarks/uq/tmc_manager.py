from typing import List, Callable
from pathlib import Path
import openmc
import numpy as np
import json
import copy
import xarray as xr
import inspect


class TMCManager:
    def __init__(self, base_model: openmc.Model, perturbations: List[Callable],
                  realizations:int, rng:np.random._generator.Generator=None):
        self.base_model = base_model
        # self.perturbations = perturbations
        self.realizations = realizations
        self.rng = rng or np.random.default_rng()

        # perturbations is a list of factories: factory(rng) -> perturb(model)
        # call each factory once to get a closure perturb(model) -> model
        self.perturbations = [factory(self.rng) for factory in perturbations]


    def run(self, cwd='.', *args, **kwargs):

        cwd = Path(cwd).resolve()

        # Prepare TMC manifest file
        manifest = cwd / "tmc_manifest.jsonl"
        manifest.parent.mkdir(parents=True, exist_ok=True)

        # Open TMC manifest for folder structure
        with manifest.open("a") as f_manifest:
            # Run TMC engine
            for p_idx, p in enumerate(self.perturbations):
                for r_idx in range(self.realizations):

                    # fresh copy so perturbations do not accumulate
                    model_copy = copy.deepcopy(self.base_model)
                    perturbed_model = p(model_copy)

                    run_dir = cwd / "tmc" / f"perturbation_{p_idx}" / f"realization_{r_idx}"
                    run_dir.mkdir(parents=True, exist_ok=True)

                    sp_path = perturbed_model.run(cwd=run_dir, *args, **kwargs)
                    sp_path = Path(sp_path).resolve()

                    # Record in manifest (relative path from cwd)
                    rec = {
                        "perturbation": int(p_idx),
                        "realization": int(r_idx),
                        "statepoint": str(sp_path.relative_to(cwd)),
                        # "params": perturbation_params_if_any,
                    }
                    f_manifest.write(json.dumps(rec) + "\n")
        
        # Postprocess the whole TMC set
        self._process_tmc(manifest_path=manifest)

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

        for tid, nd_shape in tally_shapes.items():
            tmc_data[tid] = np.empty((n_realizations,) + nd_shape, dtype=float)

        # ---- 4. Fill arrays by looping over all statepoints ----
        for i, rec in enumerate(records):
            sp_path = Path(rec["statepoint"]).resolve()
            with openmc.StatePoint(str(sp_path)) as sp:
                for tid, arr in tmc_data.items():
                    # assumes same tally IDs exist in every statepoint
                    tally = sp.tallies[tid]
                    mean_flat = tally.mean
                    nd_shape = tally_shapes[tid]
                    mean_nd = mean_flat.reshape(nd_shape)
                    arr[i, ...] = mean_nd

        # ---- 5. Build xarray Dataset and write to disk ----
        ds = xr.Dataset()
        sample_coord = np.arange(n_realizations)

        for tid, arr in tmc_data.items():
            nd_shape = tally_shapes[tid]
            filters = tally_filters[tid]
            
            # Build dimension names following OpenMC conventions
            filter_dims = []
            for f in filters:
                # Use filter type name without "Filter" suffix, lowercase
                filter_type = type(f).__name__.replace("Filter", "").lower()
                filter_dims.append(filter_type)
            
            dims = ("realization",) + tuple(filter_dims) + ("nuclide", "score")

            # Use tally name if available, otherwise fall back to ID
            tally_name = tally_names[tid] or f"tally_{tid}"
            
            da = xr.DataArray(
                arr,
                dims=dims,
                coords={"realization": sample_coord},
                name=tally_name,
            )

            # Attach tally metadata
            da.attrs["tally_id"] = tid
            da.attrs["tally_name"] = tally_names[tid]

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

            ds[da.name] = da

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
                da = self._ds[var_name]
                tally_id = da.attrs.get('tally_id')
                if tally_id is not None:
                    self._tallies[tally_id] = TMCTally(da)
        return self._tallies
    
    def get_tally(self, id=None, name=None):
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
        if id is not None:
            return self.tallies[id]
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
    """
    
    def __init__(self, data_array):
        self._da = data_array
        
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
        """Mean values across all realizations."""
        return self._da.mean(dim='realization').values
    
    @property
    def std_dev(self):
        """Standard deviation across realizations."""
        return self._da.std(dim='realization').values
    
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