"""Parse and validate model answers before they become table rows."""

from __future__ import annotations

import json

ENTITY_TYPES = ("Oncological", "Symptom", "Treatment")
ASSERTION_ENTITY_TYPES = ("Oncological", "Symptom")
ASSERTION_STATUSES = (
    "Present",
    "Absent",
    "Possible",
    "Hypothetical",
    "Conditional",
    "Someone_else",
)
TEMPORAL_RELATIONS = ("BEFORE", "AFTER", "OVERLAP")
TEMPORAL_ENTITY_TYPES = ("Treatment", "Problem", "Symptom", "Test")
BODYPART_ENTITY_TYPES = ("Internal_organ_or_component", "Problem", "Procedure")


def parse_items(answer: str) -> list[dict]:
    """Parse a model answer that must be a JSON array of objects."""
    try:
        items = json.loads(answer)
    except json.JSONDecodeError as error:
        message = f"model answer is not JSON: {error.msg} at position {error.pos}"
        raise ValueError(message) from error
    if not isinstance(items, list):
        message = "model answer is not a JSON array"
        raise ValueError(message)
    return [item for item in items if isinstance(item, dict)]


def _check_confidence(item: dict) -> str:
    confidence = item.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return "confidence is not a number"
    if not 0 <= float(confidence) <= 1:
        return "confidence is not between 0 and 1"
    return ""


def _check_text(item: dict, key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        return f"missing or empty {key}"
    return ""


def validate_oncology_item(item: dict) -> str:
    """Return the reason the oncology finding is rejected, or "" when it is valid."""
    for key in ("chunk", "icd10_code", "code_name"):
        reason = _check_text(item, key)
        if reason:
            return reason
    if item.get("entity") not in ENTITY_TYPES:
        return f"entity is not one of {ENTITY_TYPES}"
    if not isinstance(item.get("billable"), bool):
        return "billable is not a boolean"
    hcc_score = item.get("hcc_score")
    if not isinstance(hcc_score, (int, float)) or isinstance(hcc_score, bool) or hcc_score < 0:
        return "hcc_score is not a non-negative number"
    candidates = item.get("candidates", [])
    if not isinstance(candidates, list):
        return "candidates is not a list"
    for candidate in candidates:
        if not isinstance(candidate, dict):
            return "a candidate is not an object"
        for key in ("code", "name"):
            reason = _check_text(candidate, key)
            if reason:
                return f"candidate {reason}"
        if not isinstance(candidate.get("billable"), bool):
            return "candidate billable is not a boolean"
        score = candidate.get("hcc_score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or score < 0:
            return "candidate hcc_score is not a non-negative number"
    return _check_confidence(item)


def validate_drug_item(item: dict) -> str:
    """Return the reason the drug mention is rejected, or "" when it is valid."""
    for key in ("chunk", "rxnorm_code", "drug_name"):
        reason = _check_text(item, key)
        if reason:
            return reason
    return _check_confidence(item)


def validate_procedure_item(item: dict) -> str:
    """Return the reason the procedure mention is rejected, or "" when it is valid."""
    for key in ("chunk", "cpt_code", "procedure_name"):
        reason = _check_text(item, key)
        if reason:
            return reason
    return _check_confidence(item)


def validate_assertion_item(item: dict) -> str:
    """Return the reason the assertion row is rejected, or "" when it is valid."""
    reason = _check_text(item, "chunk")
    if reason:
        return reason
    if item.get("entity") not in ASSERTION_ENTITY_TYPES:
        return f"entity is not one of {ASSERTION_ENTITY_TYPES}"
    if item.get("assertion") not in ASSERTION_STATUSES:
        return f"assertion is not one of {ASSERTION_STATUSES}"
    return _check_confidence(item)


def validate_temporal_relation_item(item: dict) -> str:
    """Return the reason the temporal relation is rejected, or "" when it is valid."""
    if item.get("relation") not in TEMPORAL_RELATIONS:
        return f"relation is not one of {TEMPORAL_RELATIONS}"
    for key in ("entity1", "entity2"):
        if item.get(key) not in TEMPORAL_ENTITY_TYPES:
            return f"{key} is not one of {TEMPORAL_ENTITY_TYPES}"
    for key in ("chunk1", "chunk2"):
        reason = _check_text(item, key)
        if reason:
            return reason
    return _check_confidence(item)


def validate_bodypart_relation_item(item: dict) -> str:
    """Return the reason the body-part relation is rejected, or "" when it is valid."""
    reason = _check_text(item, "relation")
    if reason:
        return reason
    for key in ("entity1", "entity2"):
        if item.get(key) not in BODYPART_ENTITY_TYPES:
            return f"{key} is not one of {BODYPART_ENTITY_TYPES}"
    for key in ("chunk1", "chunk2"):
        reason = _check_text(item, key)
        if reason:
            return reason
    return _check_confidence(item)
