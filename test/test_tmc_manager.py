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


def _patch_tmc_processing(monkeypatch, mean_values=None, std_values=None):
    mean_values = np.array([1.0, 2.0]) if mean_values is None else np.array(mean_values)
    std_values = np.array([0.1, 0.2]) if std_values is None else np.array(std_values)

    class DummyTally:
        def __init__(self):
            self.id = 1
            self.name = "tally"
            self.mean = mean_values
            self.std_dev = std_values

    class DummyStatePoint:
        def __init__(self, _path):
            self.tallies = {1: DummyTally()}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    def _fake_statepoint(path):
        return DummyStatePoint(path)

    def _fake_openmc_tally_to_dataset(_tally):
        da = xr.DataArray(mean_values, dims=("cell",), coords={"cell": [0, 1]}, name="mean")
        return xr.Dataset({"mean": da})

    monkeypatch.setattr("openmc_fusion_benchmarks.uq.tmc_manager.openmc.StatePoint", _fake_statepoint)
    monkeypatch.setattr("openmc_fusion_benchmarks.uq.tmc_manager.openmc_tally_to_dataset", _fake_openmc_tally_to_dataset)


def test_process_tmc_diagonal(tmp_path, monkeypatch):
    manager = TMCManager(DummyModel(), [_make_factory("p0")], realizations=2, seed=123)

    manifest = tmp_path / "tmc_manifest.jsonl"
    lines = [
        {"mode": "diagonal", "indices": [0], "statepoint": "sp0.h5"},
        {"mode": "diagonal", "indices": [1], "statepoint": "sp1.h5"},
    ]
    manifest.write_text("\n".join(json.dumps(l) for l in lines))

    for name in ("sp0.h5", "sp1.h5"):
        (tmp_path / name).write_text("data")

    _patch_tmc_processing(monkeypatch)

    manager._process_tmc(manifest_path=manifest)
    sp = TMCStatePoint(manager.tmc_statepoint_path)
    assert sp.tmc_mode == "diagonal"
    tally = sp.get_tally(name="tally")
    assert tally.tmc_dims == ("realization",)


def test_process_tmc_matrix_and_tmc_tally_stats(tmp_path, monkeypatch):
    manager = TMCManager(DummyModel(), [_make_factory("p0"), _make_factory("p1")], realizations=2, seed=123)

    manifest = tmp_path / "tmc_manifest.jsonl"
    records = []
    for i in range(2):
        for j in range(2):
            name = f"sp{i}{j}.h5"
            (tmp_path / name).write_text("data")
            records.append({"mode": "matrix", "indices": [i, j], "statepoint": name})
    manifest.write_text("\n".join(json.dumps(r) for r in records))

    _patch_tmc_processing(monkeypatch)

    manager._process_tmc(manifest_path=manifest)
    sp = TMCStatePoint(manager.tmc_statepoint_path)
    tally = sp.get_tally(tally_id=1)

    assert tally.perturbation_dims == ("perturbation_0", "perturbation_1")
    assert tally.per_perturbation_mean.shape[0] == 2
    assert tally.per_perturbation_std_dev.shape[0] == 2


def test_process_tmc_matrix_mismatch_raises(tmp_path, monkeypatch):
    manager = TMCManager(DummyModel(), [_make_factory("p0"), _make_factory("p1")], realizations=2, seed=123)

    manifest = tmp_path / "tmc_manifest.jsonl"
    records = []
    for i in range(2):
        name = f"sp{i}.h5"
        (tmp_path / name).write_text("data")
        records.append({"mode": "matrix", "indices": [i, 0], "statepoint": name})
    manifest.write_text("\n".join(json.dumps(r) for r in records))

    _patch_tmc_processing(monkeypatch)

    with pytest.raises(RuntimeError, match="implies"):
        manager._process_tmc(manifest_path=manifest)


def test_tmc_statepoint_get_tally_errors(tmp_path, monkeypatch):
    manager = TMCManager(DummyModel(), [_make_factory("p0")], realizations=1, seed=123)
    manifest = tmp_path / "tmc_manifest.jsonl"
    manifest.write_text(json.dumps({"perturbation": 0, "realization": 0, "statepoint": "sp0.h5"}))
    (tmp_path / "sp0.h5").write_text("data")
    _patch_tmc_processing(monkeypatch)
    manager._process_tmc(manifest_path=manifest)

    sp = TMCStatePoint(manager.tmc_statepoint_path)
    with pytest.raises(ValueError, match="No tally with id"):
        sp.get_tally(tally_id=999)
    with pytest.raises(ValueError, match="No tally with name"):
        sp.get_tally(name="missing")
    with pytest.raises(ValueError, match="Must specify either"):
        sp.get_tally()


def test_tmc_tally_per_perturbation_sequential(tmp_path, monkeypatch):
    manager = TMCManager(DummyModel(), [_make_factory("p0")], realizations=2, seed=123)
    manifest = tmp_path / "tmc_manifest.jsonl"
    records = [
        {"perturbation": 0, "realization": 0, "statepoint": "sp0.h5"},
        {"perturbation": 0, "realization": 1, "statepoint": "sp1.h5"},
    ]
    manifest.write_text("\n".join(json.dumps(r) for r in records))
    (tmp_path / "sp0.h5").write_text("data")
    (tmp_path / "sp1.h5").write_text("data")

    _patch_tmc_processing(monkeypatch, mean_values=[1.0, 3.0], std_values=[0.1, 0.3])

    manager._process_tmc(manifest_path=manifest)
    sp = TMCStatePoint(manager.tmc_statepoint_path)
    tally = sp.get_tally(tally_id=1)
    assert tally.per_perturbation_mean.shape[0] == 1
    assert tally.per_perturbation_std_dev.shape[0] == 1


def test_process_tmc_empty_manifest_raises(tmp_path):
    manager = TMCManager(DummyModel(), [_make_factory("p0")], realizations=1, seed=123)
    manifest = tmp_path / "tmc_manifest.jsonl"
    manifest.write_text("")
    with pytest.raises(RuntimeError, match="manifest is empty"):
        manager._process_tmc(manifest_path=manifest)


def test_process_tmc_unrecognized_format_raises(tmp_path):
    manager = TMCManager(DummyModel(), [_make_factory("p0")], realizations=1, seed=123)
    manifest = tmp_path / "tmc_manifest.jsonl"
    manifest.write_text(json.dumps({"statepoint": "sp0.h5"}))
    with pytest.raises(RuntimeError, match="Unrecognized manifest record format"):
        manager._process_tmc(manifest_path=manifest)


def test_run_invalid_mode_raises(tmp_path):
    manager = TMCManager(DummyModel(), [_make_factory("p0")], realizations=1, seed=123)
    with pytest.raises(ValueError, match="Unknown TMC mode"):
        manager.run(mode="unknown", cwd=tmp_path)


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
