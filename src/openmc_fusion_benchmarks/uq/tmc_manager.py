from typing import List, Callable
from pathlib import Path
import openmc
import numpy as np
import json
import copy
import xarray as xr
import inspect
import itertools
import h5py


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

        # If file exists from a previous run, remove it so we can append groups cleanly
        if tmc_statepoint.exists():
            tmc_statepoint.unlink()

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

            # Infer per-dimension sizes from the data:
            indices_array = np.array([rec["indices"] for rec in records], dtype=int)
            # assume indices run from 0..(n_i-1) along each axis
            per_dim_sizes = indices_array.max(axis=0) + 1  # length per perturbation dim

            extra_shape = tuple(int(n) for n in per_dim_sizes)
            extra_dims = tuple(f"perturbation_{i}" for i in range(p))
            extra_coords = {dim: np.arange(n) for dim, n in zip(extra_dims, extra_shape)}

            n_combos = len(records)
            expected_combos = int(np.prod(extra_shape))
            if n_combos != expected_combos:
                raise RuntimeError(
                    f"Matrix TMC manifest has {n_combos} runs, but inferred grid shape "
                    f"{extra_shape} implies {expected_combos} combinations."
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

        # ---- 6. Build per-tally Datasets and write each into its own group ----

        # We'll use h5netcdf or netcdf4 so that group=... works.
        # Each tally_id gets a group: /tally_<tid>/ with variables: mean, mc_std.

        for tid, arr in tmc_data.items():
            nd_shape = tally_shapes[tid]
            filters = tally_filters[tid]
            axisinfo = tally_axisinfo[tid]

            # filter dims based on filter types
            filter_dims = []
            for f in filters:
                filter_type = type(f).__name__.replace("Filter", "").lower()
                filter_dims.append(filter_type)

            # within each tally group, we can use generic "nuclide" and "score"
            dims = extra_dims + tuple(filter_dims) + ("nuclide", "score")

            # coords: TMC dims
            coords = dict(extra_coords)

            # coords: nuclide / score for this tally
            nuclides = axisinfo["nuclides"]
            scores   = axisinfo["scores"]

            coords["nuclide"] = ("nuclide", np.array(nuclides, dtype="U"))
            coords["score"]   = ("score",   np.array(scores,   dtype="U"))

            # Per-tally dataset
            ds_tid = xr.Dataset()

            da_mean = xr.DataArray(
                arr,
                dims=dims,
                coords=coords,
                name="mean",
            )

            da_mc_std = xr.DataArray(
                tmc_mc_std[tid],
                dims=dims,
                coords=coords,
                name="mc_std",
            )

            # basic attrs
            tally_name = tally_names[tid] or f"tally_{tid}"
            for target_da in (da_mean, da_mc_std):
                target_da.attrs["tally_id"] = tid
                target_da.attrs["tally_name"] = tally_name

            # serialize complex axisinfo at dataset level
            for k, v in axisinfo.items():
                if isinstance(v, (int, float, bool, str, np.number)):
                    ds_tid.attrs[k] = v
                else:
                    if isinstance(v, np.ndarray):
                        to_dump = v.tolist()
                    else:
                        to_dump = v
                    ds_tid.attrs[k] = json.dumps(to_dump)

            ds_tid["mean"] = da_mean
            ds_tid["mc_std"] = da_mc_std

            group_name = f"tally_{tid}"

            # append this tally-dataset as a group in the same file
            ds_tid.to_netcdf(
                tmc_statepoint,
                mode="a",
                group=group_name,
                engine="h5netcdf",  # or "netcdf4"
            )

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


class TMCTally:
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
        self._da = mean_da
        self._da_mc_std = mc_std_da
        self._parent_ds = parent_ds

        # Identify TMC dimensions: "realization" for sequential, "perturbation_*" for matrix
        self._tmc_dims = [
            d for d in self._da.dims
            if d == "realization" or d.startswith("perturbation_")
        ]

    @property
    def id(self):
        """Tally ID."""
        return self._da.attrs.get("tally_id")

    @property
    def name(self):
        """Tally name."""
        return self._da.attrs.get("tally_name")

    # --- TMC statistics ---

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
    def realization_means(self):
        """
        Raw mean value for each TMC point (all TMC dims retained).
        Shape: (TMC dims..., filters..., nuclide, score).
        """
        return self._da.values

    @property
    def realization_stds(self):
        """
        Monte Carlo standard deviation for each run/combo.

        This is the statistical uncertainty from particle sampling within each
        individual OpenMC run, shaped like self._da.
        """
        if self._da_mc_std is not None:
            return self._da_mc_std.values

        # Fallback to zeros if not available
        return np.zeros_like(self._da.values)

    # --- Metadata & helpers ---

    @property
    def data(self):
        """Full TMC mean data array (all TMC entries)."""
        return self._da.values

    @property
    def scores(self):
        """List of score names."""
        # Preferred: from 'score' coordinate, if present
        if "score" in self._da.coords:
            return [str(s) for s in self._da.coords["score"].values]

        # Fallback: from parent_ds attrs "scores" (JSON)
        if self._parent_ds is not None:
            scores_json = self._parent_ds.attrs.get("scores")
            if scores_json:
                return json.loads(scores_json)
        # Last resort: from variable attrs (if you changed writer)
        scores_json = self._da.attrs.get("scores")
        if scores_json:
            return json.loads(scores_json)
        return []

    @property
    def nuclides(self):
        """List of nuclide names."""
        if "nuclide" in self._da.coords:
            return [str(n) for n in self._da.coords["nuclide"].values]

        if self._parent_ds is not None:
            nuclides_json = self._parent_ds.attrs.get("nuclides")
            if nuclides_json:
                return json.loads(nuclides_json)
        nuclides_json = self._da.attrs.get("nuclides")
        if nuclides_json:
            return json.loads(nuclides_json)
        return []

    @property
    def filters(self):
        """List of filter information (type and number of bins)."""
        if self._parent_ds is not None:
            filt_json = self._parent_ds.attrs.get("filter_axes")
            if filt_json:
                return json.loads(filt_json)
        filt_json = self._da.attrs.get("filter_axes")
        if filt_json:
            return json.loads(filt_json)
        return []

    @property
    def tmc_dims(self):
        """Names of TMC dimensions (realization / perturbation_*)."""
        return tuple(self._tmc_dims)

    @property
    def shape(self):
        """Shape of the underlying mean data array."""
        return self._da.shape

    @property
    def dims(self):
        """Dimension names of the underlying mean data array."""
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
            Filtered TMC mean data
        """
        da = self._da

        # Apply filter dimension selections (energy, cell, mesh, perturbation_x, etc.)
        if filter_kwargs:
            da = da.sel(**filter_kwargs)

        # Apply score selection
        if scores is not None and "score" in da.dims:
            all_scores = self.scores
            score_indices = [all_scores.index(s) for s in scores]
            da = da.isel(score=score_indices)

        # Apply nuclide selection
        if nuclides is not None and "nuclide" in da.dims:
            all_nuclides = self.nuclides
            nuclide_indices = [all_nuclides.index(n) for n in nuclides]
            da = da.isel(nuclide=nuclide_indices)

        return da

    def __repr__(self):
        return f"<TMCTally {self.id}: '{self.name}', shape={self.shape}>"