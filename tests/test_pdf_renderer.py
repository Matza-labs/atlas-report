"""Tests for PDF renderer."""

from atlas_sdk.models.findings import Finding
from atlas_sdk.models.graph import CICDGraph
from atlas_sdk.models.nodes import PipelineNode, JobNode
from atlas_sdk.enums import Severity

from atlas_report.pdf_renderer import render_pdf_html
from atlas_report.report_data import ReportData
from atlas_report.scorer import compute_scores


def _make_report_data():
    graph = CICDGraph(name="Test Pipeline")
    graph.add_node(PipelineNode(name="CI"))
    graph.add_node(JobNode(name="Build"))
    scores = compute_scores(graph)
    findings = [
        Finding(rule_id="no-timeout", title="No timeout set", description="", severity=Severity.MEDIUM),
        Finding(rule_id="no-cache", title="No cache configured", description="", severity=Severity.LOW),
    ]
    return ReportData(graph=graph, findings=findings, scores=scores)


def test_pdf_html_contains_pipeline_name():
    data = _make_report_data()
    html = render_pdf_html(data)
    assert "Test Pipeline" in html


def test_pdf_html_contains_scores():
    data = _make_report_data()
    html = render_pdf_html(data)
    assert "Complexity" in html
    assert "Fragility" in html
    assert "Maturity" in html


def test_pdf_html_contains_findings():
    data = _make_report_data()
    html = render_pdf_html(data)
    assert "no-timeout" in html
    assert "no-cache" in html
    assert "Findings (2)" in html


def test_pdf_html_is_valid():
    data = _make_report_data()
    html = render_pdf_html(data)
    assert html.startswith("<!DOCTYPE html>")
    assert html.endswith("</html>")
    assert "<table>" in html
