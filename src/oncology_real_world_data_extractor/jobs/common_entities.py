"""The most common oncological findings or symptoms."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align, run_query
from oncology_real_world_data_extractor.schemas import COMMON_ENTITIES

INPUTS = ("icd10_hcc",)
OUTPUTS = ("common_entities",)


@dataclass(frozen=True)
class Params:
    """Parameters for the most-common-entities job."""

    entity_type: str = "Oncological"
    limit: int = 20


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return the most common findings or symptoms, by the number of notes they appear in."""
    if params.entity_type not in ("Oncological", "Symptom", "Treatment"):
        message = (
            f"Parameter entity_type is {params.entity_type!r}; "
            "common_entities needs 'Oncological', 'Symptom' or 'Treatment'"
        )
        raise ValueError(message)
    if params.limit < 1:
        message = f"Parameter limit is {params.limit}; it must be at least 1"
        raise ValueError(message)
    table = run_query(
        io.read_sql("common_entities"),
        inputs,
        {"entity_type": params.entity_type, "limit": params.limit},
    )
    return {"common_entities": align(table, COMMON_ENTITIES)}
