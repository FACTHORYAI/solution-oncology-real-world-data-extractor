"""Extract the relations between body parts, problems and procedures in notes."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.jobs._duck import align
from oncology_real_world_data_extractor.schemas import BODYPART_RELATIONS, REJECTED
from oncology_real_world_data_extractor.text.interface import TextModel
from oncology_real_world_data_extractor.text.parse import (
    parse_items,
    validate_bodypart_relation_item,
)

INPUTS = ("notes",)
OUTPUTS = ("bodypart_relations", "rejected_bodypart")


@dataclass(frozen=True)
class Params:
    """Parameters for body-part relation extraction."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the body-part relations and every answer that failed validation."""
    notes = inputs["notes"]
    instructions = io.read_prompt("extract_bodypart_relations")
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
            reason = validate_bodypart_relation_item(item)
            if reason:
                rejected.append(
                    {"note_id": note["note_id"], "reason": reason, "model_answer": str(item)}
                )
                continue
            rows.append(
                {
                    "note_id": note["note_id"],
                    "relation": item["relation"],
                    "entity1": item["entity1"],
                    "chunk1": item["chunk1"],
                    "entity2": item["entity2"],
                    "chunk2": item["chunk2"],
                    "confidence": float(item["confidence"]),
                }
            )
    return {
        "bodypart_relations": align(
            pa.Table.from_pylist(rows, schema=BODYPART_RELATIONS), BODYPART_RELATIONS
        ),
        "rejected_bodypart": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }
