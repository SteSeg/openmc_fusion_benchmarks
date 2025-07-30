# Structure

Each benchmark in Openmc Fusion Benchmarks (OFB) is defined by a single specifications.yaml file located at the root of its benchmark folder:

```
src/openmc_fusion_benchmarks/benchmarks/benchmark_name/
                                               └── specifications.yaml
```

This modular, schema-driven YAML file ensures consistency and validation across all benchmarks. Each section is described below with minimal examples. The format is human-readable, transport-code agnostic, and can be parsed by the OFB Python API to automatically generate code-specific models.

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
The `Geometry` object links to a `.step` file located in the repository’s `lfs` _submodule_ and includes suggested meshing parameters, such as the maximum element size.
Example: 

```yaml
```

### Sources
List of `Source` objects. Provides specification of the neutron or photon source, including spatial, angular, and energy distributions.

```yaml
```

### Settings
Code-independent configuration of simulation controls, such as number of particles, batches, source distribution settings, and physics options. These parameters define how the simulation should be run, regardless of the underlying transport code.

```yaml
```

### Tallies
List of `Tally` objects. Definition of observables to be recorded during the simulation (e.g., flux, dose, reaction rates), including spatial, energy, and material filters. Tallies are structured to ensure consistent output formats across different transport codes.

```yaml
```

### Uncertainty Quantification
Setup for input perturbations, sampling strategies, and metrics for uncertainty propagation.
```yaml
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