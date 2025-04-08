import yaml
from pathlib import Path
from abc import ABC, abstractmethod
import openmc
from .validate import validate_benchmark


class Benchmark(ABC):
    def __init__(self, name: str):
        self.name = name

        # # Validate the benchmark specification
        # validate_benchmark(name)

        base_dir = Path(__file__).parent
        benchmark_dir = base_dir / "benchmarks" / name
        with (benchmark_dir / "specifications.yaml").open("r") as f:
            benchmark_spec = yaml.safe_load(f)

        self._benchmark_spec = benchmark_spec

    @abstractmethod
    def build_materials(self):
        """Build materials for the benchmark."""
        pass

    # @abstractmethod
    # def build_geometry(self):
    #     """Build geometry for the benchmark."""
    #     pass

    # @abstractmethod
    # def build_source(self):
    #     """Build settings for the benchmark."""
    #     pass

    # @abstractmethod
    # def build_settings(self):
    #     """Build settings for the benchmark."""
    #     pass

    # @abstractmethod
    # def build_tallies(self):
    #     """Build tallies for the benchmark."""
    #     pass


class OpenmcBenchmark(Benchmark):
    def __init__(self, name: str):
        super().__init__(name)
        self._materials = None
        self._geometry = None
        self._settings = None
        self._tallies = None

    def build_materials(self):
        # Implement the logic to build materials for OpenMC
        material_data = self._benchmark_spec['materials']

        fraction_map = {'atomic': 'ao', 'weight': 'wo'}

        materials = []
        for m in material_data:
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
