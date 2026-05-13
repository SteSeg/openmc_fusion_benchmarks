from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import xarray as xr

from ..benchmark_results import BenchmarkResults
from ..tallies import BaseTally
from .comparison import aggregate_benchmark, compare_point_set
from .model import BenchmarkComparison, DataPoint, ObservableComparison


def _normalize_flatten_dims(tally: BaseTally, flatten_dims: Sequence[str] | None) -> list[str]:
    if flatten_dims is None:
        return list(tally.dims)

    dims = list(tally.dims)
    missing = [d for d in flatten_dims if d not in dims]
    if missing:
        raise ValueError(f"Flatten dims not found in tally dims: {missing}")
    return list(flatten_dims)


def _format_point_ids(dims: Sequence[str], index_values: Iterable) -> list[str]:
    ids: list[str] = []
    for entry in index_values:
        values = entry if isinstance(entry, tuple) else (entry,)
        parts = [f"{dim}={value}" for dim, value in zip(dims, values)]
        ids.append("|".join(parts))
    return ids


def _stack_dataarray(da: xr.DataArray, dims: Sequence[str]) -> xr.DataArray:
    if list(da.dims) == list(dims):
        return da.stack(point=dims)
    return da.transpose(*dims).stack(point=dims)


def datapoints_from_tally(
    experiment: BaseTally,
    calculation: BaseTally,
    flatten_dims: Sequence[str] | None = None,
) -> tuple[list[DataPoint], list[DataPoint], list[str]]:
    """
    Convert two BaseTally objects into DataPoint lists and point IDs.

    Parameters
    ----------
    experiment:
        Reference results tally.
    calculation:
        Calculated results tally.
    flatten_dims:
        Dimensions to flatten into points. Defaults to all tally dims.
    """
    if experiment.dims != calculation.dims or experiment.shape != calculation.shape:
        raise ValueError("Experiment and calculation tallies must share dims and shape.")

    dims = _normalize_flatten_dims(experiment, flatten_dims)

    exp_da = experiment._da
    calc_da = calculation._da

    exp_std = experiment._da_mc_std
    if exp_std is None:
        exp_std = xr.zeros_like(exp_da)

    calc_std = calculation._da_mc_std
    if calc_std is None:
        calc_std = xr.zeros_like(calc_da)

    exp_vals = _stack_dataarray(exp_da, dims)
    calc_vals = _stack_dataarray(calc_da, dims)
    exp_unc = _stack_dataarray(exp_std, dims)
    calc_unc = _stack_dataarray(calc_std, dims)

    if exp_vals.shape != calc_vals.shape:
        raise ValueError("Experiment and calculation tallies produce mismatched point counts.")

    point_ids = _format_point_ids(dims, exp_vals["point"].values)

    exp_points = [
        DataPoint(value=float(val), uncertainty=float(unc))
        for val, unc in zip(exp_vals.values, exp_unc.values)
    ]
    calc_points = [
        DataPoint(value=float(val), uncertainty=float(unc))
        for val, unc in zip(calc_vals.values, calc_unc.values)
    ]

    return exp_points, calc_points, point_ids


def compare_tallies(
    observable_name: str,
    observable_type: str,
    experiment: BaseTally,
    calculation: BaseTally,
    flatten_dims: Sequence[str] | None = None,
) -> ObservableComparison:
    """Compare two tallies by converting them into point metrics."""
    exp_points, calc_points, point_ids = datapoints_from_tally(
        experiment=experiment,
        calculation=calculation,
        flatten_dims=flatten_dims,
    )

    return compare_point_set(
        observable_name=observable_name,
        observable_type=observable_type,
        experiment_points=exp_points,
        calculation_points=calc_points,
        point_ids=point_ids,
    )


def compare_benchmark_results(
    benchmark_id: str,
    code_name: str,
    code_version: str,
    reference_source: str,
    experiment: BenchmarkResults,
    calculation: BenchmarkResults,
    tally_names: Sequence[str] | None = None,
    observable_type_map: dict[str, str] | None = None,
    flatten_dims_map: dict[str, Sequence[str]] | None = None,
) -> BenchmarkComparison:
    """
    Compare two BenchmarkResults objects and aggregate to benchmark-level metrics.

    Parameters
    ----------
    benchmark_id, code_name, code_version, reference_source:
        Metadata for the benchmark comparison.
    experiment, calculation:
        Benchmark results with matching tally groups.
    tally_names:
        Optional list of tally names/groups to compare. Defaults to experiment.tallies.
    observable_type_map:
        Optional mapping from tally name to observable type.
    flatten_dims_map:
        Optional per-tally flatten dims. If provided, overrides flatten_dims per tally.
    """
    names = list(tally_names) if tally_names is not None else list(experiment.tallies)
    if not names:
        raise ValueError("No tallies found to compare.")

    observable_type_map = observable_type_map or {}
    flatten_dims_map = flatten_dims_map or {}
    observables: list[ObservableComparison] = []

    for name in names:
        exp_tally = experiment.get_tally(name)
        calc_tally = calculation.get_tally(name)
        observable_type = observable_type_map.get(name, "tally")

        tally_flatten_dims = flatten_dims_map.get(name)

        obs = compare_tallies(
            observable_name=name,
            observable_type=observable_type,
            experiment=exp_tally,
            calculation=calc_tally,
            flatten_dims=tally_flatten_dims,
        )
        observables.append(obs)

    return aggregate_benchmark(
        benchmark_id=benchmark_id,
        code_name=code_name,
        code_version=code_version,
        reference_source=reference_source,
        observables=observables,
    )
