from typing import List, Callable
from pathlib import Path

from numpy import rec
import openmc
import numpy as np
import json
import copy
import xarray as xr
import inspect
import itertools
import h5py

from ..tallies import BaseTally
from ..backends.openmc.tallies import openmc_tally_to_dataset


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

    def run(self, mode="diagonal", cwd='.', *args, **kwargs):

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
                        perturbed_model = perturb(model_copy, r_idx, stream="A")

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

            self._process_tmc(manifest_path=manifest)
            return

        if mode == "pick-freeze":
            with manifest.open("a") as f_manifest:

                # Generate A realizations
                for r_idx in range(r):
                    model_copy = copy.deepcopy(self.base_model)

                    for perturb in self.perturbations:
                        model_copy = perturb(model_copy, r_idx, stream="A")

                    run_dir = cwd / "tmc" / f"A_{r_idx}"
                    run_dir.mkdir(parents=True, exist_ok=True)

                    sp_path = model_copy.run(cwd=run_dir, *args, **kwargs)
                    sp_path = Path(sp_path).resolve()

                    rec = {
                        "mode": "pick-freeze",
                        "set": "A",
                        "index": int(r_idx),
                        "statepoint": str(sp_path.relative_to(cwd)),
                    }
                    f_manifest.write(json.dumps(rec) + "\n")
                    f_manifest.flush()

                # Generate B realizations
                for r_idx in range(r):
                    model_copy = copy.deepcopy(self.base_model)

                    for perturb in self.perturbations:
                        model_copy = perturb(model_copy, r_idx, stream="B")

                    run_dir = cwd / "tmc" / f"B_{r_idx}"
                    run_dir.mkdir(parents=True, exist_ok=True)

                    sp_path = model_copy.run(cwd=run_dir, *args, **kwargs)
                    sp_path = Path(sp_path).resolve()

                    rec = {
                        "mode": "pick-freeze",
                        "set": "B",
                        "index": int(r_idx),
                        "statepoint": str(sp_path.relative_to(cwd)),
                    }
                    f_manifest.write(json.dumps(rec) + "\n")
                    f_manifest.flush()

                                # Generate AB pick-freeze realizations
                for p_idx in range(p):
                    for r_idx in range(r):
                        model_copy = copy.deepcopy(self.base_model)

                        for i_idx, perturb in enumerate(self.perturbations):
                            stream = "B" if i_idx == p_idx else "A"
                            model_copy = perturb(
                                model_copy,
                                r_idx,
                                stream=stream
                            )

                        run_dir = cwd / "tmc" / f"AB_{p_idx}_{r_idx}"
                        run_dir.mkdir(parents=True, exist_ok=True)

                        sp_path = model_copy.run(
                            cwd=run_dir, *args, **kwargs
                        )
                        sp_path = Path(sp_path).resolve()

                        rec = {
                            "mode": "pick-freeze",
                            "set": "AB",
                            "perturbation": int(p_idx),
                            "index": int(r_idx),
                            "statepoint": str(sp_path.relative_to(cwd)),
                        }
                        f_manifest.write(json.dumps(rec) + "\n")
                        f_manifest.flush()

            self._process_tmc(manifest_path=manifest)
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
                    perturbed_model = perturb(perturbed_model, ridx, stream="A")

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
        self._process_tmc(manifest_path=manifest)

    def _build_indexed_perturbations(self, user_factories):
        """
        Wrap user perturbation factories into indexed perturb(model, idx, stream)
        functions.

        stream="A" is the default and preserves existing behavior.
        """
        # Use a SeedSequence hierarchy for robust, collision-resistant child
        # seeds. This produces deterministic, well-spaced child sequences and
        # is preferable to simple additive seed arithmetic.
        indexed = []

        # Draw an integer master seed from the master RNG so we can create a
        # reproducible SeedSequence root. Store it on the instance for
        # provenance and later recording in the tmc_statepoint metadata.
        master_seed = int(self.master_rng.integers(0, 2**31))
        self._rng_master_seed = int(master_seed)
        ss_master = np.random.SeedSequence(master_seed)

        # For each user factory spawn two base sequences (A and B) and then
        # spawn per-realization children so the wrapper can index directly by
        # `idx` without dynamically spawning at call time.
        for factory in user_factories:
            inner = factory()

            ss_A_base, ss_B_base = ss_master.spawn(2)

            # Spawn per-realization child sequences using the configured
            # `self.realizations` so each (perturbation, realization) has a
            # dedicated SeedSequence.
            ss_A_children = ss_A_base.spawn(int(self.realizations))
            ss_B_children = ss_B_base.spawn(int(self.realizations))

            def make_wrapper(inner_func, ss_A_children, ss_B_children):
                def perturb(model, idx, stream="A"):
                    if stream == "A":
                        child_ss = ss_A_children[int(idx)]
                    elif stream == "B":
                        child_ss = ss_B_children[int(idx)]
                    else:
                        raise ValueError(f"Unknown perturbation stream: {stream!r}")

                    # Construct a Generator from the child SeedSequence.
                    local_rng = np.random.default_rng(child_ss)

                    return inner_func(model, local_rng)

                return perturb

            indexed.append(
                make_wrapper(inner, ss_A_children, ss_B_children)
            )

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

        # Detect mode: sequential vs diagonal vs matrix vs pick-freeze
        # Do not rely on manifest ordering; inspect records to decide.
        mode = None
        # Prefer explicit pick-freeze marker
        if any(rec.get("mode") == "pick-freeze" for rec in records):
            mode = "pick-freeze"
        # Next prefer records with explicit indices (matrix/diagonal)
        elif any("indices" in rec for rec in records):
            # Use mode field if present (matrix/diagonal), default to matrix
            rec_with_indices = next(rec for rec in records if "indices" in rec)
            mode = rec_with_indices.get("mode", "matrix")
        # Next prefer sequential-style records with perturbation+realization
        elif any(("perturbation" in rec and "realization" in rec) for rec in records):
            mode = "sequential"
        else:
            raise RuntimeError("Unrecognized manifest record format")

        # Persist the detected mode for downstream consumers
        with h5py.File(tmc_statepoint, "a") as h5f:
            h5f.attrs["tmc_mode"] = mode
            # Record RNG provenance so results can be reproduced later.
            try:
                h5f.attrs["rng_scheme"] = "seedsequence"
                if hasattr(self, "_rng_master_seed"):
                    h5f.attrs["rng_master_seed"] = int(self._rng_master_seed)
            except Exception:
                # Best-effort metadata: ignore failures to write attrs
                pass
        # Remember last produced TMC statepoint path for callers of get_tmc_statepoint()
        try:
            # Store resolved Path on the manager instance
            self.tmc_statepoint_path = Path(tmc_statepoint).resolve()
        except Exception:
            # Best-effort: ignore failures to set the attribute
            pass

        # ---- 2. Sort & index logic depending on mode ----
        # Choose a stable reference record for extracting tally templates
        # (do not assume records[0] is representative)
        if mode == "pick-freeze":
            reference_rec = next((rec for rec in records if rec.get("set") == "AB"), records[0])
        elif mode in ("matrix", "diagonal"):
            reference_rec = next((rec for rec in records if "indices" in rec), records[0])
        elif mode == "sequential":
            reference_rec = next((rec for rec in records if "perturbation" in rec and "realization" in rec), records[0])
        else:
            reference_rec = records[0]

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
                "realization": np.arange(n_realizations),
            }

        elif mode == "diagonal":
            # Diagonal matrix mode: indices are present but we treat them as a 1D TMC dim
            # e.g. idx_tuple = (k, k, ..., k) for k in range(realizations)
            records.sort(key=lambda r: tuple(r["indices"]))
            n_points = len(records)
            extra_shape = (n_points,)
            extra_dims = ("realization",)
            extra_coords = {"realization": np.arange(n_points)}

        elif mode == "matrix":
            # each record: {"indices": [i0, i1, ..., i_{p-1}], "statepoint": ...}
            # sort lexicographically by indices
            records.sort(key=lambda r: tuple(r["indices"]))

            # number of perturbations = length of indices
            p = len(reference_rec["indices"])

            # Infer per-dimension sizes from the data:
            indices_array = np.array([rec["indices"] for rec in records], dtype=int)
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
            
        elif mode == "pick-freeze":
            # records: {"set": "A"|"B"|"AB", "index": int, "perturbation": int (for AB), "statepoint": ...}
            A_records = [rec for rec in records if rec.get("set") == "A"]
            B_records = [rec for rec in records if rec.get("set") == "B"]
            AB_records = [rec for rec in records if rec.get("set") == "AB"]

            # Infer number of realizations from A/B
            n_realizations = max(
                rec["index"] for rec in A_records + B_records
            ) + 1

            # Infer number of perturbations from AB
            n_perturbations = max(
                rec["perturbation"] for rec in AB_records
            ) + 1

            # Validate completeness
            if len(A_records) != n_realizations:
                raise RuntimeError("Incomplete A set")

            if len(B_records) != n_realizations:
                raise RuntimeError("Incomplete B set")

            expected_AB = n_perturbations * n_realizations
            if len(AB_records) != expected_AB:
                raise RuntimeError(
                    f"Pick-freeze AB set has {len(AB_records)} runs, "
                    f"expected {expected_AB}"
                )

            A_records.sort(key=lambda rec: rec["index"])
            B_records.sort(key=lambda rec: rec["index"])
            AB_records.sort(
                key=lambda rec: (rec["perturbation"], rec["index"])
            )


        # ---- 3. Use reference record's statepoint as reference for tallies ----
        first_sp_path = resolve_statepoint_path(reference_rec["statepoint"])
        tally_names = {}       # tid -> name
        tally_shapes = {}      # tid -> nd_shape (filters..., nuclide, score)
        tally_templates = {}   # tid -> xarray.Dataset template
        tally_dims = {}        # tid -> tuple of dims (filters..., nuclide, score)
        tally_coords = {}      # tid -> dim -> coord values

        with openmc.StatePoint(str(first_sp_path)) as sp0:
            for tally in sp0.tallies.values():
                tid = tally.id

                ds_template = openmc_tally_to_dataset(tally)
                da_template = ds_template["mean"]

                tally_names[tid] = tally.name
                tally_shapes[tid] = tuple(int(s) for s in da_template.shape)
                tally_templates[tid] = ds_template
                tally_dims[tid] = tuple(da_template.dims)
                tally_coords[tid] = {
                    dim: np.asarray(da_template.coords[dim].values)
                    for dim in da_template.dims
                }

        # ---- 4. Allocate arrays: one per tally ----
        tmc_data = {}    # tid -> ndarray (extra_shape + nd_shape)
        tmc_mc_std = {}  # tid -> ndarray (extra_shape + nd_shape)

        pf_data = {}
        pf_mc_std = {}

        if mode == "pick-freeze":
            for tid, nd_shape in tally_shapes.items():
                pf_data[tid] = {
                    "A": np.empty((n_realizations,) + nd_shape, dtype=float),
                    "B": np.empty((n_realizations,) + nd_shape, dtype=float),
                    "AB": np.empty(
                        (n_perturbations, n_realizations) + nd_shape,
                        dtype=float,
                    ),
                }

                pf_mc_std[tid] = {
                    "A": np.empty((n_realizations,) + nd_shape, dtype=float),
                    "B": np.empty((n_realizations,) + nd_shape, dtype=float),
                    "AB": np.empty(
                        (n_perturbations, n_realizations) + nd_shape,
                        dtype=float,
                    ),
                }

        # Allocate the standard TMC arrays only for non-pick-freeze modes.
        # Pick-freeze uses the separate `pf_data` / `pf_mc_std` structures above,
        # so we avoid referencing `extra_shape` which is undefined for pick-freeze.
        if mode != "pick-freeze":
            for tid, nd_shape in tally_shapes.items():
                full_shape = extra_shape + nd_shape
                tmc_data[tid] = np.empty(full_shape, dtype=float)
                tmc_mc_std[tid] = np.empty(full_shape, dtype=float)

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

        elif mode == "matrix":
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

        elif mode == "pick-freeze":
            for rec in records:
                sp_path = resolve_statepoint_path(rec["statepoint"])

                with openmc.StatePoint(str(sp_path)) as sp:
                    for tid in pf_data.keys():
                        tally = sp.tallies[tid]

                        nd_shape = tally_shapes[tid]
                        mean_nd = tally.mean.reshape(nd_shape)
                        std_nd = tally.std_dev.reshape(nd_shape)

                        if rec["set"] == "A":
                            r_idx = rec["index"]

                            pf_data[tid]["A"][r_idx, ...] = mean_nd
                            pf_mc_std[tid]["A"][r_idx, ...] = std_nd

                        elif rec["set"] == "B":
                            r_idx = rec["index"]

                            pf_data[tid]["B"][r_idx, ...] = mean_nd
                            pf_mc_std[tid]["B"][r_idx, ...] = std_nd

                        elif rec["set"] == "AB":
                            p_idx = rec["perturbation"]
                            r_idx = rec["index"]

                            pf_data[tid]["AB"][p_idx, r_idx, ...] = mean_nd
                            pf_mc_std[tid]["AB"][p_idx, r_idx, ...] = std_nd

                        else:
                            raise RuntimeError(f"Unknown pick-freeze set: {rec['set']!r}")

        # ---- 6. Build per-tally Datasets and write each into its own group ----

        if mode == "pick-freeze":

            for tid in pf_data:
                template = tally_templates[tid]
                template_dims = tally_dims[tid]

                tally_name = tally_names[tid] or f"tally_{tid}"

                # ==========================================================
                # A ensemble
                # Shape:
                #   (realization, tally_dims...)
                # ==========================================================
                A_dims_full = ("realization",) + template_dims

                A_coords = {
                    "realization": np.arange(n_realizations),
                }

                for dim in template_dims:
                    A_coords[dim] = (
                        dim,
                        tally_coords[tid][dim],
                    )

                ds_A = xr.Dataset(
                    {
                        "mean": xr.DataArray(
                            pf_data[tid]["A"],
                            dims=A_dims_full,
                            coords=A_coords,
                            name="mean",
                        ),
                        "mc_std": xr.DataArray(
                            pf_mc_std[tid]["A"],
                            dims=A_dims_full,
                            coords=A_coords,
                            name="mc_std",
                        ),
                    }
                )

                # ==========================================================
                # B ensemble
                # Shape:
                #   (realization, tally_dims...)
                # ==========================================================
                B_dims_full = ("realization",) + template_dims

                B_coords = {
                    "realization": np.arange(n_realizations),
                }

                for dim in template_dims:
                    B_coords[dim] = (
                        dim,
                        tally_coords[tid][dim],
                    )

                ds_B = xr.Dataset(
                    {
                        "mean": xr.DataArray(
                            pf_data[tid]["B"],
                            dims=B_dims_full,
                            coords=B_coords,
                            name="mean",
                        ),
                        "mc_std": xr.DataArray(
                            pf_mc_std[tid]["B"],
                            dims=B_dims_full,
                            coords=B_coords,
                            name="mc_std",
                        ),
                    }
                )

                # ==========================================================
                # AB ensemble
                # Shape:
                #   (perturbation, realization, tally_dims...)
                # ==========================================================
                AB_dims_full = (
                    "perturbation",
                    "realization",
                ) + template_dims

                AB_coords = {
                    "perturbation": np.arange(n_perturbations),
                    "realization": np.arange(n_realizations),
                }

                for dim in template_dims:
                    AB_coords[dim] = (
                        dim,
                        tally_coords[tid][dim],
                    )

                ds_AB = xr.Dataset(
                    {
                        "mean": xr.DataArray(
                            pf_data[tid]["AB"],
                            dims=AB_dims_full,
                            coords=AB_coords,
                            name="mean",
                        ),
                        "mc_std": xr.DataArray(
                            pf_mc_std[tid]["AB"],
                            dims=AB_dims_full,
                            coords=AB_coords,
                            name="mc_std",
                        ),
                    }
                )

                # ==========================================================
                # Metadata
                # ==========================================================
                for ds in (ds_A, ds_B, ds_AB):

                    for variable in ("mean", "mc_std"):
                        ds[variable].attrs["tally_id"] = tid
                        ds[variable].attrs["tally_name"] = tally_name

                    # Copy metadata from the original tally template
                    for key, value in template.attrs.items():
                        ds.attrs[key] = value

                # Explicitly record the pick-freeze ensemble
                ds_A.attrs["pick_freeze_set"] = "A"
                ds_B.attrs["pick_freeze_set"] = "B"
                ds_AB.attrs["pick_freeze_set"] = "AB"

                # ==========================================================
                # Write A, B and AB as separate groups
                # ==========================================================
                ds_A.to_netcdf(
                    tmc_statepoint,
                    mode="a",
                    group=f"tally_{tid}/A",
                    engine="h5netcdf",
                )

                ds_B.to_netcdf(
                    tmc_statepoint,
                    mode="a",
                    group=f"tally_{tid}/B",
                    engine="h5netcdf",
                )

                ds_AB.to_netcdf(
                    tmc_statepoint,
                    mode="a",
                    group=f"tally_{tid}/AB",
                    engine="h5netcdf",
                )

        else:
            # ==============================================================
            # Existing sequential / diagonal / matrix writing
            # ==============================================================
            for tid, arr in tmc_data.items():

                template = tally_templates[tid]
                template_dims = tally_dims[tid]

                dims = extra_dims + template_dims

                coords = dict(extra_coords)

                for dim in template_dims:
                    coords[dim] = (
                        dim,
                        tally_coords[tid][dim],
                    )

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

                # Basic metadata
                tally_name = tally_names[tid] or f"tally_{tid}"

                for target_da in (da_mean, da_mc_std):
                    target_da.attrs["tally_id"] = tid
                    target_da.attrs["tally_name"] = tally_name

                # Copy dataset-level metadata from template
                for key, value in template.attrs.items():
                    ds_tid.attrs[key] = value

                ds_tid["mean"] = da_mean
                ds_tid["mc_std"] = da_mc_std

                group_name = f"tally_{tid}"

                ds_tid.to_netcdf(
                    tmc_statepoint,
                    mode="a",
                    group=group_name,
                    engine="h5netcdf",
                )

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
        self._tmc_mode = None

    @property
    def tmc_mode(self):
        """TMC mode recorded in the statepoint file (sequential, matrix, diagonal)."""
        if self._tmc_mode is None:
            with h5py.File(self.path, "r") as h5f:
                raw = h5f.attrs.get("tmc_mode")
            # h5py can return bytes or numpy scalar types for attributes; normalize to str
            if isinstance(raw, (bytes, bytearray)):
                self._tmc_mode = raw.decode("utf-8")
            else:
                # covers str and numpy.string_ / numpy.str_
                self._tmc_mode = str(raw) if raw is not None else None
        return self._tmc_mode

    @property
    def tallies(self):
        """Dictionary of tallies, indexed by tally ID."""
        if self._tallies is None:
            self._tallies = {}

            with h5py.File(self.path, "r") as f:

                for group_name in f.keys():
                    if not group_name.startswith("tally_"):
                        continue

                    # Extract tally ID
                    try:
                        tally_id = int(group_name.split("_", 1)[1])
                    except Exception:
                        continue

                    # --------------------------------------------------
                    # Pick-freeze: tally_<id>/{A,B,AB}
                    # --------------------------------------------------
                    if self.tmc_mode == "pick-freeze":

                        ds_A = xr.open_dataset(
                            self.path,
                            group=f"{group_name}/A",
                            engine="h5netcdf",
                        )

                        ds_B = xr.open_dataset(
                            self.path,
                            group=f"{group_name}/B",
                            engine="h5netcdf",
                        )

                        ds_AB = xr.open_dataset(
                            self.path,
                            group=f"{group_name}/AB",
                            engine="h5netcdf",
                        )

                        self._tallies[tally_id] = TMCTally(
                            mean_da=ds_AB["mean"],
                            mc_std_da=ds_AB.get("mc_std"),
                            parent_ds=ds_AB,
                            A_da=ds_A["mean"],
                            B_da=ds_B["mean"],
                            A_mc_std_da=ds_A.get("mc_std"),
                            B_mc_std_da=ds_B.get("mc_std"),
                            A_parent_ds=ds_A,
                            B_parent_ds=ds_B,
                            AB_parent_ds=ds_AB,
                            mode=self.tmc_mode,
                        )

                    # --------------------------------------------------
                    # Existing modes: tally_<id>
                    # --------------------------------------------------
                    else:

                        ds = xr.open_dataset(
                            self.path,
                            group=group_name,
                            engine="h5netcdf",
                        )

                        if "mean" not in ds:
                            continue

                        da_mean = ds["mean"]
                        da_mc_std = ds["mc_std"] if "mc_std" in ds else None

                        self._tallies[tally_id] = TMCTally(
                            da_mean,
                            da_mc_std,
                            parent_ds=ds,
                            AB_parent_ds=ds,
                            mode=self.tmc_mode,
                        )

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
        # Close any cached xarray Dataset objects opened in `tallies`.
        if self._tallies is None:
            return
        for tally in list(self._tallies.values()):
            try:
                # Prefer tally-managed close if available
                close_fn = getattr(tally, "close", None)
                if callable(close_fn):
                    close_fn()
                else:
                    parent_ds = getattr(tally, "_parent_ds", None)
                    if parent_ds is not None:
                        try:
                            parent_ds.close()
                        except Exception:
                            pass
            except Exception:
                # best-effort close; ignore any issues
                pass
        # Clear the cache
        self._tallies = None

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
        mode = self.tmc_mode or "unknown"
        return f"<TMCStatePoint: mode={mode}, {n_realizations} TMC combinations, {n_tallies} tallies>"


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

    def __init__(
        self,
        mean_da,
        mc_std_da=None,
        parent_ds=None,
        A_da=None,
        B_da=None,
        A_mc_std_da=None,
        B_mc_std_da=None,
        mode=None,
        A_parent_ds=None,
        B_parent_ds=None,
        AB_parent_ds=None,
    ):
        super().__init__(
            mean_da,
            mc_std_da=mc_std_da,
            parent_ds=parent_ds,
        )

        self._A_da = A_da
        self._B_da = B_da
        self._A_mc_std_da = A_mc_std_da
        self._B_mc_std_da = B_mc_std_da
        self._mode = mode
        # Keep references to parent datasets so their file handles remain
        # open for as long as the TMCTally is in use. These are closed by
        # `TMCStatePoint.close()` via `TMCTally.close()`.
        self._A_parent_ds = A_parent_ds
        self._B_parent_ds = B_parent_ds
        # AB / main parent dataset - may also be present in _parent_ds
        self._AB_parent_ds = AB_parent_ds

        self._tmc_dims = [
            d for d in self._da.dims
            if d in ("perturbation", "realization")
            or d.startswith("perturbation_")
        ]

    @property
    def id(self):
        """Tally ID."""
        return self._da.attrs.get("tally_id")

    @property
    def name(self):
        """Tally name."""
        return self._da.attrs.get("tally_name")

    @property
    def mode(self):
        """TMC execution mode for this tally (sequential, diagonal, matrix, pick-freeze)."""
        return self._mode

    @property
    def ensemble_views(self):
        """Return mode-specific ensemble views as a dictionary, if present."""
        views = {}
        if self.mode == "pick-freeze":
            if self._A_da is not None:
                views["A"] = self._A_da
            if self._B_da is not None:
                views["B"] = self._B_da
            if self._da is not None:
                views["AB"] = self._da
            return views

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

    # --- Pick-freeze ensembles ---
    @property
    def A(self):
        return None if self._A_da is None else self._A_da.values

    @property
    def B(self):
        return None if self._B_da is None else self._B_da.values

    @property
    def AB(self):
        return self._da.values
    
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
        Mean value for each perturbation type, with mode-aware marginalization.

        - sequential: average over realizations, keeping separate perturbation entries
        - diagonal: collapse the single realization axis
        - matrix: marginalize each perturbation axis separately and stack the results
        - pick-freeze: average the AB ensemble over realization for each perturbation
        """
        dims = tuple(self._da.dims)
        has_pert = "perturbation" in dims
        has_real = "realization" in dims

        if self.mode == "pick-freeze":
            result = self._da.mean(dim="realization") if "realization" in self._da.dims else self._da
            return result.values

        if has_pert and has_real:
            result = self._da.mean(dim="realization")
            return result.values
        if has_pert:
            return self._da.values

        pert_dims = [d for d in self._tmc_dims if d.startswith("perturbation_")]
        if pert_dims:
            marginal_values = []
            for dim in pert_dims:
                kept = [d for d in pert_dims if d != dim]
                if has_real:
                    kept.append("realization")
                if kept:
                    result = self._da.mean(dim=kept)
                else:
                    result = self._da
                marginal_values.append(result.values)
            return np.stack(marginal_values, axis=0)
        return self.mean

    @property
    def per_perturbation_std_dev(self):
        """
        Standard deviation for each perturbation type with mode-aware marginalization.
        """
        dims = tuple(self._da.dims)
        has_pert = "perturbation" in dims
        has_real = "realization" in dims

        if self.mode == "pick-freeze":
            result = self._da.std(dim="realization") if "realization" in self._da.dims else self._da
            return result.values

        if has_pert and has_real:
            result = self._da.std(dim="realization")
            return result.values
        if has_pert:
            return np.zeros_like(self._da.values)

        pert_dims = [d for d in self._tmc_dims if d.startswith("perturbation_")]
        if pert_dims:
            marginal_values = []
            for dim in pert_dims:
                kept = [d for d in pert_dims if d != dim]
                if has_real:
                    kept.append("realization")
                if kept:
                    result = self._da.std(dim=kept)
                else:
                    result = self._da
                marginal_values.append(result.values)
            return np.stack(marginal_values, axis=0)
        return self.std_dev

    
    @property
    def perturbation_dims(self):
        """Names of perturbation dimensions used by the current TMC mode."""
        dims = [d for d in self._tmc_dims if d.startswith("perturbation_")]
        if not dims and "perturbation" in self._tmc_dims:
            dims = ["perturbation"]
        return tuple(dims)

    def mode_summary(self):
        """Return a compact mode-aware summary that hides the internal manifest detail."""
        summary = {
            "mode": self.mode,
            "tmc_dims": list(self.tmc_dims),
            "perturbation_dims": list(self.perturbation_dims),
            "shape": self.shape,
            "has_pick_freeze_views": bool(self.ensemble_views),
        }
        if self.mode == "pick-freeze":
            summary["ensemble_sets"] = sorted(self.ensemble_views.keys())
        return summary

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

    def close(self):
        """Close any retained parent xarray Datasets to release file handles."""
        for ds in (getattr(self, "_A_parent_ds", None), getattr(self, "_B_parent_ds", None), getattr(self, "_AB_parent_ds", None), getattr(self, "_parent_ds", None)):
            if ds is None:
                continue
            try:
                ds.close()
            except Exception:
                pass