"""Scoring — complexity, fragility, and maturity metrics for a CICDGraph.

Complexity: based on node count, edge count, depth, max fan-out.
Fragility: based on secrets, unpinned images, cross-triggers, missing docs.
Maturity: based on caching, parallelism, pinned deps, doc coverage, retries, env isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_sdk.enums import EdgeType, NodeType
from atlas_sdk.models.graph import CICDGraph


@dataclass
class Scores:
    """Aggregated complexity and fragility scores."""

    # Complexity components
    node_count: int = 0
    edge_count: int = 0
    max_depth: int = 0
    max_fan_out: int = 0
    complexity_score: float = 0.0  # 0-100

    # Fragility components
    secret_count: int = 0
    cross_trigger_count: int = 0
    unpinned_image_count: int = 0
    missing_doc_types: int = 0
    fragility_score: float = 0.0  # 0-100

    # Maturity components
    has_caching: bool = False
    has_parallelism: bool = False
    pinned_image_ratio: float = 0.0
    doc_coverage: float = 0.0
    has_retries: bool = False
    has_env_isolation: bool = False
    maturity_score: float = 0.0  # 0-100


def compute_scores(graph: CICDGraph) -> Scores:
    """Compute complexity and fragility scores from a CICDGraph."""
    s = Scores()

    # ── Complexity ────────────────────────────────────────────
    s.node_count = len(graph.nodes)
    s.edge_count = len(graph.edges)

    # Max fan-out: most outgoing edges from any single node
    fan_out: dict[str, int] = {}
    for edge in graph.edges:
        fan_out[edge.source_node_id] = fan_out.get(edge.source_node_id, 0) + 1
    s.max_fan_out = max(fan_out.values(), default=0)

    # Depth: longest chain of CALLS edges from any pipeline
    pipelines = [n for n in graph.nodes if n.node_type == NodeType.PIPELINE]
    for p in pipelines:
        depth = _compute_depth(graph, p.id, set())
        s.max_depth = max(s.max_depth, depth)

    # Complexity score: weighted formula (capped at 100)
    raw = (s.node_count * 1.0) + (s.edge_count * 1.5) + (s.max_depth * 5) + (s.max_fan_out * 3)
    s.complexity_score = min(round(raw, 1), 100.0)

    # ── Fragility ─────────────────────────────────────────────
    s.secret_count = sum(1 for n in graph.nodes if n.node_type == NodeType.SECRET_REF)
    s.cross_trigger_count = sum(1 for e in graph.edges if e.edge_type == EdgeType.TRIGGERS)
    s.unpinned_image_count = sum(
        1 for n in graph.nodes
        if n.node_type == NodeType.CONTAINER_IMAGE
        and getattr(n, "tag", "latest") in ("latest", "stable", "nightly")
    )

    expected_docs = {"readme", "architecture", "runbook", "security_policy", "codeowners"}
    found_docs = {
        getattr(n, "doc_type", "").value
        if hasattr(getattr(n, "doc_type", ""), "value")
        else str(getattr(n, "doc_type", ""))
        for n in graph.nodes
        if n.node_type == NodeType.DOC_FILE
    }
    s.missing_doc_types = len(expected_docs - found_docs)

    frag_raw = (
        s.secret_count * 5
        + s.cross_trigger_count * 10
        + s.unpinned_image_count * 15
        + s.missing_doc_types * 8
    )
    s.fragility_score = min(round(frag_raw, 1), 100.0)

    # ── Maturity ──────────────────────────────────────────────
    maturity_points = 0
    max_points = 6  # 6 dimensions, each worth ~16.7 points

    # 1. Caching: any step/job referencing "cache"
    step_nodes = [n for n in graph.nodes if n.node_type == NodeType.STEP]
    s.has_caching = any(
        "cache" in (getattr(n, "command", "") or "").lower()
        for n in step_nodes
    )
    if s.has_caching:
        maturity_points += 1

    # 2. Parallelism: any stage with parallel=True or multiple jobs from one pipeline
    stages = [n for n in graph.nodes if n.node_type == NodeType.STAGE]
    s.has_parallelism = any(getattr(n, "parallel", False) for n in stages)
    if not s.has_parallelism and s.max_fan_out >= 2:
        s.has_parallelism = True
    if s.has_parallelism:
        maturity_points += 1

    # 3. Pinned images
    images = [n for n in graph.nodes if n.node_type == NodeType.CONTAINER_IMAGE]
    if images:
        pinned = sum(1 for n in images if getattr(n, "pinned", False))
        s.pinned_image_ratio = pinned / len(images)
    else:
        s.pinned_image_ratio = 1.0  # No images = no risk
    if s.pinned_image_ratio >= 0.8:
        maturity_points += 1

    # 4. Doc coverage
    expected_docs = {"readme", "architecture", "runbook", "security_policy", "codeowners"}
    s.doc_coverage = 1.0 - (s.missing_doc_types / len(expected_docs)) if expected_docs else 1.0
    if s.doc_coverage >= 0.6:
        maturity_points += 1

    # 5. Retry policies
    s.has_retries = any(
        "retry" in (getattr(n, "command", "") or "").lower()
        or "retry" in str(getattr(n, "metadata", {}))
        for n in graph.nodes
    )
    if s.has_retries:
        maturity_points += 1

    # 6. Environment isolation
    env_nodes = [n for n in graph.nodes if n.node_type == NodeType.ENVIRONMENT]
    s.has_env_isolation = len(env_nodes) >= 2
    if s.has_env_isolation:
        maturity_points += 1

    s.maturity_score = round((maturity_points / max_points) * 100, 1)

    return s


def _compute_depth(graph: CICDGraph, node_id: str, visited: set[str]) -> int:
    """Recursively compute the depth from a node following CALLS edges."""
    if node_id in visited:
        return 0
    visited.add(node_id)
    children = [
        e.target_node_id for e in graph.edges
        if e.source_node_id == node_id and e.edge_type == EdgeType.CALLS
    ]
    if not children:
        return 1
    return 1 + max(_compute_depth(graph, c, visited) for c in children)
