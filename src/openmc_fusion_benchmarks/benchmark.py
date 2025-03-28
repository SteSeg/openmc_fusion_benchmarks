"""Module for defining and managing benchmarks"""
import yaml
import os
# from .geometry import Geometry
# from .material import Material
# from .source import Source
# from .tally import Tally


class Benchmark:
    """Main class representing a neutron transport benchmark."""

    def __init__(self, name: str):
        self.benchmark_name = name
        base_dir = os.path.dirname(__file__)
        benchmark_dir = os.path.join(base_dir, 'benchmarks', name)

        with open(os.path.join(benchmark_dir, 'benchmark_specs.yaml'), 'r') as f:
            data = yaml.safe_load(f)

        self.metadata = data.get("metadata", {})
        self.geometry = Geometry(data["geometry"], benchmark_dir)
        self.materials = [Material(m) for m in data.get("materials", [])]
        self.source = Source(data["source"])
        self.tallies = [Tally(t) for t in data.get("tallies", [])]

    def __repr__(self):
        return (f"<Benchmark(name={self.benchmark_name}, "
                f"geometry={self.geometry.geometry_type}, "
                f"materials={len(self.materials)}, "
                f"tallies={len(self.tallies)})>")


class Geometry:
    def __init__(self, geometry_data: dict, benchmark_dir: str):
        self.geometry_type = geometry_data.get("geometry_type")
        self.units = geometry_data.get("units", "cm")
        self.cad = geometry_data.get("cad")

        if self.geometry_type == "CSG":
            csg_file = geometry_data.get("csg_file")
            if csg_file:
                with open(os.path.join(benchmark_dir, csg_file), 'r') as f:
                    self.csg = yaml.safe_load(f)
            else:
                self.csg = geometry_data.get("csg")
        else:
            self.csg = None

    def __repr__(self):
        return f"<Geometry(type={self.geometry_type}, units={self.units})>"


class Material:
    def __init__(self, mat_data: dict):
        self.name = mat_data["name"]
        self.density = mat_data["density"]
        self.composition = mat_data["composition"]

    def __repr__(self):
        return f"<Material(name={self.name}, density={self.density})>"


class Source:
    def __init__(self, source_data: dict):
        self.type = source_data["type"]
        self.location = source_data["location"]
        self.energy_dist = source_data["energy_distribution"]
        self.rate = source_data.get("rate", 1.0)

    def __repr__(self):
        return (f"<Source(type={self.type}, location={self.location}, "
                f"rate={self.rate})>")


class Tally:
    def __init__(self, tally_data: dict):
        self.type = tally_data["type"]
        self.quantity = tally_data["quantity"]
        self.mesh = tally_data.get("mesh", None)

    def __repr__(self):
        return f"<Tally(type={self.type}, quantity={self.quantity})>"


class FngStr(Benchmark):
    def __init__(self, run_option: str = 'onaxis'):
        super().__init__("fng_str")

        self.run_option = run_option


class FngW(Benchmark):
    def __init__(self, run_option: str = 'reaction_rates'):
        super().__init__("fng_w")

        self.run_option = run_option


class Oktavian(Benchmark):
    def __init__(self, run_option: str = 'Al'):
        super().__init__("oktavian")


class FnsDuct(Benchmark):
    def __init__(self):
        super().__init__("fns_duct")


class FnsCleanW(Benchmark):
    def __init__(self):
        super().__init__("fns_clean_w")


class BenchmarkDatabase:
    @staticmethod
    def get_benchmark(name: str, **kwargs):
        if name == "fng_str":
            return FngStr(**kwargs)
        elif name == "fng_w":
            return FngW(**kwargs)
        elif name == "oktavian":
            return Oktavian(**kwargs)
        elif name == "fns_duct":
            return FnsDuct(**kwargs)
        elif name == "fns_clean_w":
            return FnsCleanW(**kwargs)
        else:
            return Benchmark(name)
