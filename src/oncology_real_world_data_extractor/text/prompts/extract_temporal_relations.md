task: extract_temporal_relations

Extract the temporal relations between clinical events in one oncology note:
which event happened before, after or at the same time as another. Return only a
JSON array, one object per relation, with these keys:

- `relation`: "BEFORE", "AFTER" or "OVERLAP", read from the first event to the
  second: "AFTER" means the first event happened after the second one.
- `entity1`, `chunk1`: the type and text of the first event (Treatment, Problem,
  Symptom or Test).
- `entity2`, `chunk2`: the type and text of the second event.
- `confidence`: a number between 0 and 1.

Return [] when the note has no such relation. Return only the JSON array.
