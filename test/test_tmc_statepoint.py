from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from openmc_fusion_benchmarks.uq.tmc_statepoint import TMCStatePoint


def _write_tally_group(path: Path, group: str, tally_id: int, tally_name: str):
    data = np.ones((2, 1, 1), dtype=float)
    ds = xr.Dataset(
        {
            "mean": xr.DataArray(
                data,
                dims=("realization", "nuclide", "score"),
                coords={
                    "realization": np.arange(2),
                    "nuclide": np.array(["total"], dtype="U"),
                    "score": np.array(["current"], dtype="U"),
                },
            ),
            "mc_std": xr.DataArray(
                np.full_like(data, 0.1),
                dims=("realization", "nuclide", "score"),
                coords={
                    "realization": np.arange(2),
                    "nuclide": np.array(["total"], dtype="U"),
                    "score": np.array(["current"], dtype="U"),
                },
            ),
        }
    )
    ds["mean"].attrs["tally_id"] = tally_id
    ds["mean"].attrs["tally_name"] = tally_name
    ds["mc_std"].attrs["tally_id"] = tally_id
    ds["mc_std"].attrs["tally_name"] = tally_name

    mode = "a" if path.exists() else "w"
    ds.to_netcdf(path, mode=mode, group=group, engine="h5netcdf")


def test_tmc_statepoint_discovers_name_groups_and_gets_by_name(tmp_path):
    fpath = tmp_path / "tmc_statepoint.2.h5"
    _write_tally_group(fpath, group="neutron_leakage", tally_id=1, tally_name="neutron_leakage")
    _write_tally_group(fpath, group="photon_leakage", tally_id=2, tally_name="photon_leakage")

    sp = TMCStatePoint(fpath)

    assert set(sp.tallies) == {"neutron_leakage", "photon_leakage"}
    assert set(sp.tallies_by_id.keys()) == {1, 2}

    t1 = sp.get_tally(name="neutron_leakage")
    assert t1.id == 1
    assert t1.name == "neutron_leakage"

    # Positional string convenience should resolve to name lookup.
    t2 = sp.get_tally("photon_leakage")
    assert t2.id == 2
    assert t2.name == "photon_leakage"

    # ID lookup remains supported.
    t_by_id = sp.get_tally(tally_id=1)
    assert t_by_id.name == "neutron_leakage"


def test_tmc_statepoint_get_tally_errors(tmp_path):
    fpath = tmp_path / "tmc_statepoint.1.h5"
    _write_tally_group(fpath, group="neutron_leakage", tally_id=11, tally_name="neutron_leakage")

    sp = TMCStatePoint(fpath)

    with pytest.raises(ValueError, match="name 'missing'"):
        sp.get_tally(name="missing")

    with pytest.raises(ValueError, match="id '99'"):
        sp.get_tally(tally_id=99)

    with pytest.raises(ValueError, match="Must specify either 'name' or 'tally_id'"):
        sp.get_tally()
