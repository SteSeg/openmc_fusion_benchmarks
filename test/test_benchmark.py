import pytest
import yaml
import openmc
from pathlib import Path
from unittest.mock import patch, mock_open
from openmc_fusion_benchmarks import Benchmark, OpenmcBenchmark


# ======= Fixtures =======
@pytest.fixture
def mock_spec():
    """Returns a mock benchmark specification YAML content."""
    return """
    materials:
      - material_id: 1
        name: "Steel"
        density:
          units: "g/cm3"
          value: 7.85
        composition:
          fraction_type: "atomic"
          composition_type: "element"
          data:
            Fe: 0.98
            C: 0.02
    """


@pytest.fixture
def invalid_fraction_spec():
    """Returns a mock benchmark with an invalid fraction type."""
    return """
    materials:
      - material_id: 1
        name: "Steel"
        density:
          units: "g/cm3"
          value: 7.85
        composition:
          fraction_type: "invalid_type"
          composition_type: "element"
          data:
            Fe: 0.98
            C: 0.02
    """


@pytest.fixture
def benchmark_name():
    return "mock_benchmark"


# ======= Benchmark Class Tests =======
def test_benchmark_initialization(mock_spec, benchmark_name):
    """Test that Benchmark initializes and loads YAML correctly."""
    with patch("pathlib.Path.open", mock_open(read_data=mock_spec)), \
            patch.object(Path, "is_file", return_value=True), \
            patch.object(Path, "__truediv__", lambda self, other: self):  # Avoid real path joining

        class MockBenchmark(Benchmark):
            def build_materials(self):
                return super().build_materials()

        benchmark = MockBenchmark(benchmark_name)
        # Ensure materials were loaded
        assert benchmark._benchmark_spec["materials"]
        assert benchmark.build_materials() == yaml.safe_load(mock_spec)[
            "materials"]

# ======= OpenmcBenchmark Class Tests =======


def test_openmcbenchmark_material_conversion(mock_spec):
    """Test that OpenmcBenchmark correctly converts materials."""
    with patch("pathlib.Path.open", mock_open(read_data=mock_spec)), \
            patch.object(Path, "is_file", return_value=True), \
            patch.object(Path, "__truediv__", lambda self, other: self):

        benchmark = OpenmcBenchmark("mock_benchmark")
        materials = benchmark.build_materials()

        assert isinstance(materials, openmc.Materials)
        assert len(materials) == 1
        assert materials[0].name == "Steel"
        assert materials[0].density == 7.85  # Fixed assertion


def test_openmcbenchmark_invalid_fraction_type(invalid_fraction_spec, benchmark_name):
    """Test that OpenmcBenchmark raises ValueError for invalid fraction type."""
    with patch("pathlib.Path.open", mock_open(read_data=invalid_fraction_spec)), \
            patch.object(Path, "is_file", return_value=True), \
            patch.object(Path, "__truediv__", lambda self, other: self):

        benchmark = OpenmcBenchmark(benchmark_name)
        with pytest.raises(ValueError, match="Invalid fraction type: invalid_type"):
            benchmark.build_materials()
