from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..tallies import BaseTally
from .models import PlotStyle


@dataclass
class PlotArtifacts:
    tally_name: str
    absolute_plot: Path
    ce_plot: Path


def _flatten_tally(tally: BaseTally) -> np.ndarray:
    da = tally._da
    if da.ndim == 1:
        return np.asarray(da.values, dtype=float)
    stacked = da.stack(point=da.dims)
    return np.asarray(stacked.values, dtype=float)


def _default_x(tally: BaseTally) -> np.ndarray:
    da = tally._da
    if da.ndim == 1:
        dim = da.dims[0]
        if dim in da.coords:
            return np.asarray(da.coords[dim].values, dtype=float)
    return np.arange(int(da.size), dtype=float)


def _align_step_x(x_vals: np.ndarray, y_vals: np.ndarray) -> np.ndarray:
    if x_vals.shape[0] == y_vals.shape[0] + 1:
        return x_vals[:-1]
    return x_vals


def _align_line_x(x_vals: np.ndarray, y_vals: np.ndarray) -> np.ndarray:
    if x_vals.shape[0] == y_vals.shape[0] + 1:
        return x_vals[:-1]
    return x_vals


def build_plot_artifacts(
    tally_name: str,
    experiment: BaseTally,
    calculation: BaseTally,
    output_dir: Path,
) -> PlotArtifacts:
    output_dir.mkdir(parents=True, exist_ok=True)

    x_vals = _default_x(experiment)
    exp_vals = _flatten_tally(experiment)
    calc_vals = _flatten_tally(calculation)

    if exp_vals.shape != calc_vals.shape:
        raise ValueError(f"Tally '{tally_name}' has mismatched shapes for plotting")

    ce_vals = np.divide(calc_vals, exp_vals, out=np.full_like(calc_vals, np.nan), where=exp_vals != 0)

    absolute_plot = output_dir / f"{tally_name}_absolute.png"
    ce_plot = output_dir / f"{tally_name}_ce.png"

    return PlotArtifacts(
        tally_name=tally_name,
        absolute_plot=absolute_plot,
        ce_plot=ce_plot,
    )


def _auto_scale(values: np.ndarray, threshold: float) -> str:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    values = values[values > 0]
    if values.size == 0:
        return "linear"
    vmin = float(np.min(values))
    vmax = float(np.max(values))
    if vmin <= 0:
        return "linear"
    if vmax / vmin >= threshold:
        return "log"
    return "linear"


def render_plots(
    artifacts: PlotArtifacts,
    experiment: BaseTally,
    calculation: BaseTally,
    style: PlotStyle | None = None,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for plotting. Install it to render plots.") from exc

    style = style or PlotStyle()

    x_vals = _default_x(experiment)
    exp_vals = _flatten_tally(experiment)
    calc_vals = _flatten_tally(calculation)
    ce_vals = np.divide(calc_vals, exp_vals, out=np.full_like(calc_vals, np.nan), where=exp_vals != 0)

    exp_std = experiment._da_mc_std
    if exp_std is None:
        exp_std_vals = np.zeros_like(exp_vals)
    else:
        exp_std_vals = _flatten_tally(BaseTally(exp_std, parent_ds=experiment._parent_ds))

    x_is_edges = x_vals.shape[0] == exp_vals.shape[0] + 1
    step_x = _align_step_x(x_vals, exp_vals)
    line_x = _align_line_x(x_vals, exp_vals)

    y_scale = style.y_scale
    if y_scale == "auto":
        combined = np.concatenate([exp_vals, calc_vals])
        y_scale = _auto_scale(combined, style.auto_scale_threshold)

    ce_y_scale = style.ce_y_scale
    if ce_y_scale == "auto":
        ce_y_scale = _auto_scale(ce_vals, style.auto_scale_threshold)

    plt.figure(figsize=(7, 4))
    exp_line = plt.plot(line_x, exp_vals, label="experiment", linewidth=1.5)
    calc_line = plt.plot(line_x, calc_vals, label="calculation", linewidth=1.5)
    exp_color = exp_line[0].get_color()
    if np.any(exp_std_vals > 0):
        upper = exp_vals + 3.0 * exp_std_vals
        lower = exp_vals - 3.0 * exp_std_vals
        fill_x = step_x if x_is_edges else line_x
        if x_is_edges:
            plt.fill_between(
                fill_x,
                lower,
                upper,
                step="post",
                color=exp_color,
                alpha=0.15,
                label="exp ±3σ",
            )
        else:
            plt.fill_between(
                fill_x,
                lower,
                upper,
                color=exp_color,
                alpha=0.15,
                label="exp ±3σ",
            )
    plt.xlabel(style.x_label)
    plt.ylabel(style.y_label)
    plt.yscale(y_scale)
    plt.xscale(style.x_scale)
    title = style.title or f"{artifacts.tally_name} absolute"
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(artifacts.absolute_plot, dpi=200)
    plt.close()

    plt.figure(figsize=(7, 4))
    plt.plot(line_x, ce_vals, label="C/E", linewidth=1.5)
    ref_line = plt.axhline(1.0, color="black", linestyle="--", linewidth=1.0)
    ref_color = ref_line.get_color()
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_std = np.divide(exp_std_vals, exp_vals, out=np.zeros_like(exp_std_vals), where=exp_vals != 0)
    if np.any(rel_std > 0):
        upper = 1.0 + 3.0 * rel_std
        lower = 1.0 - 3.0 * rel_std
        fill_x = step_x if x_is_edges else line_x
        if x_is_edges:
            plt.fill_between(
                fill_x,
                lower,
                upper,
                step="post",
                color=ref_color,
                alpha=0.15,
                label="exp ±3σ",
            )
        else:
            plt.fill_between(
                fill_x,
                lower,
                upper,
                color=ref_color,
                alpha=0.15,
                label="exp ±3σ",
            )
    plt.xlabel(style.x_label)
    plt.ylabel(style.ce_y_label)
    plt.yscale(ce_y_scale)
    plt.xscale(style.x_scale)
    ce_title = style.ce_title or f"{artifacts.tally_name} C/E"
    plt.title(ce_title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(artifacts.ce_plot, dpi=200)
    plt.close()
