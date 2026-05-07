from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Sequence

import numpy as np

from .model import (
    BenchmarkComparison,
    BenchmarkStatus,
    ComparisonPoint,
    DataPoint,
    ObservableComparison,
)
from .metrics import compute_point_metrics


def _as_datapoint(item) -> DataPoint:
    """
    Normalize an input item to DataPoint.

    Expected input can be:
    - DataPoint
    - dict with keys: value, uncertainty
    - xarray / object wrapper if you adapt it later
    """
    if isinstance(item, DataPoint):
        return item
    if isinstance(item, dict):
        return DataPoint(
            value=float(item["value"]),
            uncertainty=float(item["uncertainty"]),
        )
    raise TypeError(f"Unsupported point type: {type(item)!r}")


def compare_point_set(
    observable_name: str,
    observable_type: str,
    experiment_points: Sequence,
    calculation_points: Sequence,
    point_ids: Sequence[str] | None = None,
) -> ObservableComparison:
    """
    Compare one observable point-by-point.

    Parameters
    ----------
    observable_name:
        Name of the tally / observable.
    observable_type:
        Category such as reaction_rate, spectrum, leakage.
    experiment_points:
        Reference values.
    calculation_points:
        Calculated values from the transport code.
    point_ids:
        Optional point labels. If omitted, indices are used.
    """
    if len(experiment_points) != len(calculation_points):
        raise ValueError("Experiment and calculation point counts must match.")

    n = len(experiment_points)
    ids = point_ids if point_ids is not None else [str(i) for i in range(n)]

    if len(ids) != n:
        raise ValueError("point_ids length must match number of points.")

    points: list[ComparisonPoint] = []

    for pid, exp_raw, calc_raw in zip(ids, experiment_points, calculation_points):
        exp = _as_datapoint(exp_raw)
        calc = _as_datapoint(calc_raw)

        point = ComparisonPoint(
            id=str(pid),
            observable_type=observable_type,
            experiment=exp,
            calculation=calc,
        )
        point.metrics = compute_point_metrics(point)
        points.append(point)

    return _aggregate_observable(observable_name, observable_type, points)


def _aggregate_observable(
    name: str,
    observable_type: str,
    points: Sequence[ComparisonPoint],
) -> ObservableComparison:
    """Compute observable-level summary metrics."""
    if not points:
        return ObservableComparison(name=name, observable_type=observable_type, points=[])

    metrics = [p.metrics for p in points if p.metrics is not None]
    if len(metrics) != len(points):
        raise ValueError("All points must have computed metrics.")

    rel_dev = np.array([m.relative_deviation for m in metrics], dtype=float)
    norm_res = np.array([m.normalized_residual for m in metrics], dtype=float)
    chi2 = np.array([m.chi2_contribution for m in metrics], dtype=float)

    total = len(points)
    within_1 = np.sum(np.abs(norm_res) <= 1.0)
    within_2 = np.sum(np.abs(norm_res) <= 2.0)
    beyond_3 = np.sum(np.abs(norm_res) > 3.0)

    return ObservableComparison(
        name=name,
        observable_type=observable_type,
        points=list(points),
        mean_bias=float(np.mean(rel_dev)),
        mean_abs_relative_deviation=float(np.mean(np.abs(rel_dev))),
        rms_relative_deviation=float(np.sqrt(np.mean(rel_dev**2))),
        mean_abs_normalized_residual=float(np.mean(np.abs(norm_res))),
        reduced_chi2=float(np.sum(chi2) / max(total - 1, 1)),
        fraction_within_1sigma=float(within_1 / total),
        fraction_within_2sigma=float(within_2 / total),
        fraction_beyond_3sigma=float(beyond_3 / total),
        outlier_fraction=float(beyond_3 / total),
        pass_count=int(within_1),
        warning_count=int(within_2 - within_1),
        outlier_count=int(beyond_3),
    )


def aggregate_benchmark(
    benchmark_id: str,
    code_name: str,
    code_version: str,
    reference_source: str,
    observables: Sequence[ObservableComparison],
) -> BenchmarkComparison:
    """Aggregate observable-level comparisons into a benchmark-level result."""
    if not observables:
        return BenchmarkComparison(
            benchmark_id=benchmark_id,
            code_name=code_name,
            code_version=code_version,
            reference_source=reference_source,
            observables=[],
            benchmark_status=BenchmarkStatus.ACCEPTABLE,
        )

    total_points = sum(len(obs.points) for obs in observables)
    if total_points == 0:
        return BenchmarkComparison(
            benchmark_id=benchmark_id,
            code_name=code_name,
            code_version=code_version,
            reference_source=reference_source,
            observables=list(observables),
            benchmark_status=BenchmarkStatus.ACCEPTABLE,
        )

    weights = np.array([len(obs.points) for obs in observables], dtype=float)
    mean_biases = np.array([obs.mean_bias for obs in observables], dtype=float)
    rms_devs = np.array([obs.rms_relative_deviation for obs in observables], dtype=float)
    chi2_vals = np.array([obs.reduced_chi2 for obs in observables], dtype=float)

    weighted_mean_bias = float(np.average(mean_biases, weights=weights))
    weighted_rms_relative_deviation = float(np.average(rms_devs, weights=weights))
    global_reduced_chi2 = float(np.average(chi2_vals, weights=weights))

    return BenchmarkComparison(
        benchmark_id=benchmark_id,
        code_name=code_name,
        code_version=code_version,
        reference_source=reference_source,
        observables=list(observables),
        weighted_mean_bias=weighted_mean_bias,
        weighted_rms_relative_deviation=weighted_rms_relative_deviation,
        global_reduced_chi2=global_reduced_chi2,
        total_point_count=total_points,
        benchmark_status=BenchmarkStatus.ACCEPTABLE,
    )