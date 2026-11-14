"""Build the oncology knowledge graph as node and edge tables."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align, run_query
from oncology_real_world_data_extractor.schemas import GRAPH_EDGES, GRAPH_NODES

INPUTS = (
    "notes",
    "icd10_hcc",
    "rxnorm_drugs",
    "procedure_codes",
    "assertions",
    "temporal_relations",
    "bodypart_relations",
)
OUTPUTS = ("graph_nodes", "graph_edges")


@dataclass(frozen=True)
class Params:
    """Parameters for the knowledge-graph build."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return graph_nodes and graph_edges built from the coded and related findings of notes."""
    nodes = align(run_query(io.read_sql("build_graph_nodes"), inputs), GRAPH_NODES)
    edges = align(run_query(io.read_sql("build_graph_edges"), inputs), GRAPH_EDGES)
    return {"graph_nodes": nodes, "graph_edges": edges}
