# atlas-report

Report Generator for **PipelineAtlas** — produces human- and machine-readable CI/CD analysis reports.

## Purpose

Aggregates graph data, rule engine findings, and AI insights into comprehensive reports.

## Output Formats

| Format | Content |
|--------|---------|
| Markdown | Structure Map, Dependency Graph, scores, improvements |
| JSON | Full machine-readable output |
| HTML/PDF | Phase 2 |

## Report Sections

1. Structure Map
2. Dependency Graph
3. Complexity Score
4. Fragility Score
5. Documentation Coverage Report
6. Improvement List (with confidence scores)
7. Modernization Roadmap (from `atlas-ai`)
8. Evidence Index

## Dependencies

- `atlas-sdk` (shared models)
- `redis` (Redis Streams)
- `httpx` (query graph/rule services)

## Related Services

Receives from ← `atlas-graph`, `atlas-rule-engine`, `atlas-ai`
Publishes to → `atlas-api`
