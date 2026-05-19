import json
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from openmc_fusion_benchmarks.uq.tmc_manager import TMCManager, TMCStatePoint


class DummyModel:
    def __init__(self):
        self.calls = []

    def run(self, cwd=".", *args, **kwargs):
        self.calls.append(Path(cwd))
        path = Path(cwd) / "statepoint.h5"
        path.write_text("data")
        return str(path)


def _make_factory(tag):
    def factory():
        def inner(model, rng):
            model.calls.append((tag, int(rng.integers(0, 1000))))
            return model
        return inner
    return factory


def test_init_seed_rng_conflict():
    with pytest.raises(ValueError, match="Pass either seed or rng"):
        TMCManager(DummyModel(), [], realizations=1, seed=1, rng=np.random.default_rng())


def test_run_sequential_writes_manifest(tmp_path, monkeypatch):
    model = DummyModel()
    manager = TMCManager(model, [_make_factory("p0")], realizations=2, seed=123)

    called = {"value": False}

    def _fake_process(manifest_path):
        called["value"] = True
        assert Path(manifest_path).exists()

    monkeypatch.setattr(manager, "_process_tmc", _fake_process)

    manager.run(mode="sequential", cwd=tmp_path)

    manifest = tmp_path / "tmc_manifest.jsonl"
    lines = manifest.read_text().strip().splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert "perturbation" in rec
    assert "realization" in rec
    assert "statepoint" in rec
    assert called["value"] is True


def test_run_matrix_writes_manifest(tmp_path, monkeypatch):
    model = DummyModel()
    manager = TMCManager(model, [_make_factory("p0"), _make_factory("p1")], realizations=2, seed=123)

    called = {"value": False}

    def _fake_process(manifest_path):
        called["value"] = True

    monkeypatch.setattr(manager, "_process_tmc", _fake_process)

    manager.run(mode="matrix", cwd=tmp_path)

    manifest = tmp_path / "tmc_manifest.jsonl"
    lines = manifest.read_text().strip().splitlines()
    assert len(lines) == 4
    rec = json.loads(lines[0])
    assert rec["mode"] == "matrix"
    assert rec["indices"]
    assert called["value"] is True


def test_process_tmc_sequential(tmp_path, monkeypatch):
    manager = TMCManager(DummyModel(), [_make_factory("p0")], realizations=1, seed=123)

    manifest = tmp_path / "tmc_manifest.jsonl"
    manifest.write_text(json.dumps({"perturbation": 0, "realization": 0, "statepoint": "sp0.h5"}))

    class DummyTally:
        def __init__(self):
            self.id = 1
            self.name = "tally"
            self.mean = np.array([1.0, 2.0])
            self.std_dev = np.array([0.1, 0.2])

    class DummyStatePoint:
        def __init__(self, _path):
            self.tallies = {1: DummyTally()}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def _fake_statepoint(path):
        return DummyStatePoint(path)

    def _fake_openmc_tally_to_dataset(tally):
        da = xr.DataArray(np.array([1.0, 2.0]), dims=("cell",), coords={"cell": [0, 1]}, name="mean")
        return xr.Dataset({"mean": da})

    monkeypatch.setattr("openmc_fusion_benchmarks.uq.tmc_manager.openmc.StatePoint", _fake_statepoint)
    monkeypatch.setattr("openmc_fusion_benchmarks.uq.tmc_manager.openmc_tally_to_dataset", _fake_openmc_tally_to_dataset)

    manager._process_tmc(manifest_path=manifest)

    assert manager.tmc_statepoint_path.exists()

    sp = TMCStatePoint(manager.tmc_statepoint_path)
    assert sp.tmc_mode == "sequential"
    tally = sp.get_tally(tally_id=1)
    assert tally.name == "tally"
    assert np.allclose(tally.mean, np.array([1.0, 2.0]))
    assert "TMC combinations" in repr(sp)
