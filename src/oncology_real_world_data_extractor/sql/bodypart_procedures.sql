-- Which procedures were performed on which internal body part, one row per note and pair.
SELECT DISTINCT note_id,
                entity1,
                chunk1,
                entity2,
                chunk2,
                confidence
FROM bodypart_relations
WHERE entity1 <> entity2
  AND chunk1 <> ''
  AND chunk2 <> ''
ORDER BY note_id, entity1, chunk1, entity2, chunk2
