"""Which procedures were performed on which internal body part."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align, run_query
from oncology_real_world_data_extractor.schemas import BODYPART_PROCEDURES

INPUTS = ("bodypart_relations",)
OUTPUTS = ("bodypart_procedures",)


@dataclass(frozen=True)
class Params:
    """Parameters for the bodypart-procedures job."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the distinct organ-to-procedure relations, one row per note and pair."""
    table = run_query(io.read_sql("bodypart_procedures"), inputs)
    return {"bodypart_procedures": align(table, BODYPART_PROCEDURES)}
