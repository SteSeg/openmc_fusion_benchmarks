from pathlib import Path
import shutil


def get_lfs_file(relative_lfs_path: str) -> Path:
    """
    Copies a file from the lfs/ submodule to the current working directory.

    Args:
        relative_lfs_path (str): Relative path from lfs/ to the target file
                                 (e.g., "benchmarks/model/model_a.step").

    Returns:
        Path: Absolute path to the copied file in the current working directory.
    """
    # Get repo root assuming function is in src/myrepo/
    repo_root = Path(__file__).resolve().parents[2]
    source_path = repo_root / "lfs" / relative_lfs_path

    if not source_path.exists():
        raise FileNotFoundError(
            f"{source_path} does not exist. Try initializing the lfs submodule.")

    # Target is current working directory + filename
    destination_path = Path.cwd() / source_path.name
    shutil.copy(source_path, destination_path)

    return destination_path.resolve()
