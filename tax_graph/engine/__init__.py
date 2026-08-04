"""Deterministic execution engine for Tax Graph."""

from tax_graph.engine.engine import (
    Engine,
    Graph,
    Result,
    TABLE_FACTS_KEY,
    build_incomplete_cell_payload,
    frontier_text_coverage,
    load_facts,
    load_facts_document,
    render_trace,
)
from tax_graph.engine.operations import MISSING

__all__ = [
    "Engine",
    "Graph",
    "MISSING",
    "Result",
    "TABLE_FACTS_KEY",
    "build_incomplete_cell_payload",
    "frontier_text_coverage",
    "load_facts",
    "load_facts_document",
    "render_trace",
]
