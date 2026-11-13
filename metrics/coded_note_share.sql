-- Share of notes with at least one billable ICD-10-CM code.
SELECT CAST(count(DISTINCT note_id) AS DOUBLE)
       / (SELECT count(*) FROM notes) AS coded_note_share
FROM billable_codes
