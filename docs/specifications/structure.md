# Structure

Each benchmark in Openmc Fusion Benchmarks (OFB) is defined by a single specifications.yaml file located at the root of its benchmark folder:
```
src/openmc_fusion_benchmarks/benchmarks/benchmark_name/
                                               └── specifications.yaml
```

This file is modular and schema-driven, ensuring consistent structure and validation across all benchmarks. Below is a description of each main section in the YAML file, along with minimal examples.

## Sections Overview

### Metadata  
General information such as benchmark name, description, references, authors, and version. 
Example:
```yaml
```

### Materials
It is a list of `Material` objects. Each one contains, composition, temperature, density, and other nuclear properties defined in a structured format. 
Example:
```yaml
```

### Geometry
The `geometry` object links to a `.step` file located in the repository’s `lfs` _submodule_ and includes suggested meshing parameters, such as the maximum element size.
Example: 

```yaml
```

### Sources

```yaml
```

### Settings

```yaml
```

### Tallies

```yaml
```

### Uncertainty Quantification

```yaml
```

### Irradiation Schedule

## Notes

- All sections are optional unless required by the [schema](schema.md).

- All paths are relative to the benchmark folder.

- Additional keys may be added to support custom workflows, but they will be ignored during validation unless explicitly included in the schema.

- For a section-by-section explanation, see overview.md.