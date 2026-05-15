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

        description = _resolve_benchmark_description(report)
        y_cursor = _wrap_text(fig, 0.1, 0.86, description, fontsize=9, width_chars=80)
        y_cursor = _wrap_text(fig, 0.1, y_cursor - 0.02, report.metadata.model_description, fontsize=9, width_chars=80)

        reference_line = _format_reference(report)
        if reference_line:
            fig.text(0.1, y_cursor - 0.02, f"Reference: {reference_line}", fontsize=9)
            y_cursor -= 0.06

        validation_line = _format_validation(report)
        if validation_line:
            fig.text(0.1, y_cursor - 0.02, f"Validation case: {validation_line}", fontsize=9)
            y_cursor -= 0.06

        _wrap_text(fig, 0.1, y_cursor - 0.02, report.metadata.notes, fontsize=9, width_chars=80)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        verbosity = int(report.data.get("verbosity", 0) or 0)
        if verbosity > 0:
            _render_specifications(pdf, report, verbosity)

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

    lines = _wrap_lines(text, width_chars)
    line_height = 0.02
    for idx, line in enumerate(lines):
        fig.text(x, y - idx * line_height, line, fontsize=fontsize)
    return y - len(lines) * line_height


def _wrap_lines(text: str, width_chars: int) -> list[str]:
    if not text:
        return []

    import textwrap

    return textwrap.wrap(text, width=width_chars, break_long_words=True, break_on_hyphens=False)


def _resolve_benchmark_description(report: Report) -> str:
    spec = report.data.get("specifications", {})
    spec_meta = spec.get("metadata", {}) if isinstance(spec, dict) else {}
    return spec_meta.get("description") or report.metadata.description


def _format_reference(report: Report) -> str:
    for entry in report.data.get("sources", []):
        if entry.get("kind") != "experiment":
            continue
        run_meta = entry.get("run_metadata", {})
        if run_meta.get("kind") == "experiment":
            return "experiment"
        return _format_run_metadata(run_meta)
    return ""


def _format_validation(report: Report) -> str:
    for entry in report.data.get("sources", []):
        if entry.get("kind") != "calculation":
            continue
        run_meta = entry.get("run_metadata", {})
        return _format_run_metadata(run_meta)
    return ""


def _format_run_metadata(run_meta: dict) -> str:
    if not run_meta:
        return ""

    code = " ".join([run_meta.get("code_name", ""), run_meta.get("code_version", "")]).strip()
    library = " ".join(
        [run_meta.get("nuclear_data_name", ""), run_meta.get("nuclear_data_version", "")]
    ).strip()

    parts = [p for p in (code, library) if p]
    return " | ".join(parts)


def _render_specifications(pdf, report: Report, verbosity: int) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    spec = report.data.get("specifications", {})
    if not isinstance(spec, dict) or not spec:
        return

    sections = _build_spec_sections(spec, verbosity)
    if not sections:
        return

    fig = plt.figure(figsize=(8.5, 11))
    y_cursor = 0.95
    fig.text(0.5, y_cursor, "Specification Summary", ha="center", fontsize=13)
    y_cursor -= 0.04

    for title, body in sections:
        body_lines = _wrap_lines(body, width_chars=100)
        needed = 0.03 + (len(body_lines) * 0.02) + 0.03
        if y_cursor - needed < 0.12:
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close(fig)
            fig = plt.figure(figsize=(8.5, 11))
            y_cursor = 0.95

        fig.text(0.1, y_cursor, title, fontsize=10, weight="bold")
        y_cursor -= 0.03
        y_cursor = _wrap_text(fig, 0.1, y_cursor, body, fontsize=8, width_chars=100)
        y_cursor -= 0.03

    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def _build_spec_sections(spec: dict, verbosity: int) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    meta = spec.get("metadata", {})

    if meta:
        fields = {k: v for k, v in meta.items() if k not in {"geometry", "settings"}}
        sections.append(("Metadata", _format_inline(fields)))

    materials = spec.get("materials", [])
    if materials:
        if verbosity >= 3:
            sections.append(("Materials", _format_inline(materials)))
        elif verbosity == 2:
            sections.append((
                "Materials",
                _format_key_fields(
                    materials,
                    keys=["id", "name", "density", "composition"],
                    max_items=10,
                ),
            ))
        else:
            names = [m.get("name", "") for m in materials if isinstance(m, dict)]
            sections.append(("Materials", f"count={len(materials)}; names={', '.join(n for n in names if n)}"))

    tallies = spec.get("tallies", [])
    if tallies:
        if verbosity >= 3:
            sections.append(("Tallies", _format_inline(tallies)))
        elif verbosity == 2:
            sections.append((
                "Tallies",
                _format_key_fields(
                    tallies,
                    keys=["name", "particle", "scores", "filters"],
                    max_items=12,
                ),
            ))
        else:
            names = [t.get("name", "") for t in tallies if isinstance(t, dict)]
            sections.append(("Tallies", ", ".join(n for n in names if n)))

    geometry = spec.get("geometry")
    if geometry is not None:
        if verbosity >= 3:
            sections.append(("Geometry", _format_inline(geometry)))
        elif verbosity == 2:
            sections.append(("Geometry", _format_key_fields([geometry], keys=["cad_file", "meshing"], max_items=1)))

    settings = spec.get("settings")
    if settings is not None:
        if verbosity >= 3:
            sections.append(("Settings", _format_inline(settings)))
        elif verbosity == 2:
            sections.append((
                "Settings",
                _format_key_fields(
                    [settings],
                    keys=["run_mode", "batches", "particles_per_batch", "photon_transport"],
                    max_items=1,
                ),
            ))

    return sections


def _format_inline(value: object) -> str:
    import json

    try:
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    except TypeError:
        return json.dumps(str(value), ensure_ascii=True)


def _format_key_fields(items: list, keys: list[str], max_items: int) -> str:
    rows = []
    for item in items[:max_items]:
        if not isinstance(item, dict):
            rows.append(_format_inline(item))
            continue
        row = {k: item.get(k) for k in keys if k in item}
        rows.append(_format_inline(row))
    if len(items) > max_items:
        rows.append(f"... ({len(items) - max_items} more)")
    return " | ".join(rows)
