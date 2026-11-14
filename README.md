<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FACTHORYAI/.github/main/brand/word-mark-only-mono.svg">
    <img alt="Facthory" src="https://raw.githubusercontent.com/FACTHORYAI/.github/main/brand/word-mark-only.svg" width="360">
  </picture>
</p>

# Oncology Real-World Data Extractor

Turn oncology notes into structured real-world data: diagnoses, staging, treatments and outcomes as tables in Facthory.

![Licence: Apache-2.0](https://img.shields.io/badge/licence-Apache--2.0-blue) ![Runs on Facthory](https://img.shields.io/badge/runs%20on-Facthory-1f6feb) ![Status: install coming](https://img.shields.io/badge/status-install%20coming-lightgrey)

> **Install coming.** This is a Facthory solution: its data, analysis code, agent skill and starting pages load into a Facthory workspace as a ready project. Installing from this page is not available yet; this repository is being prepared for it.

## What it does

Oncology Real-World Data Extractor reads free-text oncology notes and turns them into tables: which cancers, metastases and symptoms a note names and how each is coded, which drugs and procedures it names, whether each finding is really present for the patient, in which order the events happened, and which organ each procedure or finding concerns. It then ties those rows into a knowledge graph and answers eight analysis questions on them.

1. **Extract.** Six jobs read each note through a text model, which answers in JSON that is validated before it becomes rows. Answers that fail validation go to `rejected_*` tables with the reason.
   - `extract_oncology_entities`: cancers, metastases, symptoms and treatments, each coded to ICD-10-CM with a billable flag and an HCC score (`icd10_hcc`), and the nearest billable code with its oncology category (`billable_codes`);
   - `extract_drugs`: drug mentions resolved to RxNorm;
   - `extract_procedure_codes`: procedure mentions coded to ICD-10-PCS;
   - `extract_assertions`: whether each cancer and symptom mention is Present, Absent, Possible, Hypothetical, Conditional or Someone_else ("denies chest pain", "her mother was treated for breast cancer");
   - `extract_temporal_relations`: which event came before, after or at the same time as another ("two weeks after the last cycle, he developed neuropathy");
   - `extract_bodypart_relations`: which organ a procedure was done on or a problem sits in.
2. **Build the graph.** One SQL job, `build_knowledge_graph`, turns the extracted rows into two tables, `graph_nodes` and `graph_edges`: condition, drug, procedure and body-part nodes, and facts about them. Every edge records the note and text span it came from.
3. **Analyse.** Eight SQL jobs summarise the extracted tables:
   - the most common cancers or symptoms, by the notes they appear in;
   - the notes and the average HCC score per ICD-10 oncology category;
   - cancer and symptom pairs in the same note, scaled per symptom;
   - the drugs named most often;
   - the problems that followed a treatment;
   - which procedures were done on which organ;
   - the procedures coded most often;
   - how the assertion statuses distribute and how symptoms are asserted.

Step 1 needs a text model. Steps 2 and 3 are plain SQL on DuckDB and need none.

## How it works in Facthory

- Jobs read tables and write tables. They draw no screens and own no storage; querying, charting, joining with your own data, permissions and audit belong to the platform.
- The knowledge graph is two tables, not a graph database. See "Graph tables" below. Any graph view can be drawn from them.
- The agent skill in `skills/` and the starter page in `pages/` describe how to work with the tables and the jobs.
- Sample data in this repository is synthetic. No real patient data.

## What the result could look like

![Mock-up of a Facthory report page titled "Insights from oncology reports", marked "Sample data": four figures (reports processed, entities extracted, share mapped to ICD-10, procedure mentions), a table of ICD-10 coded entities with note id, text chunk, entity type, code and description, the share of entities by type, the top ten ICD-10 categories and top ten procedures as bar charts, the assertion statuses, and the average risk score per cancer category.](docs/images/oncology-report-mockup.png)

A design illustration of a report built from this solution's tables: coded entities, procedures, assertion statuses and the average risk score per category. It is a mock-up. Its figures are illustrative: they are not produced by this repository's sample data, and it is not a screenshot of a released feature.

## Jobs

| Job | What it does | Inputs | Outputs |
| --- | --- | --- | --- |
| `extract_oncology_entities` | Extracts cancer, symptom and treatment findings and codes each to ICD-10-CM with billable status and HCC score | `notes` | `icd10_hcc`, `billable_codes`, `rejected_icd10` |
| `extract_drugs` | Extracts drug mentions and resolves them to RxNorm | `notes` | `rxnorm_drugs`, `rejected_drugs` |
| `extract_procedure_codes` | Extracts procedure mentions and codes them to ICD-10-PCS | `notes` | `procedure_codes`, `rejected_procedures` |
| `extract_assertions` | Judges whether each cancer and symptom mention is Present, Absent, Possible, Hypothetical, Conditional or Someone_else | `notes` | `assertions`, `rejected_assertions` |
| `extract_temporal_relations` | Extracts which clinical event happened before, after or with another | `notes` | `temporal_relations`, `rejected_temporal` |
| `extract_bodypart_relations` | Extracts which organ a procedure was done on or a problem involves | `notes` | `bodypart_relations`, `rejected_bodypart` |
| `build_knowledge_graph` | Builds the oncology knowledge graph as node and edge tables | `notes`, `icd10_hcc`, `rxnorm_drugs`, `procedure_codes`, `assertions`, `temporal_relations`, `bodypart_relations` | `graph_nodes`, `graph_edges` |
| `common_entities` | The most common cancer findings or symptoms, by notes they appear in | `icd10_hcc` | `common_entities` |
| `category_risk` | Notes and average HCC score per ICD-10 oncology category | `billable_codes` | `category_risk` |
| `condition_symptom_pairs` | Cancer and symptom pairs in the same note, normalised per symptom | `icd10_hcc` | `condition_symptom_pairs` |
| `drug_usage` | The drugs named most often, above a confidence floor | `rxnorm_drugs` | `drug_usage` |
| `problems_after_treatment` | Treatment and problem pairs where the problem followed the treatment | `temporal_relations` | `problems_after_treatment` |
| `bodypart_procedures` | Which procedures were performed on which internal body part | `bodypart_relations` | `bodypart_procedures` |
| `common_procedures` | The procedures coded most often, above a confidence floor | `procedure_codes` | `common_procedures` |
| `assertion_summary` | How assertion statuses distribute and how symptoms are asserted | `assertions` | `assertion_breakdown`, `symptom_assertions` |

The six extraction jobs take a `TextModel` (see `src/oncology_real_world_data_extractor/text/interface.py`) as a third argument; Facthory provides model access, and every model answer is validated before it becomes a row. The table of notes and every table extracted from it have a `note_id` column that names the note; the graph's `evidence_document_id` holds the same value. Named measures for billing and family history live in `metrics/`.

### Graph tables

The graph follows the "graph tables, draft 0" shape that all Facthory solutions share.

- `graph_nodes`: `node_id` (stable across runs, `<node_type>:<key>`), `node_type`, `key` (the natural key, with its code system where there is one, for example `icd10:C50.912`), `label`, `properties` (JSON text).
- `graph_edges`: `edge_id` (stable hash of source, relationship, target or value, and evidence), `source_id`, `target_id` (null when the fact is a literal), `relationship`, `value` (the literal, else null), `valid_from` and `valid_to` (dates the fact held; `valid_to` is null when unknown), `evidence_document_id`, `evidence_start`, `evidence_end` (character offsets in that note; null when the text was not found), `confidence` (null when not scored), `properties`.

Every node an edge names exists in `graph_nodes`, and a fact has either `target_id` or `value`, never both. In this repository the nodes are:

- `Condition`, one per ICD-10-CM code that `icd10_hcc` gives a cancer, a metastasis or a symptom (`Condition:icd10:C50.912`), labelled with the code's description. The family-history codes are conditions too. The treatment rows of `icd10_hcc` (encounter codes such as Z51.11) are not nodes: the drug or the procedure behind a treatment is.
- `Drug`, one per RxNorm code (`Drug:rxnorm:10382`), labelled with the resolved drug name.
- `Procedure`, one per procedure code with its code system (`Procedure:icd10pcs:0HBU3ZX`), labelled with the code's description.
- `Body_Part`, one per organ text, lower-cased and trimmed (`Body_Part:left breast`), labelled with the text as written.

A text becomes a node through the code the same note gives it, so the same words in two notes can be two nodes. The facts are:

- `Condition -ASSERTION-> <status>` for every assertion row: a literal edge with the status (Present, Absent, Possible, Hypothetical, Conditional or Someone_else) in `value`, and the confidence of that row.
- `Procedure -PERFORMED_ON-> Body_Part` and `Condition -INVOLVES-> Body_Part` for the body-part relations of a procedure and of a problem.
- `<event> -BEFORE | AFTER | OVERLAP-> <event>` for every temporal relation, read from the first event to the second (`AFTER` means the first event happened after the second). An event is a condition, a drug or a procedure.

A row whose text has no code in its note has no node to attach to and gives no edge. An edge is evidence of what the note says, not of what is true: read `ASSERTION` for the same condition and `evidence_document_id` to see whether it is present. A node is shared by all notes; `evidence_document_id` (a `note_id` of `notes`) says which note a fact belongs to. The evidence span is the first occurrence of the source's text in that note (`evidence_start` inclusive, `evidence_end` exclusive, 0-based): the condition for an assertion, the procedure for `PERFORMED_ON`, the condition for `INVOLVES`, the first event for a temporal fact. The notes carry no patient or date, so `valid_from` and `valid_to` are always null.

## Data

The sample tables in `data/sample/` are synthetic and CC0-1.0: `notes`, `icd10_hcc`, `billable_codes`, `rxnorm_drugs`, `procedure_codes`, `assertions`, `temporal_relations`, `bodypart_relations`, `graph_nodes` and `graph_edges`. They hold 150 invented oncology notes (breast, lung, colon and rectal, pancreatic, prostate, kidney, lymphoma and melanoma), 909 coded findings, 244 drug mentions, 203 procedure codes, 865 assertions, 352 temporal relations, 352 body-part relations, 199 graph nodes and 1,562 edges, made by `data/generate_sample.py`. See [data/README.md](data/README.md) for origin and licence per file. No real patient data.

## Run it locally

```
uv sync
uv run python -m oncology_real_world_data_extractor common_entities --entity-type Oncological
uv run python -m oncology_real_world_data_extractor category_risk
uv run python -m oncology_real_world_data_extractor problems_after_treatment --min-confidence 0.8
uv run python -m oncology_real_world_data_extractor build_knowledge_graph
uv run pytest
```

`uv run python -m oncology_real_world_data_extractor --help` lists every job; each job has its own `--help`. The six extraction jobs additionally take `--model-answers <file>` with a recorded-answers JSON (see `tests/recorded_answers.json`), since they read notes through a model behind `text.interface`; the other jobs run without any model. Verified on the synthetic sample data only, not yet in a Facthory workspace.

Codes are coding suggestions for analytics: `icd10_hcc` keeps the model's best code with its billable flag and HCC score, `billable_codes` keeps the nearest billable code with its ICD-10 oncology category, and `condition_symptom_pairs` expresses each pair's note count as a share of the most frequent condition for its symptom.

## Open points

- **No clinical text model ships.** The six extraction jobs run through the `TextModel` interface. The only implementation is `text/recorded.py`, which replays recorded answers for the sample notes. A model must be plugged in behind `text/interface.py` before new notes can be processed. A rules-based stand-in for clinical extraction is deliberately not provided.
- **Each note is read six times.** The six extraction jobs each send the note to the model with their own prompt. Facthory will replace them with one combined extraction call per document: one prompt and one JSON schema that returns the findings, drugs, procedures, assertions, temporal relations and body-part relations together.
- **Codes are resolved inside the extraction prompts.** There is no vocabulary lookup. The ICD-10-CM codes in the sample are real, public codes that have not been checked against the current release of the code set, the RxNorm codes are illustrative, and the HCC scores are illustrative: they follow the pattern of the CMS-HCC relative factors per cancer group, and the mapping from code to group is not verified.
- **Procedures are coded to ICD-10-PCS, not to CPT.** CPT is not included because of its licence: it is copyrighted by the American Medical Association. ICD-10-PCS is published by CMS and is in the public domain. The procedure codes in the sample are illustrative seven-character identifiers in ICD-10-PCS shape that have not been checked against the vocabulary.
- **Evidence spans are found by text search**, not reported by the model: `evidence_start` and `evidence_end` mark the first occurrence of the source's text in the note, and are null when it is not found (for example a word the model normalised). `valid_from` and `valid_to` are always null.
- **The notes carry no patient and no date.** The graph has no patient node, a patient's notes cannot be followed together, and a temporal relation says only which event came first, not when.
- **Staging and outcomes are not extracted.** The notes name stages and responses, but no job turns them into rows yet.
- **The analyses count every mention.** `common_entities`, `category_risk` and `condition_symptom_pairs` do not look at the assertion status, so a denied finding or a relative's cancer counts like a present one. Join with `assertions` to leave them out.
- **`problems_after_treatment` reads only relations of a problem and a treatment** (`Problem AFTER Treatment` and `Treatment BEFORE Problem`). A symptom that followed a treatment is not in it.
- **The graph keeps only what a code names.** A mention a model leaves uncoded, a treatment such as "chemotherapy" (an ICD-10-CM encounter code, not a condition) and a relation whose text has no code in its note are not in the graph.
- **A query that reads `icd10_hcc` twice** (`condition_symptom_pairs` joins it with itself) counts it as one dataset in the analytics engine: to confirm against the engine; it has not been run against it.
- **No graph algorithms** are included. Paths, similarity and communities would be added as jobs over the edge tables.
- **Installing into Facthory is not available yet.** The code is verified on the sample data on a laptop only.
- **The sample is invented and small.** It is generated from templates, so its notes are cleaner than real oncology notes, and it shows the shape of the tables, not realistic volumes or accuracy. The extracted rows are exact by construction, not model output.
- **The Dockerfile has not been built or verified.**
- **DuckDB 2.x only.** The code uses the DuckDB 2.0 Arrow API (`to_arrow_table`).
- No orchestrator or DAG files: Facthory, or a scheduler, calls the jobs.

## Not for clinical use

This is software for research and analytics. It is not a medical device and must not be used to diagnose or treat a patient. Results can be wrong; a qualified person reviews them.

## Disclaimers

Bandpey GmbH (“Facthory”) does not dispense medical, diagnosis, or treatment advice. This Solution (“tool”) is for informational purposes only and may not be used as a substitute for professional medical advice, treatment, or diagnosis. This tool may not be used within Facthory to process Protected Health Information (“PHI”) as defined in the Health Insurance Portability and Accountability Act of 1996, unless you have executed with Facthory a contract that allows for processing PHI, an accompanying Business Associate Agreement (BAA), and are running this tool within a HIPAA Account.

## Licence

Apache-2.0. See [LICENSE](LICENSE). "Facthory" and the Facthory logo are trademarks of their owner and are not covered by that licence. This includes the logo shown in the image under `docs/images/`.

