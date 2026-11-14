-- Which procedures were performed on which internal body part, one row per note and pair.
-- The relations of a problem to its organ are not procedures and are left out.
SELECT DISTINCT note_id,
                entity1,
                chunk1,
                entity2,
                chunk2,
                confidence
FROM bodypart_relations
WHERE ((entity1 = 'Internal_organ_or_component' AND entity2 = 'Procedure')
       OR (entity1 = 'Procedure' AND entity2 = 'Internal_organ_or_component'))
  AND chunk1 <> ''
  AND chunk2 <> ''
ORDER BY note_id, entity1, chunk1, entity2, chunk2
