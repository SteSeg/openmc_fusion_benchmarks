from __future__ import annotations

from pathlib import Path
from typing import Union

import h5py
import xarray as xr

from .database import _resolve_database_path
from .tallies import Tally


class Results:
    """Class to handle OFB results stored in HDF5 files.

    This is the generic entry point and can be used for benchmark and non-benchmark
    workflows as long as they follow the OFB tally group schema.

    usage:
        - Load from arbitrary file path: `Results.from_file(filepath)`
        - Load from run directory: `Results.from_run_dir(run_dir, filename)`
        - Load from package database: `Results.from_database(benchmark, filename)`
    """

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"Results file not found: {self.filepath}")

    @classmethod
    def from_file(cls, filepath: Union[str, Path]) -> "Results":
        """Load results from an arbitrary file path."""
        return cls(filepath)

    @classmethod
    def from_run_dir(
        cls,
        run_dir: Union[str, Path] = ".",
        filename: str = "benchmark_results.h5",
    ) -> "Results":
        """Load results from a run directory (default: current directory)."""
        path = Path(run_dir) / filename
        return cls(path)

    @classmethod
    def from_database(cls, benchmark: str, filename: str = "reference_results.h5") -> "Results":
        """Load reference results from the package database."""
        db_path = _resolve_database_path(benchmark, filename)
        return cls(db_path)

    @property
    def tallies(self):
        with h5py.File(self.filepath, "r") as f:
            tallies = list(f.keys())
        return tallies

    def get_tally(self, name: str) -> Tally:
        """
        Get a tally wrapper.

        `name` can be either:
        - an HDF5 group name (for example `tally_1`), or
        - a tally logical name stored in attrs (for example `nuclear_heating`).
        """
        group = None

        with h5py.File(self.filepath, "r") as f:
            if name in f:
                group = name
            else:
                # Fallback lookup by tally_name attribute.
                for candidate in f.keys():
                    try:
                        with xr.open_dataset(self.filepath, group=candidate, engine="h5netcdf") as ds:
                            if "mean" not in ds:
                                continue
                            if ds["mean"].attrs.get("tally_name") == name:
                                group = candidate
                                break
                    except (OSError, ValueError, KeyError):
                        continue

        if group is None:
            raise ValueError(f"No tally with name or group '{name}' found")

        ds = xr.open_dataset(self.filepath, group=group, engine="h5netcdf")
        if "mean" not in ds:
            ds.close()
            raise ValueError(f"Group '{group}' does not contain a 'mean' dataset")

        da_mean = ds["mean"]
        da_mc_std = ds["mc_std"] if "mc_std" in ds else None
        return Tally(da_mean, da_mc_std, parent_ds=ds)


class BenchmarkResults(Results):
    """Backward-compatible alias class for benchmark-centric naming."""


# Optional explicit alias for OFB naming style.
OFBResults = Results
