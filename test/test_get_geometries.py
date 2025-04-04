import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from openmc_fusion_benchmarks import get_cad_file  # adjust as needed
import subprocess


@pytest.fixture
def mock_paths(tmp_path):
    """Fixture for local file paths."""
    benchmark_name = "test_model"
    local_file = tmp_path / f"{benchmark_name}.stp"
    source_file = tmp_path / ".lfs_temp_repo" / \
        "benchmarks" / benchmark_name / f"{benchmark_name}.stp"
    return benchmark_name, tmp_path, source_file, local_file


def test_clone_and_copy_success(mock_paths):
    benchmark_name, cwd, source_file, local_file = mock_paths

    with patch("pathlib.Path.exists", side_effect=[False, True]), \
            patch("subprocess.run") as mock_subproc, \
            patch("shutil.copy") as mock_copy, \
            patch("builtins.print") as mock_print, \
            patch("shutil.rmtree") as mock_rmtree:

        # Create fake .stp file structure
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.touch()

        result = get_cad_file(benchmark_name, cwd=str(cwd))

        mock_subproc.assert_called_once_with(
            ["git", "clone", "--depth", "1",
             "https://github.com/SteSeg/openmc_fusion_benchmarks-lfs", str(cwd / ".lfs_temp_repo")],
            check=True
        )
        mock_copy.assert_called_once_with(source_file, local_file)
        mock_print.assert_called()
        mock_rmtree.assert_called_once()
        assert result == local_file


def test_file_not_found_raises(mock_paths):
    benchmark_name, cwd, source_file, _ = mock_paths

    with patch("pathlib.Path.exists", side_effect=[True, False]), \
            patch("subprocess.run"), \
            patch("shutil.rmtree"):

        with pytest.raises(FileNotFoundError, match="Could not find .* in LFS repo."):
            get_cad_file(benchmark_name, cwd=str(cwd))
