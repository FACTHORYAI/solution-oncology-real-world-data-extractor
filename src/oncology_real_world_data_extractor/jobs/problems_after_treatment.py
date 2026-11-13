"""Problems that occurred after a treatment, from the temporal relations."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align, run_query
from oncology_real_world_data_extractor.schemas import PROBLEMS_AFTER_TREATMENT

INPUTS = ("temporal_relations",)
OUTPUTS = ("problems_after_treatment",)


@dataclass(frozen=True)
class Params:
    """Parameters for the problems-after-treatment job."""

    min_confidence: float = 0.8


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the treatment and problem pairs where the problem followed the treatment."""
    if not 0 <= params.min_confidence <= 1:
        message = f"Parameter min_confidence is {params.min_confidence}; it must be between 0 and 1"
        raise ValueError(message)
    table = run_query(
        io.read_sql("problems_after_treatment"),
        inputs,
        {"min_confidence": params.min_confidence},
    )
    return {"problems_after_treatment": align(table, PROBLEMS_AFTER_TREATMENT)}
