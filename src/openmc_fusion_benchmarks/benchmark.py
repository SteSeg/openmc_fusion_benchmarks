import yaml
import os


class Benchmark:
    def __init__(self, name: str):
        self.name = name
        base_dir = os.path.dirname(__file__)
        benchmark_dir = os.path.join(base_dir, 'benchmarks', name)
        with open(os.path.join(benchmark_dir, 'specifications.yaml'), 'r') as f:
            benchmark_spec = yaml.safe_load(f)

        self._benchmark_spec = benchmark_spec

        # self._benchmark_spec = data
        # use private methods
        # self._build_materials() --> write the function build_materials(..) -> return openmc.Materials
        #

    def __repr__(self):
        pass
