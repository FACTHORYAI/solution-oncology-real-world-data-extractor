"""The procedures coded most often, above a confidence floor."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align, run_query
from oncology_real_world_data_extractor.schemas import COMMON_PROCEDURES

INPUTS = ("procedure_codes",)
OUTPUTS = ("common_procedures",)


@dataclass(frozen=True)
class Params:
    """Parameters for the common-procedures job."""

    min_confidence: float = 0.8
    limit: int = 20


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the most mentioned procedures and their mention counts."""
    if not 0 <= params.min_confidence <= 1:
        message = f"Parameter min_confidence is {params.min_confidence}; it must be between 0 and 1"
        raise ValueError(message)
    if params.limit < 1:
        message = f"Parameter limit is {params.limit}; it must be at least 1"
        raise ValueError(message)
    table = run_query(
        io.read_sql("common_procedures"),
        inputs,
        {"min_confidence": params.min_confidence, "limit": params.limit},
    )
    return {"common_procedures": align(table, COMMON_PROCEDURES)}
