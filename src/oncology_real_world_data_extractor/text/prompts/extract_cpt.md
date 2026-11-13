task: extract_cpt

Extract the procedure mentions from one oncology note and code each one to CPT.
Return only a JSON array, one object per procedure mention, with these keys:

- `chunk`: the procedure text as written in the note.
- `cpt_code`: the CPT code of the procedure.
- `procedure_name`: the CPT description of that code.
- `confidence`: a number between 0 and 1.

Return [] when the note names no procedure. Return only the JSON array.
