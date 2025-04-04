import json
import gdown
import importlib
import subprocess
import shutil
from pathlib import Path

# replace with actual URL
LFS_REPO_URL = "https://github.com/SteSeg/openmc_fusion_benchmarks-lfs"


def get_cad_file(benchmark_name: str, cwd: str = ".") -> Path:
    """
    Downloads a .stp file from the myrepo-lfs repository based on model_name.

    Parameters:
    - model_name (str): Name of the model (used to locate the .stp file)
    - cwd (str): Directory where the file should be saved (default: current directory)

    Returns:
    - Path to the downloaded .stp file
    """
    # temp_clone_path = Path(".lfs_temp_repo")  # hidden temp folder
    # hidden temp folder
    temp_clone_path = (Path(cwd) / ".lfs_temp_repo").resolve()
    local_target_path = Path(cwd) / f"{benchmark_name}.stp"
    remote_file_path = f"benchmarks/{benchmark_name}/{benchmark_name}.stp"

    try:
        # Clone only if not already present
        if not temp_clone_path.exists():
            subprocess.run(
                ["git", "clone", "--depth", "1",
                    LFS_REPO_URL, str(temp_clone_path)],
                check=True
            )
        else:
            subprocess.run(
                ["git", "-C", str(temp_clone_path), "pull"],
                check=True
            )

        source_file = temp_clone_path / remote_file_path
        if not source_file.exists():
            raise FileNotFoundError(
                f"Could not find {source_file} in LFS repo.")

        shutil.copy(source_file, local_target_path)
        print(f"✅ Downloaded {source_file} → {local_target_path}")
        return local_target_path

    finally:
        # Optional: clean up temp repo
        shutil.rmtree(temp_clone_path, ignore_errors=True)


LIB_PATH = importlib.resources.files(
    "openmc_fusion_benchmarks.utils")


def download_from_drive(benchmark_name: str, file_format: str, run_option: str = None, cwd: str = None):

    filepath = LIB_PATH / "cad_geometries.json"
    with open(filepath, "r") as f:
        data = json.load(f)

        # Your Google Drive file link
    if run_option is not None:
        url = data[benchmark_name][run_option][file_format]
    else:
        url = data[benchmark_name][file_format]

    # Extract the file ID from the URL
    file_id = url.split("/d/")[1].split("/")[0]
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    # make sure cwd is identified as directory:
    if cwd is not None:
        if not cwd.endswith("/"):
            cwd += "/"

    # Download the file
    gdown.download(download_url, output=cwd, quiet=False, use_cookies=False)
