# Overview

The **OpenMC Fusion Benchmarks (OFB)** project uses a structured, YAML-based specification format to define every component of a radiation transport benchmark. This approach ensures **clarity, reproducibility, and automation** in defining, running, and analyzing benchmarks.

Each benchmark is defined by a `specifications.yaml` file that is **validated against a strict schema (`benchmark_schema.yaml`)** to enforce consistency and completeness across the benchmark suite.

---

## Specifications Components

The `specifications.yaml` file captures all essential aspects of a benchmark, including:

- **Metadata**  
  General information such as benchmark name, description, references, authors, and version.
  
- **Materials**  
  Composition, temperature, density, and other nuclear properties defined in a structured format.

- **Geometry**  
  CAD-based geometry definitions, including references to CAD files and meshing parameters.

- **Sources**  
  Neutron or photon source definitions, including energy, spatial, and angular distributions.

- **Settings**  
  Transport code configuration such as particle count, batches, and other run control parameters.

- **Tallies**  
  Definition of observables (e.g., flux, dose) with filters and expected data structure.

- **Uncertainty Quantification (Optional)**  
  Setup for input perturbations, sampling, and uncertainty propagation metrics.

- **Irradiation Schedule (Optional)**  
  Time-dependent irradiation and cooling steps for activation and shutdown dose rate analysis.

---

## Schema Validation

To guarantee interoperability and catch user errors early, every `specifications.yaml` file must conform to the `benchmark_schema.yaml`. The schema:

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

- [Specifications Structure](structure.md) — detailed documentation of `specifications.yaml` structure and syntax
- [Benchmark Schema](schema.md) — documentation of the `benchmark_schema.yaml` and _specifications_ validation