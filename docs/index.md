# Openmc Fusion Benchmarks

Welcome to the **OpenMC Fusion Benchmarks** project — a modular, code-agnostic, and automation-ready repository for defining, executing, and analyzing radiation transport benchmarks in fusion energy systems. Benchmarks are described through a rigorous, schema-driven YAML specification, and include detailed **CAD-based geometries** with automatic meshing support. The framework is designed for **easy integration and testing of new neutronics methods**, facilitating rapid development, comparison, and validation across codes, workflows, and datasets.


:::{div} .cards

:::{div} .card
[a href="quickstart.md"]
![Quickstart](_static/icons/rocket-24.svg){width="60"}

### Python API
Install, validate and run a benchmark.
[/a]
:::

:::{div} .card
[a href="specifications/overview.md"]
![Specification Format](_static/icons/gear-24.svg){width="60"}

### Benchmark Specification
Learn about the schema-driven format to standardize a benchmark.
[/a]
:::

:::{div} .card
[a href="benchmark_collection/index.md"]
![Benchmarks](_static/icons/list-unordered-24.svg){width="60"}

### Available Benchmarks
Explore the library of validated fusion neutronics benchmarks.
[/a]
:::

:::

<!-- Shortcut cards
<div class="cards">

<div class="card">
  <a href="quickstart.html">
    <img src="_static/icons/rocket-24.svg" alt="Quickstart" width="60">
    <h3>Python API</h3>
    <p>Install, validate and run a benchmark.</p>
  </a>
</div>

<div class="card">
  <a href="specifications/overview.html">
    <img src="_static/icons/gear-24.svg" alt="Specification Format" width="60">
    <h3>Benchmark Specification</h3>
    <p>Learn about the schema-driven format to standardize a benchmark.</p>
  </a>
</div>

<div class="card">
  <a href="benchmark_collection/index.html">
    <img src="_static/icons/list-unordered-24.svg" alt="Benchmarks" width="60">
    <h3>Available Benchmarks</h3>
    <p>Explore the library of validated fusion neutronics benchmarks.</p>
  </a>
</div>

</div> -->


## Sections
```{toctree}
:maxdepth: 1

intro
quickstart
specifications/index
benchmark_collection/index
```