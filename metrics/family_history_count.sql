-- Mentions of a cancer or symptom that a relative has (family history).
SELECT count(*) AS family_history_mentions
FROM assertions
WHERE assertion = 'Someone_else'
