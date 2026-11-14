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

# Graph tables, draft 0 (the shared contract for all solutions).
# graph_nodes: node_id is stable across runs and built as "<node_type>:<key>"; key is the
# natural key, with its code system where there is one (for example "rxnorm:11289").
GRAPH_NODES = pa.schema(
    [
        pa.field("node_id", pa.string()),
        pa.field("node_type", pa.string()),
        pa.field("key", pa.string()),
        pa.field("label", pa.string()),
        pa.field("properties", pa.string()),  # JSON text, only for things nobody filters on
    ]
)

# graph_edges: one fact per row. A fact points at another node (target_id) or holds a
# literal (value, with target_id null). Every node an edge names exists in graph_nodes.
# evidence_* ties the fact to the character span of a note; null when unknown.
GRAPH_EDGES = pa.schema(
    [
        pa.field("edge_id", pa.string()),  # stable: hash of source, relationship, target, evidence
        pa.field("source_id", pa.string()),
        pa.field("target_id", pa.string()),
        pa.field("relationship", pa.string()),
        pa.field("value", pa.string()),
        pa.field("valid_from", pa.date32()),
        pa.field("valid_to", pa.date32()),
        pa.field("evidence_document_id", pa.string()),
        pa.field("evidence_start", pa.int32()),
        pa.field("evidence_end", pa.int32()),
        pa.field("confidence", pa.float64()),
        pa.field("properties", pa.string()),
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
