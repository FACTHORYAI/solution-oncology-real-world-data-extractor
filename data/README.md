# Sample data

Every file below is synthetic, generated for this repository from hand-written
oncology notes; no real patient data. Licence: CC0-1.0. The folder is a few
kilobytes in total, far under the 5 MB per file and 20 MB per folder limits.

| File | What it is | Where it came from | Licence | Synthetic |
| --- | --- | --- | --- | --- |
| `notes.parquet` | 5 oncology notes: note_id, text | Hand-written for this repository | CC0-1.0 | yes |
| `icd10_hcc.parquet` | Each finding coded to ICD-10-CM with its billable flag and HCC score | Produced by `extract_oncology_entities` from the notes | CC0-1.0 | yes |
| `billable_codes.parquet` | The nearest billable ICD-10-CM code per finding, with its oncology category | Produced by `extract_oncology_entities` from the notes | CC0-1.0 | yes |
| `rxnorm_drugs.parquet` | Drug mentions resolved to RxNorm | Produced by `extract_drugs` from the notes | CC0-1.0 | yes |
| `cpt_codes.parquet` | Procedure mentions coded to CPT | Produced by `extract_cpt` from the notes | CC0-1.0 | yes |
| `assertions.parquet` | Assertion status per cancer and symptom mention | Produced by `extract_assertions` from the notes | CC0-1.0 | yes |
| `temporal_relations.parquet` | Temporal relations between clinical events | Produced by `extract_temporal_relations` from the notes | CC0-1.0 | yes |
| `bodypart_relations.parquet` | Relations between body parts, problems and procedures | Produced by `extract_bodypart_relations` from the notes | CC0-1.0 | yes |

The ICD-10-CM codes, CPT codes and RxNorm codes in the sample are public
identifiers where known and illustrative elsewhere; the HCC scores are
illustrative. A workspace run resolves every code against the real vocabularies
through the text model.

The original solution's source dataset (MT Oncology Notes, 50 de-identified
transcribed oncology reports) is real EHR-derived material and is not
redistributed here; a workspace reads it from its own storage.
