# Branch description and todo

## Rationale and structure

This branch implements a first, end-to-end validation and scoring pipeline that goes from a single comparison point to a full benchmark score. The goal is to provide a consistent, repeatable framework for comparing calculated results to experimental/reference results.

### Scoring flow

1) A single comparison point represents one value in a tally, such as:
- One energy bin of a spectrum
- One foil reaction rate value
- One leakage value

2) Point-level metrics are computed for each comparison point.

3) Points are aggregated into an observable (a single tally), yielding observable-level metrics.

4) Observables are aggregated into a benchmark-level comparison, producing a coarse status and a rudimentary score.

### Point-level metrics (PointMetrics)

For each point, with calculated value C, experimental value E, and uncertainties u_C, u_E:

- C/E: C / E
- Relative deviation: (C - E) / E
- Absolute deviation: |C - E|
- Combined uncertainty: sqrt(u_E^2 + u_C^2)
- Normalized residual: (C - E) / sqrt(u_E^2 + u_C^2)
- chi2 contribution: (C - E)^2 / (u_E^2 + u_C^2)

Each point is classified by |normalized residual| using 1, 2, 3 sigma bands:
- OK: |z| <= 2
- WARNING: 2 < |z| <= 3
- OUTLIER: |z| > 3

Implementation: [src/openmc_fusion_benchmarks/validation/metrics.py](src/openmc_fusion_benchmarks/validation/metrics.py)

### Observable-level metrics (ObservableComparison)

Given all points for a tally, observable-level aggregates include:
- mean_bias: mean of relative deviation
- mean_abs_relative_deviation
- rms_relative_deviation
- mean_abs_normalized_residual
- reduced_chi2
- fraction_within_1sigma, fraction_within_2sigma, fraction_within_3sigma
- pass_count, warning_count, outlier_count

Implementation: [src/openmc_fusion_benchmarks/validation/comparison.py](src/openmc_fusion_benchmarks/validation/comparison.py)

### Benchmark-level aggregation and grading (BenchmarkComparison)

Observables are aggregated into benchmark-level metrics:
- weighted_mean_bias
- weighted_rms_relative_deviation
- global_reduced_chi2
- outlier_fraction
- total_point_count

A rudimentary grading layer assigns:
- benchmark_status: ACCEPTABLE, BORDERLINE, PROBLEMATIC
- dashboard_score: 0 to 100

The grading uses thresholds and linear penalties for:
- weighted_rms_relative_deviation
- global_reduced_chi2
- outlier_fraction

Implementation: [src/openmc_fusion_benchmarks/validation/comparison.py](src/openmc_fusion_benchmarks/validation/comparison.py) and [src/openmc_fusion_benchmarks/validation/model.py](src/openmc_fusion_benchmarks/validation/model.py)

## Usage

### Basic workflow

1) Load calculated results and reference results into BenchmarkResults.
2) Call compare_benchmark_results.
3) Inspect benchmark-level metrics and score.

Example:

```python
from openmc_fusion_benchmarks.validation import compare_benchmark_results
from openmc_fusion_benchmarks.benchmark_results import BenchmarkResults

exp = BenchmarkResults.from_file("reference_results.h5")
calc = BenchmarkResults.from_file("benchmark_results.h5")

bench = compare_benchmark_results(
    benchmark_id="fng",
    code_name="openmc",
    code_version="0.14.0",
    reference_source="experiment_xyz",
    experiment=exp,
    calculation=calc,
    tally_names=["tally_1", "tally_2"],  # optional
    observable_type_map={
        "tally_1": "spectrum",
        "tally_2": "reaction_rate",
    },
    flatten_dims_map={
        "tally_1": ["energy", "surface", "nuclide", "score"],
        "tally_2": ["energy", "nuclide", "score"],
    },
)

print(bench.benchmark_status, bench.dashboard_score)
print(bench.weighted_rms_relative_deviation, bench.global_reduced_chi2, bench.outlier_fraction)
```

If you already have BaseTally objects:

```python
from openmc_fusion_benchmarks.validation import compare_tallies

obs = compare_tallies(
    observable_name="tally_1",
    observable_type="spectrum",
    experiment=exp_tally,
    calculation=calc_tally,
    flatten_dims=["energy", "nuclide", "score"],
)
```

## API map

### Core model objects
- [src/openmc_fusion_benchmarks/validation/model.py](src/openmc_fusion_benchmarks/validation/model.py)
  - DataPoint
  - PointComparison
  - ObservableComparison
  - BenchmarkComparison
  - PointMetrics

### Core computation
- [src/openmc_fusion_benchmarks/validation/metrics.py](src/openmc_fusion_benchmarks/validation/metrics.py)
  - compute_point_metrics
- [src/openmc_fusion_benchmarks/validation/comparison.py](src/openmc_fusion_benchmarks/validation/comparison.py)
  - compare_point_set
  - aggregate_benchmark

### Adapters for OFB results
- [src/openmc_fusion_benchmarks/validation/adapters.py](src/openmc_fusion_benchmarks/validation/adapters.py)
  - datapoints_from_tally
  - compare_tallies
  - compare_benchmark_results

### High-level flow

compare_benchmark_results:
- loads each tally with BenchmarkResults.get_tally
- converts tallies to DataPoint lists via datapoints_from_tally
- builds ObservableComparison with compare_point_set
- aggregates to BenchmarkComparison with aggregate_benchmark

## What is left to do

- Code review and cleanup
- Add unit tests for validation adapters and scoring thresholds
- Replace rudimentary thresholds with benchmark-specific and statistically justified thresholds
- Calibrate score weights with real benchmark data
- Add report generation (tables, plots, summary markdown or PDF)
- Decide whether to keep or expose grading configuration (thresholds and weights) in the public API
