"""Report generator — orchestrator that wires graph + findings → report.

Usage:
    generator = ReportGenerator()
    md = generator.generate_markdown(graph, findings)
    js = generator.generate_json(graph, findings)
"""

from __future__ import annotations

import logging
from typing import Any

from atlas_sdk.models.findings import Finding
from atlas_sdk.models.graph import CICDGraph

from atlas_report.json_renderer import render_json
from atlas_report.markdown_renderer import render_markdown
from atlas_report.report_data import ReportData
from atlas_report.scorer import Scores, compute_scores

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates Markdown and JSON reports from graph + findings."""

    def generate(
        self,
        graph: CICDGraph,
        findings: list[Finding],
        modernization_notes: str = "",
    ) -> ReportData:
        """Compute scores and assemble report data."""
        scores = compute_scores(graph)
        data = ReportData(
            graph=graph,
            findings=findings,
            scores=scores,
            modernization_notes=modernization_notes,
        )
        logger.info(
            "Report data assembled: %d nodes, %d findings, complexity=%.1f, fragility=%.1f",
            len(graph.nodes), len(findings),
            scores.complexity_score, scores.fragility_score,
        )
        return data

    def generate_markdown(
        self,
        graph: CICDGraph,
        findings: list[Finding],
        modernization_notes: str = "",
    ) -> str:
        """Generate a full Markdown report."""
        data = self.generate(graph, findings, modernization_notes)
        return render_markdown(data)

    def generate_json(
        self,
        graph: CICDGraph,
        findings: list[Finding],
        modernization_notes: str = "",
    ) -> str:
        """Generate a full JSON report."""
        data = self.generate(graph, findings, modernization_notes)
        return render_json(data)
