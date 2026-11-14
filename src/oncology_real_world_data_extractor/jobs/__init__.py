"""The jobs of this solution: plain functions from named tables to named tables."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pyarrow as pa

from oncology_real_world_data_extractor.jobs import (
    assertion_summary,
    bodypart_procedures,
    build_knowledge_graph,
    category_risk,
    common_entities,
    common_procedures,
    condition_symptom_pairs,
    drug_usage,
    extract_assertions,
    extract_bodypart_relations,
    extract_drugs,
    extract_oncology_entities,
    extract_procedure_codes,
    extract_temporal_relations,
    problems_after_treatment,
)


@dataclass(frozen=True)
class JobSpec:
    """One job: its callable, its parameter class and its input and output tables."""

    name: str
    description: str
    run: Callable[..., dict[str, pa.Table]]
    params_cls: type
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    needs_model: bool = False


REGISTRY: dict[str, JobSpec] = {
    spec.name: spec
    for spec in (
        JobSpec(
            name="extract_oncology_entities",
            description="Extract oncological findings and code them to ICD-10-CM with HCC data.",
            run=extract_oncology_entities.run,
            params_cls=extract_oncology_entities.Params,
            inputs=extract_oncology_entities.INPUTS,
            outputs=extract_oncology_entities.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="extract_drugs",
            description="Extract drug mentions and resolve them to RxNorm.",
            run=extract_drugs.run,
            params_cls=extract_drugs.Params,
            inputs=extract_drugs.INPUTS,
            outputs=extract_drugs.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="extract_procedure_codes",
            description="Extract procedure mentions and code them to ICD-10-PCS.",
            run=extract_procedure_codes.run,
            params_cls=extract_procedure_codes.Params,
            inputs=extract_procedure_codes.INPUTS,
            outputs=extract_procedure_codes.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="extract_assertions",
            description="Judge whether each cancer and symptom mention is present.",
            run=extract_assertions.run,
            params_cls=extract_assertions.Params,
            inputs=extract_assertions.INPUTS,
            outputs=extract_assertions.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="extract_temporal_relations",
            description="Extract the temporal relations between clinical events.",
            run=extract_temporal_relations.run,
            params_cls=extract_temporal_relations.Params,
            inputs=extract_temporal_relations.INPUTS,
            outputs=extract_temporal_relations.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="extract_bodypart_relations",
            description="Extract the relations between body parts, problems and procedures.",
            run=extract_bodypart_relations.run,
            params_cls=extract_bodypart_relations.Params,
            inputs=extract_bodypart_relations.INPUTS,
            outputs=extract_bodypart_relations.OUTPUTS,
            needs_model=True,
        ),
        JobSpec(
            name="build_knowledge_graph",
            description="Build the oncology knowledge graph as node and edge tables.",
            run=build_knowledge_graph.run,
            params_cls=build_knowledge_graph.Params,
            inputs=build_knowledge_graph.INPUTS,
            outputs=build_knowledge_graph.OUTPUTS,
        ),
        JobSpec(
            name="common_entities",
            description="The most common oncological findings or symptoms.",
            run=common_entities.run,
            params_cls=common_entities.Params,
            inputs=common_entities.INPUTS,
            outputs=common_entities.OUTPUTS,
        ),
        JobSpec(
            name="category_risk",
            description="Notes and average HCC score per oncology category.",
            run=category_risk.run,
            params_cls=category_risk.Params,
            inputs=category_risk.INPUTS,
            outputs=category_risk.OUTPUTS,
        ),
        JobSpec(
            name="condition_symptom_pairs",
            description="Condition and symptom pairs that appear in the same note.",
            run=condition_symptom_pairs.run,
            params_cls=condition_symptom_pairs.Params,
            inputs=condition_symptom_pairs.INPUTS,
            outputs=condition_symptom_pairs.OUTPUTS,
        ),
        JobSpec(
            name="drug_usage",
            description="The drugs named most often, above a confidence floor.",
            run=drug_usage.run,
            params_cls=drug_usage.Params,
            inputs=drug_usage.INPUTS,
            outputs=drug_usage.OUTPUTS,
        ),
        JobSpec(
            name="problems_after_treatment",
            description="Problems that occurred after a treatment.",
            run=problems_after_treatment.run,
            params_cls=problems_after_treatment.Params,
            inputs=problems_after_treatment.INPUTS,
            outputs=problems_after_treatment.OUTPUTS,
        ),
        JobSpec(
            name="bodypart_procedures",
            description="Which procedures were performed on which internal body part.",
            run=bodypart_procedures.run,
            params_cls=bodypart_procedures.Params,
            inputs=bodypart_procedures.INPUTS,
            outputs=bodypart_procedures.OUTPUTS,
        ),
        JobSpec(
            name="common_procedures",
            description="The procedures coded most often, above a confidence floor.",
            run=common_procedures.run,
            params_cls=common_procedures.Params,
            inputs=common_procedures.INPUTS,
            outputs=common_procedures.OUTPUTS,
        ),
        JobSpec(
            name="assertion_summary",
            description="How assertion statuses distribute and how symptoms are asserted.",
            run=assertion_summary.run,
            params_cls=assertion_summary.Params,
            inputs=assertion_summary.INPUTS,
            outputs=assertion_summary.OUTPUTS,
        ),
    )
}


def param_values(spec: JobSpec, args: Any) -> Any:
    """Build the job's Params instance from parsed command-line arguments."""
    values = {
        field.name: getattr(args, field.name)
        for field in spec.params_cls.__dataclass_fields__.values()
    }
    return spec.params_cls(**values)


def call_run(
    spec: JobSpec, inputs: dict[str, pa.Table], params: Any, model: Any
) -> dict[str, pa.Table]:
    """Call the job's run with the arguments its signature asks for."""
    if spec.needs_model:
        return spec.run(inputs=inputs, params=params, model=model)
    return spec.run(inputs=inputs, params=params)
