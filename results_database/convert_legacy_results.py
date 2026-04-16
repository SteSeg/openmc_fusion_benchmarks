#!/usr/bin/env python3
"""Convert legacy OFB HDF5 results to the current tally group schema.

Legacy format (per group):
- dataset named like the group, shape (realization, row, column)
- coordinate datasets: realization, row, column
- typical columns: [energy low, energy high, mean, std. dev.]

New format (per group):
- variables: mean, mc_std
- dims: (surface, energy, nuclide, score)
- attrs: filter_axes, nuclides, scores, observed_tally, optional spec_* fields
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import h5py
import numpy as np
import xarray as xr
import yaml


def _normalize_filter_type(type_name: str) -> str:
    name = str(type_name).strip().lower()
    if name.endswith("filter"):
        name = name[:-6]
    return name


def _filter_bins_match(spec_filter: dict, observed_axis: dict) -> bool:
    expected = spec_filter.get("values")
    observed = observed_axis.get("bins")
    if expected is None or observed is None:
        return True

    ftype = _normalize_filter_type(spec_filter.get("type", ""))
    if ftype == "energy":
        try:
            return np.allclose(np.asarray(expected, dtype=float), np.asarray(observed, dtype=float))
        except Exception:
            return False

    try:
        return list(expected) == list(observed)
    except Exception:
        return False


def _validate_tally_consistency(spec_tally: dict, observed_tally: dict) -> tuple[bool, list[str]]:
    issues: list[str] = []

    observed_scores = [str(s) for s in observed_tally.get("scores", [])]
    observed_nuclides = [str(n) for n in observed_tally.get("nuclides", [])]
    observed_filters = list(observed_tally.get("filters", []))

    spec_scores = [str(s) for s in spec_tally.get("scores", [])]
    if spec_scores and spec_scores != observed_scores:
        issues.append(f"scores mismatch: expected {spec_scores}, observed {observed_scores}")

    spec_nuclides = [str(n) for n in spec_tally.get("nuclides", [])]
    if spec_nuclides and spec_nuclides != observed_nuclides:
        issues.append(f"nuclides mismatch: expected {spec_nuclides}, observed {observed_nuclides}")

    expected_particle = spec_tally.get("particle")
    if expected_particle is not None:
        particle_filters = [a for a in observed_filters if _normalize_filter_type(a.get("name", "")) == "particle"]
        if not particle_filters:
            issues.append("missing ParticleFilter in observed tally")
        else:
            bins = particle_filters[0].get("bins", [])
            observed_particle = str(bins[0]) if bins else None
            if str(expected_particle) != str(observed_particle):
                issues.append(
                    f"particle mismatch: expected {expected_particle}, observed {observed_particle}"
                )

    spec_filters = spec_tally.get("filters", [])
    observed_non_particle = [
        a for a in observed_filters if _normalize_filter_type(a.get("name", "")) != "particle"
    ]

    expected_types = [_normalize_filter_type(f.get("type", "")) for f in spec_filters]
    observed_types = [_normalize_filter_type(a.get("name", "")) for a in observed_non_particle]
    if expected_types != observed_types:
        issues.append(f"filter type/order mismatch: expected {expected_types}, observed {observed_types}")

    return len(issues) == 0, issues


def _load_spec_lookup(repo_root: Path, benchmark: str | None) -> dict[str, dict]:
    if not benchmark:
        return {}

    spec_path = repo_root / "src" / "openmc_fusion_benchmarks" / "benchmarks" / benchmark / "specifications.yaml"
    if not spec_path.exists():
        raise FileNotFoundError(f"Could not find specifications file: {spec_path}")

    with spec_path.open("r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    lookup: dict[str, dict] = {}
    for entry in spec.get("tallies", []):
        if isinstance(entry, dict) and entry.get("name"):
            lookup[str(entry["name"])] = entry
    return lookup


def _decode_columns(group: h5py.Group) -> list[str]:
    cols_raw = group["column"][()]
    cols: list[str] = []
    for c in cols_raw:
        if isinstance(c, bytes):
            cols.append(c.decode("utf-8"))
        else:
            cols.append(str(c))
    return cols


def _col_index(columns: list[str], candidates: list[str]) -> int:
    normalized = [c.strip().lower().replace("_", " ") for c in columns]
    for cand in candidates:
        c = cand.strip().lower().replace("_", " ")
        for i, col in enumerate(normalized):
            if c == col:
                return i
    for cand in candidates:
        c = cand.strip().lower().replace("_", " ")
        for i, col in enumerate(normalized):
            if c in col:
                return i
    raise KeyError(f"Could not find column from candidates {candidates}. Found columns: {columns}")


def _legacy_group_to_dataset(group_name: str, arr: np.ndarray, columns: list[str], tally_id: int, spec_tally: dict | None) -> xr.Dataset:
    if arr.ndim != 3:
        raise ValueError(f"Expected legacy data shape (realization, row, column), got {arr.shape}")
    if arr.shape[0] < 1:
        raise ValueError(f"Legacy dataset for '{group_name}' has no realization axis entries")

    low_idx = _col_index(columns, ["energy low [ev]", "energy low", "energy_low [ev]", "energy_low"])
    high_idx = _col_index(columns, ["energy high [ev]", "energy high", "energy_high [ev]", "energy_high"])
    mean_idx = _col_index(columns, ["mean"])
    std_idx = _col_index(columns, ["std. dev.", "std dev", "std_dev", "mc_std", "std"])

    first = arr[0, :, :]
    low = np.asarray(first[:, low_idx], dtype=float)
    high = np.asarray(first[:, high_idx], dtype=float)
    mean = np.asarray(first[:, mean_idx], dtype=float)
    mc_std = np.asarray(first[:, std_idx], dtype=float)

    if len(low) == 0:
        energy_edges = np.asarray([], dtype=float)
    else:
        energy_edges = np.concatenate([low[:1], high])

    particle = None
    if isinstance(spec_tally, dict):
        particle = spec_tally.get("particle")
    if not particle:
        low_name = group_name.lower()
        if "neutron" in low_name:
            particle = "neutron"
        elif "photon" in low_name or "gamma" in low_name:
            particle = "photon"

    mean_5d = mean.reshape(1, 1, mean.shape[0], 1, 1)
    std_5d = mc_std.reshape(1, 1, mc_std.shape[0], 1, 1)

    dims = ("particle", "surface", "energy", "nuclide", "score")
    coords = {
        "particle": ("particle", np.asarray([0], dtype=int)),
        "surface": ("surface", np.asarray([0], dtype=int)),
        "energy": ("energy", np.arange(mean.shape[0], dtype=int)),
        "nuclide": ("nuclide", np.asarray([0], dtype=int)),
        "score": ("score", np.asarray([0], dtype=int)),
    }

    ds = xr.Dataset(
        {
            "mean": xr.DataArray(mean_5d, dims=dims, coords=coords),
            "mc_std": xr.DataArray(std_5d, dims=dims, coords=coords),
        }
    )

    filter_axes = [
        {
            "name": "ParticleFilter",
            "axis": "particle",
            "num_bins": 1,
            "bins": [particle] if particle is not None else [],
        },
        {
            "name": "SurfaceFilter",
            "axis": "surface",
            "num_bins": 1,
            "bins": [7],
        },
        {
            "name": "EnergyFilter",
            "axis": "energy",
            "num_bins": int(mean.shape[0]),
            "bins": energy_edges.tolist(),
            "kind": "edges",
            "units": "eV",
        },
    ]

    scores = ["current"]
    nuclides = ["total"]

    ds.attrs["filter_axes"] = json.dumps(filter_axes)
    ds.attrs["scores"] = json.dumps(scores)
    ds.attrs["nuclides"] = json.dumps(nuclides)

    ds.attrs["group"] = group_name
    ds.attrs["tally_name"] = group_name

    ds["mean"].attrs["tally_id"] = int(tally_id)
    ds["mean"].attrs["tally_name"] = group_name
    ds["mean"].attrs["tally_group"] = group_name

    ds["mc_std"].attrs["tally_id"] = int(tally_id)
    ds["mc_std"].attrs["tally_name"] = group_name
    ds["mc_std"].attrs["tally_group"] = group_name

    observed_tally = {
        "name": group_name,
        "id": int(tally_id),
        "filters": filter_axes,
        "scores": scores,
        "nuclides": nuclides,
    }
    ds.attrs["observed_tally"] = json.dumps(observed_tally)

    if spec_tally is not None:
        ds.attrs["spec_tally"] = json.dumps(spec_tally)
        consistent, issues = _validate_tally_consistency(spec_tally, observed_tally)
        ds.attrs["spec_consistent"] = int(bool(consistent))
        ds.attrs["spec_consistency_issues"] = json.dumps(issues)

    return ds


def convert_file(input_path: Path, output_path: Path, benchmark: str | None, engine: str) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    spec_lookup = _load_spec_lookup(repo_root, benchmark)

    if output_path.exists():
        output_path.unlink()

    with h5py.File(input_path, "r") as src:
        for idx, group_name in enumerate(src.keys(), start=1):
            group = src[group_name]
            if group_name not in group:
                raise KeyError(f"Legacy group '{group_name}' missing data dataset '{group_name}'")
            if "column" not in group:
                raise KeyError(f"Legacy group '{group_name}' missing 'column' dataset")

            arr = np.asarray(group[group_name][()])
            columns = _decode_columns(group)
            spec_tally = spec_lookup.get(group_name)

            ds = _legacy_group_to_dataset(
                group_name=group_name,
                arr=arr,
                columns=columns,
                tally_id=idx,
                spec_tally=spec_tally,
            )
            mode = "w" if idx == 1 else "a"
            ds.to_netcdf(output_path, mode=mode, group=group_name, engine=engine)

    return output_path.resolve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert legacy OFB result HDF5 format to the current tally schema.")
    parser.add_argument("input", type=Path, help="Legacy input .h5 file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .h5 file (default: <input_stem>_converted.h5)",
    )
    parser.add_argument(
        "--benchmark",
        type=str,
        default=None,
        help="Optional benchmark name to attach spec_tally and spec_consistency metadata.",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "h5netcdf"],
        default="auto",
        help="NetCDF engine to use (default: auto, which resolves to h5netcdf).",
    )
    args = parser.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = args.output.resolve() if args.output else input_path.with_name(f"{input_path.stem}_converted.h5")
    engine = _select_engine() if args.engine == "auto" else args.engine
    out = convert_file(input_path=input_path, output_path=output_path, benchmark=args.benchmark, engine=engine)
    print(f"Converted: {input_path} -> {out}")


def _select_engine() -> str:
    if importlib.util.find_spec("h5netcdf") is not None:
        return "h5netcdf"
    raise RuntimeError(
        "h5netcdf is required for this converter. Install it with: pip install h5netcdf"
    )


if __name__ == "__main__":
    main()