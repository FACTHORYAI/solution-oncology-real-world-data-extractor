"""PyArrow schemas for every table the jobs read or write."""

import pyarrow as pa

NOTES = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("text", pa.string()),
    ]
)

ICD10_HCC = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("entity", pa.string()),
        pa.field("icd10_code", pa.string()),
        pa.field("code_name", pa.string()),
        pa.field("billable", pa.bool_()),
        pa.field("hcc_score", pa.float64()),
        pa.field("confidence", pa.float64()),
    ]
)

BILLABLE_CODES = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("icd10_code", pa.string()),
        pa.field("code_name", pa.string()),
        pa.field("hcc_score", pa.float64()),
        pa.field("oncology_category", pa.string()),
        pa.field("candidate_rank", pa.int32()),
    ]
)

RXNORM_DRUGS = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("drug_chunk", pa.string()),
        pa.field("rxnorm_code", pa.string()),
        pa.field("drug_name", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

PROCEDURE_CODES = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("procedure_code", pa.string()),
        pa.field("procedure_name", pa.string()),
        pa.field("code_system", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

ASSERTIONS = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("chunk", pa.string()),
        pa.field("entity", pa.string()),
        pa.field("assertion", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

TEMPORAL_RELATIONS = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("relation", pa.string()),
        pa.field("entity1", pa.string()),
        pa.field("chunk1", pa.string()),
        pa.field("entity2", pa.string()),
        pa.field("chunk2", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

BODYPART_RELATIONS = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("relation", pa.string()),
        pa.field("entity1", pa.string()),
        pa.field("chunk1", pa.string()),
        pa.field("entity2", pa.string()),
        pa.field("chunk2", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

REJECTED = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("reason", pa.string()),
        pa.field("model_answer", pa.string()),
    ]
)

COMMON_ENTITIES = pa.schema(
    [
        pa.field("name", pa.string()),
        pa.field("notes", pa.int64()),
    ]
)

CATEGORY_RISK = pa.schema(
    [
        pa.field("category", pa.string()),
        pa.field("notes", pa.int64()),
        pa.field("avg_hcc_score", pa.float64()),
    ]
)

CONDITION_SYMPTOM_PAIRS = pa.schema(
    [
        pa.field("condition", pa.string()),
        pa.field("symptom", pa.string()),
        pa.field("notes", pa.int64()),
        pa.field("normalized_count", pa.float64()),
    ]
)

DRUG_USAGE = pa.schema(
    [
        pa.field("drug_name", pa.string()),
        pa.field("mentions", pa.int64()),
    ]
)

PROBLEMS_AFTER_TREATMENT = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("treatment", pa.string()),
        pa.field("problem", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

BODYPART_PROCEDURES = pa.schema(
    [
        pa.field("note_id", pa.string()),
        pa.field("entity1", pa.string()),
        pa.field("chunk1", pa.string()),
        pa.field("entity2", pa.string()),
        pa.field("chunk2", pa.string()),
        pa.field("confidence", pa.float64()),
    ]
)

COMMON_PROCEDURES = pa.schema(
    [
        pa.field("procedure_name", pa.string()),
        pa.field("mentions", pa.int64()),
    ]
)

ASSERTION_BREAKDOWN = pa.schema(
    [
        pa.field("assertion", pa.string()),
        pa.field("mentions", pa.int64()),
    ]
)

SYMPTOM_ASSERTIONS = pa.schema(
    [
        pa.field("symptom", pa.string()),
        pa.field("assertion", pa.string()),
        pa.field("mentions", pa.int64()),
    ]
)
