-- The most common symptoms and whether the note reports them present or absent.
SELECT lower(chunk) AS symptom,
       assertion,
       count(*) AS mentions
FROM assertions
WHERE entity = 'Symptom'
  AND assertion IN ('Present', 'Absent')
  AND chunk <> ''
GROUP BY lower(chunk), assertion
ORDER BY mentions DESC, symptom, assertion
LIMIT $limit
