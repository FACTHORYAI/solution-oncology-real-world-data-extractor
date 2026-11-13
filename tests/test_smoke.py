"""One smoke test per job, on the synthetic sample data."""

from __future__ import annotations

from pathlib import Path

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
from oncology_real_world_data_extractor.jobs.extract_cpt import Params as CptParams
from oncology_real_world_data_extractor.jobs.extract_drugs import Params as DrugsParams
from oncology_real_world_data_extractor.jobs.extract_oncology_entities import (
    Params as OncologyParams,
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
    CPT_CODES,
    DRUG_USAGE,
    ICD10_HCC,
    PROBLEMS_AFTER_TREATMENT,
    RXNORM_DRUGS,
    SYMPTOM_ASSERTIONS,
    TEMPORAL_RELATIONS,
)
from oncology_real_world_data_extractor.text.recorded import RecordedTextModel, load_answers

REPO = Path(__file__).resolve().parent.parent
SETTINGS = Settings(sample_dir=REPO / "data" / "sample", output_dir=REPO / "output")

SAMPLE_TABLES = (
    "notes",
    "icd10_hcc",
    "billable_codes",
    "rxnorm_drugs",
    "cpt_codes",
    "assertions",
    "temporal_relations",
    "bodypart_relations",
)


@pytest.fixture(scope="module")
def recorded_model() -> RecordedTextModel:
    return RecordedTextModel(load_answers(io.read_json(REPO / "tests" / "recorded_answers.json")))


@pytest.fixture(scope="module")
def tables() -> dict[str, object]:
    return {name: io.read_table(name, SETTINGS) for name in SAMPLE_TABLES}


def run_job(name: str, tables: dict, params, model=None):
    return call_run(REGISTRY[name], tables, params, model)


def test_extract_oncology_entities(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_oncology_entities", {"notes": tables["notes"]}, OncologyParams(), recorded_model
    )
    assert outputs["icd10_hcc"].schema.equals(ICD10_HCC)
    assert outputs["icd10_hcc"].equals(tables["icd10_hcc"].select(ICD10_HCC.names))
    assert outputs["icd10_hcc"].num_rows == 22
    assert outputs["billable_codes"].schema.equals(BILLABLE_CODES)
    assert outputs["billable_codes"].equals(tables["billable_codes"].select(BILLABLE_CODES.names))
    assert outputs["rejected_icd10"].num_rows == 0


def test_extract_drugs(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job("extract_drugs", {"notes": tables["notes"]}, DrugsParams(), recorded_model)
    assert outputs["rxnorm_drugs"].schema.equals(RXNORM_DRUGS)
    assert outputs["rxnorm_drugs"].equals(tables["rxnorm_drugs"].select(RXNORM_DRUGS.names))
    assert outputs["rxnorm_drugs"].num_rows == 5
    assert outputs["rejected_drugs"].num_rows == 0


def test_extract_cpt(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job("extract_cpt", {"notes": tables["notes"]}, CptParams(), recorded_model)
    assert outputs["cpt_codes"].schema.equals(CPT_CODES)
    assert outputs["cpt_codes"].equals(tables["cpt_codes"].select(CPT_CODES.names))
    assert outputs["cpt_codes"].num_rows == 5
    assert outputs["rejected_cpt"].num_rows == 0


def test_extract_assertions(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_assertions", {"notes": tables["notes"]}, AssertionsParams(), recorded_model
    )
    assert outputs["assertions"].schema.equals(ASSERTIONS)
    assert outputs["assertions"].equals(tables["assertions"].select(ASSERTIONS.names))
    assert outputs["assertions"].num_rows == 19
    assert outputs["rejected_assertions"].num_rows == 0


def test_extract_temporal_relations(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_temporal_relations", {"notes": tables["notes"]}, TemporalParams(), recorded_model
    )
    assert outputs["temporal_relations"].schema.equals(TEMPORAL_RELATIONS)
    assert outputs["temporal_relations"].equals(
        tables["temporal_relations"].select(TEMPORAL_RELATIONS.names)
    )
    assert outputs["temporal_relations"].num_rows == 4
    assert outputs["rejected_temporal"].num_rows == 0


def test_extract_bodypart_relations(tables: dict, recorded_model: RecordedTextModel) -> None:
    outputs = run_job(
        "extract_bodypart_relations", {"notes": tables["notes"]}, BodypartParams(), recorded_model
    )
    assert outputs["bodypart_relations"].schema.equals(BODYPART_RELATIONS)
    assert outputs["bodypart_relations"].equals(
        tables["bodypart_relations"].select(BODYPART_RELATIONS.names)
    )
    assert outputs["bodypart_relations"].num_rows == 5
    assert outputs["rejected_bodypart"].num_rows == 0


def test_common_entities(tables: dict) -> None:
    common = run_job("common_entities", {"icd10_hcc": tables["icd10_hcc"]}, CommonEntitiesParams())[
        "common_entities"
    ]
    assert common.schema.equals(COMMON_ENTITIES)
    rows = {row["name"]: row["notes"] for row in common.to_pylist()}
    assert rows["Secondary malignant neoplasm of unspecified site"] == 2

    symptoms = run_job(
        "common_entities",
        {"icd10_hcc": tables["icd10_hcc"]},
        CommonEntitiesParams(entity_type="Symptom"),
    )["common_entities"]
    assert {row["name"]: row["notes"] for row in symptoms.to_pylist()}["Other fatigue"] == 2


def test_category_risk(tables: dict) -> None:
    risk = run_job(
        "category_risk", {"billable_codes": tables["billable_codes"]}, CategoryRiskParams()
    )["category_risk"]
    assert risk.schema.equals(CATEGORY_RISK)
    rows = {row["category"]: row for row in risk.to_pylist()}
    assert len(rows) == 8
    ill_defined = rows["Malignant neoplasms of ill-defined, other secondary and unspecified sites"]
    assert ill_defined["notes"] == 2
    assert ill_defined["avg_hcc_score"] == 1.02
    breast = rows["Malignant neoplasms of breast"]
    assert breast["notes"] == 1
    assert breast["avg_hcc_score"] == 0.148


def test_condition_symptom_pairs(tables: dict) -> None:
    pairs = run_job("condition_symptom_pairs", {"icd10_hcc": tables["icd10_hcc"]}, PairsParams())[
        "condition_symptom_pairs"
    ]
    assert pairs.schema.equals(CONDITION_SYMPTOM_PAIRS)
    rows = {(row["condition"], row["symptom"]) for row in pairs.to_pylist()}
    assert ("Malignant neoplasm of sigmoid colon", "Nausea") in rows
    assert ("Malignant neoplasm of sigmoid colon", "Abnormal weight loss") in rows


def test_drug_usage(tables: dict) -> None:
    usage = run_job("drug_usage", {"rxnorm_drugs": tables["rxnorm_drugs"]}, DrugUsageParams())[
        "drug_usage"
    ]
    assert usage.schema.equals(DRUG_USAGE)
    rows = {row["drug_name"]: row["mentions"] for row in usage.to_pylist()}
    assert rows["carboplatin"] == 1
    assert rows["paclitaxel"] == 1
    assert len(rows) == 5


def test_problems_after_treatment(tables: dict) -> None:
    problems = run_job(
        "problems_after_treatment",
        {"temporal_relations": tables["temporal_relations"]},
        ProblemsParams(),
    )["problems_after_treatment"]
    assert problems.schema.equals(PROBLEMS_AFTER_TREATMENT)
    rows = {(row["note_id"], row["treatment"], row["problem"]) for row in problems.to_pylist()}
    assert ("n02", "carboplatin and paclitaxel", "non-small cell lung cancer") in rows
    assert len(rows) == 4


def test_bodypart_procedures(tables: dict) -> None:
    relations = run_job(
        "bodypart_procedures",
        {"bodypart_relations": tables["bodypart_relations"]},
        BodypartProceduresParams(),
    )["bodypart_procedures"]
    assert relations.schema.equals(BODYPART_PROCEDURES)
    rows = {(row["note_id"], row["chunk1"], row["chunk2"]) for row in relations.to_pylist()}
    assert ("n03", "sigmoid colon", "colonoscopy") in rows
    assert len(rows) == 5


def test_common_procedures(tables: dict) -> None:
    procedures = run_job(
        "common_procedures", {"cpt_codes": tables["cpt_codes"]}, CommonProceduresParams()
    )["common_procedures"]
    assert procedures.schema.equals(COMMON_PROCEDURES)
    assert procedures.num_rows == 5


def test_assertion_summary(tables: dict) -> None:
    outputs = run_job(
        "assertion_summary", {"assertions": tables["assertions"]}, AssertionSummaryParams()
    )
    breakdown = outputs["assertion_breakdown"]
    assert breakdown.schema.equals(ASSERTION_BREAKDOWN)
    rows = {row["assertion"]: row["mentions"] for row in breakdown.to_pylist()}
    assert rows == {"Present": 12, "Absent": 5, "Someone_else": 2}

    symptoms = outputs["symptom_assertions"]
    assert symptoms.schema.equals(SYMPTOM_ASSERTIONS)
    symptom_rows = {
        (row["symptom"], row["assertion"]): row["mentions"] for row in symptoms.to_pylist()
    }
    assert symptom_rows[("fatigue", "Present")] == 2


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
