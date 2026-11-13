"""Extract drug mentions from notes and resolve them to RxNorm."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align
from oncology_real_world_data_extractor.schemas import REJECTED, RXNORM_DRUGS
from oncology_real_world_data_extractor.text.interface import TextModel
from oncology_real_world_data_extractor.text.parse import parse_items, validate_drug_item

INPUTS = ("notes",)
OUTPUTS = ("rxnorm_drugs", "rejected_drugs")


@dataclass(frozen=True)
class Params:
    """Parameters for drug extraction."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the resolved drug mentions and every answer that failed validation."""
    notes = inputs["notes"]
    instructions = io.read_prompt("extract_drugs")
    rows: list[dict] = []
    rejected: list[dict] = []
    for note in notes.to_pylist():
        answer = model.complete(instructions, note["text"])
        try:
            items = parse_items(answer)
        except ValueError as error:
            rejected.append(
                {"note_id": note["note_id"], "reason": str(error), "model_answer": answer}
            )
            items = []
        for item in items:
            reason = validate_drug_item(item)
            if reason:
                rejected.append(
                    {"note_id": note["note_id"], "reason": reason, "model_answer": str(item)}
                )
                continue
            rows.append(
                {
                    "note_id": note["note_id"],
                    "drug_chunk": item["chunk"],
                    "rxnorm_code": item["rxnorm_code"],
                    "drug_name": item["drug_name"],
                    "confidence": float(item["confidence"]),
                }
            )
    return {
        "rxnorm_drugs": align(pa.Table.from_pylist(rows, schema=RXNORM_DRUGS), RXNORM_DRUGS),
        "rejected_drugs": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }
