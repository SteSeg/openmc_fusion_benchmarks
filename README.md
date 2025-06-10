[![License](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)
[![CI testing](https://github.com/SteSeg/openmc_fusion_benchmarks/actions/workflows/ci.yml/badge.svg?branch=add_ci)](https://github.com/SteSeg/openmc_fusion_benchmarks/workflows/ci.yml)
[![Code Coverage](https://coveralls.io/repos/github/SteSeg/openmc_fusion_benchmarks/badge.svg?branch=add_ci)](https://coveralls.io/github/SteSeg/openmc_fusion_benchmarks?branch=add_ci)

# OpenMC Fusion Benchmarks

Here the full [Documentation](https://openmc-fusion-benchmarks.readthedocs.io/en/latest/intro.html).

A CAD-based collection of benchmark models for validating and verifying **nuclear fusion neutronics simulations**.
This repository provides standardized geometries, sources, materials, and results to facilitate comparison and reproducibility across codes and experiments.

## 💡 Motivation

Reliable neutronics simulations are essential in the design of fusion reactors. This project collects and organizes benchmark problems, enabling:

- Rigorous benchmark definition
- Code verification (e.g., OpenMC)
- Fusion neutronics design validation (e.g., for blankets and shields)
- Consistent documentation of assumptions, inputs, and outputs
- Comparisons against experimental data when available
- Automated workflow

## 📦 Features
- ✅ Benchmark **specifications** yaml files for complete and self-contained benchmark description 
- ✅ A *unified* **schema** yaml file ensures *specifications* validity and consistency
- ✅ **CAD-based** geometries for V&V *meshing tools*, *unstructured mesh transport*, etc.
- ✅ Processed tally data saved in HDF5 format using `xarray`
- ✅ A **database** of experimental and computational results
- 🔧 Python API to load *specifications* and build a transport code model (currently available for (OpenMC)[https://docs.openmc.org/en/stable/])
- 🔧 Python API to load analyze and compare simulation results and database results

## 🛠 Installation

Clone the repository and install dependencies:

```bash
git clone --recursive-submodules https://github.com/eepeterson/openmc_fusion_benchmarks.git
cd openmc-fusion-benchmarks
pip install -e .[dev]