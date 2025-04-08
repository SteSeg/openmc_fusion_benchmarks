import yaml
from pathlib import Path
from abc import ABC, abstractmethod
import openmc
import numpy as np
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
    #     return self._benchmark_spec['geometry']

    @abstractmethod
    def build_source(self):
        """Build settings for the benchmark."""
        pass

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

    def build_source(self):
        source_data = self._benchmark_spec['source']

        def energy_conversion(units):
            if units == 'eV':
                return 1
            elif units == 'keV':
                return 1e3
            elif units == 'MeV':
                return 1e6
            elif units == 'GeV':
                return 1e9
            else:
                raise ValueError(f"Unsupported energy unit: {units}")

        if source_data['angular_distribution']['angulardistribution_type'] == 'polar_azimuthal':
            # One source per angle bin
            for angle in source_data['angular_distribution']['bins']:
                source = openmc.IndependentSource()
                # Handle angular distribution
                lb = angle['angle_range'][0]
                ub = angle['angle_range'][1]
                mu = openmc.stats.Uniform(a=lb, b=ub)  # polar angle
                # azimuthal angle --> STILL TO HANDLE
                phi = openmc.stats.Uniform(a=0, b=2*np.pi)
                # polar-azimuthal direction -> STILL TO HANDLE
                reference_uvw = source_data['angular_distribution']['reference_uvw']
                angle = openmc.stats.PolarAzimuthal(
                    mu=mu, phi=phi, reference_uvw=reference_uvw)
                # Handle energy distribution
                evalues = np.array(
                    angle['energy_distribution']['bins']['values'])
                evalues *= energy_conversion(
                    angle['energy_distribution']['units'])
                interpolation = angle['energy_distribution']['interpolation']
                # energy distribution type --> STILL TO HANDLE
                energy = openmc.stats.Tabular(
                    evalues, fvalues[i], interpolation=interpolation)
                # Handle strength
                strength = angle['strength']
                # Build source

        # if source_data['spatial_distribution']['spatialdistribution_type'] == 'point':
        #     center = source_data['spatial_distribution']['location']
        #     source.space = openmc.stats.Point(center)
        # if source_data['particle_type'] == 'neutron':
        #     source.particle = 'neutron'

        source = openmc.IndependentSource()
        if source_data['spatial_distribution']['spatialdistribution_type'] == 'point':
            center = source_data['spatial_distribution']['location']
            source.space = openmc.stats.Point(center)
        if source_data['angulardistribution_type'] == 'isotropic':
            source.angle = openmc.stats.Isotropic()
        source.angle = None
        source.energy = None
        source.strength = None
        if source_data['particle_type'] == 'neutron':
            source.particle = 'neutron'

        # #

        # # angular bins in [0, pi)
        # pbins = np.cos(np.linspace(0, np.pi, 37))

        # # energy and flux values from tables
        # evalues = (fng_source_fr[0] + fng_source_fr[0]) / 2
        # fvalues = fng_source_fr[2:]

        # # yield values for strengths
        # yields = np.sum(fvalues, axis=-1) * np.diff(pbins)
        # yields /= np.sum(yields)

        # # azimuthal values
        # phi = openmc.stats.Uniform(a=0, b=2*np.pi)

        # all_sources = []
        # for i, angle in enumerate(pbins[:-1]):

        #     mu = openmc.stats.Uniform(a=pbins[i+1], b=pbins[i])

        #     space = openmc.stats.Point(center)
        #     angle = openmc.stats.PolarAzimuthal(
        #         mu=mu, phi=phi, reference_uvw=reference_uvw)
        #     energy = openmc.stats.Tabular(
        #         evalues, fvalues[i], interpolation='linear-linear')
        #     strength = yields[i]

        #     my_source = openmc.IndependentSource(
        #         space=space, angle=angle, energy=energy, strength=strength, particle='neutron')

        #     all_sources.append(my_source)

        # return all_sources

        # return source_data
