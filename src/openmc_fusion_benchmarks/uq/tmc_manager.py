from typing import List, Callable
from pathlib import Path
import openmc
import numpy as np
import json
import xarray as xr


class TMCManager:
    def __init__(self, base_model: openmc.Model, perturbations: List[Callable],
                  realizations:int, rng:np.random._generator.Generator=None):
        self.base_model = base_model
        self.perturbations = perturbations
        self.realizations = realizations
        self.results = []

        # Example of setting rng for reproducibility
        if rng is None:
            self.rng = np.random.default_rng()
        else:
            self.rng = rng

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
                    # Build perturbed model
                    perturbed_model = p(self.base_model, rng=self.rng)

                    # Build run directory
                    run_dir = cwd / "tmc" / f"perturbation_{p_idx}" / f"realization_{r_idx}"
                    run_dir.mkdir(parents=True, exist_ok=True)

                    # Run openmc in that directory
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
        self._process_tmc(filepath=manifest)

    def _process_tmc(self, manifest_path="tmc_manifest.jsonl"):
        manifest_path = Path(manifest_path).resolve()
        tmc_dir = manifest_path.parent

        # Write the TMC statepoint file
        tmc_statepoint = tmc_dir / f"tmc_statepoint.{int(self.realizations)}.h5"

        # Read TMC manifest
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
        n_samples = len(records)
        if n_samples == 0:
            raise RuntimeError("TMC manifest is empty; no runs to process")

        # Use first statepoint as reference to determine shape & metadata
        first_sp_path = Path(records[0]["statepoint"]).resolve()
        tally_shapes   = {}  # key: tally id, value: nd_shape
        tally_filters  = {}  # key: tally id, value: list of filters
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

                tally_shapes[tid]  = nd_shape
                tally_filters[tid] = filters

                axis_info = {
                    "sample_axis": 0,
                    "filter_axes": [
                        {"name": type(f).__name__, "num_bins": f.num_bins}
                        for f in filters
                    ],
                    "nuclide_axis": len(filter_bins) + 1,
                    "score_axis": len(filter_bins) + 2,
                    "nuclides": [str(n) for n in tally.nuclides] if tally.nuclides else ["total"],
                    "scores": list(tally.scores),
                }
                for f in filters:
                    if isinstance(f, openmc.EnergyFilter):
                        axis_info["energy_edges_eV"] = f.bins

                tally_axisinfo[tid] = axis_info

        # Allocate TMC arrays, one per tally
        tmc_data = {}  # key: tally id, value: ndarray (n_samples, ...)

        for tid, nd_shape in tally_shapes.items():
            tmc_data[tid] = np.empty((n_samples,) + nd_shape, dtype=float)

        # Fill arrays by looping over all statepoints
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

        # Build xarray Dataset and write to disk
        ds = xr.Dataset()
        sample_coord = np.arange(n_samples)

        for tid, arr in tmc_data.items():
            nd_shape = tally_shapes[tid]
            dims = ("sample",) + tuple(f"dim_{k}" for k in range(len(nd_shape)))

            da = xr.DataArray(
                arr,
                dims=dims,
                coords={"sample": sample_coord},
                name=f"tally_{tid}",
            )

            # attach axis info as attrs
            for k, v in tally_axisinfo[tid].items():
                da.attrs[k] = v

            ds[da.name] = da

        ds.to_netcdf(tmc_statepoint)

