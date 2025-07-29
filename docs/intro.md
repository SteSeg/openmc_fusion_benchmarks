# Introduction

**OpenMC Fusion Benchmarks** builds on a modular and schema-driven approach to radiation transport benchmarking, with a focus on reproducibility, extensibility, and automation. Each benchmark is fully defined by a standardized `specifications.yaml` file, which captures all aspects of the model — including CAD-based geometry, materials, source definitions, simulation parameters, and reference results.

This approach enables consistent validation, execution, and postprocessing of benchmarks across tools and workflows. The repository is also designed to facilitate the implementation and testing of new neutronics methods in a code-agnostic environment.

---

## 🔧 Key Features

- **Standardized benchmark definitions** via `specifications.yaml`
- **Validation** of `specifications.yaml` against a strict `benchmark_schema.yaml`
- **CAD-based geometries** and automatic meshing tools
- **Automated workflow** for benchmark building, running and analysis through Python APIs
- **Unified results format** for comparing experimental, historical, and simulated data
- **Embedded Uncertainty Quantification** for *best estimate plus uncertainty* approach
- **Benchmark and results libraries** with descriptions, *specifications* and results

---

## 🚀 Get Started

- [Quickstart Guide](quickstart.md)
- [Available Benchmarks](benchmarks.md)
- [Benchmark Specification Format](benchmark-spec/overview.md)
- [Workflows: from definition to analysis](workflows/define-benchmark.md)
- [Python API](api.md)
- [Example Notebooks](notebooks.md)

---

## 💬 How to Contribute

We welcome contributions of new benchmarks, improvements to the schema, and extensions to the tools and analysis pipelines. See our [Contributing Guidelines](https://github.com/your-org/your-repo/blob/main/CONTRIBUTING.md) for more.

For questions, ideas, or bug reports, please open an [issue](https://github.com/your-org/your-repo/issues) or reach out to the maintainers.

---

## 📄 License and Citation

This project is open source under the [MIT License](https://github.com/your-org/your-repo/blob/main/LICENSE).

If you use this benchmark format or collection in your work, please cite: