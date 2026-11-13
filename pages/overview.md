# Oncology Real-World Data Extractor

Turn oncology notes into structured real-world data: diagnoses, treatments and outcomes.

## Start here

1. Look at the sample tables in `data/sample` (synthetic): `notes` holds the oncology notes, and the extraction outputs hold what the six extraction jobs produced from them.
2. Read `icd10_hcc`: every finding with its ICD-10-CM code, billable flag and HCC risk score. `billable_codes` holds the nearest billable code per finding with its oncology category, ready for reimbursement analysis.
3. Ask an analysis question and run its job:

| Question | Job |
| --- | --- |
| Which cancers or symptoms are most common? | `common_entities` |
| How does risk distribute by cancer category? | `category_risk` |
| Which symptoms go with which cancer? | `condition_symptom_pairs` |
| Which drugs are used most? | `drug_usage` |
| Which problems follow a treatment? | `problems_after_treatment` |
| Which procedures were done on which organ? | `bodypart_procedures` |
| Which procedures are coded most? | `common_procedures` |
| How are findings asserted? | `assertion_summary` |

Named measures for billing and family history live in `metrics/`.

## Notes

- The sample data is synthetic; real oncology notes never enter this project.
- The six extraction jobs need a text model behind `oncology_real_world_data_extractor.text.interface`; a recorded stand-in exists for tests and demos. The analysis jobs run without any model.
- A code is a coding suggestion for analytics, not a billable claim without review.
- Results are for research and real-world-data analytics, not clinical decisions.
