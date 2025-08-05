# Openmc Fusion Benchmarks

Welcome to the **OpenMC Fusion Benchmarks** project — a modular, code-agnostic, and automation-ready repository for defining, executing, and analyzing radiation transport benchmarks in fusion energy systems. Benchmarks are described through a rigorous, schema-driven YAML specification, and include detailed **CAD-based geometries** with automatic meshing support. The framework is designed for **easy integration and testing of new neutronics methods**, facilitating rapid development, comparison, and validation across codes, workflows, and datasets.

:::{grid} 2
:gutter: 3
:class: sd-equal-height

:::{grid-item-card}
:header: 🚀 Launch
Start your simulation workflow.
+++
[Quickstart Guide](quickstart.md)
:::

:::{grid-item-card}
:header: 📊 Results
Browse and compare benchmark data.
+++
[View Results](results.md)
:::

:::

<!-- :::{grid} 3
:gutter: 3

:::{grid-item-card}
:octicon:`gear` **Benchmark Specification**
^
Learn about the schema-driven YAML format used to define fusion neutronics benchmarks.
+++
[📄 Specification Format](benchmark-spec/overview.md)
:::

:::{grid-item-card}
:octicon:`list-unordered` **Available Benchmarks**
^
Explore the library of validated fusion benchmark experiments and simulations.
+++
[📚 Benchmarks List](benchmarks.md)
:::

:::{grid-item-card}
:octicon:`code` **Python API**
^
Use the OFB Python interface to load, validate, and run benchmarks.
+++
[🧰 API Reference](api.md)
:::

::: -->


## Sections
```{toctree}
:maxdepth: 1

intro
quickstart
specifications/index
benchmark_collection/index
```