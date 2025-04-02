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
        for m in mats:
            mat = openmc.Material(name=m['name'])
            mat.material_id = m['material_id']
            mat.set_density(m['density']['units'], m['density']['value'])
            # fraction type to openmc - atomic fraction or weight fraction
            if m['composition']['fraction_type'] == 'atomic':
                ft = 'ao'
            elif m['composition']['fraction_type'] == 'weight':
                ft = 'wo'

            # composition type to openmc - element or nuclide
            if m['composition']['composition_type'] == 'element':
                for k, v in m['composition']['data'].items():
                    mat.add_element(k, v, ft)
            elif m['composition']['composition_type'] == 'nuclide':
                for k, v in m['composition']['data'].items():
                    mat.add_nuclide(k, v, ft)

            materials.append(mat)

        return openmc.Materials(materials)
