task: extract_assertions

For every cancer and symptom mention in one oncology note, judge whether it is
actually present for the patient. Return only a JSON array, one object per
mention, with these keys:

- `chunk`: the cancer or symptom text.
- `entity`: "Oncological" for a cancer or neoplasm, "Symptom" for a sign or symptom.
- `assertion`: one of Present, Absent, Possible, Hypothetical, Conditional,
  Someone_else. "Present" when the patient has it; "Absent" when the note denies
  it; "Someone_else" when a relative or another person has it; "Hypothetical"
  when it is only a risk or a plan; "Conditional" when it depends on something
  happening first; "Possible" when the note is unsure.
- `confidence`: a number between 0 and 1.

Return [] when the note names no cancer or symptom. Return only the JSON array.
