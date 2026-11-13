"""Condition and symptom pairs that appear in the same note."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align, run_query
from oncology_real_world_data_extractor.schemas import CONDITION_SYMPTOM_PAIRS

INPUTS = ("icd10_hcc",)
OUTPUTS = ("condition_symptom_pairs",)


@dataclass(frozen=True)
class Params:
    """Parameters for the condition-symptom-pairs job."""

    min_confidence: float = 0.3
    min_notes: int = 1


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the condition-symptom pairs with their note counts and normalised shares."""
    if not 0 <= params.min_confidence <= 1:
        message = f"Parameter min_confidence is {params.min_confidence}; it must be between 0 and 1"
        raise ValueError(message)
    if params.min_notes < 1:
        message = f"Parameter min_notes is {params.min_notes}; it must be at least 1"
        raise ValueError(message)
    table = run_query(
        io.read_sql("condition_symptom_pairs"),
        inputs,
        {"min_confidence": params.min_confidence, "min_notes": params.min_notes},
    )
    return {"condition_symptom_pairs": align(table, CONDITION_SYMPTOM_PAIRS)}
