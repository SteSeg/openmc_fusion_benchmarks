import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


def _module_available(name: str) -> bool:
    if name in sys.modules:
        return True
    try:
        return importlib.util.find_spec(name) is not None
    except ValueError:
        return False


# The package imports benchmark.py at import time; provide stubs when unavailable.
if not _module_available("openmc"):
    openmc_stub = types.ModuleType("openmc")
    openmc_stub.__path__ = []
    for cls_name in (
        "StatePoint",
        "Tally",
        "Filter",
        "CellFilter",
        "SurfaceFilter",
        "MaterialFilter",
        "EnergyFilter",
        "ParticleFilter",
        "Materials",
        "Material",
        "Geometry",
        "Settings",
        "Tallies",
        "Model",
        "DAGMCUniverse",
    ):
        setattr(openmc_stub, cls_name, type(cls_name, (), {}))
    sys.modules.setdefault("openmc", openmc_stub)

    openmc_data_stub = types.ModuleType("openmc.data")
    openmc_data_stub.zam = lambda _name: (1, 1, 0)
    sys.modules.setdefault("openmc.data", openmc_data_stub)

try:
    import pydagmc as _pydagmc  # noqa: F401
except Exception:
    pydagmc_stub = types.ModuleType("pydagmc")
    pydagmc_stub.Model = type("Model", (), {})
    sys.modules["pydagmc"] = pydagmc_stub

try:
    import cad_to_dagmc as _cad_to_dagmc  # noqa: F401
except Exception:
    cad_stub = types.ModuleType("cad_to_dagmc")
    cad_stub.CadToDagmc = type("CadToDagmc", (), {})
    sys.modules["cad_to_dagmc"] = cad_stub

if not _module_available("sandy"):
    sys.modules.setdefault("sandy", types.ModuleType("sandy"))


from openmc_fusion_benchmarks.benchmark import OpenmcBenchmark


def test_postprocess_with_open_statepoint_object():
    fake_self = SimpleNamespace(_benchmark_spec={"tallies": [{"name": "t1"}, {"name": "t2"}]})
    fake_sp = object()

    with patch("openmc_fusion_benchmarks.benchmark.make_default_openmc_normalizer", return_value="norm") as mk_norm:
        with patch("openmc_fusion_benchmarks.benchmark.save_openmc_statepoint_tallies") as save:
            with patch("openmc_fusion_benchmarks.benchmark.openmc.StatePoint", new=object):
                OpenmcBenchmark._postprocess(fake_self, statepoint=fake_sp, mesh="mesh.h5m")

    mk_norm.assert_called_once_with("mesh.h5m")
    save.assert_called_once()
    kwargs = save.call_args.kwargs
    assert kwargs["statepoint"] is fake_sp
    assert kwargs["filename"] == "benchmark_results.h5"
    assert kwargs["tally_names"] == ["t1", "t2"]
    assert kwargs["tmc_coords"] == {"realization": ["baseline"]}


def test_postprocess_with_statepoint_path_uses_context_manager():
    fake_self = SimpleNamespace(_benchmark_spec={"tallies": [{"name": "t1"}]})

    class DummyStatePoint:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            return SimpleNamespace(get_tally=lambda *a, **k: None)

        def __exit__(self, *_exc):
            return False

    with patch("openmc_fusion_benchmarks.benchmark.make_default_openmc_normalizer", return_value="norm"):
        with patch("openmc_fusion_benchmarks.benchmark.save_openmc_statepoint_tallies") as save:
            with patch("openmc_fusion_benchmarks.benchmark.openmc.StatePoint", new=DummyStatePoint):
                OpenmcBenchmark._postprocess(fake_self, statepoint=Path("statepoint.10.h5"))

    save.assert_called_once()
