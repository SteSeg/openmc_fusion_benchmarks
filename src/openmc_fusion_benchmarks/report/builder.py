from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from .models import PlotSpec, Report, ReportConfig, ReportMetadata, ResultSource


def _resolve_plot_tallies(
    sources: Sequence[ResultSource],
    plot_tallies: Sequence[str] | None,
) -> list[str]:
    if plot_tallies is not None:
        return list(plot_tallies)

    for source in sources:
        if source.tally_names:
            return list(source.tally_names)

    if sources:
        return list(sources[0].results.tallies)
    return []


def build_report(
    metadata: ReportMetadata,
    sources: Sequence[ResultSource],
    config: ReportConfig,
) -> Report:
    data = {
        "title": metadata.title,
        "benchmark_id": metadata.benchmark_id,
        "description": metadata.description,
        "model_description": metadata.model_description,
        "code_name": metadata.code_name,
        "code_version": metadata.code_version,
        "notes": metadata.notes,
        "sources": [
            {
                "name": source.name,
                "kind": source.kind,
                "file": str(source.results.filepath),
                "tallies": list(source.tally_names) if source.tally_names else list(source.results.tallies),
            }
            for source in sources
        ],
    }

    plot_tallies = _resolve_plot_tallies(sources, config.plot_tallies)
    plots: list[PlotSpec] = []

    experiment = next((s for s in sources if s.kind == "experiment"), None)
    calculation = next((s for s in sources if s.kind == "calculation"), None)

    if experiment is not None and calculation is not None:
        for tally_name in plot_tallies:
            plots.append(
                PlotSpec(
                    tally_name=tally_name,
                    experiment=experiment.results,
                    calculation=calculation.results,
                )
            )

    return Report(metadata=metadata, sources=list(sources), plots=plots, data=data)
