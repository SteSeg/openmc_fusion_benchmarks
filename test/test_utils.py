import pytest
import h5py
import xarray as xr
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch
from openmc_fusion_benchmarks.utils import _save_result, _openmc_to_ofb


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


def test_save_result_creates_new_file(temp_dir):
    """Test that _save_result creates a new file if it doesn't exist."""
    filepath = temp_dir / "new_results.h5"
    
    # Create test data
    data = xr.DataArray(
        np.array([[[1.0, 0.1], [2.0, 0.2]]]),
        dims=["realization", "row", "column"],
        coords={
            "realization": ["test_run"],
            "row": [0, 1],
            "column": ["mean", "std. dev."]
        },
        name="test_tally"
    )
    
    # Save the result
    _save_result(data, str(filepath), "test_tally", "test_run")
    
    # Verify file was created
    assert filepath.exists()
    
    # Verify data can be loaded
    loaded = xr.load_dataarray(filepath, group="test_tally")
    assert loaded.shape == data.shape
    assert "test_run" in loaded.realization.values


def test_save_result_appends_to_existing_file(temp_dir):
    """Test that _save_result appends new realizations to existing file."""
    filepath = temp_dir / "existing_results.h5"
    
    # Create first realization
    data1 = xr.DataArray(
        np.array([[[1.0, 0.1], [2.0, 0.2]]]),
        dims=["realization", "row", "column"],
        coords={
            "realization": ["run1"],
            "row": [0, 1],
            "column": ["mean", "std. dev."]
        },
        name="tally1"
    )
    _save_result(data1, str(filepath), "tally1", "run1")
    
    # Create second realization
    data2 = xr.DataArray(
        np.array([[[1.5, 0.15], [2.5, 0.25]]]),
        dims=["realization", "row", "column"],
        coords={
            "realization": ["run2"],
            "row": [0, 1],
            "column": ["mean", "std. dev."]
        },
        name="tally1"
    )
    _save_result(data2, str(filepath), "tally1", "run2")
    
    # Verify both realizations are present
    loaded = xr.load_dataarray(filepath, group="tally1")
    assert len(loaded.realization) == 2
    assert "run1" in loaded.realization.values
    assert "run2" in loaded.realization.values


def test_save_result_multiple_groups(temp_dir):
    """Test that _save_result can handle multiple groups in same file."""
    filepath = temp_dir / "multi_group.h5"
    
    # Create data for first group
    data1 = xr.DataArray(
        np.array([[[1.0, 0.1]]]),
        dims=["realization", "row", "column"],
        coords={
            "realization": ["run1"],
            "row": [0],
            "column": ["mean", "std. dev."]
        }
    )
    _save_result(data1, str(filepath), "group1", "run1")
    
    # Create data for second group
    data2 = xr.DataArray(
        np.array([[[2.0, 0.2]]]),
        dims=["realization", "row", "column"],
        coords={
            "realization": ["run1"],
            "row": [0],
            "column": ["mean", "std. dev."]
        }
    )
    _save_result(data2, str(filepath), "group2", "run1")
    
    # Verify both groups exist
    with h5py.File(filepath, 'r') as f:
        assert "group1" in f
        assert "group2" in f


def test_save_result_data_integrity(temp_dir):
    """Test that saved data maintains correct values."""
    filepath = temp_dir / "data_check.h5"
    
    # Create data with specific values
    expected_mean = np.array([1.5, 2.5, 3.5])
    expected_std = np.array([0.15, 0.25, 0.35])
    # Shape should be (1, 3, 2) for (realization, row, column)
    data_values = np.stack([expected_mean, expected_std], axis=1)[np.newaxis, :, :]
    data = xr.DataArray(
        data_values,
        dims=["realization", "row", "column"],
        coords={
            "realization": ["test"],
            "row": [0, 1, 2],
            "column": ["mean", "std. dev."]
        }
    )
    
    _save_result(data, str(filepath), "tally", "test")
    
    # Load and verify
    loaded = xr.load_dataarray(filepath, group="tally")
    np.testing.assert_array_almost_equal(
        loaded.sel(column="mean", realization="test").values,
        expected_mean
    )
    np.testing.assert_array_almost_equal(
        loaded.sel(column="std. dev.", realization="test").values,
        expected_std
    )


def test_openmc_to_ofb_with_cell_filter(temp_dir, monkeypatch):
    """Test _openmc_to_ofb with cell filter normalization."""
    monkeypatch.chdir(temp_dir)
    
    # Create mock statepoint
    mock_sp = Mock()
    mock_tally = Mock()
    
    # Create a proper pandas-like mock with subscriptable behavior
    import pandas as pd
    df = pd.DataFrame({
        'mean': [10.0, 20.0],
        'std. dev.': [1.0, 2.0]
    })
    mock_tally.get_pandas_dataframe = Mock(return_value=df)
    mock_sp.get_tally = Mock(return_value=mock_tally)
    
    # Create mock mesh with volumes
    mock_mesh = Mock()
    mock_vol1 = Mock()
    mock_vol1.volume = 2.0
    mock_vol2 = Mock()
    mock_vol2.volume = 5.0
    mock_mesh.volumes_by_id = {1: mock_vol1, 2: mock_vol2}
    
    # Spec tallies with cell filter
    spec_tallies = [{
        'name': 'test_tally',
        'filters': [{'type': 'cell', 'values': [1, 2]}]
    }]
    
    with patch('openmc_fusion_benchmarks.utils.pydagmc.Model', return_value=mock_mesh):
        _openmc_to_ofb(spec_tallies, mock_sp, mesh='dummy.h5m', realization_label='test')
    
    # Verify file was created
    assert (temp_dir / "benchmark_results.h5").exists()
    
    # Load and verify normalization was applied
    result = xr.load_dataarray(temp_dir / "benchmark_results.h5", group="test_tally")
    # Values should be normalized by volumes [2.0, 5.0]
    # Row 0: 10.0/2.0 = 5.0, Row 1: 20.0/5.0 = 4.0
    assert result.sel(column='mean', row=0, realization='test').values == pytest.approx(5.0)
    assert result.sel(column='mean', row=1, realization='test').values == pytest.approx(4.0)


def test_openmc_to_ofb_with_surface_filter(temp_dir, monkeypatch):
    """Test _openmc_to_ofb with surface filter normalization."""
    monkeypatch.chdir(temp_dir)
    
    # Create mock statepoint
    mock_sp = Mock()
    mock_tally = Mock()
    
    # Create proper pandas DataFrame
    import pandas as pd
    df = pd.DataFrame({
        'mean': [100.0],
        'std. dev.': [10.0]
    })
    mock_tally.get_pandas_dataframe = Mock(return_value=df)
    mock_sp.get_tally = Mock(return_value=mock_tally)
    
    # Create mock mesh with surface areas
    mock_mesh = Mock()
    mock_surf = Mock()
    mock_surf.area = 10.0
    mock_mesh.surfaces_by_id = {1: mock_surf}
    
    # Spec tallies with surface filter
    spec_tallies = [{
        'name': 'surface_tally',
        'filters': [{'type': 'surface', 'values': [1]}]
    }]
    
    with patch('openmc_fusion_benchmarks.utils.pydagmc.Model', return_value=mock_mesh):
        _openmc_to_ofb(spec_tallies, mock_sp, mesh='dummy.h5m', realization_label='surf_test')
    
    # Verify normalization by surface area
    result = xr.load_dataarray(temp_dir / "benchmark_results.h5", group="surface_tally")
    # Value should be normalized: 100.0/10.0 = 10.0
    assert result.sel(column='mean', realization='surf_test').values[0] == pytest.approx(10.0)


def test_openmc_to_ofb_material_filter_raises_error(temp_dir, monkeypatch):
    """Test that material filter raises NotImplementedError."""
    monkeypatch.chdir(temp_dir)
    
    mock_sp = Mock()
    mock_tally = Mock()
    
    # Create proper pandas DataFrame
    import pandas as pd
    df = pd.DataFrame({
        'mean': [1.0],
        'std. dev.': [0.1]
    })
    mock_tally.get_pandas_dataframe = Mock(return_value=df)
    mock_sp.get_tally = Mock(return_value=mock_tally)
    
    mock_mesh = Mock()
    
    # Spec tallies with material filter
    spec_tallies = [{
        'name': 'mat_tally',
        'filters': [{'type': 'material', 'values': [1]}]
    }]
    
    with patch('openmc_fusion_benchmarks.utils.pydagmc.Model', return_value=mock_mesh):
        with pytest.raises(NotImplementedError, match="Material filter not implemented"):
            _openmc_to_ofb(spec_tallies, mock_sp, mesh='dummy.h5m')


def test_openmc_to_ofb_no_normalization_filter(temp_dir, monkeypatch):
    """Test _openmc_to_ofb with a filter that doesn't need normalization."""
    monkeypatch.chdir(temp_dir)
    
    mock_sp = Mock()
    mock_tally = Mock()
    
    # Create proper pandas DataFrame
    import pandas as pd
    df = pd.DataFrame({
        'mean': [42.0],
        'std. dev.': [4.2]
    })
    mock_tally.get_pandas_dataframe = Mock(return_value=df)
    mock_sp.get_tally = Mock(return_value=mock_tally)
    
    mock_mesh = Mock()
    
    # Spec tallies with energy filter (no normalization needed)
    spec_tallies = [{
        'name': 'energy_tally',
        'filters': [{'type': 'energy', 'values': [0.0, 1e6]}]
    }]
    
    # Mock pydagmc.Model to avoid loading actual mesh
    with patch('openmc_fusion_benchmarks.utils.pydagmc.Model', return_value=mock_mesh):
        _openmc_to_ofb(spec_tallies, mock_sp, mesh='dummy.h5m', realization_label='no_norm')
    
    # Verify values are unchanged (norm = 1)
    result = xr.load_dataarray(temp_dir / "benchmark_results.h5", group="energy_tally")
    assert result.sel(column='mean', realization='no_norm').values[0] == pytest.approx(42.0)
    assert result.sel(column='std. dev.', realization='no_norm').values[0] == pytest.approx(4.2)

