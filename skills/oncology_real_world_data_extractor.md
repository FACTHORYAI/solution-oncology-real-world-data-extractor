# Oncology Real-World Data Extractor — agent instructions

You help members turn oncology notes into structured real-world data: coded diagnoses and symptoms, drugs, procedures, assertion status, the relations between them, and a knowledge graph of what the notes say.

## What the project provides

- Sample tables in `data/sample` (synthetic): `notes` (150 invented oncology notes), the extraction outputs `icd10_hcc`, `billable_codes`, `rxnorm_drugs`, `procedure_codes`, `assertions`, `temporal_relations`, `bodypart_relations`, and `graph_nodes` / `graph_edges` (the knowledge graph as tables). Every row names its note in `note_id`. All synthetic.
- Jobs under `src/oncology_real_world_data_extractor/jobs`: six extraction jobs that read notes through a `TextModel` (`text/interface.py`) — oncology findings with ICD-10-CM/HCC coding, drugs with RxNorm, procedures with ICD-10-PCS, assertions, temporal relations, body-part relations — one job that turns the extracted rows into graph node and edge tables, and eight analysis jobs over the extracted tables.

## How to answer a question

1. Classify what the member asks: which cancers or symptoms are most common (`common_entities`), how risk distributes by cancer category (`category_risk`), which symptoms go with which cancer (`condition_symptom_pairs`), which drugs are used most (`drug_usage`), which problems followed a treatment (`problems_after_treatment`), which procedures were done on which organ (`bodypart_procedures`), which procedures are coded most (`common_procedures`), how findings are asserted (`assertion_summary`), or how the findings, drugs, procedures and organs of the notes connect (`build_knowledge_graph`).
2. Check the parameters with `uv run python -m oncology_real_world_data_extractor <job> --help`; `min_confidence` keeps confident mentions, `limit` trims result tables, `min_notes` drops one-note pairs.
3. Run the job, or answer directly from the tables: `icd10_hcc` holds every finding with its ICD-10-CM code, billable flag and HCC score; `billable_codes` holds the nearest billable code with its oncology category; `procedure_codes` holds ICD-10-PCS codes; `assertions` holds Present / Absent / Possible / Hypothetical / Conditional / Someone_else per cancer and symptom. `graph_nodes` holds one row per `Condition`, `Drug`, `Procedure` or `Body_Part` node (`node_id`, `node_type`, `key`, `label`); `graph_edges` holds one fact per row: `Condition -ASSERTION-> status` (the status in `value`), `Procedure -PERFORMED_ON-> Body_Part`, `Condition -INVOLVES-> Body_Part`, and `BEFORE`, `AFTER` or `OVERLAP` between two events. Join edges to nodes on `source_id` / `target_id`; filter with SQL.
4. Every edge names the note it came from (`evidence_document_id`, a `note_id` of `notes`) and the character span (`evidence_start`, `evidence_end`) of its source text in that note. Nodes are shared by all notes, so this is how you tell which note a fact belongs to. An edge records what a note says: read the `ASSERTION` fact for the same condition and note to see whether it is present, absent or a relative's. `AFTER` reads from the first event to the second: "A AFTER B" means A happened after B. Quote the evidence when you explain a result.
5. Report results as a table with the counts behind them (`notes`, `mentions`, `normalized_count`). Never guess beyond the tables; say which rows come from which job.

## Data care

- The sample data is synthetic; real oncology notes never enter this project.
- The six extraction jobs need a model behind `text.interface`; the repository ships a recorded stand-in for tests and demos.
- Codes are coding suggestions for analytics, not a billable claim without review. The sample's ICD-10-CM codes are real but not checked against the current release, its RxNorm and ICD-10-PCS codes and its HCC scores are illustrative. Procedures are coded to ICD-10-PCS; CPT is not included because of its licence.
- The notes carry no patient and no date, so the graph has no patient node and no dates.
- `common_entities`, `category_risk` and `condition_symptom_pairs` count every mention, denied ones and relatives' ones included; join with `assertions` to leave them out.
- Results are for research and real-world-data analytics, not clinical decisions.
