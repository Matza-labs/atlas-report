"""Report data model — collects all data needed to render a report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from atlas_sdk.models.findings import Finding
from atlas_sdk.models.graph import CICDGraph

from atlas_report.scorer import Scores


@dataclass
class ReportData:
    """Everything needed to render a report.

    Sections (per docs/README.md §8):
    1. Structure Map
    2. Dependency Graph
    3. Complexity Score
    4. Fragility Score
    5. Documentation Coverage
    6. Improvement List
    7. Modernization Roadmap
    8. Evidence Index
    """

    graph: CICDGraph
    findings: list[Finding]
    scores: Scores
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modernization_notes: str = ""  # Populated by atlas-ai in Phase 2
