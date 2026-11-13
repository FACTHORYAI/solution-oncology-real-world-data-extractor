# Oncology Real-World Data Extractor — agent instructions

You help members turn oncology notes into structured real-world data: coded diagnoses and symptoms, drugs, procedures, assertion status, and the relations between them.

## What the project provides

- Sample tables in `data/sample` (synthetic): `notes`, and the extraction outputs `icd10_hcc`, `billable_codes`, `rxnorm_drugs`, `cpt_codes`, `assertions`, `temporal_relations`, `bodypart_relations`.
- Jobs under `src/oncology_real_world_data_extractor/jobs`: six extraction jobs that read notes through a `TextModel` (`text/interface.py`) — oncology findings with ICD-10-CM/HCC coding, drugs with RxNorm, procedures with CPT, assertions, temporal relations, body-part relations — and eight analysis jobs over the extracted tables.

## How to answer a question

1. Classify what the member asks: which cancers or symptoms are most common (`common_entities`), how risk distributes by cancer category (`category_risk`), which symptoms go with which cancer (`condition_symptom_pairs`), which drugs are used most (`drug_usage`), which problems follow a treatment (`problems_after_treatment`), which procedures were done on which organ (`bodypart_procedures`), which procedures are coded most (`common_procedures`), or how findings are asserted (`assertion_summary`).
2. Check the parameters with `uv run python -m oncology_real_world_data_extractor <job> --help`; `min_confidence` keeps confident mentions, `limit` trims result tables, `min_notes` drops one-note pairs.
3. Run the job, or answer directly from the tables: `icd10_hcc` holds every finding with its ICD-10-CM code, billable flag and HCC score; `billable_codes` holds the nearest billable code with its oncology category; `assertions` holds Present / Absent / Possible / Hypothetical / Conditional / Someone_else per cancer and symptom.
4. Report results as a table with the counts behind them (`notes`, `mentions`, `normalized_count`). Never guess beyond the tables.

## Data care

- The sample data is synthetic; real oncology notes never enter this project.
- The six extraction jobs need a model behind `text.interface`; the repository ships a recorded stand-in for tests and demos.
- Codes are resolved against ICD-10-CM, CPT and RxNorm vocabularies; a code is a coding suggestion for analytics, not a billable claim without review.
- Results are for research and real-world-data analytics, not clinical decisions.
