# Structure

Each benchmark in Openmc Fusion Benchmarks (OFB) is defined by a single specifications.yaml file located at the root of its benchmark folder:

```
src/openmc_fusion_benchmarks/benchmarks/benchmark_name/
                                               └── specifications.yaml
```

The `specifications.yaml` file is at the core of each benchmark. It follows a **modular**, **schema-validated**, and **code-independent** structure, making benchmarks consistent, extensible, and easy to maintain. Designed to be **human-readable** and **automation-ready**, it enables the OFB Python API to generate transport-specific models directly from the specification. Each section is described below with minimal examples. Its modular design also supports future extensions for testing advanced neutronics workflows.

## Sections Overview

### Metadata  
General information such as benchmark name, description, references, authors, and version. 
Example:

```yaml
metadata:
  title: Example Benchmark
  type: experimental
  category: fusion
  version: 1.0.0
  description: >
    The Example Benchmark is just for documentation.
  date: "2025-01-01"
  location:
    facility: MIT
    city: Cambridge, MA
    country: US
  references:
    - title: "A Reference Paper"
      doi: "https://doi.org/a_doi_code"

```

### Materials
It is a list of `Material` objects. Each one contains, composition, temperature, density, and other nuclear properties defined in a structured format. 
Example:

```yaml
Materials:
  - id: 1
    name: Water
    composition:
        composition_type: element
        fraction_type: atomic
        data:
        H: 0.67
        O: 0.33
    density:
        value: 0.997
        units: g/cm3

  - id: 2
    name: Aluminum
    composition:
    composition_type: nuclide
    fraction_type: atomic
    data:
    Al27: 1.0
    density:
    value: 2.7
    units: g/cm3
```

### Geometry
The `Geometry` object links to a `.step` file located in the repository’s `lfs` _submodule_ and includes information on material assignment and suggested meshing parameters, such as the maximum element size.
Example: 

```yaml
geometry:
  cad_file: benchmark_name/benchmark_name.step
  meshing:
    global_mesh_size_min: 0.1
    global_mesh_size_max: 10
    volumes:
      - id: 1
        material: void
      - id: 3
        material: Aluminum
        mesh_size: 0.5
```

### Sources
List of `Source` objects. Provides specification of the neutron or photon source, including spatial, angular, and energy distributions.

```yaml
sources:
  - particle: neutron
    strength: 1.0
    spatial_distribution:
      type: point
      center: [0.0, 0.0, 0.0]
    angular_energy_distribution:
      polar_direction: [0.0, 1.0, 0.0]
      dims: ["angle", "energy"]
      angle: 
          bins: [0.0, 360.0]
          units: degrees
      energy:
        values: [0.1, 1, 100000, 10000000, 14100000]
        units: eV
        interpolation : linear-linear
      weights:
        - [0.01, 0.01, 0.01, 0.01, 0.95]
      strength:
        dims: ["angle"]
        data: [1.0]  # Must match len(angle)
        attrs:
          units:
          description: "Relative strength of source in each angular bin"
      attrs:
        units:
        description: "Neutron source probability distribution as a function of emission angle and energy"
```

### Settings
Code-independent configuration of simulation controls, such as number of particles, batches, source distribution settings, and physics options. These parameters define how the simulation should be run, regardless of the underlying transport code.

```yaml
settings:
  run_mode: fixed_source
  batches: 100
  particles_per_batch: 10000000
  photon_transport: true
```

### Tallies
List of `Tally` objects. Definition of observables to be recorded during the simulation (e.g., flux, dose, reaction rates), including spatial, energy, and material filters. Tallies are structured to ensure consistent output formats across different transport codes.

```yaml
  - name: neutron_spectrum
    description: "Total neutron current leaving the outer surface"
    particle: neutron
    scores: [current]
    filters:
      - type: surface
        values: [7]  # CAD-file surface ID
      - type: energy
        values: []
        units: particle/src/cm**2

  - name: photon_flux
    description: "Total photon current leaving the outer surface"
    particle: photon
    scores: [flux]
    filters:
      - type: cell
        values: [1]  # CAD-file cell ID
```

### Uncertainty Quantification
Setup for input perturbations, sampling strategies, and metrics for uncertainty propagation. Features a _total Monte Carlo_ engine and supports perturbation of main input data, such as nuclear data, material data (density, composition, temperature) and other relevant input data.

```yaml
uncertainty_quantification:
  - type: nuclear_data
    description: "Uncertainty in nuclear data"
    nuclides: [[Al27]]
    reactions: [total]
    realizations: [500]
```

### Irradiation Schedule
Time-dependent irradiation and cooling sequences for activation and shutdown dose rate analysis.

```yaml
```

## Notes

- All sections are optional unless required by the [schema](schema.md).

- All paths are relative to the benchmark folder.

- Additional keys may be added to support custom workflows, but they will be ignored during validation unless explicitly included in the schema.

- For a section-by-section explanation, see overview.md.