-- How the assertion statuses distribute over the cancer and symptom mentions.
SELECT assertion,
       count(*) AS mentions
FROM assertions
GROUP BY assertion
ORDER BY mentions DESC, assertion
