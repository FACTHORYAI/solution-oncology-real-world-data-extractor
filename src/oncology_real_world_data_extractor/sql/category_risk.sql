-- Risk by oncology category: how many notes and the average HCC score per ICD-10 block.
SELECT oncology_category AS category,
       count(DISTINCT note_id) AS notes,
       avg(hcc_score) AS avg_hcc_score
FROM billable_codes
WHERE oncology_category <> ''
GROUP BY oncology_category
ORDER BY avg_hcc_score DESC, category
