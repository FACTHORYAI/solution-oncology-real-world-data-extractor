task: extract_oncology

Extract the oncological findings from one oncology note and code each one to
ICD-10-CM. Return only a JSON array, one object per finding, with these keys:

- `chunk`: the finding text (a cancer diagnosis, a symptom, or a treatment).
- `entity`: "Oncological" for a cancer or neoplasm, "Symptom" for a sign or
  symptom, "Treatment" for a therapy the note names.
- `icd10_code`: the best ICD-10-CM code for the finding.
- `code_name`: the ICD-10-CM description of that code.
- `billable`: true when the code is a billable (specific) ICD-10-CM code.
- `hcc_score`: the HCC risk-adjustment score of the code, 0 when it has none.
- `candidates`: up to three further codes for the same finding, best first, each
  with `code`, `name`, `billable` and `hcc_score`.
- `confidence`: a number between 0 and 1.

Return [] when the note has no oncological finding. Return only the JSON array.
