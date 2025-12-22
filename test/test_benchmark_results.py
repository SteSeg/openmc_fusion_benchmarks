import pytest
import h5py
import xarray as xr
import numpy as np
from pathlib import Path
from openmc_fusion_benchmarks.benchmark_results import BenchmarkResults
from openmc_fusion_benchmarks.database import list_database_benchmarks, list_database_files


@pytest.fixture
def temp_results_file(tmp_path):
    """Create a temporary HDF5 file with test data."""
    filepath = tmp_path / "test_results.h5"
    
    # Create sample xarray DataArray
    data = xr.DataArray(
        np.random.rand(3, 2),
        dims=["row", "column"],
        coords={"row": [0, 1, 2], "column": ["mean", "std. dev."]},
        name="test_tally"
    )
    
    # Save to HDF5
    data.to_netcdf(filepath, mode="w", engine="netcdf4", group="test_tally")
    
    return filepath


def test_benchmark_results_from_file(temp_results_file):
    """Test loading results from a file path."""
    results = BenchmarkResults.from_file(temp_results_file)
    assert results.filepath == temp_results_file
    assert results.filepath.exists()


def test_benchmark_results_file_not_found():
    """Test that loading a nonexistent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        BenchmarkResults.from_file("/nonexistent/path/results.h5")


def test_benchmark_results_from_run_dir(tmp_path):
    """Test loading results from a run directory."""
    # Create a results file in the temp directory
    filepath = tmp_path / "results.h5"
    data = xr.DataArray(
        np.random.rand(2, 2),
        dims=["row", "column"],
        name="tally"
    )
    data.to_netcdf(filepath, mode="w", engine="netcdf4", group="tally")
    
    # Load from run directory
    results = BenchmarkResults.from_run_dir(tmp_path, "results.h5")
    assert results.filepath.exists()
    assert results.filepath.name == "results.h5"


def test_benchmark_results_tallies_property(temp_results_file):
    """Test the tallies property returns list of tally names."""
    results = BenchmarkResults.from_file(temp_results_file)
    tallies = results.tallies
    assert isinstance(tallies, list)
    assert "test_tally" in tallies


def test_benchmark_results_get_tally(temp_results_file):
    """Test retrieving a specific tally."""
    results = BenchmarkResults.from_file(temp_results_file)
    tally = results.get_tally("test_tally")
    assert isinstance(tally, xr.DataArray)
    assert tally.name == "test_tally"


def test_benchmark_results_from_database():
    """Test loading results from the package database."""
    benchmarks = list_database_benchmarks()
    if benchmarks:
        files = list_database_files(benchmarks[0])
        if files:
            # Try to load the first available file
            results = BenchmarkResults.from_database(benchmarks[0], files[0])
            assert results.filepath.exists()
            assert results.filepath.suffix == '.h5'
