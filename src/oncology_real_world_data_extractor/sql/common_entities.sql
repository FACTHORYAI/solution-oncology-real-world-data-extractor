-- The most common oncological findings or symptoms, by the number of notes they appear in.
SELECT code_name AS name,
       count(DISTINCT note_id) AS notes
FROM icd10_hcc
WHERE entity = $entity_type
  AND code_name <> ''
GROUP BY code_name
ORDER BY notes DESC, name
LIMIT $limit
