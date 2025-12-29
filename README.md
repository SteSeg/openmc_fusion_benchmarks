[![License](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)
[![CI testing](https://github.com/SteSeg/openmc_fusion_benchmarks/actions/workflows/ci.yml/badge.svg?branch=add_ci)](https://github.com/SteSeg/openmc_fusion_benchmarks/workflows/ci.yml)
[![Code Coverage](https://coveralls.io/repos/github/SteSeg/openmc_fusion_benchmarks/badge.svg?branch=add_ci)](https://coveralls.io/github/SteSeg/openmc_fusion_benchmarks?branch=add_ci)

# OpenMC Fusion Benchmarks

**Next-generation CAD-based V&V repository** for fusion neutronics with schema-validated, code-agnostic benchmark definitions.

## Key Features

- ✅ **Schema-validated specifications** - Every benchmark validated against [`benchmark_schema.yaml`](src/openmc_fusion_benchmarks/benchmarks/benchmark_schema.yaml)
- 🔧 **CAD-based geometry** - Native CAD files automatically meshed to DAGMC
- 🔄 **Code-agnostic** - Same `specifications.yaml` → reproducible across any transport code
- 📊 **Built-in results database** - Experimental and computational results packaged with the repository

## Installation

```bash
pip install -e .
```

Requirements: Python ≥3.7, OpenMC ≥0.14.0

## Quick Start

**Run a benchmark:**
```python
from openmc_fusion_benchmarks import OpenmcBenchmark

benchmark = OpenmcBenchmark("oktavian_al")
benchmark.run()
```

**Access results database:**
```python
from openmc_fusion_benchmarks import BenchmarkResults

# Load experimental data
exp = BenchmarkResults.from_database("oktavian_al", "experiment.h5")

# Load your simulation results  
sim = BenchmarkResults.from_file("benchmark_results.h5")

# Compare
tally = sim.get_tally("neutron_spectrum")
```

## How It Works

Each benchmark is defined by a **schema-validated `specifications.yaml`** file:
- **CAD geometry** automatically converted to DAGMC mesh
- **Materials, sources, tallies** validated against schema
- Same specification → reproducible across different codes

**Example structure:**
```yaml
metadata:
  title: OKTAVIAN AL Benchmark
  category: fusion
materials:
  - name: Aluminum
    composition: {...}
geometry:
  cad_file: oktavian_a.step  # CAD-based!
  meshing: {...}
sources: [...]
tallies: [...]
```

Validate any benchmark:
```python
from openmc_fusion_benchmarks import validate_benchmark
validate_benchmark("oktavian_al")  # Must pass schema validation
```

## Available Benchmarks

- **OKTAVIAN** - 14 MeV neutron leakage from aluminum sphere
- **FNG Streaming** - Neutron streaming experiments
- *More in development*

## Contributing

Add a new benchmark: Create `specifications.yaml` + validate + add experimental data → Pull request

Contribute results: Run benchmark → results auto-saved → Pull request

## Documentation

[Read the Docs](https://openmc-fusion-benchmarks.readthedocs.io)

## License & Contact

MIT License | **Stefano Segantin** (segantin@psfc.mit.edu) | Plasma Science and Fusion Center, MIT
