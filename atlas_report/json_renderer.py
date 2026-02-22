"""JSON renderer — produces a machine-readable JSON report."""

from __future__ import annotations

import json
from typing import Any

from atlas_report.report_data import ReportData


def render_json(data: ReportData, indent: int = 2) -> str:
    """Render the report as JSON string."""
    report = build_json_dict(data)
    return json.dumps(report, indent=indent, default=str)


def build_json_dict(data: ReportData) -> dict[str, Any]:
    """Build a JSON-serializable dict of the full report."""
    s = data.scores
    return {
        "meta": {
            "pipeline": data.graph.name,
            "generated_at": data.generated_at,
            "node_count": len(data.graph.nodes),
            "edge_count": len(data.graph.edges),
            "finding_count": len(data.findings),
        },
        "scores": {
            "complexity": {
                "score": s.complexity_score,
                "nodes": s.node_count,
                "edges": s.edge_count,
                "max_depth": s.max_depth,
                "max_fan_out": s.max_fan_out,
            },
            "fragility": {
                "score": s.fragility_score,
                "secrets": s.secret_count,
                "cross_triggers": s.cross_trigger_count,
                "unpinned_images": s.unpinned_image_count,
                "missing_doc_types": s.missing_doc_types,
            },
        },
        "structure": {
            node_type: [n.name for n in data.graph.nodes if str(n.node_type) == node_type]
            for node_type in sorted({str(n.node_type) for n in data.graph.nodes})
        },
        "dependencies": [
            {
                "source": _node_name(data, e.source_node_id),
                "edge_type": str(e.edge_type),
                "target": _node_name(data, e.target_node_id),
            }
            for e in data.graph.edges
        ],
        "findings": [
            {
                "rule_id": f.rule_id,
                "title": f.title,
                "description": f.description,
                "severity": str(f.severity),
                "confidence": getattr(f.confidence, "level", "unknown") if f.confidence else "unknown",
                "recommendation": f.recommendation,
                "evidence": [
                    {"description": ev.description}
                    for ev in f.evidence
                ],
            }
            for f in data.findings
        ],
        "modernization_roadmap": data.modernization_notes or None,
    }


def _node_name(data: ReportData, node_id: str) -> str:
    """Resolve node ID to name."""
    for n in data.graph.nodes:
        if n.id == node_id:
            return n.name
    return node_id[:8]
