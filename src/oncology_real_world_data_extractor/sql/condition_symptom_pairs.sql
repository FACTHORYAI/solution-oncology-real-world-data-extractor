-- Condition and symptom pairs that appear in the same note, with each pair's share of
-- the most frequent condition for its symptom (the per-symptom min-max normalisation).
WITH pairs AS (
    SELECT DISTINCT condition.note_id,
                    condition.code_name AS condition_name,
                    symptom.code_name AS symptom
    FROM icd10_hcc AS condition
    JOIN icd10_hcc AS symptom
        ON symptom.note_id = condition.note_id
    WHERE condition.entity = 'Oncological'
      AND symptom.entity = 'Symptom'
      AND condition.confidence >= $min_confidence
      AND symptom.confidence >= $min_confidence
      AND condition.code_name <> ''
      AND symptom.code_name <> ''
),
counts AS (
    SELECT condition_name, symptom, count(*) AS notes
    FROM pairs
    GROUP BY condition_name, symptom
    HAVING count(*) >= $min_notes
)
SELECT condition_name AS condition,
       symptom,
       notes,
       CASE
           WHEN max(notes) OVER (PARTITION BY symptom)
                = min(notes) OVER (PARTITION BY symptom) THEN 0.0
           ELSE (notes - min(notes) OVER (PARTITION BY symptom))
                / (max(notes) OVER (PARTITION BY symptom)
                   - min(notes) OVER (PARTITION BY symptom))
       END AS normalized_count
FROM counts
ORDER BY condition, symptom
