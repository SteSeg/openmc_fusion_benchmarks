# Welcome to Openmc Fusion Benchmarks Documentation

# Fusion Neutronics Benchmark Collection

Welcome to the **Fusion Neutronics Benchmark Collection** — a code-agnostic, schema-driven, and automation-ready repository for defining, running, and analyzing radiation transport benchmarks in fusion energy systems.

This repository introduces a **standardized YAML-based specification format** that rigorously describes all components of a benchmark: geometry, materials, source, simulation parameters, and reference results. It enables full automation from model creation to simulation execution, postprocessing, and reporting — independent of the transport code used.

---

## 🔧 Key Features

- ✅ **Specification-based benchmark definitions** via `specifications.yaml`
- ✅ **Validation** against a strict `benchmark_schema.yaml`
- ✅ **Automatic meshing** from CAD geometries
- ✅ **Python API** for building, running, and analyzing benchmarks
- ✅ **Unified results format** for comparing experimental, historical, and simulated data
- ✅ **Advanced workflows**: uncertainty quantification, shutdown dose rate, automated reports
- ✅ **Reusable benchmark library** with descriptions, models, and Jupyter notebooks

---

## 🚀 Get Started

- 👉 [Quickstart Guide](quickstart.md)
- 📚 [Available Benchmarks](benchmarks.md)
- 🧱 [Benchmark Specification Format](benchmark-spec/overview.md)
- 🛠 [Workflows: from definition to analysis](workflows/define-benchmark.md)
- 🧰 [Python API](api.md)
- 📓 [Example Notebooks](notebooks.md)

---

## 💬 How to Contribute

We welcome contributions of new benchmarks, improvements to the schema, and code extensions. See [Contributing Guidelines](https://github.com/your-org/your-repo/blob/main/CONTRIBUTING.md) for more.

For discussions or questions, open an [issue](https://github.com/your-org/your-repo/issues) or reach out to the maintainers.

---

## 📄 License and Citation

This project is open source under the [MIT License](https://github.com/your-org/your-repo/blob/main/LICENSE).

If you use this benchmark format or collection in your work, please cite:

## Sections
```{toctree}
:maxdepth: 2

intro
installation
benchmarks/index
```