"""Risk by oncology category: notes and average HCC score per ICD-10 block."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align, run_query
from oncology_real_world_data_extractor.schemas import CATEGORY_RISK

INPUTS = ("billable_codes",)
OUTPUTS = ("category_risk",)


@dataclass(frozen=True)
class Params:
    """Parameters for the category-risk job."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return each oncology category with its note count and average HCC score."""
    table = run_query(io.read_sql("category_risk"), inputs)
    return {"category_risk": align(table, CATEGORY_RISK)}
