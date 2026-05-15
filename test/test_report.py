import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
import yaml
import h5py


def _module_available(name: str) -> bool:
    if name in sys.modules:
        return True
    try:
        return importlib.util.find_spec(name) is not None
    except ValueError:
        return False


# Stub heavy dependencies so importing the package works in minimal test envs.
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

from openmc_fusion_benchmarks.benchmark_results import BenchmarkResults
from openmc_fusion_benchmarks.report import (
    PlotStyle,
    ReportConfig,
    ReportMetadata,
    ResultSource,
    build_report,
)
from openmc_fusion_benchmarks.report.renderers import render_plots_for_report, render_yaml


def _write_structured_group(filepath: Path, group: str, tally_name: str) -> None:
    ds = xr.Dataset(
        {
            "mean": xr.DataArray(
                np.arange(4.0).reshape(2, 1, 2),
                dims=("cell", "nuclide", "score"),
                coords={
                    "cell": [0, 1],
                    "nuclide": np.array(["total"], dtype="U"),
                    "score": np.array(["flux", "heating"], dtype="U"),
                },
            ),
            "mc_std": xr.DataArray(
                np.full((2, 1, 2), 0.1),
                dims=("cell", "nuclide", "score"),
                coords={
                    "cell": [0, 1],
                    "nuclide": np.array(["total"], dtype="U"),
                    "score": np.array(["flux", "heating"], dtype="U"),
                },
            ),
        }
    )
    ds["mean"].attrs["tally_id"] = 1
    ds["mean"].attrs["tally_name"] = tally_name
    ds["mc_std"].attrs["tally_id"] = 1
    ds["mc_std"].attrs["tally_name"] = tally_name
    ds.to_netcdf(filepath, mode="a" if filepath.exists() else "w", engine="h5netcdf", group=group)


def _write_spec_and_metadata(filepath: Path) -> None:
    spec = {"metadata": {"title": "Spec Title", "description": "Spec description"}}
    spec_bytes = yaml.safe_dump(spec).encode("utf-8")

    with h5py.File(filepath, "a") as handle:
        if "specifications" in handle:
            del handle["specifications"]
        spec_group = handle.create_group("specifications")
        spec_group.attrs["format"] = "yaml"
        spec_group.create_dataset("yaml", data=np.bytes_(spec_bytes))

        if "run_metadata" in handle:
            del handle["run_metadata"]
        meta_group = handle.create_group("run_metadata")
        meta_group.attrs["code_name"] = "openmc"
        meta_group.attrs["code_version"] = "0.15.2"


@pytest.fixture
def results_pair(tmp_path):
    exp_path = tmp_path / "reference_results.h5"
    calc_path = tmp_path / "benchmark_results.h5"
    _write_structured_group(exp_path, group="tally_1", tally_name="tally_1")
    _write_structured_group(calc_path, group="tally_1", tally_name="tally_1")
    return BenchmarkResults.from_file(exp_path), BenchmarkResults.from_file(calc_path)


def test_build_report(results_pair, tmp_path):
    exp, calc = results_pair
    metadata = ReportMetadata(title="Test", benchmark_id="bench")
    sources = [
        ResultSource(name="experiment", kind="experiment", results=exp),
        ResultSource(name="calculation", kind="calculation", results=calc),
    ]
    config = ReportConfig(output_dir=tmp_path)

    report = build_report(metadata, sources, config)

    assert report.metadata.title == "Test"
    assert report.data["benchmark_id"] == "bench"
    assert report.data["sources"][0]["name"] == "experiment"
    assert report.plots[0].tally_name == "tally_1"
    assert isinstance(report.plots[0].style, PlotStyle)


def test_build_report_without_metadata(results_pair, tmp_path):
    exp, calc = results_pair
    sources = [
        ResultSource(name="experiment", kind="experiment", results=exp),
        ResultSource(name="calculation", kind="calculation", results=calc),
    ]
    config = ReportConfig(output_dir=tmp_path)

    report = build_report(sources, config)

    assert report.metadata.title
    assert report.data["sources"][0]["name"] == "experiment"
    assert report.data["verbosity"] == 2


def test_build_report_includes_specs_and_run_metadata(tmp_path):
    exp_path = tmp_path / "reference_results.h5"
    calc_path = tmp_path / "benchmark_results.h5"
    _write_structured_group(exp_path, group="tally_1", tally_name="tally_1")
    _write_structured_group(calc_path, group="tally_1", tally_name="tally_1")
    _write_spec_and_metadata(exp_path)
    _write_spec_and_metadata(calc_path)

    exp = BenchmarkResults.from_file(exp_path)
    calc = BenchmarkResults.from_file(calc_path)
    sources = [
        ResultSource(name="experiment", kind="experiment", results=exp),
        ResultSource(name="calculation", kind="calculation", results=calc),
    ]
    config = ReportConfig(output_dir=tmp_path)

    report = build_report(sources, config)

    assert report.data["specifications"]["metadata"]["title"] == "Spec Title"
    assert report.data["run_metadata"]["code_name"] == "openmc"


def test_render_yaml(results_pair, tmp_path):
    exp, calc = results_pair
    metadata = ReportMetadata(title="Test", benchmark_id="bench")
    sources = [
        ResultSource(name="experiment", kind="experiment", results=exp),
        ResultSource(name="calculation", kind="calculation", results=calc),
    ]
    config = ReportConfig(output_dir=tmp_path)

    report = build_report(metadata, sources, config)
    output_path = render_yaml(report, tmp_path / "report.yaml")

    assert output_path.exists()
    payload = yaml.safe_load(output_path.read_text())
    assert payload["benchmark_id"] == "bench"
    assert payload["sources"][1]["name"] == "calculation"


def test_render_plots_for_report_records_plot_entries(results_pair, tmp_path, monkeypatch):
    exp, calc = results_pair
    metadata = ReportMetadata(title="Test", benchmark_id="bench")
    sources = [
        ResultSource(name="experiment", kind="experiment", results=exp),
        ResultSource(name="calculation", kind="calculation", results=calc),
    ]
    config = ReportConfig(output_dir=tmp_path)
    report = build_report(metadata, sources, config)

    class DummyArtifacts:
        def __init__(self, tally):
            self.tally_name = tally
            self.absolute_plot = tmp_path / f"{tally}_absolute.png"
            self.ce_plot = tmp_path / f"{tally}_ce.png"

    def _fake_build_plot_artifacts(tally_name, experiment, calculation, output_dir):
        return DummyArtifacts(tally_name)

    def _fake_render_plots(artifacts, experiment, calculation, style=None):
        artifacts.absolute_plot.write_text("ok")
        artifacts.ce_plot.write_text("ok")

    monkeypatch.setattr(
        "openmc_fusion_benchmarks.report.renderers.build_plot_artifacts",
        _fake_build_plot_artifacts,
    )
    monkeypatch.setattr(
        "openmc_fusion_benchmarks.report.renderers.render_plots",
        _fake_render_plots,
    )

    entries = render_plots_for_report(report, tmp_path / "plots")

    assert entries
    assert report.data["plots"][0]["tally"] == "tally_1"
    assert Path(entries[0]["absolute_plot"]).exists()
