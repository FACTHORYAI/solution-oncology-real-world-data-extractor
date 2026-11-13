"""Judge whether each cancer and symptom mention is actually present for the patient."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align
from oncology_real_world_data_extractor.schemas import ASSERTIONS, REJECTED
from oncology_real_world_data_extractor.text.interface import TextModel
from oncology_real_world_data_extractor.text.parse import parse_items, validate_assertion_item

INPUTS = ("notes",)
OUTPUTS = ("assertions", "rejected_assertions")


@dataclass(frozen=True)
class Params:
    """Parameters for assertion extraction."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the assertion status per mention and every answer that failed validation."""
    notes = inputs["notes"]
    instructions = io.read_prompt("extract_assertions")
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
            reason = validate_assertion_item(item)
            if reason:
                rejected.append(
                    {"note_id": note["note_id"], "reason": reason, "model_answer": str(item)}
                )
                continue
            rows.append(
                {
                    "note_id": note["note_id"],
                    "chunk": item["chunk"],
                    "entity": item["entity"],
                    "assertion": item["assertion"],
                    "confidence": float(item["confidence"]),
                }
            )
    return {
        "assertions": align(pa.Table.from_pylist(rows, schema=ASSERTIONS), ASSERTIONS),
        "rejected_assertions": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }
