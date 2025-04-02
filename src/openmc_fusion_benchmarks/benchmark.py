import yaml
import os
from abc import ABC, abstractmethod
import openmc


# class Benchmark(ABC):
class Benchmark:
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
        mats = self._benchmark_spec['materials']
        # for mat in mats:
        #     matid = mat['material_id']
        #     name = mat['name']
        #     density = mat['density']
        #     density_units = mat['density']['units']
        #     composition = mat['composition']

        return mats


class OpenmcBenchmark(Benchmark):
    def __init__(self, name: str):
        super().__init__(name)
        self._materials = None
        self._geometry = None
        self._settings = None
        self._tallies = None

    def build_materials(self):
        # Implement the logic to build materials for OpenMC
        mats = self._benchmark_spec['materials']
        materials = []

        fraction_map = {'atomic': 'ao', 'weight': 'wo'}

        for m in mats:
            mat = openmc.Material(name=m['name'])
            mat.material_id = m['material_id']
            mat.set_density(m['density']['units'], m['density']['value'])

            # Ensure fraction type is valid
            fraction_type = m['composition']['fraction_type']
            if fraction_type not in fraction_map:
                raise ValueError(f"Invalid fraction type: {fraction_type}")

            ft = fraction_map[fraction_type]
            add_method = mat.add_element if m['composition']['composition_type'] == 'element' else mat.add_nuclide

            for k, v in m['composition']['data'].items():
                add_method(k, v, ft)

            materials.append(mat)

        return openmc.Materials(materials)
