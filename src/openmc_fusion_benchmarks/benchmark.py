import yaml
import os
from abc import ABC, abstractmethod


class Benchmark(ABC):
    def __init__(self, name: str):
        self.name = name
        base_dir = os.path.dirname(__file__)
        benchmark_dir = os.path.join(base_dir, 'benchmarks', name)
        with open(os.path.join(benchmark_dir, 'specifications.yaml'), 'r') as f:
            benchmark_spec = yaml.safe_load(f)

        self._benchmark_spec = benchmark_spec

        @abstractmethod
        def build_materials(self):
            """Build materials for the benchmark."""
            pass

        @abstractmethod
        def build_geometry(self):
            """Build geometry for the benchmark."""
            pass

        @abstractmethod
        def build_settings(self):
            """Build settings for the benchmark."""
            pass

        @abstractmethod
        def build_tallies(self):
            """Build tallies for the benchmark."""
            pass

    def __repr__(self):
        pass
