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

Turn oncology notes into structured real-world data: diagnoses, staging, treatments and outcomes as tables in Facthory.

## How it will work in Facthory

- You install it into a workspace and get a project: sample data, the analysis, the agent's instructions and starting pages.
- Its results are tables and pages in your workspace, so you can query them, chart them and ask the agent about them, inside your permissions.
- Sample data in this repository is synthetic or openly licensed. No real patient data.

## What the result could look like

![Mock-up of a Facthory report page titled "Insights from oncology reports", marked "Sample data": four figures (reports processed, entities extracted, share mapped to ICD-10, procedure mentions), a table of ICD-10 coded entities with note id, text chunk, entity type, code and description, the share of entities by type, the top ten ICD-10 categories and top ten procedures as bar charts, the assertion statuses, and the average risk score per cancer category.](docs/images/oncology-report-mockup.png)

A design illustration of a report built from this solution's tables: coded entities, procedures, assertion statuses and the average risk score per category. It is a mock-up. Its figures are illustrative: they are not produced by this repository's sample data, and it is not a screenshot of a released feature.

## Not for clinical use

This is software for research and analytics. It is not a medical device and must not be used to diagnose or treat a patient. Results can be wrong; a qualified person reviews them.

## Licence

Apache-2.0. See [LICENSE](LICENSE). "Facthory" and the Facthory logo are trademarks of their owner and are not covered by that licence. This includes the logo shown in the image under `docs/images/`.

## Jobs

| Job | What it does | Inputs | Outputs |
| --- | --- | --- | --- |
| `extract_oncology_entities` | Extracts cancer, symptom and treatment findings and codes each to ICD-10-CM with billable status and HCC score | `notes` | `icd10_hcc`, `billable_codes`, `rejected_icd10` |
| `extract_drugs` | Extracts drug mentions and resolves them to RxNorm | `notes` | `rxnorm_drugs`, `rejected_drugs` |
| `extract_cpt` | Extracts procedure mentions and codes them to CPT | `notes` | `cpt_codes`, `rejected_cpt` |
| `extract_assertions` | Judges whether each cancer and symptom mention is Present, Absent, Possible, Hypothetical, Conditional or Someone_else | `notes` | `assertions`, `rejected_assertions` |
| `extract_temporal_relations` | Extracts which clinical event happened before, after or with another | `notes` | `temporal_relations`, `rejected_temporal` |
| `extract_bodypart_relations` | Extracts which organ a procedure was done on or a problem involves | `notes` | `bodypart_relations`, `rejected_bodypart` |
| `common_entities` | The most common cancer findings or symptoms, by notes they appear in | `icd10_hcc` | `common_entities` |
| `category_risk` | Notes and average HCC score per ICD-10 oncology category | `billable_codes` | `category_risk` |
| `condition_symptom_pairs` | Cancer and symptom pairs in the same note, normalised per symptom | `icd10_hcc` | `condition_symptom_pairs` |
| `drug_usage` | The drugs named most often, above a confidence floor | `rxnorm_drugs` | `drug_usage` |
| `problems_after_treatment` | Treatment and problem pairs where the problem followed the treatment | `temporal_relations` | `problems_after_treatment` |
| `bodypart_procedures` | Which procedures were performed on which internal body part | `bodypart_relations` | `bodypart_procedures` |
| `common_procedures` | The procedures coded most often | `cpt_codes` | `common_procedures` |
| `assertion_summary` | How assertion statuses distribute and how symptoms are asserted | `assertions` | `assertion_breakdown`, `symptom_assertions` |

The six extraction jobs take a `TextModel` (see `src/oncology_real_world_data_extractor/text/interface.py`) as a third argument; Facthory provides model access, and every model answer is validated before it becomes a row. Named measures for billing and family history live in `metrics/`.

## Data

The sample tables in `data/sample/` are synthetic and openly licensed (CC0-1.0): `notes`, `icd10_hcc`, `billable_codes`, `rxnorm_drugs`, `cpt_codes`, `assertions`, `temporal_relations` and `bodypart_relations`. See [data/README.md](data/README.md) for one row per file with origin and licence. No real patient data.

## Run it locally

```
uv sync
uv run python -m oncology_real_world_data_extractor common_entities --entity-type Oncological
uv run python -m oncology_real_world_data_extractor category_risk
uv run python -m oncology_real_world_data_extractor problems_after_treatment --min-confidence 0.8
uv run pytest
```

`uv run python -m oncology_real_world_data_extractor --help` lists every job; each job has its own `--help`. The six extraction jobs additionally take `--model-answers <file>` with a recorded-answers JSON (see `tests/recorded_answers.json`), since they read notes through a model behind `text.interface`; the analysis jobs run without any model.

Codes are coding suggestions for analytics: `icd10_hcc` keeps the model's best code with its billable flag and HCC score, `billable_codes` keeps the nearest billable code with its ICD-10 oncology category, and `condition_symptom_pairs` expresses each pair's note count as a share of the most frequent condition for its symptom.

