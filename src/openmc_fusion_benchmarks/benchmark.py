# from pydantic import BaseModel, Field
# from typing import Dict
import yaml
import os
from .material import Material


import os
import yaml


class Benchmark:
    def __init__(self, name: str):
        self.name = name
        base_dir = os.path.dirname(__file__)
        benchmark_dir = os.path.join(base_dir, 'benchmarks', name)
        with open(os.path.join(benchmark_dir, 'specifications.yaml'), 'r') as f:
            data = yaml.safe_load(f)

        self.metadata = Metadata(data.get('metadata', {}))
        self.materials = Materials(data.get('materials', []))
        self.geometry = Geometry(data.get('geometry', {}))
        self.source = Source(data.get('source', {}))
        self.results = Results(data.get('results', {}))

    def __repr__(self):
        return f"<Benchmark name={self.name}>"


# Factory function
def load_benchmark(name: str) -> Benchmark:
    class_name = name.capitalize()
    if class_name in globals():
        return globals()[class_name](name)
    return Benchmark(name)


class OktavianAl(Benchmark):
    def __init__(self, name: str = "oktavian_al"):
        super().__init__(name)
        # You can add custom parsing logic here


# class Material:
#     def __init__(self, material_id: int, name: str, composition: dict, density: dict):
#         self.material_id = material_id
#         self.name = name
#         self.composition = composition
#         self.density = density

#     def __repr__(self):
#         return f"<Material id={self.material_id}, name={self.name}>"


class Metadata:
    def __init__(self, data: dict):
        self.title = data.get('title')
        self.description = data.get('description')
        self.date = data.get('date')

    def __repr__(self):
        return f"<Metadata title='{self.title}'>"


class Materials:
    def __init__(self, data: list[dict]):
        self._materials = [Material(**entry) for entry in data]

    def __getitem__(self, index):
        return self._materials[index]

    def __iter__(self):
        return iter(self._materials)

    def __len__(self):
        return len(self._materials)

    def __repr__(self):
        return f"<Materials count={len(self)}>"


class Geometry:
    def __init__(self, data: dict):
        self.data = data

    def __repr__(self):
        return f"<Geometry type={self.data.get('type', 'unknown')}>"


class Source:
    def __init__(self, data: dict):
        self.data = data

    def __repr__(self):
        return f"<Source particle_type={self.data.get('particle_type')}>"


class Results:
    def __init__(self, data: dict):
        self.data = data

    def __repr__(self):
        return f"<Results keys={list(self.data.keys())}>"
