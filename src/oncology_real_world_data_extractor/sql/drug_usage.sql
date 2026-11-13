-- Drug usage for inventory management: the drugs named most often, above a confidence floor.
SELECT drug_name,
       count(*) AS mentions
FROM rxnorm_drugs
WHERE confidence >= $min_confidence
  AND drug_name <> ''
GROUP BY drug_name
ORDER BY mentions DESC, drug_name
LIMIT $limit
