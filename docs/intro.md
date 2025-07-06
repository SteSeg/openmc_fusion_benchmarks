# Indroduction

**OpenMC Fusion Benchmarks (OFB)** is a platform for **verification and validation (V&V)** of neutronics simulations in fusion energy research. It focuses on **fusion-relevant integral benchmarks** that use **CAD-based geometries**, enabling support for modern transport workflows.

OFB provides a fully automated pipeline for:

- Model setup  
- Simulation execution  
- Postprocessing  
- Visualization  
- Analysis  

It also includes a growing **database of experimental and numerical results** for quick comparison. Contributions to this database are encouraged and supported through an automated submission workflow.

---
## Installation
Currently, the way to install *ofb* is through:
```shell
git clone --recurse-submodules https://github.com/eepeterson/openmc_fusion_benchmarks.git
cd openmc_fusion_benchmarks
pip install .
```

---

## Validation Framework

OFB promotes a rigorous and standardized validation process. Each benchmark begins with a clearly defined **specification**, formally described as:

> *“The minimum amount of technical information necessary to unambiguously model a benchmark and collect results.”*

Each benchmark is defined in a `specification.yml` file, which includes all information about geometry, materials, sources, and results.

To ensure compliance and consistency, OFB provides a `benchmark_schema.yml` file that defines the required structure and syntax of a valid specification. The OFB Python API can be used to:

- Load and inspect specification files  
- Validate them against the schema  

---

## Geometry Integration

Benchmark *specifications* point to **CAD geometry files**, which serve as the basis for simulation:

- CAD files can be directly meshed for **unstructured mesh transport workflows**  
- Alternatively, CAD-to-CSG conversion tools can be integrated for validating geometry translation workflows  

This flexibility allows the same benchmark to support both mesh-based and CSG-based simulations, making it ideal for code-to-code comparisons and geometry tool validation.


```{tableofcontents}
```