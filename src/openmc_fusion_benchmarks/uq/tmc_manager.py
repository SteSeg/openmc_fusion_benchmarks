from typing import List, Callable
from pathlib import Path
import openmc
import numpy as np
import json
import copy
import xarray as xr
import itertools
from .tmc_statepoint import TMCStatePoint
from ..validate_results import validate_tally_consistency


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

    def run(self, mode="matrix", cwd='.', benchmark_export=None, *args, **kwargs):

        cwd = Path(cwd).resolve()

        # Prepare TMC manifest file
        manifest = cwd / "tmc_manifest.jsonl"
        manifest.parent.mkdir(parents=True, exist_ok=True)

        # If file exists from a previous run, remove it
        if manifest.exists():
            manifest.unlink()

        p = len(self.perturbations)
        r = int(self.realizations)

        # --- Sequential mode: one perturbation active at a time, old behaviour ---
        if mode == "sequential":
            with manifest.open("a") as f_manifest:
                for p_idx, perturb in enumerate(self.perturbations):
                    for r_idx in range(r):
                        # fresh copy so perturbations do not accumulate
                        model_copy = copy.deepcopy(self.base_model)

                        # our current perturbations take (model, idx)
                        perturbed_model = perturb(model_copy, r_idx)

                        run_dir = cwd / "tmc" / f"perturbation_{p_idx}" / f"realization_{r_idx}"
                        run_dir.mkdir(parents=True, exist_ok=True)

                        sp_path = perturbed_model.run(cwd=run_dir, *args, **kwargs)
                        sp_path = Path(sp_path).resolve()

                        rec = {
                            "perturbation": int(p_idx),
                            "realization": int(r_idx),
                            "statepoint": str(sp_path.relative_to(cwd)),
                            # you can optionally add "mode": "sequential" if you like,
                            # but _process_tmc already detects this format
                        }
                        f_manifest.write(json.dumps(rec) + "\n")
                        f_manifest.flush()

            self._process_tmc(manifest_path=manifest, benchmark_export=benchmark_export)
            return

        # --- Matrix / diagonal modes share the same structure and manifest keys ---
        # Choose index iterator
        if mode == "matrix":
            # Full r^p Cartesian product
            index_iter = itertools.product(range(r), repeat=p)
        elif mode == "diagonal":
            # Main diagonal: (0,0,...,0), (1,1,...,1), ...
            index_iter = (tuple([k] * p) for k in range(r))
        else:
            raise ValueError(f"Unknown TMC mode {mode!r}")

        with manifest.open("a") as f_manifest:
            for idx_tuple in index_iter:
                # Copy base model
                perturbed_model = copy.deepcopy(self.base_model)

                # Apply all perturbations to the same model with their indices
                for perturb, ridx in zip(self.perturbations, idx_tuple):
                    perturbed_model = perturb(perturbed_model, ridx)

                # Directory name encoding the index tuple
                s = ".".join(map(str, idx_tuple))
                run_dir = cwd / "tmc" / f"perturbation_{s}"
                run_dir.mkdir(parents=True, exist_ok=True)

                # Run model
                sp_path = perturbed_model.run(cwd=run_dir, *args, **kwargs)
                sp_path = Path(sp_path).resolve()

                # Store statepoint path in manifest
                rec = {
                    "mode": mode,                  # "matrix" or "diagonal"
                    "indices": list(idx_tuple),    # [i0, i1, ..., i_{p-1}]
                    "statepoint": str(sp_path.relative_to(cwd)),
                }
                f_manifest.write(json.dumps(rec) + "\n")
                f_manifest.flush()

        # Postprocess the whole TMC set
        self._process_tmc(manifest_path=manifest, benchmark_export=benchmark_export)

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

    def _process_tmc(self, manifest_path="tmc_manifest.jsonl", benchmark_export=None):
        manifest_path = Path(manifest_path).resolve()
        tmc_dir = manifest_path.parent  # directory containing the manifest

        # xarray will write NetCDF (HDF5-backed); extension is up to you
        tmc_statepoint = tmc_dir / f"tmc_statepoint.{int(self.realizations)}.h5"

        # If file exists from a previous run, remove it so we can append groups cleanly
        if tmc_statepoint.exists():
            tmc_statepoint.unlink()

        benchmark_file = None
        benchmark_normalizer = None
        spec_lookup = {}
        if benchmark_export:
            benchmark_file = Path(benchmark_export.get("filename", "benchmark_results.h5"))
            if not benchmark_file.is_absolute():
                benchmark_file = (tmc_dir / benchmark_file).resolve()
            if benchmark_file.exists():
                benchmark_file.unlink()

            benchmark_normalizer = benchmark_export.get("normalizer")

            spec_tallies = benchmark_export.get("spec_tallies")
            if isinstance(spec_tallies, dict):
                spec_lookup = spec_tallies
            elif spec_tallies is not None:
                for entry in spec_tallies:
                    if isinstance(entry, dict) and entry.get("name"):
                        spec_lookup[str(entry["name"])] = entry

        # ---- helper: resolve statepoint path robustly ----
        def _normalize_filter_type(type_name: str) -> str:
            name = str(type_name).strip().lower()
            if name.endswith("filter"):
                name = name[:-6]
            return name

        def _unique_filter_dims(filters):
            counts = {}
            dims = []
            for flt in filters:
                base = type(flt).__name__.replace("Filter", "").lower() or "filter"
                idx = counts.get(base, 0)
                counts[base] = idx + 1
                dims.append(base if idx == 0 else f"{base}_{idx}")
            return dims

        def _serialize_filter_bins(flt):
            bins = flt.bins
            arr = np.asarray(bins)

            if isinstance(flt, openmc.EnergyFilter):
                if arr.ndim == 1:
                    return arr.tolist()
                if arr.ndim == 2 and arr.shape[1] == 2:
                    low = arr[:, 0]
                    high = arr[:, 1]
                    if low.size == 0:
                        return []
                    return np.concatenate([low[:1], high]).tolist()
                return arr.reshape(-1).tolist()

            if arr.ndim <= 1:
                return arr.tolist()

            return [list(np.asarray(b).tolist()) for b in bins]

        def _build_filter_axis_metadata(filters, filter_dims):
            axes = []
            for flt, dim in zip(filters, filter_dims):
                ftype = _normalize_filter_type(type(flt).__name__)
                axis_meta = {
                    "name": type(flt).__name__,
                    "axis": dim,
                    "num_bins": int(flt.num_bins),
                    "bins": _serialize_filter_bins(flt),
                }
                if ftype == "energy":
                    axis_meta["kind"] = "edges"
                    axis_meta["units"] = "eV"
                    axis_meta["closure"] = "[low, high)"
                axes.append(axis_meta)
            return axes

        def _safe_group_name(name: str, tid: int, used: set[str]) -> str:
            base = (name or "").strip()
            if not base:
                candidate = f"tally_{int(tid)}"
            else:
                # Avoid creating nested paths in HDF groups.
                candidate = base.replace("/", "_")

            if candidate not in used:
                used.add(candidate)
                return candidate

            with_id = f"{candidate}__{int(tid)}"
            if with_id not in used:
                used.add(with_id)
                return with_id

            i = 1
            while True:
                alt = f"{with_id}_{i}"
                if alt not in used:
                    used.add(alt)
                    return alt
                i += 1

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

        # Detect mode: sequential vs diagonal vs matrix
        first_rec = records[0]
        if "indices" in first_rec:
            # new: allow explicit "mode" in manifest for diagonal vs full matrix
            mode = first_rec.get("mode", "matrix")  # default to matrix if not specified
        elif "perturbation" in first_rec and "realization" in first_rec:
            mode = "sequential"
        else:
            raise RuntimeError("Unrecognized manifest record format")

        # ---- 2. Sort & index logic depending on mode ----
        if mode == "sequential":
            # sort by (perturbation, realization)
            records.sort(key=lambda r: (r["perturbation"], r["realization"]))
            
            # Infer number of perturbations and realizations
            n_perturbations = max(r["perturbation"] for r in records) + 1
            n_realizations = max(r["realization"] for r in records) + 1
            
            # Verify we have complete data
            expected_total = n_perturbations * n_realizations
            if len(records) != expected_total:
                raise RuntimeError(
                    f"Sequential TMC manifest has {len(records)} runs, but inferred "
                    f"{n_perturbations} perturbations × {n_realizations} realizations = {expected_total}"
                )
            
            extra_shape = (n_perturbations, n_realizations)
            extra_dims = ("perturbation", "realization")
            extra_coords = {
                "perturbation": np.arange(n_perturbations),
                "realization": np.arange(n_realizations)
            }

        elif mode == "diagonal":
            # Diagonal matrix mode: indices are present but we treat them as a 1D TMC dim
            # e.g. idx_tuple = (k, k, ..., k) for k in range(realizations)
            records.sort(key=lambda r: tuple(r["indices"]))
            n_points = len(records)
            extra_shape = (n_points,)
            extra_dims = ("realization",)
            extra_coords = {"realization": np.arange(n_points)}

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

                filter_dims = _unique_filter_dims(filters)
                filter_axes = _build_filter_axis_metadata(filters, filter_dims)
                scores = [str(s) for s in tally.scores]
                nuclides = [str(n) for n in tally.nuclides] if tally.nuclides else ["total"]

                axis_info = {
                    "filter_dims": filter_dims,
                    "filter_axes": filter_axes,
                    "nuclides": nuclides,
                    "scores": scores,
                }

                tally_axisinfo[tid] = axis_info

        # ---- 4. Allocate arrays: one per tally ----
        tmc_data = {}    # tid -> ndarray (extra_shape + nd_shape)
        tmc_mc_std = {}  # tid -> ndarray (extra_shape + nd_shape)
        benchmark_data = {}
        benchmark_mc_std = {}

        for tid, nd_shape in tally_shapes.items():
            full_shape = extra_shape + nd_shape
            tmc_data[tid] = np.empty(full_shape, dtype=float)
            tmc_mc_std[tid] = np.empty(full_shape, dtype=float)
            if benchmark_file is not None:
                benchmark_data[tid] = np.empty(full_shape, dtype=float)
                benchmark_mc_std[tid] = np.empty(full_shape, dtype=float)

        # ---- 5. Fill arrays by looping over statepoints ----
        if mode == "sequential":
            # 2D structure: (perturbation, realization)
            for rec in records:
                sp_path = resolve_statepoint_path(rec["statepoint"])
                with openmc.StatePoint(str(sp_path)) as sp:
                    for tid in tmc_data.keys():
                        tally = sp.tallies[tid]
                        mean_flat = tally.mean
                        std_flat = tally.std_dev
                        nd_shape = tally_shapes[tid]
                        mean_nd = mean_flat.reshape(nd_shape)
                        std_nd = std_flat.reshape(nd_shape)
                        p_idx = rec["perturbation"]
                        r_idx = rec["realization"]
                        tmc_data[tid][p_idx, r_idx, ...] = mean_nd
                        tmc_mc_std[tid][p_idx, r_idx, ...] = std_nd
                        if benchmark_file is not None:
                            if benchmark_normalizer is not None:
                                b_mean, b_std = benchmark_normalizer(tally, mean_nd.copy(), std_nd.copy())
                            else:
                                b_mean, b_std = mean_nd, std_nd
                            benchmark_data[tid][p_idx, r_idx, ...] = b_mean
                            benchmark_mc_std[tid][p_idx, r_idx, ...] = b_std

        elif mode == "diagonal":
            # 1D structure: one "realization" dim
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
                        if benchmark_file is not None:
                            if benchmark_normalizer is not None:
                                b_mean, b_std = benchmark_normalizer(tally, mean_nd.copy(), std_nd.copy())
                            else:
                                b_mean, b_std = mean_nd, std_nd
                            benchmark_data[tid][i, ...] = b_mean
                            benchmark_mc_std[tid][i, ...] = b_std

        else:  # mode == "matrix"
            # Fill as flat (n_combos, ...) then reshape first axis into extra_shape
            n_combos = len(records)
            flat_data = {}
            flat_mc_std = {}
            flat_benchmark_data = {}
            flat_benchmark_mc_std = {}
            for tid, nd_shape in tally_shapes.items():
                flat_shape = (n_combos,) + nd_shape
                flat_data[tid] = np.empty(flat_shape, dtype=float)
                flat_mc_std[tid] = np.empty(flat_shape, dtype=float)
                if benchmark_file is not None:
                    flat_benchmark_data[tid] = np.empty(flat_shape, dtype=float)
                    flat_benchmark_mc_std[tid] = np.empty(flat_shape, dtype=float)

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
                        if benchmark_file is not None:
                            if benchmark_normalizer is not None:
                                b_mean, b_std = benchmark_normalizer(tally, mean_nd.copy(), std_nd.copy())
                            else:
                                b_mean, b_std = mean_nd, std_nd
                            flat_benchmark_data[tid][i, ...] = b_mean
                            flat_benchmark_mc_std[tid][i, ...] = b_std

            # reshape into extra_shape + nd_shape
            for tid, arr in flat_data.items():
                arr.shape = extra_shape + tally_shapes[tid]
                tmc_data[tid][...] = arr
            for tid, arr in flat_mc_std.items():
                arr.shape = extra_shape + tally_shapes[tid]
                tmc_mc_std[tid][...] = arr
            if benchmark_file is not None:
                for tid, arr in flat_benchmark_data.items():
                    arr.shape = extra_shape + tally_shapes[tid]
                    benchmark_data[tid][...] = arr
                for tid, arr in flat_benchmark_mc_std.items():
                    arr.shape = extra_shape + tally_shapes[tid]
                    benchmark_mc_std[tid][...] = arr

        # ---- 6. Build per-tally Datasets and write each into its own group ----

        used_group_names = set()

        for tid, arr in tmc_data.items():
            nd_shape = tally_shapes[tid]
            filters = tally_filters[tid]
            axisinfo = tally_axisinfo[tid]

            # filter dims based on filter types (stable + unique)
            filter_dims = list(axisinfo["filter_dims"])

            # within each tally group, we can use generic "nuclide" and "score"
            dims = extra_dims + tuple(filter_dims) + ("nuclide", "score")

            # coords: TMC dims
            coords = dict(extra_coords)

            # coords: filter dimensions (add integer indices for each filter)
            for i, (f, fdim) in enumerate(zip(filters, filter_dims)):
                coords[fdim] = (fdim, np.arange(f.num_bins))

            # coords: nuclide / score for this tally
            nuclides = axisinfo["nuclides"]
            scores = axisinfo["scores"]

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

            observed_tally = {
                "name": tally_name,
                "id": int(tid),
                "filters": axisinfo["filter_axes"],
                "scores": scores,
                "nuclides": nuclides,
            }

            ds_tid.attrs["filter_axes"] = json.dumps(axisinfo["filter_axes"])
            ds_tid.attrs["nuclides"] = json.dumps(nuclides)
            ds_tid.attrs["scores"] = json.dumps(scores)
            ds_tid.attrs["observed_tally"] = json.dumps(observed_tally)

            # serialize complex axisinfo at dataset level
            for k, v in axisinfo.items():
                if k in {"filter_axes", "nuclides", "scores"}:
                    # Canonical copies already written above.
                    continue
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

            group_name = _safe_group_name(tally_name, tid, used_group_names)
            ds_tid.attrs["group"] = group_name
            ds_tid["mean"].attrs["tally_group"] = group_name
            ds_tid["mc_std"].attrs["tally_group"] = group_name

            # append this tally-dataset as a group in the same file
            ds_tid.to_netcdf(
                tmc_statepoint,
                mode="a",
                group=group_name,
                engine="h5netcdf",  # or "netcdf4"
            )

            if benchmark_file is not None:
                da_mean_b = xr.DataArray(
                    benchmark_data[tid],
                    dims=dims,
                    coords=coords,
                    name="mean",
                )
                da_mc_std_b = xr.DataArray(
                    benchmark_mc_std[tid],
                    dims=dims,
                    coords=coords,
                    name="mc_std",
                )

                for target_da in (da_mean_b, da_mc_std_b):
                    target_da.attrs["tally_id"] = tid
                    target_da.attrs["tally_name"] = tally_name
                    target_da.attrs["tally_group"] = group_name

                ds_b = xr.Dataset(
                    {
                        "mean": da_mean_b,
                        "mc_std": da_mc_std_b,
                    }
                )
                ds_b.attrs["filter_axes"] = json.dumps(axisinfo["filter_axes"])
                ds_b.attrs["nuclides"] = json.dumps(nuclides)
                ds_b.attrs["scores"] = json.dumps(scores)
                ds_b.attrs["observed_tally"] = json.dumps(observed_tally)
                ds_b.attrs["group"] = group_name

                spec_tally = spec_lookup.get(str(tally_name))
                if spec_tally is not None:
                    ds_b.attrs["spec_tally"] = json.dumps(spec_tally)
                    consistent, issues = validate_tally_consistency(spec_tally, observed_tally)
                    ds_b.attrs["spec_consistent"] = int(bool(consistent))
                    ds_b.attrs["spec_consistency_issues"] = json.dumps(issues)

                mode_write = "a" if benchmark_file.exists() else "w"
                ds_b.to_netcdf(
                    benchmark_file,
                    mode=mode_write,
                    group=group_name,
                    engine="h5netcdf",
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