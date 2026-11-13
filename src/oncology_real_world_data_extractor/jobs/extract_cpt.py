"""Extract procedure mentions from notes and code them to CPT."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align
from oncology_real_world_data_extractor.schemas import CPT_CODES, REJECTED
from oncology_real_world_data_extractor.text.interface import TextModel
from oncology_real_world_data_extractor.text.parse import parse_items, validate_procedure_item

INPUTS = ("notes",)
OUTPUTS = ("cpt_codes", "rejected_cpt")


@dataclass(frozen=True)
class Params:
    """Parameters for procedure extraction."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the coded procedure mentions and every answer that failed validation."""
    notes = inputs["notes"]
    instructions = io.read_prompt("extract_cpt")
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
            reason = validate_procedure_item(item)
            if reason:
                rejected.append(
                    {"note_id": note["note_id"], "reason": reason, "model_answer": str(item)}
                )
                continue
            rows.append(
                {
                    "note_id": note["note_id"],
                    "chunk": item["chunk"],
                    "cpt_code": item["cpt_code"],
                    "procedure_name": item["procedure_name"],
                    "confidence": float(item["confidence"]),
                }
            )
    return {
        "cpt_codes": align(pa.Table.from_pylist(rows, schema=CPT_CODES), CPT_CODES),
        "rejected_cpt": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }
