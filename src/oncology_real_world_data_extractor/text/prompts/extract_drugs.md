task: extract_drugs

Extract the drug mentions from one oncology note and resolve each one to RxNorm.
Return only a JSON array, one object per drug mention, with these keys:

- `chunk`: the drug text as written in the note.
- `rxnorm_code`: the RxNorm code of the drug.
- `drug_name`: the resolved generic drug name in lower case.
- `confidence`: a number between 0 and 1.

Return [] when the note names no drug. Return only the JSON array.
