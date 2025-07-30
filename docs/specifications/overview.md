# Benchmark Specification Overview

The **OpenMC Fusion Benchmarks (OFB)** project uses a structured, YAML-based specification format to define every component of a radiation transport benchmark. This approach ensures **clarity, reproducibility, and automation** in defining, running, and analyzing benchmarks.

Each benchmark is defined by a `specifications.yaml` file that is **validated against a strict schema (`benchmark_schema.yaml`)** to enforce consistency and completeness across the benchmark suite.

---

## Specification Components

The `specifications.yaml` file captures all essential aspects of a benchmark, including:

- **Metadata**  
  General information such as benchmark name, description, references, authors, and version.

- **Geometry**  
  CAD-based geometry definitions, including references to CAD files and meshing parameters.

- **Materials**  
  Composition, temperature, density, and other nuclear properties defined in a structured format.

- **Source**  
  Neutron or photon source definitions, including energy, spatial, and angular distributions.

- **Simulation Parameters**  
  Code-independent description of simulation settings (e.g., tally definitions, particles, run modes).

- **Results**  
  Expected or reference results (e.g., experimental data, published simulations) to be used for comparison or validation.

- **Postprocessing Instructions**  
  Optional definitions of derived quantities, statistical metrics, or automatic report generation steps.

---

## Schema Validation

To guarantee interoperability and catch user errors early, every `specifications.yaml` file must conform to the [`benchmark_schema.yaml`](../benchmark_schema.yaml). The schema:

- Enforces required fields and correct types
- Validates units, formats, and structure
- Allows custom extensions while preserving core validation

Validation is automatically handled by the OFB Python API.

---

## Why This Matters

- **Consistency** across all benchmarks  
- **Automation** of modeling, simulation, and analysis workflows  
- **Comparability** of results across codes and experiments  
- **Modularity** to support method testing and rapid development

---

## 📖 Learn More

- [Schema Reference](schema-reference.md) — detailed documentation of every schema section  
- [Examples](../benchmarks.md) — browse real benchmark specifications  
- [Workflows](../workflows/define-benchmark.md) — how specifications fit into modeling and analysis pipelines