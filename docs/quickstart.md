# Quickstart Guide

This guide walks you through the basic steps to install the package, load a benchmark, run a simulation, and view results — using the **OpenMC Fusion Benchmarks** framework.

> ⚠️ This guide assumes you have Python 3.9+ and a working OpenMC installation. For OpenMC setup, refer to the [OpenMC documentation](https://docs.openmc.org/en/stable/).

---

## 1. Install the Package

Clone the repository and install dependencies in a clean Python environment:

```shell
git clone --recurse-submodules https://github.com/eepeterson/openmc_fusion_benchmarks.git
cd openmc_fusion_benchmarks
pip install .
```

You may wish to make use of a virtual environment using [Conda](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html), [Mamba](https://mamba.readthedocs.io/en/latest/user_guide/mamba.html) or [Venv](https://docs.python.org/3/library/venv.html).


## 2. Run a Benchmark Simulation

Minimal working example of instantiating and running a benchmark with the [OpenMC](https://docs.openmc.org/en/stable/) transport code. 

```python
import openmc_fusion_benchmarks as ofb

benchmark = ofb.OpenmcBenchmark(name='oktavian_al')
benchmark.run()
```

Running in uncertainty quantification mode:

```python
import openmc_fusion_benchmarks as ofb

benchmark = ofb.OpenmcBenchmark(name='oktavian_al')
benchmark.run(uq=True)
```