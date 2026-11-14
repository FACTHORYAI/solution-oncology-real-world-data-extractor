-- Problems that followed a treatment, from the temporal relations of each note. A relation reads
-- from the first event to the second ("AFTER": the first event happened after the second), so
-- "problem AFTER treatment" and "treatment BEFORE problem" both say the problem followed it.
SELECT note_id,
       treatment,
       problem,
       confidence
FROM (
    SELECT note_id,
           chunk2 AS treatment,
           chunk1 AS problem,
           confidence
    FROM temporal_relations
    WHERE relation = 'AFTER'
      AND entity1 = 'Problem'
      AND entity2 = 'Treatment'

    UNION ALL

    SELECT note_id,
           chunk1,
           chunk2,
           confidence
    FROM temporal_relations
    WHERE relation = 'BEFORE'
      AND entity1 = 'Treatment'
      AND entity2 = 'Problem'
)
WHERE confidence >= $min_confidence
ORDER BY note_id, treatment, problem
