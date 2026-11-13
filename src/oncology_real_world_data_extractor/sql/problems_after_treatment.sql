-- Problems that occurred after a treatment, from the temporal relations of each note.
SELECT note_id,
       chunk1 AS treatment,
       chunk2 AS problem,
       confidence
FROM temporal_relations
WHERE relation = 'AFTER'
  AND entity1 = 'Treatment'
  AND entity2 = 'Problem'
  AND confidence >= $min_confidence
ORDER BY note_id, treatment, problem
