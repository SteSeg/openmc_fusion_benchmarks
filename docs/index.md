# Openmc Fusion Benchmarks

Welcome to the **OpenMC Fusion Benchmarks** project — a modular, code-agnostic, and automation-ready repository for defining, executing, and analyzing radiation transport benchmarks in fusion energy systems. Benchmarks are described through a rigorous, schema-driven YAML specification, and include detailed **CAD-based geometries** with automatic meshing support. The framework is designed for **easy integration and testing of new neutronics methods**, facilitating rapid development, comparison, and validation across codes, workflows, and datasets.

:::{grid} 3
:gutter: 3

:::{grid-item-card}
:octicon:`gear` **Benchmark Specs**
^
See the structure of schema-based specifications.
+++
[Go to specs](benchmark-spec/overview.md)
:::

:::{grid-item-card}
:octicon:`checklist` **Available Benchmarks**
^
Browse the validated fusion benchmarks.
+++
[Explore benchmarks](benchmarks.md)
:::

:::{grid-item-card}
:octicon:`code` **Python API**
^
Use OFB programmatically to load and simulate.
+++
[Read API docs](api.md)
:::
:::

## Sections
```{toctree}
:maxdepth: 1

intro
quickstart
specifications/index
benchmark_collection/index
```