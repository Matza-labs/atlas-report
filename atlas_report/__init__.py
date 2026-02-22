"""PipelineAtlas Report Generator — Markdown + JSON CI/CD analysis reports."""

__version__ = "0.1.0"

from atlas_report.generator import ReportGenerator  # noqa: F401
from atlas_report.report_data import ReportData  # noqa: F401
from atlas_report.scorer import Scores, compute_scores  # noqa: F401
