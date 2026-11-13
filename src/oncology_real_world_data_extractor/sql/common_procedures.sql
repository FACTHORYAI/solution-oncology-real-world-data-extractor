-- The procedures coded most often, above a confidence floor.
SELECT procedure_name,
       count(*) AS mentions
FROM cpt_codes
WHERE confidence >= $min_confidence
  AND procedure_name <> ''
GROUP BY procedure_name
ORDER BY mentions DESC, procedure_name
LIMIT $limit
