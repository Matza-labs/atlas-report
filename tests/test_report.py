"""Unit tests for atlas-report — scorer, renderers, generator."""

import json

import pytest

from atlas_sdk.enums import DocType, EdgeType, NodeType, Platform, Severity
from atlas_sdk.confidence import ConfidenceScore
from atlas_sdk.models.edges import Edge
from atlas_sdk.models.findings import Evidence, Finding
from atlas_sdk.models.graph import CICDGraph
from atlas_sdk.models.nodes import (
    ContainerImageNode,
    DocFileNode,
    EnvironmentNode,
    JobNode,
    PipelineNode,
    SecretRefNode,
    StageNode,
    StepNode,
)

from atlas_report.generator import ReportGenerator
from atlas_report.json_renderer import build_json_dict, render_json
from atlas_report.markdown_renderer import render_markdown
from atlas_report.report_data import ReportData
from atlas_report.scorer import Scores, compute_scores


# ── Test helpers ──────────────────────────────────────────────────────

def _sample_graph() -> CICDGraph:
    g = CICDGraph(name="test-pipeline", platform=Platform.JENKINS)
    p = PipelineNode(name="main-build")
    s1 = StageNode(name="Build", order=0)
    s2 = StageNode(name="Test", order=1)
    s3 = StageNode(name="Deploy", order=2)
    step = StepNode(name="sh: make", command="make build", shell="sh")
    secret = SecretRefNode(name="AWS_KEY", key="AWS_KEY")
    img = ContainerImageNode(name="python:latest", tag="latest")
    doc = DocFileNode(name="README.md", path="README.md", doc_type=DocType.README)
    downstream = JobNode(name="notify-slack")

    for n in [p, s1, s2, s3, step, secret, img, doc, downstream]:
        g.add_node(n)

    g.add_edge(Edge(edge_type=EdgeType.CALLS, source_node_id=p.id, target_node_id=s1.id))
    g.add_edge(Edge(edge_type=EdgeType.CALLS, source_node_id=p.id, target_node_id=s2.id))
    g.add_edge(Edge(edge_type=EdgeType.CALLS, source_node_id=p.id, target_node_id=s3.id))
    g.add_edge(Edge(edge_type=EdgeType.CALLS, source_node_id=s1.id, target_node_id=step.id))
    g.add_edge(Edge(edge_type=EdgeType.TRIGGERS, source_node_id=p.id, target_node_id=downstream.id))
    return g


def _sample_findings() -> list[Finding]:
    return [
        Finding(
            rule_id="no-timeout",
            title="No timeout: main-build",
            description="Pipeline has no timeout configured.",
            severity=Severity.HIGH,
            evidence=[Evidence(description="No timeout on pipeline 'main-build'")],
            confidence=ConfidenceScore.high(),
            recommendation="Add a timeout of 30 minutes.",
            impact_category="reliability",
        ),
        Finding(
            rule_id="unpinned-images",
            title="Unpinned Docker image: python:latest",
            description="Image 'python:latest' uses a floating tag.",
            severity=Severity.HIGH,
            evidence=[Evidence(description="Tag: latest, no digest")],
            confidence=ConfidenceScore.high(),
            recommendation="Pin to python:3.11.7 or use a digest.",
            impact_category="security",
        ),
    ]


# ── Scorer tests ──────────────────────────────────────────────────────

class TestScorer:
    def test_empty_graph(self):
        g = CICDGraph(name="empty")
        s = compute_scores(g)
        assert s.node_count == 0
        assert s.edge_count == 0
        assert s.complexity_score == 0.0

    def test_scores_populated(self):
        s = compute_scores(_sample_graph())
        assert s.node_count == 9
        assert s.edge_count == 5
        assert s.max_fan_out >= 3  # pipeline fans out to 3 stages + downstream
        assert s.max_depth >= 2  # pipeline → stage → step
        assert s.complexity_score > 0

    def test_fragility_counts(self):
        s = compute_scores(_sample_graph())
        assert s.secret_count == 1
        assert s.cross_trigger_count == 1
        assert s.unpinned_image_count == 1
        assert s.missing_doc_types == 4  # only readme found, missing 4
        assert s.fragility_score > 0


# ── Markdown renderer tests ──────────────────────────────────────────

class TestMarkdownRenderer:
    def test_renders_all_sections(self):
        data = ReportData(
            graph=_sample_graph(),
            findings=_sample_findings(),
            scores=compute_scores(_sample_graph()),
        )
        md = render_markdown(data)
        assert "# PipelineAtlas Analysis Report" in md
        assert "## 1. Structure Map" in md
        assert "## 2. Dependency Graph" in md
        assert "## 3. Complexity Score" in md
        assert "## 4. Fragility Score" in md
        assert "## 5. Documentation Coverage" in md
        assert "## 6. Improvement List" in md
        assert "## 7. Modernization Roadmap" in md
        assert "## 8. Evidence Index" in md

    def test_contains_pipeline_name(self):
        data = ReportData(
            graph=_sample_graph(),
            findings=[],
            scores=compute_scores(_sample_graph()),
        )
        md = render_markdown(data)
        assert "test-pipeline" in md

    def test_findings_rendered(self):
        data = ReportData(
            graph=_sample_graph(),
            findings=_sample_findings(),
            scores=compute_scores(_sample_graph()),
        )
        md = render_markdown(data)
        assert "no-timeout" in md
        assert "unpinned-images" in md
        assert "Recommendation" in md

    def test_empty_findings(self):
        data = ReportData(
            graph=_sample_graph(),
            findings=[],
            scores=compute_scores(_sample_graph()),
        )
        md = render_markdown(data)
        assert "No findings" in md


# ── JSON renderer tests ──────────────────────────────────────────────

class TestJsonRenderer:
    def test_valid_json(self):
        data = ReportData(
            graph=_sample_graph(),
            findings=_sample_findings(),
            scores=compute_scores(_sample_graph()),
        )
        result = render_json(data)
        parsed = json.loads(result)
        assert "meta" in parsed
        assert "scores" in parsed
        assert "findings" in parsed

    def test_json_structure(self):
        data = ReportData(
            graph=_sample_graph(),
            findings=_sample_findings(),
            scores=compute_scores(_sample_graph()),
        )
        d = build_json_dict(data)
        assert d["meta"]["pipeline"] == "test-pipeline"
        assert d["meta"]["node_count"] == 9
        assert d["meta"]["finding_count"] == 2
        assert d["scores"]["complexity"]["score"] > 0
        assert d["scores"]["fragility"]["score"] > 0
        assert len(d["findings"]) == 2
        assert len(d["dependencies"]) == 5

    def test_empty_graph_json(self):
        data = ReportData(
            graph=CICDGraph(name="empty"),
            findings=[],
            scores=compute_scores(CICDGraph(name="empty")),
        )
        d = build_json_dict(data)
        assert d["meta"]["node_count"] == 0
        assert d["meta"]["finding_count"] == 0


# ── Generator tests ───────────────────────────────────────────────────

class TestReportGenerator:
    def test_generate_markdown(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(_sample_graph(), _sample_findings())
        assert "# PipelineAtlas Analysis Report" in md
        assert "## 8. Evidence Index" in md

    def test_generate_json(self):
        gen = ReportGenerator()
        result = gen.generate_json(_sample_graph(), _sample_findings())
        parsed = json.loads(result)
        assert parsed["meta"]["pipeline"] == "test-pipeline"

    def test_generate_data(self):
        gen = ReportGenerator()
        data = gen.generate(_sample_graph(), _sample_findings(), modernization_notes="Phase 2 TBD")
        assert isinstance(data, ReportData)
        assert data.modernization_notes == "Phase 2 TBD"
        assert data.scores.node_count == 9

    def test_generate_empty(self):
        gen = ReportGenerator()
        md = gen.generate_markdown(CICDGraph(name="empty"), [])
        assert "empty" in md
