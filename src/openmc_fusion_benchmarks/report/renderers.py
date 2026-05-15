from __future__ import annotations

from pathlib import Path

import yaml

from .models import Report
from .plots import build_plot_artifacts, render_plots


def render_yaml(report: Report, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(report.data, handle, sort_keys=False)
    return output_path


def render_plots_for_report(report: Report, output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    for plot in report.plots:
        artifacts = build_plot_artifacts(
            tally_name=plot.tally_name,
            experiment=plot.experiment.get_tally(plot.tally_name),
            calculation=plot.calculation.get_tally(plot.tally_name),
            output_dir=output_dir,
        )
        render_plots(
            artifacts,
            plot.experiment.get_tally(plot.tally_name),
            plot.calculation.get_tally(plot.tally_name),
            style=plot.style,
        )
        entries.append(
            {
                "tally": plot.tally_name,
                "absolute_plot": str(artifacts.absolute_plot),
                "ce_plot": str(artifacts.ce_plot),
            }
        )
    report.data["plots"] = entries
    return entries


def render_pdf(report: Report, output_path: Path, plots_dir: Path) -> Path:
    try:
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for PDF rendering. Install it to enable PDF output.") from exc

    plot_entries = render_plots_for_report(report, plots_dir)

    with PdfPages(output_path) as pdf:
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.95, report.metadata.title, ha="center", fontsize=14)
        fig.text(0.1, 0.9, f"Benchmark: {report.metadata.benchmark_id}", fontsize=10)
        fig.text(0.1, 0.86, f"Code: {report.metadata.code_name} {report.metadata.code_version}", fontsize=10)
        y_cursor = _wrap_text(fig, 0.1, 0.82, report.metadata.description, fontsize=9, width_chars=80)
        y_cursor = _wrap_text(fig, 0.1, y_cursor - 0.02, report.metadata.model_description, fontsize=9, width_chars=80)

        run_meta = report.data.get("run_metadata", {})
        if run_meta:
            code_name = run_meta.get("code_name", "")
            code_version = run_meta.get("code_version", "")
            geometry = run_meta.get("geometry", "")
            fig.text(0.1, y_cursor - 0.02, f"Run: {code_name} {code_version} ({geometry})", fontsize=9)
            y_notes = y_cursor - 0.06
        else:
            y_notes = y_cursor - 0.02

        _wrap_text(fig, 0.1, y_notes, report.metadata.notes, fontsize=9, width_chars=80)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        for entry in plot_entries:
            fig = plt.figure(figsize=(8.5, 11))
            fig.text(0.5, 0.95, f"Tally: {entry['tally']}", ha="center", fontsize=12)
            try:
                abs_img = plt.imread(entry["absolute_plot"])
                ce_img = plt.imread(entry["ce_plot"])
                ax1 = fig.add_axes([0.1, 0.55, 0.8, 0.35])
                ax1.imshow(abs_img)
                ax1.axis("off")
                ax2 = fig.add_axes([0.1, 0.1, 0.8, 0.35])
                ax2.imshow(ce_img)
                ax2.axis("off")
            except Exception:
                fig.text(0.1, 0.6, "Plot images could not be loaded.", fontsize=9)
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)

    return output_path


def _wrap_text(fig, x: float, y: float, text: str, fontsize: int, width_chars: int) -> float:
    if not text:
        return y

    import textwrap

    lines = textwrap.wrap(text, width=width_chars, break_long_words=True, break_on_hyphens=False)
    line_height = 0.02
    for idx, line in enumerate(lines):
        fig.text(x, y - idx * line_height, line, fontsize=fontsize)
    return y - len(lines) * line_height
