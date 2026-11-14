# Oncology Real-World Data Extractor

Turn oncology notes into structured real-world data: diagnoses, treatments and outcomes.

## Start here

1. Look at the sample tables in `data/sample` (synthetic): `notes` holds 150 oncology notes, and the extraction outputs hold what the six extraction jobs produced from them.
2. Read `icd10_hcc`: every finding with its ICD-10-CM code, billable flag and HCC risk score. `billable_codes` holds the nearest billable code per finding with its oncology category, ready for reimbursement analysis. `procedure_codes` holds the procedures with their ICD-10-PCS codes.
3. Read `graph_nodes` and `graph_edges`: every edge is one fact — whether a condition is present, absent or a relative's, which organ a procedure was done on or a problem sits in, and which event came before or after another. Each fact names the note it came from and the text span.
4. Ask an analysis question and run its job:

| Question | Job |
| --- | --- |
| Which cancers or symptoms are most common? | `common_entities` |
| How does risk distribute by cancer category? | `category_risk` |
| Which symptoms go with which cancer? | `condition_symptom_pairs` |
| Which drugs are used most? | `drug_usage` |
| Which problems followed a treatment? | `problems_after_treatment` |
| Which procedures were done on which organ? | `bodypart_procedures` |
| Which procedures are coded most? | `common_procedures` |
| How are findings asserted? | `assertion_summary` |
| How do findings, drugs, procedures and organs connect? | `build_knowledge_graph` |

Named measures for billing and family history live in `metrics/`.

## Notes

- The sample data is synthetic; real oncology notes never enter this project.
- The six extraction jobs need a text model behind `oncology_real_world_data_extractor.text.interface`; a recorded stand-in exists for tests and demos. The graph and analysis jobs run without any model.
- A code is a coding suggestion for analytics, not a billable claim without review. Procedures are coded to ICD-10-PCS; CPT is not included because of its licence.
- Results are for research and real-world-data analytics, not clinical decisions.
