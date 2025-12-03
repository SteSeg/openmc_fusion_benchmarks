from pathlib import Path
try:
    from importlib.resources import files, as_file
except ImportError:
    # Python < 3.9
    from importlib_resources import files, as_file


def _resolve_database_path(benchmark: str, filename: str) -> Path:
    """Resolve a path to a file in the packaged results database."""
    try:
        db_root = files("openmc_fusion_benchmarks.results_database")
    except (TypeError, ModuleNotFoundError):
        # Fallback for development: use relative path from this file
        db_root = Path(__file__).parent / "results_database"
        if not db_root.exists():
            raise FileNotFoundError(
                "Could not locate results_database. "
                "Ensure the package is installed or results_database exists."
            )
        return db_root / benchmark / filename
    
    target = db_root / benchmark / filename
    
    # resources.files returns a Traversable; convert to real Path
    # using as_file context manager ensures it works even from zipped packages
    with as_file(target) as real_path:
        if not real_path.exists():
            raise FileNotFoundError(
                f"Database file not found: {benchmark}/{filename}\n"
                f"Available benchmarks: {list_database_benchmarks()}"
            )
        return Path(real_path)


def list_database_benchmarks() -> list[str]:
    """List all benchmarks available in the database."""
    try:
        db_root = files("openmc_fusion_benchmarks.results_database")
        with as_file(db_root) as real_path:
            return [p.name for p in real_path.iterdir() if p.is_dir()]
    except (TypeError, ModuleNotFoundError):
        db_root = Path(__file__).parent / "results_database"
        if db_root.exists():
            return [p.name for p in db_root.iterdir() if p.is_dir()]
        return []


def list_database_files(benchmark: str) -> list[str]:
    """List all result files for a specific benchmark."""
    try:
        db_root = files("openmc_fusion_benchmarks.results_database")
        bench_dir = db_root / benchmark
        with as_file(bench_dir) as real_path:
            return [p.name for p in real_path.iterdir() if p.is_file() and p.suffix == ".h5"]
    except (TypeError, ModuleNotFoundError):
        db_root = Path(__file__).parent / "results_database"
        bench_dir = db_root / benchmark
        if bench_dir.exists():
            return [p.name for p in bench_dir.iterdir() if p.is_file() and p.suffix == ".h5"]
        return []