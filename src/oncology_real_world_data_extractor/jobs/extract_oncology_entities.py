"""Extract oncological findings from notes and code them to ICD-10-CM with HCC data."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.codes import oncology_category
from oncology_real_world_data_extractor.jobs._duck import align
from oncology_real_world_data_extractor.schemas import BILLABLE_CODES, ICD10_HCC, REJECTED
from oncology_real_world_data_extractor.text.interface import TextModel
from oncology_real_world_data_extractor.text.parse import parse_items, validate_oncology_item

INPUTS = ("notes",)
OUTPUTS = ("icd10_hcc", "billable_codes", "rejected_icd10")


@dataclass(frozen=True)
class Params:
    """Parameters for oncological finding extraction."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return coded findings, the nearest billable code per finding, and rejected answers."""
    notes = inputs["notes"]
    instructions = io.read_prompt("extract_oncology")
    findings: list[dict] = []
    billable: list[dict] = []
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
            reason = validate_oncology_item(item)
            if reason:
                rejected.append(
                    {"note_id": note["note_id"], "reason": reason, "model_answer": str(item)}
                )
                continue
            findings.append(
                {
                    "note_id": note["note_id"],
                    "chunk": item["chunk"],
                    "entity": item["entity"],
                    "icd10_code": item["icd10_code"],
                    "code_name": item["code_name"],
                    "billable": bool(item["billable"]),
                    "hcc_score": float(item["hcc_score"]),
                    "confidence": float(item["confidence"]),
                }
            )
            billable.extend(_billable_rows(note["note_id"], item))
    return {
        "icd10_hcc": align(pa.Table.from_pylist(findings, schema=ICD10_HCC), ICD10_HCC),
        "billable_codes": align(
            pa.Table.from_pylist(billable, schema=BILLABLE_CODES), BILLABLE_CODES
        ),
        "rejected_icd10": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }


def _billable_rows(note_id: str, item: dict) -> list[dict]:
    """Return the nearest billable code for one finding, or no row when none is billable."""
    candidates = [
        {
            "code": item["icd10_code"],
            "name": item["code_name"],
            "billable": bool(item["billable"]),
            "hcc_score": float(item["hcc_score"]),
        }
    ]
    candidates.extend(
        {
            "code": candidate["code"],
            "name": candidate["name"],
            "billable": bool(candidate["billable"]),
            "hcc_score": float(candidate["hcc_score"]),
        }
        for candidate in item.get("candidates", [])
    )
    for rank, candidate in enumerate(candidates):
        if candidate["billable"]:
            return [
                {
                    "note_id": note_id,
                    "chunk": item["chunk"],
                    "icd10_code": candidate["code"],
                    "code_name": candidate["name"],
                    "hcc_score": candidate["hcc_score"],
                    "oncology_category": oncology_category(candidate["code"]),
                    "candidate_rank": rank,
                }
            ]
    return []
