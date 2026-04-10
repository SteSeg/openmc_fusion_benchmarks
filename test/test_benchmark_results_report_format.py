import json
from pathlib import Path

import xarray as xr
import numpy as np

from openmc_fusion_benchmarks.benchmark_results import Results


def _write_group(path: Path, group: str, consistent: int, issues):
    ds = xr.Dataset(
        {
            "mean": xr.DataArray(
                np.ones((1, 1), dtype=float),
                dims=("nuclide", "score"),
                coords={
                    "nuclide": np.array(["total"], dtype="U"),
                    "score": np.array(["current"], dtype="U"),
                },
            ),
            "mc_std": xr.DataArray(
                np.full((1, 1), 0.1, dtype=float),
                dims=("nuclide", "score"),
                coords={
                    "nuclide": np.array(["total"], dtype="U"),
                    "score": np.array(["current"], dtype="U"),
                },
            ),
        }
    )

    ds["mean"].attrs["tally_id"] = 1
    ds["mean"].attrs["tally_name"] = group
    ds["mc_std"].attrs["tally_id"] = 1
    ds["mc_std"].attrs["tally_name"] = group

    ds.attrs["spec_consistent"] = int(consistent)
    ds.attrs["spec_consistency_issues"] = json.dumps(issues)
    ds.attrs["observed_tally"] = json.dumps({"name": group})

    mode = "a" if path.exists() else "w"
    ds.to_netcdf(path, mode=mode, group=group, engine="h5netcdf")


def test_format_spec_consistency_report(tmp_path):
    p = tmp_path / "benchmark_results.h5"
    _write_group(p, "neutron_leakage", 1, [])
    _write_group(p, "photon_leakage", 0, ["scores mismatch"])

    r = Results.from_file(p)
    text = r.format_spec_consistency_report()

    assert "Spec Consistency Report" in text
    assert "Tally neutron_leakage (group=neutron_leakage)" in text
    assert "Status" in text and "OK" in text
    assert "Tally photon_leakage (group=photon_leakage)" in text
    assert "MISMATCH" in text
    assert "scores mismatch" in text
