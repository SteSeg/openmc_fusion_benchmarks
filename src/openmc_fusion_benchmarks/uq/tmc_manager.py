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
                seed = 123456
            self.master_rng = np.random.default_rng(seed)
        else:
            self.master_rng = rng

        self.base_model = base_model
        self.realizations = realizations

       # Wrap user perturbations into indexed perturb(model, idx)
        self.perturbations = self._build_indexed_perturbations(perturbations)

    def run(self, cwd='.', *args, **kwargs):

        cwd = Path(cwd).resolve()

        # Prepare TMC manifest file
        manifest = cwd / "tmc_manifest.jsonl"
        manifest.parent.mkdir(parents=True, exist_ok=True)

        # Open TMC manifest for folder structure
        with manifest.open("a") as f_manifest:

            # Run TMC engine in matrix combined perturbations mode
            for idx_tuple in itertools.product(range(self.realizations),
                                            repeat=len(self.perturbations)):
                # idx_tuple length == p, e.g. (0, 2) for p=2

                # Copy base model
                perturbed_model = copy.deepcopy(self.base_model)

                # Apply each perturbation with its corresponding realization index
                for pert, ridx in zip(self.perturbations, idx_tuple):
                    perturbed_model = pert(perturbed_model, ridx)

                # NOW run once per idx_tuple, after all perturbations have been applied
                s = ".".join(map(str, idx_tuple))
                run_dir = cwd / "tmc" / f"perturbation_{s}"
                run_dir.mkdir(parents=True, exist_ok=True)

                # Run model
                sp_path = perturbed_model.run(cwd=run_dir, *args, **kwargs)
                sp_path = Path(sp_path).resolve()

                # Store statepoint path in manifest
                rec = {
                    "indices": list(idx_tuple),  # [i0, i1, ..., i_{p-1}]
                    "statepoint": str(sp_path.relative_to(cwd)),
                }
                f_manifest.write(json.dumps(rec) + "\n")
                f_manifest.flush()

        # Postprocess the whole TMC set
        self._process_tmc(manifest_path=manifest)

    def _build_indexed_perturbations(self, user_factories):
        """
        user_factories: list of callables, each like:
            factory() -> inner(model, rng)

        Returns list of callables:
            perturb(model, idx) -> model
        """
        indexed = []
        for factory in user_factories:
            # 1) get user's inner function: (model, rng) -> model
            inner = factory()

            # 2) draw a unique base_seed for this perturbation
            base_seed = int(self.master_rng.integers(0, 2**31))

            # 3) wrap inner into perturb(model, idx)
            def make_wrapper(inner_func, base_seed):
                def perturb(model, idx):
                    local_seed = base_seed + idx
                    local_rng = np.random.default_rng(local_seed)
                    return inner_func(model, local_rng)
                return perturb

            indexed.append(make_wrapper(inner, base_seed))

        return indexed

    def _process_tmc(self, manifest_path="tmc_manifest.jsonl"):
        manifest_path = Path(manifest_path).resolve()
        tmc_dir = manifest_path.parent  # directory containing the manifest

        # xarray will write NetCDF (HDF5-backed); extension is up to you
        tmc_statepoint = tmc_dir / f"tmc_statepoint.{int(self.realizations)}.h5"

        # ---- helper: resolve statepoint path robustly ----
        def resolve_statepoint_path(sp_str: str) -> Path:
            sp_path = Path(sp_str)
            if sp_path.is_absolute():
                return sp_path
            # Try relative to manifest dir
            cand1 = tmc_dir / sp_path
            if cand1.exists():
                return cand1
            # Try relative to parent of manifest dir (project root)
            cand2 = tmc_dir.parent / sp_path
            if cand2.exists():
                return cand2
            # Fallback: plain resolve (current CWD)
            return sp_path.resolve()

        # ---- 1. Read manifest ----
        records = []
        with manifest_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                records.append(rec)

        if not records:
            raise RuntimeError("TMC manifest is empty; no runs to process")

        # Detect mode: old sequential vs new matrix
        first_rec = records[0]
        if "indices" in first_rec:
            mode = "matrix"
        elif "perturbation" in first_rec and "realization" in first_rec:
            mode = "sequential"
        else:
            raise RuntimeError("Unrecognized manifest record format")

        # ---- 2. Sort & index logic depending on mode ----
        if mode == "sequential":
            # sort by (perturbation, realization)
            records.sort(key=lambda r: (r["perturbation"], r["realization"]))
            n_realizations = len(records)
            extra_shape = (n_realizations,)
            extra_dims = ("realization",)
            extra_coords = {"realization": np.arange(n_realizations)}

        else:  # mode == "matrix"
            # each record: {"indices": [i0, i1, ..., i_{p-1}], "statepoint": ...}
            # sort lexicographically by indices
            records.sort(key=lambda r: tuple(r["indices"]))

            # number of perturbations = length of indices
            p = len(first_rec["indices"])

            # In the matrix TMC driver, you used:
            #   for idx_tuple in itertools.product(range(self.realizations), repeat=p):
            # so each perturbation dimension has length self.realizations
            r = int(self.realizations)
            extra_shape = tuple(r for _ in range(p))  # (r, r, ..., r)
            extra_dims = tuple(f"perturbation_{i}" for i in range(p))
            extra_coords = {dim: np.arange(r) for dim in extra_dims}

            n_combos = len(records)
            expected_combos = r ** p
            if n_combos != expected_combos:
                raise RuntimeError(
                    f"Matrix TMC manifest has {n_combos} runs, but expected {expected_combos} "
                    f"for realizations={r}, perturbations={p}."
                )

        # ---- 3. Use first statepoint as reference for tallies ----
        first_sp_path = resolve_statepoint_path(first_rec["statepoint"])
        tally_names = {}    # tid -> name
        tally_shapes = {}   # tid -> nd_shape (filters..., nuclide, score)
        tally_filters = {}  # tid -> list of filters
        tally_axisinfo = {} # tid -> axis_info dict

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

                tally_names[tid] = tally.name
                tally_shapes[tid] = nd_shape
                tally_filters[tid] = filters

                axis_info = {
                    "filter_axes": [
                        {"name": type(f).__name__, "num_bins": f.num_bins}
                        for f in filters
                    ],
                    "nuclides": [str(n) for n in tally.nuclides] if tally.nuclides else ["total"],
                    "scores": list(tally.scores),
                }

                tally_axisinfo[tid] = axis_info

        # ---- 4. Allocate arrays: one per tally ----
        tmc_data = {}    # tid -> ndarray (extra_shape + nd_shape)
        tmc_mc_std = {}  # tid -> ndarray (extra_shape + nd_shape)

        for tid, nd_shape in tally_shapes.items():
            full_shape = extra_shape + nd_shape
            tmc_data[tid] = np.empty(full_shape, dtype=float)
            tmc_mc_std[tid] = np.empty(full_shape, dtype=float)

        # ---- 5. Fill arrays by looping over statepoints ----
        if mode == "sequential":
            for i, rec in enumerate(records):
                sp_path = resolve_statepoint_path(rec["statepoint"])
                with openmc.StatePoint(str(sp_path)) as sp:
                    for tid in tmc_data.keys():
                        tally = sp.tallies[tid]
                        mean_flat = tally.mean
                        std_flat = tally.std_dev
                        nd_shape = tally_shapes[tid]
                        mean_nd = mean_flat.reshape(nd_shape)
                        std_nd = std_flat.reshape(nd_shape)
                        tmc_data[tid][i, ...] = mean_nd
                        tmc_mc_std[tid][i, ...] = std_nd

        else:  # mode == "matrix"
            # Fill as flat (n_combos, ...) then reshape first axis into extra_shape
            n_combos = len(records)
            flat_data = {}
            flat_mc_std = {}
            for tid, nd_shape in tally_shapes.items():
                flat_shape = (n_combos,) + nd_shape
                flat_data[tid] = np.empty(flat_shape, dtype=float)
                flat_mc_std[tid] = np.empty(flat_shape, dtype=float)

            for i, rec in enumerate(records):
                sp_path = resolve_statepoint_path(rec["statepoint"])
                with openmc.StatePoint(str(sp_path)) as sp:
                    for tid in flat_data.keys():
                        tally = sp.tallies[tid]
                        mean_flat = tally.mean
                        std_flat = tally.std_dev
                        nd_shape = tally_shapes[tid]
                        mean_nd = mean_flat.reshape(nd_shape)
                        std_nd = std_flat.reshape(nd_shape)
                        flat_data[tid][i, ...] = mean_nd
                        flat_mc_std[tid][i, ...] = std_nd

            # reshape into extra_shape + nd_shape
            for tid, arr in flat_data.items():
                arr.shape = extra_shape + tally_shapes[tid]
                tmc_data[tid][...] = arr
            for tid, arr in flat_mc_std.items():
                arr.shape = extra_shape + tally_shapes[tid]
                tmc_mc_std[tid][...] = arr

        # ---- 6. Build xarray Dataset and write ----
        ds = xr.Dataset()

        for tid, arr in tmc_data.items():
            nd_shape = tally_shapes[tid]
            filters = tally_filters[tid]

            # Filter dims based on filter types
            filter_dims = []
            for f in filters:
                filter_type = type(f).__name__.replace("Filter", "").lower()
                filter_dims.append(filter_type)

            nuclide_dim = f"nuclide_{tid}"
            score_dim = f"score_{tid}"

            dims = extra_dims + tuple(filter_dims) + (nuclide_dim, score_dim)

            coords = dict(extra_coords)

            tally_name = tally_names[tid] or f"tally_{tid}"

            da = xr.DataArray(
                arr,
                dims=dims,
                coords=coords,
                name=tally_name,
            )

            da_mc_std = xr.DataArray(
                tmc_mc_std[tid],
                dims=dims,
                coords=coords,
                name=f"{tally_name}_mc_std",
            )

            da.attrs["tally_id"] = tid
            da.attrs["tally_name"] = tally_names[tid]
            da_mc_std.attrs["tally_id"] = tid
            da_mc_std.attrs["tally_name"] = tally_names[tid]

            axisinfo = tally_axisinfo[tid]
            for target_da in (da, da_mc_std):
                for k, v in axisinfo.items():
                    if isinstance(v, (int, float, bool, str, np.number)):
                        target_da.attrs[k] = v
                    else:
                        if isinstance(v, np.ndarray):
                            to_dump = v.tolist()
                        else:
                            to_dump = v
                        target_da.attrs[k] = json.dumps(to_dump)

            ds[da.name] = da
            ds[da_mc_std.name] = da_mc_std

        ds.to_netcdf(tmc_statepoint)
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