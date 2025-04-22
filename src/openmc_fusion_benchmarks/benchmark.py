import yaml
from pathlib import Path
from abc import ABC, abstractmethod
import openmc
import numpy as np
from .validate import validate_benchmark


BENCHMARK_DIR = Path(__file__).parent / "benchmarks"


class Benchmark(ABC):
    def __init__(self, name: str):
        self.name = name

        # Validate the benchmark specification
        validate_benchmark(name)

        with (BENCHMARK_DIR / f"{self.name}/specifications.yaml").open("r") as f:
            self._benchmark_spec = yaml.safe_load(f)

    @abstractmethod
    def build_materials(self):
        """Build materials for the benchmark."""
        pass

    @abstractmethod
    def build_geometry(self):
        """Build geometry for the benchmark."""
        pass

    @abstractmethod
    def build_source(self):
        """Build source for the benchmark."""
        pass

    @abstractmethod
    def build_settings(self):
        """Build settings for the benchmark."""
        pass

    @abstractmethod
    def build_tallies(self):
        """Build tallies for the benchmark."""
        pass


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

        materials = openmc.Materials()
        for m in material_data:
            mat = openmc.Material(name=m['name'])
            mat.id = m['id']
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

        return materials

    def build_source(self):
        source_data = self._benchmark_spec['source']

        def energy_conversion(values, units):
            values = np.array(values)
            if units == 'eV':
                return values
            elif units == 'keV':
                return values * 1e3
            elif units == 'MeV':
                return values * 1e6
            elif units == 'GeV':
                return values * 1e9
            else:
                raise ValueError(f"Unsupported energy unit: {units}")

        def angular_conversion(values, units):
            values = np.array(values)
            if units == 'degrees':
                return values * np.pi / 180
            elif units == 'radians':
                return values
            else:
                raise ValueError(f"Unsupported angle unit: {units}")

        sources = []
        # More than one source is possible
        for source in source_data:
            # Handle source particle type
            particle = source['particle_type']

            # Handle source spatial distribution
            if source['spatial_distribution']['type'] == 'point':
                center = source['spatial_distribution']['location']
                space = openmc.stats.Point(center)
            elif source['spatial_distribution']['type'] == 'box':
                raise NotImplementedError(
                    'Box source distribution not implemented yet.')
            elif source['spatial_distribution']['type'] == 'sphere':
                raise NotImplementedError(
                    'Sphere source distribution not implemented yet.')
            elif source['spatial_distribution']['type'] == 'cylinder':
                raise NotImplementedError(
                    'Cylinder source distribution not implemented yet.')
            elif source['spatial_distribution']['type'] == 'cartesian':
                raise NotImplementedError(
                    'Cartesian source distribution not implemented yet.')
            elif source['spatial_distribution']['type'] == 'mesh':
                raise NotImplementedError(
                    'Mesh source distribution not implemented yet.')
            else:
                raise ValueError(
                    f"Unsupported spatial distribution type: {source['spatial_distribution']['type']}")

            # Handle if source is associated with a domain (e.g. a cell, volume or material)
            if source['spatial_distribution']['domain'] is not None:
                raise NotImplementedError(
                    'Source domain not implemented yet.')

            # Handle angular and energy distributions
            angular_sources = []
            # Openmc needs one source per angle bin:
            angles = source['angular_energy_distribution']
            abins = np.array(angles['angle']['bins'])
            for i in range(len(abins)-1):
                lb = angular_conversion(
                    abins[i], angles['angle']['units'])
                ub = angular_conversion(
                    abins[i+1], angles['angle']['units'])
                mu = openmc.stats.Uniform(a=lb, b=ub)  # polar angle
                # Azimuthal angle --> STILL TO HANDLE
                phi = openmc.stats.Uniform(0, 2*np.pi)
                reference_uvw = angles['polar_direction']
                # Polar-azimuthal distribution
                angle = openmc.stats.PolarAzimuthal(mu, phi, reference_uvw)
                # Energy distribution
                evalues = energy_conversion(
                    angles['energy']['values'], angles['energy']['units'])
                # Weights
                weights = np.array(angles['weights'])

                # Check weights has the right shape
                # Weights must be a 2D array (rows, columns)
                if weights.ndim != 2:
                    raise ValueError(
                        'Weights must be a 2D array (rows, columns).')
                # Angle bins: check the number of rows is equal to the number of angle bins minus one
                if weights.shape[0] != len(abins)-1:
                    raise ValueError(
                        'Number of weights rows must match number of angle bins minus one.')
                # Energy values: check the number of columns is equal to the number of energy values
                if weights.shape[1] != len(evalues):
                    raise ValueError(
                        'Number of weights columns must match number of energy values.')

                interpolation = angles['energy']['interpolation']
                # energy distribution type --> STILL TO HANDLE
                energy = openmc.stats.Tabular(
                    evalues, weights[i], interpolation=interpolation)
                # Handle strength
                strength = angles['strength']['data'][i]
                # Build source
                source = openmc.IndependentSource()
                source.paricle = particle
                source.space = space
                source.angle = angle
                source.energy = energy
                source.strength = strength
                # Append to source list
                angular_sources.append(source)
            # Append angular sources to the main source list
            sources.extend(angular_sources)

        return source

    def build_tallies(self):
        tallies_data = self._benchmark_spec['tallies']
