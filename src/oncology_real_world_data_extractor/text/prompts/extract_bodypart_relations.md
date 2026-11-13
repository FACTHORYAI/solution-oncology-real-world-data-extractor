task: extract_bodypart_relations

Extract the relations between internal body parts, problems and procedures in
one oncology note: which organ a procedure was performed on or a problem
involves. Return only a JSON array, one object per relation, with these keys:

- `relation`: the relation word the note supports, such as "is" or "in".
- `entity1`, `chunk1`: the type and text of the first entity
  (Internal_organ_or_component, Problem or Procedure).
- `entity2`, `chunk2`: the type and text of the second entity.
- `confidence`: a number between 0 and 1.

Return [] when the note has no such relation. Return only the JSON array.
