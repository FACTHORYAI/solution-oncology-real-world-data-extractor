-- Share of coded findings whose best ICD-10-CM code is billable.
SELECT CAST(SUM(CASE WHEN billable THEN 1 ELSE 0 END) AS DOUBLE)
       / count(*) AS billable_share
FROM icd10_hcc
