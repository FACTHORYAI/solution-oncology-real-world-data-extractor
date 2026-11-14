"""One test per job, on the synthetic sample data.

The extraction jobs must give back the sample tables from the recorded answers, with nothing
rejected. Each analysis job is compared with a plain-Python reference computed here from the
extracted tables, and the graph jobs with a reference of the graph contract.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import duckdb
import pyarrow as pa
import pytest

from oncology_real_world_data_extractor import io
from oncology_real_world_data_extractor.codes import oncology_category
from oncology_real_world_data_extractor.config import Settings
from oncology_real_world_data_extractor.jobs import REGISTRY, call_run
from oncology_real_world_data_extractor.jobs.assertion_summary import (
    Params as AssertionSummaryParams,
)
from oncology_real_world_data_extractor.jobs.bodypart_procedures import (
    Params as BodypartProceduresParams,
)
from oncology_real_world_data_extractor.jobs.build_knowledge_graph import Params as GraphParams
from oncology_real_world_data_extractor.jobs.category_risk import Params as CategoryRiskParams
from oncology_real_world_data_extractor.jobs.common_entities import Params as CommonEntitiesParams
from oncology_real_world_data_extractor.jobs.common_procedures import (
    Params as CommonProceduresParams,
)
from oncology_real_world_data_extractor.jobs.condition_symptom_pairs import (
    Params as PairsParams,
)
from oncology_real_world_data_extractor.jobs.drug_usage import Params as DrugUsageParams
from oncology_real_world_data_extractor.jobs.extract_assertions import Params as AssertionsParams
from oncology_real_world_data_extractor.jobs.extract_bodypart_relations import (
    Params as BodypartParams,
)
from oncology_real_world_data_extractor.jobs.extract_drugs import Params as DrugsParams
from oncology_real_world_data_extractor.jobs.extract_oncology_entities import (
    Params as OncologyParams,
)
from oncology_real_world_data_extractor.jobs.extract_procedure_codes import (
    Params as ProcedureCodesParams,
)
from oncology_real_world_data_extractor.jobs.extract_temporal_relations import (
    Params as TemporalParams,
)
from oncology_real_world_data_extractor.jobs.problems_after_treatment import (
    Params as ProblemsParams,
)
from oncology_real_world_data_extractor.schemas import (
    ASSERTION_BREAKDOWN,
    ASSERTIONS,
    BILLABLE_CODES,
    BODYPART_PROCEDURES,
    BODYPART_RELATIONS,
    CATEGORY_RISK,
    COMMON_ENTITIES,
    COMMON_PROCEDURES,
    CONDITION_SYMPTOM_PAIRS,
    DRUG_USAGE,
    GRAPH_EDGES,
    GRAPH_NODES,
    ICD10_HCC,
    NOTES,
    PROBLEMS_AFTER_TREATMENT,
    PROCEDURE_CODES,
    REJECTED,
    RXNORM_DRUGS,
    SYMPTOM_ASSERTIONS,
    TEMPORAL_RELATIONS,
)
from oncology_real_world_data_extractor.text.parse import ASSERTION_STATUSES
from oncology_real_world_data_extractor.text.recorded import RecordedTextModel, load_answers

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings(sample_dir=REPO / "data" / "sample", output_dir=REPO / "output")

SAMPLE_TABLES = (
    "notes",
    "icd10_hcc",
    "billable_codes",
    "rxnorm_drugs",
    "procedure_codes",
    "assertions",
    "temporal_relations",
    "bodypart_relations",
    "graph_nodes",
    "graph_edges",
)
GRAPH_INPUTS = (
    "notes",
    "icd10_hcc",
    "rxnorm_drugs",
    "procedure_codes",
    "assertions",
    "temporal_relations",
    "bodypart_relations",
)


@pytest.fixture(scope="module")
def recorded_model() -> RecordedTextModel:
    return RecordedTextModel(load_answers(io.read_json(REPO / "tests" / "recorded_answers.json")))


@pytest.fixture(scope="module")
def tables() -> dict[str, pa.Table]:
    return {name: io.read_table(name, SETTINGS) for name in SAMPLE_TABLES}


def run_job(name: str, tables: dict, params, model=None):
    return call_run(REGISTRY[name], tables, params, model)


def rows(tables: dict, name: str) -> list[dict]:
    return tables[name].to_pylist()


# The extraction jobs reproduce the sample tables from the recorded answers.


def test_extract_oncology_entities(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_oncology_entities", {"notes": tables["notes"]}, OncologyParams(), recorded_model
    )
    assert outputs["icd10_hcc"].schema.equals(ICD10_HCC)
    assert outputs["icd10_hcc"].num_rows > 0
    assert outputs["icd10_hcc"].equals(tables["icd10_hcc"].select(ICD10_HCC.names))
    assert outputs["billable_codes"].schema.equals(BILLABLE_CODES)
    assert outputs["billable_codes"].num_rows > 0
    assert outputs["billable_codes"].equals(tables["billable_codes"].select(BILLABLE_CODES.names))
    assert outputs["rejected_icd10"].num_rows == 0
    # A finding coded to a category that is not billable falls back to a billable code.
    not_billable = [row for row in rows(outputs, "icd10_hcc") if not row["billable"]]
    assert not_billable
    ranks = {row["candidate_rank"] for row in rows(outputs, "billable_codes")}
    assert ranks == {0, 1}


def test_extract_drugs(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job("extract_drugs", {"notes": tables["notes"]}, DrugsParams(), recorded_model)
    assert outputs["rxnorm_drugs"].schema.equals(RXNORM_DRUGS)
    assert outputs["rxnorm_drugs"].num_rows > 0
    assert outputs["rxnorm_drugs"].equals(tables["rxnorm_drugs"].select(RXNORM_DRUGS.names))
    assert outputs["rejected_drugs"].num_rows == 0


def test_extract_procedure_codes(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_procedure_codes",
        {"notes": tables["notes"]},
        ProcedureCodesParams(),
        recorded_model,
    )
    codes = outputs["procedure_codes"]
    assert codes.schema.equals(PROCEDURE_CODES)
    assert codes.num_rows > 0
    assert codes.equals(tables["procedure_codes"].select(PROCEDURE_CODES.names))
    assert outputs["rejected_procedures"].num_rows == 0
    assert {row["code_system"] for row in codes.to_pylist()} == {"ICD-10-PCS"}
    assert all(len(row["procedure_code"]) == 7 for row in codes.to_pylist())


class FixedModel:
    """A text model that gives one fixed answer."""

    def __init__(self, answer: str) -> None:
        self.answer = answer

    def complete(self, instructions: str, text: str) -> str:
        return self.answer


def test_extract_procedure_codes_rejects_what_is_not_icd10_pcs() -> None:
    notes = pa.Table.from_pylist([{"note_id": "a", "text": "A biopsy."}], schema=NOTES)
    good = {
        "chunk": "biopsy",
        "procedure_code": "0HBU3ZX",
        "procedure_name": "Excision of Left Breast, Percutaneous Approach, Diagnostic",
        "code_system": "ICD-10-PCS",
        "confidence": 0.9,
    }
    answer = [
        good,
        {**good, "procedure_code": "19081"},  # a five-digit code is not ICD-10-PCS
        {**good, "procedure_code": "0HBU3ZI"},  # the letter I is not used in ICD-10-PCS
        {**good, "code_system": "ICD-10-CM"},
        {k: v for k, v in good.items() if k != "code_system"},
    ]
    outputs = run_job(
        "extract_procedure_codes",
        {"notes": notes},
        ProcedureCodesParams(),
        FixedModel(json.dumps(answer)),
    )
    assert [row["procedure_code"] for row in rows(outputs, "procedure_codes")] == ["0HBU3ZX"]
    rejected = rows(outputs, "rejected_procedures")
    assert len(rejected) == 4
    assert outputs["rejected_procedures"].schema.equals(REJECTED)


def test_extract_assertions(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_assertions", {"notes": tables["notes"]}, AssertionsParams(), recorded_model
    )
    assert outputs["assertions"].schema.equals(ASSERTIONS)
    assert outputs["assertions"].num_rows > 0
    assert outputs["assertions"].equals(tables["assertions"].select(ASSERTIONS.names))
    assert outputs["rejected_assertions"].num_rows == 0
    assert {row["assertion"] for row in rows(outputs, "assertions")} == set(ASSERTION_STATUSES)


def test_extract_temporal_relations(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_temporal_relations", {"notes": tables["notes"]}, TemporalParams(), recorded_model
    )
    assert outputs["temporal_relations"].schema.equals(TEMPORAL_RELATIONS)
    assert outputs["temporal_relations"].num_rows > 0
    assert outputs["temporal_relations"].equals(
        tables["temporal_relations"].select(TEMPORAL_RELATIONS.names)
    )
    assert outputs["rejected_temporal"].num_rows == 0


def test_extract_bodypart_relations(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_bodypart_relations", {"notes": tables["notes"]}, BodypartParams(), recorded_model
    )
    assert outputs["bodypart_relations"].schema.equals(BODYPART_RELATIONS)
    assert outputs["bodypart_relations"].num_rows > 0
    assert outputs["bodypart_relations"].equals(
        tables["bodypart_relations"].select(BODYPART_RELATIONS.names)
    )
    assert outputs["rejected_bodypart"].num_rows == 0


def test_every_extracted_row_belongs_to_a_note_and_its_chunk_stands_in_it(tables: dict) -> None:
    texts = {row["note_id"]: row["text"] for row in rows(tables, "notes")}
    assert len(texts) == tables["notes"].num_rows
    for name, columns in (
        ("icd10_hcc", ("chunk",)),
        ("rxnorm_drugs", ("drug_chunk",)),
        ("procedure_codes", ("chunk",)),
        ("assertions", ("chunk",)),
        ("temporal_relations", ("chunk1", "chunk2")),
        ("bodypart_relations", ("chunk1", "chunk2")),
    ):
        for row in rows(tables, name):
            for column in columns:
                assert row[column] in texts[row["note_id"]], (name, row)


# The analysis tests compare each job with a plain-Python reference over the extracted tables.


def test_common_entities(tables: dict) -> None:
    def expected(entity: str, limit: int) -> list[tuple[str, int]]:
        notes_by_name: dict[str, set[str]] = defaultdict(set)
        for row in rows(tables, "icd10_hcc"):
            if row["entity"] == entity and row["code_name"] != "":
                notes_by_name[row["code_name"]].add(row["note_id"])
        ranked = sorted(((name, len(ids)) for name, ids in notes_by_name.items()), key=_by_count)
        return ranked[:limit]

    for params, entity, limit in (
        (CommonEntitiesParams(), "Oncological", 20),
        (CommonEntitiesParams(entity_type="Symptom", limit=5), "Symptom", 5),
        (CommonEntitiesParams(entity_type="Treatment"), "Treatment", 20),
    ):
        common = run_job("common_entities", {"icd10_hcc": tables["icd10_hcc"]}, params)[
            "common_entities"
        ]
        assert common.schema.equals(COMMON_ENTITIES)
        reference = expected(entity, limit)
        assert reference
        assert [(r["name"], r["notes"]) for r in common.to_pylist()] == reference


def _by_count(item: tuple[str, int]) -> tuple[int, str]:
    return (-item[1], item[0])


def test_category_risk(tables: dict) -> None:
    risk = run_job(
        "category_risk", {"billable_codes": tables["billable_codes"]}, CategoryRiskParams()
    )["category_risk"]
    assert risk.schema.equals(CATEGORY_RISK)
    notes_by_category: dict[str, set[str]] = defaultdict(set)
    scores: dict[str, list[float]] = defaultdict(list)
    for row in rows(tables, "billable_codes"):
        # The category of a code is the one the code's block gives.
        assert row["oncology_category"] == oncology_category(row["icd10_code"])
        if row["oncology_category"]:
            notes_by_category[row["oncology_category"]].add(row["note_id"])
            scores[row["oncology_category"]].append(row["hcc_score"])
    reference = sorted(
        ((c, len(ids), mean(scores[c])) for c, ids in notes_by_category.items()),
        key=lambda item: (-item[2], item[0]),
    )
    assert len(reference) >= 8
    result = risk.to_pylist()
    assert [r["category"] for r in result] == [c for c, _n, _s in reference]
    assert [r["notes"] for r in result] == [n for _c, n, _s in reference]
    assert [r["avg_hcc_score"] for r in result] == pytest.approx([s for _c, _n, s in reference])


def test_condition_symptom_pairs(tables: dict) -> None:
    def expected(min_confidence: float, min_notes: int) -> list[tuple[str, str, int, float]]:
        pairs: set[tuple[str, str, str]] = set()
        findings = rows(tables, "icd10_hcc")
        for condition in findings:
            for symptom in findings:
                if (
                    condition["note_id"] == symptom["note_id"]
                    and condition["entity"] == "Oncological"
                    and symptom["entity"] == "Symptom"
                    and condition["confidence"] >= min_confidence
                    and symptom["confidence"] >= min_confidence
                    and condition["code_name"]
                    and symptom["code_name"]
                ):
                    pairs.add((condition["note_id"], condition["code_name"], symptom["code_name"]))
        counts = Counter((condition, symptom) for _note, condition, symptom in pairs)
        counts = Counter({pair: n for pair, n in counts.items() if n >= min_notes})
        by_symptom: dict[str, list[int]] = defaultdict(list)
        for (_condition, symptom), n in counts.items():
            by_symptom[symptom].append(n)
        result = []
        for (condition, symptom), n in counts.items():
            low, high = min(by_symptom[symptom]), max(by_symptom[symptom])
            result.append((condition, symptom, n, 0.0 if low == high else (n - low) / (high - low)))
        return sorted(result)

    for params in (PairsParams(), PairsParams(min_notes=2), PairsParams(min_confidence=0.9)):
        pairs = run_job("condition_symptom_pairs", {"icd10_hcc": tables["icd10_hcc"]}, params)[
            "condition_symptom_pairs"
        ]
        assert pairs.schema.equals(CONDITION_SYMPTOM_PAIRS)
        reference = expected(params.min_confidence, params.min_notes)
        assert reference
        result = [
            (r["condition"], r["symptom"], r["notes"], r["normalized_count"])
            for r in pairs.to_pylist()
        ]
        assert [r[:3] for r in result] == [r[:3] for r in reference]
        assert [r[3] for r in result] == pytest.approx([r[3] for r in reference])
    # With a second note needed, some pair stays and some are dropped.
    assert 0 < len(expected(0.3, 2)) < len(expected(0.3, 1))


def test_drug_usage(tables: dict) -> None:
    def expected(min_confidence: float, limit: int) -> list[tuple[str, int]]:
        counts = Counter(
            row["drug_name"]
            for row in rows(tables, "rxnorm_drugs")
            if row["confidence"] >= min_confidence and row["drug_name"]
        )
        return sorted(counts.items(), key=_by_count)[:limit]

    for params in (DrugUsageParams(), DrugUsageParams(min_confidence=0.9, limit=5)):
        usage = run_job("drug_usage", {"rxnorm_drugs": tables["rxnorm_drugs"]}, params)[
            "drug_usage"
        ]
        assert usage.schema.equals(DRUG_USAGE)
        reference = expected(params.min_confidence, params.limit)
        assert reference
        assert [(r["drug_name"], r["mentions"]) for r in usage.to_pylist()] == reference


def test_problems_after_treatment(tables: dict) -> None:
    def expected(min_confidence: float) -> list[tuple[str, str, str, float]]:
        found = []
        for row in rows(tables, "temporal_relations"):
            if row["confidence"] < min_confidence:
                continue
            # "A AFTER B" and "B BEFORE A" both say that A came later.
            if (row["relation"], row["entity1"], row["entity2"]) == (
                "AFTER",
                "Problem",
                "Treatment",
            ):
                found.append((row["note_id"], row["chunk2"], row["chunk1"], row["confidence"]))
            if (row["relation"], row["entity1"], row["entity2"]) == (
                "BEFORE",
                "Treatment",
                "Problem",
            ):
                found.append((row["note_id"], row["chunk1"], row["chunk2"], row["confidence"]))
        return sorted(found)

    for params in (ProblemsParams(), ProblemsParams(min_confidence=0.0)):
        problems = run_job(
            "problems_after_treatment",
            {"temporal_relations": tables["temporal_relations"]},
            params,
        )["problems_after_treatment"]
        assert problems.schema.equals(PROBLEMS_AFTER_TREATMENT)
        reference = expected(params.min_confidence)
        assert reference
        result = [
            (r["note_id"], r["treatment"], r["problem"], r["confidence"])
            for r in problems.to_pylist()
        ]
        assert result == reference


def test_problems_after_treatment_reads_the_direction_of_the_relation() -> None:
    relations = [
        ("a", "AFTER", "Problem", "rash", "Treatment", "carboplatin"),  # the rash came later
        ("b", "BEFORE", "Treatment", "carboplatin", "Problem", "rash"),  # the same, turned round
        ("c", "AFTER", "Treatment", "carboplatin", "Problem", "rash"),  # the treatment came later
        ("d", "BEFORE", "Problem", "rash", "Treatment", "carboplatin"),  # the same, turned round
        ("e", "OVERLAP", "Problem", "rash", "Treatment", "carboplatin"),
    ]
    table = pa.Table.from_pylist(
        [
            dict(zip(TEMPORAL_RELATIONS.names, (note, rel, e1, c1, e2, c2, 0.9), strict=True))
            for note, rel, e1, c1, e2, c2 in relations
        ],
        schema=TEMPORAL_RELATIONS,
    )
    outputs = run_job("problems_after_treatment", {"temporal_relations": table}, ProblemsParams())
    result = [
        (r["note_id"], r["treatment"], r["problem"])
        for r in rows(outputs, "problems_after_treatment")
    ]
    assert result == [("a", "carboplatin", "rash"), ("b", "carboplatin", "rash")]


def test_bodypart_procedures(tables: dict) -> None:
    organ, procedure = "Internal_organ_or_component", "Procedure"
    expected = sorted(
        (r["note_id"], r["entity1"], r["chunk1"], r["entity2"], r["chunk2"], r["confidence"])
        for r in rows(tables, "bodypart_relations")
        if {r["entity1"], r["entity2"]} == {organ, procedure} and r["chunk1"] and r["chunk2"]
    )
    # The sample also relates organs to problems, and those are not procedures.
    assert any(r["entity2"] == "Problem" for r in rows(tables, "bodypart_relations"))
    relations = run_job(
        "bodypart_procedures",
        {"bodypart_relations": tables["bodypart_relations"]},
        BodypartProceduresParams(),
    )["bodypart_procedures"]
    assert relations.schema.equals(BODYPART_PROCEDURES)
    assert expected
    result = sorted(
        (r["note_id"], r["entity1"], r["chunk1"], r["entity2"], r["chunk2"], r["confidence"])
        for r in relations.to_pylist()
    )
    assert result == expected
    assert all("Problem" not in (r[1], r[3]) for r in result)


def test_common_procedures(tables: dict) -> None:
    def expected(min_confidence: float, limit: int) -> list[tuple[str, int]]:
        counts = Counter(
            row["procedure_name"]
            for row in rows(tables, "procedure_codes")
            if row["confidence"] >= min_confidence and row["procedure_name"]
        )
        return sorted(counts.items(), key=_by_count)[:limit]

    for params in (CommonProceduresParams(), CommonProceduresParams(min_confidence=0.9, limit=5)):
        procedures = run_job(
            "common_procedures", {"procedure_codes": tables["procedure_codes"]}, params
        )["common_procedures"]
        assert procedures.schema.equals(COMMON_PROCEDURES)
        reference = expected(params.min_confidence, params.limit)
        assert reference
        result = [(r["procedure_name"], r["mentions"]) for r in procedures.to_pylist()]
        assert result == reference


def test_assertion_summary(tables: dict) -> None:
    def expected_symptoms(limit: int) -> list[tuple[str, str, int]]:
        counts = Counter(
            (row["chunk"].lower(), row["assertion"])
            for row in rows(tables, "assertions")
            if row["entity"] == "Symptom"
            and row["assertion"] in ("Present", "Absent")
            and row["chunk"]
        )
        ranked = sorted(
            ((s, a, n) for (s, a), n in counts.items()), key=lambda i: (-i[2], i[0], i[1])
        )
        return ranked[:limit]

    breakdown_counts = Counter(row["assertion"] for row in rows(tables, "assertions"))
    expected_breakdown = sorted(breakdown_counts.items(), key=lambda i: (-i[1], i[0]))
    for params in (AssertionSummaryParams(), AssertionSummaryParams(limit=5)):
        outputs = run_job("assertion_summary", {"assertions": tables["assertions"]}, params)
        breakdown = outputs["assertion_breakdown"]
        assert breakdown.schema.equals(ASSERTION_BREAKDOWN)
        assert [
            (r["assertion"], r["mentions"]) for r in breakdown.to_pylist()
        ] == expected_breakdown
        symptoms = outputs["symptom_assertions"]
        assert symptoms.schema.equals(SYMPTOM_ASSERTIONS)
        reference = expected_symptoms(params.limit)
        assert reference
        result = [(r["symptom"], r["assertion"], r["mentions"]) for r in symptoms.to_pylist()]
        assert result == reference
    assert set(breakdown_counts) == set(ASSERTION_STATUSES)


def test_oncology_category() -> None:
    assert oncology_category("C18.7") == "Malignant neoplasms of digestive organs"
    assert oncology_category("C50.912") == "Malignant neoplasms of breast"
    assert (
        oncology_category("C81.10")
        == "Malignant neoplasms of lymphoid, hematopoietic and related tissue"
    )
    assert oncology_category("R53.83") == "General symptoms and signs"
    assert oncology_category("Z99.9") == ""
    assert oncology_category("") == ""


# The knowledge graph.

RELATIONSHIPS = {"ASSERTION", "PERFORMED_ON", "INVOLVES", "BEFORE", "AFTER", "OVERLAP"}
NODE_TYPES = {"Condition", "Drug", "Procedure", "Body_Part"}
KINDS = {
    "Oncological": ("Condition",),
    "Symptom": ("Condition",),
    "Problem": ("Condition",),
    "Treatment": ("Drug", "Procedure"),
    "Test": ("Procedure",),
    "Procedure": ("Procedure",),
}


def mentions(tables: dict) -> list[tuple[str, str, str, str]]:
    """The (note, text, node type, node id) of every text a code gives a node."""
    found = []
    for r in rows(tables, "icd10_hcc"):
        if r["entity"] in ("Oncological", "Symptom") and r["icd10_code"].strip():
            found.append(
                (r["note_id"], r["chunk"], "Condition", f"Condition:icd10:{r['icd10_code']}")
            )
    for r in rows(tables, "rxnorm_drugs"):
        if r["rxnorm_code"].strip():
            found.append((r["note_id"], r["drug_chunk"], "Drug", f"Drug:rxnorm:{r['rxnorm_code']}"))
    for r in rows(tables, "procedure_codes"):
        system = r["code_system"].lower().replace("-", "")
        node = f"Procedure:{system}:{r['procedure_code']}"
        found.append((r["note_id"], r["chunk"], "Procedure", node))
    return found


def expected_graph(tables: dict) -> tuple[dict[str, str], dict[tuple, float]]:
    """Plain-Python reference of the graph: node labels and edges with their confidence."""
    texts = {r["note_id"]: r["text"] for r in rows(tables, "notes")}
    coded = mentions(tables)

    def nodes_for(note: str, chunk: str, entity: str) -> list[str]:
        return [
            node
            for n, c, kind, node in coded
            if n == note and c == chunk and kind in KINDS.get(entity, ())
        ]

    labels: dict[str, list[str]] = defaultdict(list)
    for r in rows(tables, "icd10_hcc"):
        if r["entity"] in ("Oncological", "Symptom") and r["icd10_code"].strip():
            labels[f"Condition:icd10:{r['icd10_code']}"].append(r["code_name"].strip())
    for r in rows(tables, "rxnorm_drugs"):
        labels[f"Drug:rxnorm:{r['rxnorm_code']}"].append(r["drug_name"].strip())
    for r in rows(tables, "procedure_codes"):
        system = r["code_system"].lower().replace("-", "")
        labels[f"Procedure:{system}:{r['procedure_code']}"].append(r["procedure_name"].strip())
    organs = []
    for r in rows(tables, "bodypart_relations"):
        if r["entity1"] == "Internal_organ_or_component":
            organs.append((r["note_id"], r["chunk1"], r["entity2"], r["chunk2"], r["confidence"]))
        if r["entity2"] == "Internal_organ_or_component":
            organs.append((r["note_id"], r["chunk2"], r["entity1"], r["chunk1"], r["confidence"]))
    for r in rows(tables, "bodypart_relations"):
        for entity, chunk in ((r["entity1"], r["chunk1"]), (r["entity2"], r["chunk2"])):
            if entity == "Internal_organ_or_component":
                labels[f"Body_Part:{chunk.strip().lower()}"].append(chunk.strip())

    facts: list[tuple[str, str | None, str, str | None, str, str, float]] = []
    for r in rows(tables, "assertions"):
        for source in nodes_for(r["note_id"], r["chunk"], r["entity"]):
            facts.append(
                (
                    source,
                    None,
                    "ASSERTION",
                    r["assertion"],
                    r["note_id"],
                    r["chunk"],
                    r["confidence"],
                )
            )
    for note, organ, entity, chunk, confidence in organs:
        for source in nodes_for(note, chunk, entity):
            if source.startswith("Procedure:"):
                relationship = "PERFORMED_ON"
            elif source.startswith("Condition:"):
                relationship = "INVOLVES"
            else:
                continue
            target = f"Body_Part:{organ.strip().lower()}"
            facts.append((source, target, relationship, None, note, chunk, confidence))
    for r in rows(tables, "temporal_relations"):
        for source in nodes_for(r["note_id"], r["chunk1"], r["entity1"]):
            for target in nodes_for(r["note_id"], r["chunk2"], r["entity2"]):
                if source != target:
                    facts.append(
                        (
                            source,
                            target,
                            r["relation"],
                            None,
                            r["note_id"],
                            r["chunk1"],
                            r["confidence"],
                        )
                    )

    edges: dict[tuple, float] = {}
    for source, target, relationship, value, note, chunk, confidence in facts:
        start = texts[note].find(chunk)
        span = (start, start + len(chunk)) if start >= 0 else (None, None)
        key = (source, target, relationship, value, note, *span)
        edges[key] = max(confidence, edges.get(key, confidence))
    return {node: min(names) for node, names in labels.items()}, edges


def test_build_knowledge_graph(tables: dict) -> None:
    inputs = {name: tables[name] for name in GRAPH_INPUTS}
    outputs = run_job("build_knowledge_graph", inputs, GraphParams())
    assert outputs["graph_nodes"].schema.equals(GRAPH_NODES)
    assert outputs["graph_edges"].schema.equals(GRAPH_EDGES)
    assert outputs["graph_nodes"].num_rows > 0
    assert outputs["graph_edges"].num_rows > 0
    assert outputs["graph_nodes"].equals(tables["graph_nodes"].select(GRAPH_NODES.names))
    assert outputs["graph_edges"].equals(tables["graph_edges"].select(GRAPH_EDGES.names))


def test_graph_tables_follow_the_contract(tables: dict) -> None:
    nodes = rows(tables, "graph_nodes")
    edges = rows(tables, "graph_edges")
    texts = {r["note_id"]: r["text"] for r in rows(tables, "notes")}
    node_ids = {node["node_id"] for node in nodes}
    assert len(node_ids) == len(nodes)
    assert all(node["node_id"] == f"{node['node_type']}:{node['key']}" for node in nodes)
    assert {node["node_type"] for node in nodes} == NODE_TYPES
    assert {edge["relationship"] for edge in edges} == RELATIONSHIPS
    assert len({edge["edge_id"] for edge in edges}) == len(edges)
    mention_spans = {(node, note, chunk) for note, chunk, _kind, node in mentions(tables)}
    for edge in edges:
        assert edge["source_id"] in node_ids
        # A fact points at a node or holds a literal value, never both.
        assert (edge["target_id"] in node_ids) != (edge["value"] is not None)
        assert edge["evidence_document_id"] in texts
        assert edge["valid_from"] is None
        assert edge["valid_to"] is None
        assert edge["confidence"] is not None
        # The edge id is the hash of its source, relationship, target or value, and evidence.
        parts = [
            edge["source_id"],
            edge["relationship"],
            edge["target_id"] or "",
            edge["value"] or "",
            edge["evidence_document_id"],
            str(-1 if edge["evidence_start"] is None else edge["evidence_start"]),
        ]
        assert edge["edge_id"] == hashlib.md5("|".join(parts).encode()).hexdigest()
        # The span is the text of the edge's source as the note writes it, found by text search.
        text = texts[edge["evidence_document_id"]]
        assert edge["evidence_start"] is not None
        span = text[edge["evidence_start"] : edge["evidence_end"]]
        assert (edge["source_id"], edge["evidence_document_id"], span) in mention_spans
        assert text.find(span) == edge["evidence_start"]
        if edge["relationship"] == "ASSERTION":
            assert edge["source_id"].startswith("Condition:icd10:")
            assert edge["value"] in ASSERTION_STATUSES
        elif edge["relationship"] == "PERFORMED_ON":
            assert edge["source_id"].startswith("Procedure:icd10pcs:")
            assert edge["target_id"].startswith("Body_Part:")
        elif edge["relationship"] == "INVOLVES":
            assert edge["source_id"].startswith("Condition:icd10:")
            assert edge["target_id"].startswith("Body_Part:")
        else:
            assert edge["target_id"] is not None


def test_graph_matches_the_plain_python_reference(tables: dict) -> None:
    labels, edges = expected_graph(tables)
    assert {n["node_id"]: n["label"] for n in rows(tables, "graph_nodes")} == labels
    actual = {
        (
            e["source_id"],
            e["target_id"],
            e["relationship"],
            e["value"],
            e["evidence_document_id"],
            e["evidence_start"],
            e["evidence_end"],
        ): e["confidence"]
        for e in rows(tables, "graph_edges")
    }
    assert actual == edges
    assert len(rows(tables, "graph_edges")) == len(edges)
    # Every kind of fact is in the sample, and so is a node of every type.
    assert {key[2] for key in actual} >= RELATIONSHIPS
    # Every node an edge names exists.
    node_ids = set(labels)
    assert all(key[0] in node_ids for key in actual)
    assert all(key[1] in node_ids for key in actual if key[1] is not None)


def test_graph_of_a_few_rows_drops_what_has_no_node_and_merges_repeats() -> None:
    notes = [
        {"note_id": "a", "text": "Rash after carboplatin and a biopsy of the left breast."},
        {"note_id": "b", "text": "No findings."},
    ]
    icd = {"entity": "Symptom", "icd10_code": "R21", "billable": True, "hcc_score": 0.0}
    icd10_hcc = [
        {"note_id": "a", "chunk": "Rash", "code_name": "Rash", "confidence": 0.9, **icd},
        {"note_id": "b", "chunk": "Rash", "code_name": "rash", "confidence": 0.9, **icd},
    ]
    rxnorm = [
        {
            "note_id": "a",
            "drug_chunk": "carboplatin",
            "rxnorm_code": "2264",
            "drug_name": "carboplatin",
            "confidence": 0.9,
        }
    ]
    procedures = [
        {
            "note_id": "a",
            "chunk": "biopsy",
            "procedure_code": "0HBU3ZX",
            "procedure_name": "Excision of Left Breast, Percutaneous Approach, Diagnostic",
            "code_system": "ICD-10-PCS",
            "confidence": 0.9,
        }
    ]
    mention = {"entity": "Symptom", "assertion": "Present"}
    assertions = [
        {"note_id": "a", "chunk": "Rash", "confidence": 0.7, **mention},
        {"note_id": "a", "chunk": "Rash", "confidence": 0.9, **mention},  # the same fact again
        {"note_id": "a", "chunk": "fever", "confidence": 0.8, **mention},  # no code, no node
        {"note_id": "b", "chunk": "Rash", "confidence": 0.8, **mention},  # text not in the note
    ]
    after = {"relation": "AFTER", "entity1": "Problem", "chunk1": "Rash"}
    after |= {"entity2": "Treatment", "chunk2": "carboplatin", "note_id": "a"}
    temporal = [
        {**after, "confidence": 0.7},
        {**after, "confidence": 0.9},  # the same fact again
        {**after, "chunk2": "cisplatin", "confidence": 0.9},  # no code, no node
        {**after, "entity2": "Problem", "chunk2": "Rash", "confidence": 0.9},  # a node to itself
    ]
    bodypart = [
        {
            "note_id": "a",
            "relation": "in",
            "entity1": "Internal_organ_or_component",
            "chunk1": "left breast",
            "entity2": "Procedure",
            "chunk2": "biopsy",
            "confidence": 0.8,
        },
        {
            "note_id": "a",
            "relation": "in",
            "entity1": "Internal_organ_or_component",
            "chunk1": "left breast",
            "entity2": "Problem",
            "chunk2": "scar",  # no code, no node
            "confidence": 0.8,
        },
    ]
    inputs = {
        "notes": pa.Table.from_pylist(notes, schema=NOTES),
        "icd10_hcc": pa.Table.from_pylist(icd10_hcc, schema=ICD10_HCC),
        "rxnorm_drugs": pa.Table.from_pylist(rxnorm, schema=RXNORM_DRUGS),
        "procedure_codes": pa.Table.from_pylist(procedures, schema=PROCEDURE_CODES),
        "assertions": pa.Table.from_pylist(assertions, schema=ASSERTIONS),
        "temporal_relations": pa.Table.from_pylist(temporal, schema=TEMPORAL_RELATIONS),
        "bodypart_relations": pa.Table.from_pylist(bodypart, schema=BODYPART_RELATIONS),
    }
    outputs = run_job("build_knowledge_graph", inputs, GraphParams())
    nodes = {r["node_id"]: r["label"] for r in rows(outputs, "graph_nodes")}
    assert nodes == {
        "Body_Part:left breast": "left breast",
        "Condition:icd10:R21": "Rash",
        "Drug:rxnorm:2264": "carboplatin",
        "Procedure:icd10pcs:0HBU3ZX": "Excision of Left Breast, Percutaneous Approach, Diagnostic",
    }
    edges = {
        (e["source_id"], e["relationship"], e["evidence_document_id"]): e
        for e in rows(outputs, "graph_edges")
    }
    assert len(edges) == outputs["graph_edges"].num_rows == 4
    found = edges[("Condition:icd10:R21", "ASSERTION", "a")]
    assert (found["evidence_start"], found["evidence_end"], found["confidence"]) == (0, 4, 0.9)
    assert found["value"] == "Present"
    missing = edges[("Condition:icd10:R21", "ASSERTION", "b")]
    assert (missing["evidence_start"], missing["evidence_end"]) == (None, None)
    after_edge = edges[("Condition:icd10:R21", "AFTER", "a")]
    assert after_edge["target_id"] == "Drug:rxnorm:2264"
    assert after_edge["confidence"] == 0.9
    performed = edges[("Procedure:icd10pcs:0HBU3ZX", "PERFORMED_ON", "a")]
    assert performed["target_id"] == "Body_Part:left breast"
    assert (performed["evidence_start"], performed["evidence_end"]) == (29, 35)


# The named measures.


def test_metrics_run_on_the_sample(tables: dict) -> None:
    connection = duckdb.connect()
    for name, table in tables.items():
        connection.register(name, table)
    results = {}
    for path in sorted((REPO / "metrics").glob("*.sql")):
        result = connection.sql(path.read_text(encoding="utf-8")).fetchall()
        assert len(result) == 1 and len(result[0]) == 1, path.name
        results[path.stem] = result[0][0]
    assert set(results) == {"billable_share", "coded_note_share", "family_history_count"}
    assert 0 < results["billable_share"] <= 1
    assert 0 < results["coded_note_share"] <= 1
    expected_family = sum(r["assertion"] == "Someone_else" for r in rows(tables, "assertions"))
    assert results["family_history_count"] == expected_family > 0


# The manifest.


def test_manifest_matches_the_registry_and_the_sample() -> None:
    manifest = tomllib.loads((REPO / "facthory.toml").read_text(encoding="utf-8"))
    datasets = {d["name"]: d for d in manifest["dataset"]}
    assert set(datasets) == set(SAMPLE_TABLES)
    for dataset in datasets.values():
        assert (REPO / dataset["path"]).is_file()
        assert dataset["synthetic"] is True
        assert dataset["licence"] == "CC0-1.0"
    jobs = {j["name"]: j for j in manifest["job"]}
    assert set(jobs) == set(REGISTRY)
    available = set(datasets)
    for name, job in jobs.items():
        spec = REGISTRY[name]
        module, _, function = job["entry"].partition(":")
        assert getattr(importlib.import_module(module), function) is spec.run
        assert tuple(job["inputs"]) == spec.inputs
        assert tuple(job["outputs"]) == spec.outputs
        assert job["mode"] == ("job" if spec.needs_model else "call")
        # Every input is a sample table or what an earlier job writes.
        assert set(job["inputs"]) <= available | {o for j in jobs.values() for o in j["outputs"]}
    assert (REPO / manifest["skill"]["instructions"]).is_file()
