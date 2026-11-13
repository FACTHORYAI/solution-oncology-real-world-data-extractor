"""Assertion summary: how statuses distribute and how symptoms are asserted."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align, run_query
from oncology_real_world_data_extractor.schemas import ASSERTION_BREAKDOWN, SYMPTOM_ASSERTIONS

INPUTS = ("assertions",)
OUTPUTS = ("assertion_breakdown", "symptom_assertions")


@dataclass(frozen=True)
class Params:
    """Parameters for the assertion-summary job."""

    limit: int = 20


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the status distribution and the most common symptoms with their status."""
    if params.limit < 1:
        message = f"Parameter limit is {params.limit}; it must be at least 1"
        raise ValueError(message)
    breakdown = run_query(io.read_sql("assertion_breakdown"), inputs)
    symptoms = run_query(io.read_sql("symptom_assertions"), inputs, {"limit": params.limit})
    return {
        "assertion_breakdown": align(breakdown, ASSERTION_BREAKDOWN),
        "symptom_assertions": align(symptoms, SYMPTOM_ASSERTIONS),
    }
