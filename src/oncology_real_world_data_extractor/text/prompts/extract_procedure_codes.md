task: extract_procedure_codes

Extract the procedure mentions from one oncology note and code each one to
ICD-10-PCS. Return only a JSON array, one object per procedure mention, with
these keys:

- `chunk`: the procedure text as written in the note.
- `procedure_code`: the seven-character ICD-10-PCS code of the procedure.
- `procedure_name`: the ICD-10-PCS description of that code.
- `code_system`: always "ICD-10-PCS".
- `confidence`: a number between 0 and 1.

Return [] when the note names no procedure. Return only the JSON array.
