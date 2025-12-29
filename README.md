[![License](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)
[![CI testing](https://github.com/SteSeg/openmc_fusion_benchmarks/actions/workflows/ci.yml/badge.svg?branch=add_ci)](https://github.com/SteSeg/openmc_fusion_benchmarks/workflows/ci.yml)
[![Code Coverage](https://coveralls.io/repos/github/SteSeg/openmc_fusion_benchmarks/badge.svg?branch=add_ci)](https://coveralls.io/github/SteSeg/openmc_fusion_benchmarks?branch=add_ci)

# OpenMC Fusion Benchmarks

A next-generation Verification & Validation (V&V) repository for fusion neutronics featuring **rigorous, code-agnostic benchmark definitions** validated against a formal schema.

## What Makes This Different?

Traditional benchmark repositories mix code-specific implementations with experimental data, making it difficult to:
- Verify benchmark definitions are complete and consistent
- Implement benchmarks in different transport codes
- Ensure reproducibility across codes and versions

**This repository separates concerns** through:

### 1. **Schema-Validated Benchmark Specifications** 
Each benchmark is defined in a code-agnostic `specifications.yaml` file that serves as the **single source of truth**. Every specification is automatically validated against [`benchmark_schema.yaml`](src/openmc_fusion_benchmarks/benchmarks/benchmark_schema.yaml), ensuring:
- **Completeness**: All required fields (materials, geometry, sources, tallies, settings) are present
- **Consistency**: Data types, units, and formats follow a strict schema
- **Reproducibility**: Same specification → same benchmark, regardless of implementation
- **Interoperability**: Any transport code can implement the same benchmark from the same specification

### 2. **Built-in Reference Database**
Packaged experimental and computational results for immediate validation, accessible via simple Python API.

### 3. **Automated Workflows**
From specification to simulation to validation, with minimal manual intervention.

---

## Quick Start

### Installation

```bash
# Basic installation
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

**Requirements**: Python ≥3.7, OpenMC ≥0.14.0

### Run a Benchmark in 3 Lines

```python
from openmc_fusion_benchmarks import OpenmcBenchmark

# Instantiate benchmark from validated specification
benchmark = OpenmcBenchmark("oktavian_al")

# Run simulation
benchmark.run()
```

That's it! The benchmark is automatically constructed from the validated `specifications.yaml` file:
- Materials are built from composition data
- Geometry is generated from CAD files with specified meshing parameters
- Sources are created with angular-energy distributions
- Tallies are configured according to experimental measurements
- Results are saved in a standardized format

### View Benchmark Metadata

```python
print(benchmark.metadata)
```

Output:
```
📘 Title: OKTAVIAN AL Benchmark
🔖 Type: experimental
📂 Category: fusion
🧮 Version: 1.0.0
📝 Description: The Osaka Aluminium Sphere Benchmark Experiment...
📅 Date: 1988-12-22
📍 Location:
   - Facility: OKTAVIAN
   - City: Osaka
   - Country: Japan
🔗 References: ...
👥 Authors: ...
```

---

## The Schema-Driven Philosophy

### Benchmark Definition Flow

```
Experimental Data → specifications.yaml → Schema Validation → ✓ Valid Benchmark
                                       ↘ Validation Errors → Fix & Retry
```

Every benchmark **must** pass schema validation:

```python
from openmc_fusion_benchmarks import validate_benchmark

# Automatically validates against benchmark_schema.yaml
validate_benchmark("oktavian_al")  # Raises exception if invalid
```

### What the Schema Enforces

The [`benchmark_schema.yaml`](src/openmc_fusion_benchmarks/benchmarks/benchmark_schema.yaml) defines the complete structure:

- **Metadata**: Title, type, category, version, references, authors, location
- **Materials**: Composition (nuclide/element), density, fraction type (atomic/weight)
- **Geometry**: CAD file, meshing parameters, material tags
- **Sources**: Particle type, spatial distribution, angular-energy distributions
- **Settings**: Run mode, batch/particle counts, physics options
- **Tallies**: Filters (cell/material/surface/energy), scores, particles
- **Uncertainty Quantification** (optional): Nuclides, realizations, perturbation methods

### Example: Material Specification

```yaml
materials:
  - id: 1
    name: Aluminum
    composition:
      composition_type: nuclide  # Must be 'nuclide' or 'element'
      fraction_type: atomic       # Must be 'atomic' or 'weight'
      data:
        Al27: 0.9975488
        Si28: 0.001329808
        # ... validated against schema
    density:
      value: 1.223
      units: g/cm3  # Units are enforced
```

If you violate the schema (e.g., use `fraction_type: "volumetric"`), validation **fails immediately** with a clear error message.

---

## Access the Results Database

The repository includes a built-in database of experimental and computational results:

```python
from openmc_fusion_benchmarks import list_database_benchmarks, BenchmarkResults

# List available benchmarks
benchmarks = list_database_benchmarks()
print(benchmarks)  # ['oktavian_al', 'fng_str_heating', ...]

# Load experimental results
exp_results = BenchmarkResults.from_database("oktavian_al", "experiment.h5")
tally_data = exp_results.get_tally("neutron_leakage_spectrum")
```

### Compare Your Results

```python
# Run your simulation
benchmark = OpenmcBenchmark("oktavian_al")
benchmark.run()

# Load your results
my_results = BenchmarkResults.from_file("benchmark_results.h5")

# Load reference experimental data
exp_results = BenchmarkResults.from_database("oktavian_al", "experiment.h5")

# Compare
import matplotlib.pyplot as plt
plt.errorbar(my_results.get_tally("spectrum")['mean'], label="My Simulation")
plt.errorbar(exp_results.get_tally("spectrum")['mean'], label="Experiment")
plt.legend()
```

---

## Repository Structure

```
openmc_fusion_benchmarks/
├── src/openmc_fusion_benchmarks/
│   ├── benchmarks/
│   │   ├── benchmark_schema.yaml      # Ground truth schema
│   │   ├── oktavian_al/
│   │   │   └── specifications.yaml    # Code-agnostic benchmark definition
│   │   └── fng_str_heating/
│   │       └── specifications.yaml
│   ├── benchmark.py                   # OpenmcBenchmark class
│   ├── validate.py                    # Schema validation
│   ├── database.py                    # Results database access
│   └── results_database/              # Packaged experimental/computational results
│       ├── oktavian_al/
│       │   ├── experiment.h5
│       │   └── openmc-0.14.0_endfb80.h5
│       └── fng_str_heating/
│           └── experiment.h5
├── test/                              # 80% test coverage
└── docs/                              # Documentation
```

---

## Available Benchmarks

- **OKTAVIAN Aluminum Sphere**: 14 MeV neutron leakage from Al sphere (Osaka, 1988)
- **FNG Streaming**: Neutron streaming through steel/concrete assemblies (Frascati)
- *More benchmarks in development*

---

## Advanced Features

### Uncertainty Quantification

Run Total Monte Carlo (TMC) uncertainty propagation:

```python
benchmark = OpenmcBenchmark("oktavian_al")
benchmark.run(uq=True)  # Performs nuclear data uncertainty quantification
```

### Validate All Benchmarks

```bash
python scripts/validate_all_benchmark.py
```

---

## Contributing

### Add a New Benchmark

1. **Create `specifications.yaml`** following the schema structure
2. **Validate** against `benchmark_schema.yaml`:
   ```python
   from openmc_fusion_benchmarks import validate_benchmark
   validate_benchmark("my_new_benchmark")
   ```
3. **Add experimental results** to `results_database/my_new_benchmark/experiment.h5`
4. **Submit a pull request**

### Contribute Simulation Results

1. Run an existing benchmark
2. Results are automatically saved in standardized format
3. Submit `benchmark_results.h5` via pull request to `results_database/`

---

## Documentation

Full documentation available at: [Read the Docs](https://openmc-fusion-benchmarks.readthedocs.io)

---

## Citation

If you use this repository, please cite:

```bibtex
@software{openmc_fusion_benchmarks,
  author = {Segantin, Stefano},
  title = {OpenMC Fusion Benchmarks: Schema-Validated V\&V Repository},
  year = {2024},
  url = {https://github.com/SteSeg/openmc_fusion_benchmarks}
}
```

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Contact

**Stefano Segantin** - segantin@psfc.mit.edu

Plasma Science and Fusion Center, MIT
