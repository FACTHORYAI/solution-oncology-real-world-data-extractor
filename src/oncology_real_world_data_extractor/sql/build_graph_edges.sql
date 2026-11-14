-- Edges of the oncology knowledge graph (graph tables, draft 0): one fact per row.
--   Condition -ASSERTION-> (literal status)   from every assertion row; the status is in value
--   Procedure -PERFORMED_ON-> Body_Part       from a body-part relation of a procedure
--   Condition -INVOLVES-> Body_Part           from a body-part relation of a problem
--   <event> -BEFORE | AFTER | OVERLAP-> <event>   from every temporal relation, read from the
--                                             first event to the second
-- A text becomes a node through the code the same note gives it: a condition through
-- icd10_hcc, a drug through rxnorm_drugs, a procedure through procedure_codes. A row whose text
-- has no code in its note has no node to attach to and gives no edge.
-- Every fact carries the note it came from and, when the text of its source is found in the
-- note, the character span of its first occurrence (evidence_start inclusive, evidence_end
-- exclusive, 0-based). The notes carry no date, so valid_from and valid_to are null.
WITH coded AS (
    SELECT note_id,
           chunk,
           'Condition' AS node_type,
           'Condition:icd10:' || trim(icd10_code) AS node_id
    FROM icd10_hcc
    WHERE entity IN ('Oncological', 'Symptom') AND trim(icd10_code) <> ''

    UNION ALL

    SELECT note_id,
           drug_chunk,
           'Drug',
           'Drug:rxnorm:' || trim(rxnorm_code)
    FROM rxnorm_drugs
    WHERE trim(rxnorm_code) <> ''

    UNION ALL

    SELECT note_id,
           chunk,
           'Procedure',
           'Procedure:' || lower(replace(trim(code_system), '-', '')) || ':'
               || trim(procedure_code)
    FROM procedure_codes
    WHERE trim(procedure_code) <> '' AND trim(code_system) <> ''
),
-- The node type an entity type of the extraction tables stands for.
kinds(entity, node_type) AS (
    VALUES ('Oncological', 'Condition'),
           ('Symptom', 'Condition'),
           ('Problem', 'Condition'),
           ('Treatment', 'Drug'),
           ('Treatment', 'Procedure'),
           ('Test', 'Procedure'),
           ('Procedure', 'Procedure')
),
organ_links AS (
    SELECT note_id,
           chunk1 AS organ,
           entity2 AS entity,
           chunk2 AS chunk,
           confidence
    FROM bodypart_relations
    WHERE entity1 = 'Internal_organ_or_component' AND trim(chunk1) <> ''

    UNION ALL

    SELECT note_id,
           chunk2,
           entity1,
           chunk1,
           confidence
    FROM bodypart_relations
    WHERE entity2 = 'Internal_organ_or_component' AND trim(chunk2) <> ''
),
facts AS (
    SELECT c.node_id AS source_id,
           NULL::VARCHAR AS target_id,
           'ASSERTION' AS relationship,
           a.assertion AS value,
           a.note_id AS evidence_document_id,
           a.chunk AS evidence_text,
           a.confidence
    FROM assertions AS a
    JOIN kinds AS k ON k.entity = a.entity
    JOIN coded AS c
        ON c.note_id = a.note_id AND c.chunk = a.chunk AND c.node_type = k.node_type
    WHERE a.assertion <> '' AND trim(a.chunk) <> ''

    UNION ALL

    SELECT c.node_id,
           'Body_Part:' || lower(trim(o.organ)),
           CASE c.node_type WHEN 'Procedure' THEN 'PERFORMED_ON' ELSE 'INVOLVES' END,
           NULL::VARCHAR,
           o.note_id,
           o.chunk,
           o.confidence
    FROM organ_links AS o
    JOIN kinds AS k ON k.entity = o.entity
    JOIN coded AS c
        ON c.note_id = o.note_id AND c.chunk = o.chunk AND c.node_type = k.node_type
    WHERE k.node_type IN ('Procedure', 'Condition')

    UNION ALL

    SELECT s.node_id,
           t.node_id,
           r.relation,
           NULL::VARCHAR,
           r.note_id,
           r.chunk1,
           r.confidence
    FROM temporal_relations AS r
    JOIN kinds AS k1 ON k1.entity = r.entity1
    JOIN coded AS s
        ON s.note_id = r.note_id AND s.chunk = r.chunk1 AND s.node_type = k1.node_type
    JOIN kinds AS k2 ON k2.entity = r.entity2
    JOIN coded AS t
        ON t.note_id = r.note_id AND t.chunk = r.chunk2 AND t.node_type = k2.node_type
    WHERE r.relation <> '' AND s.node_id <> t.node_id
),
located AS (
    SELECT f.*,
           instr(n.text, f.evidence_text) - 1 AS found
    FROM facts AS f
    LEFT JOIN notes AS n ON n.note_id = f.evidence_document_id
),
keyed AS (
    SELECT source_id,
           target_id,
           relationship,
           value,
           evidence_document_id,
           CASE WHEN found >= 0 THEN found END AS evidence_start,
           CASE WHEN found >= 0 THEN found + length(evidence_text) END AS evidence_end,
           confidence
    FROM located
),
hashed AS (
    SELECT md5(concat_ws('|', source_id, relationship, coalesce(target_id, ''),
                         coalesce(value, ''), evidence_document_id,
                         coalesce(evidence_start, -1))) AS edge_id,
           *
    FROM keyed
)
SELECT edge_id,
       any_value(source_id) AS source_id,
       any_value(target_id) AS target_id,
       any_value(relationship) AS relationship,
       any_value(value) AS value,
       NULL::DATE AS valid_from,
       NULL::DATE AS valid_to,
       any_value(evidence_document_id) AS evidence_document_id,
       any_value(evidence_start) AS evidence_start,
       any_value(evidence_end) AS evidence_end,
       max(confidence) AS confidence,
       NULL::VARCHAR AS properties
FROM hashed
GROUP BY edge_id
ORDER BY evidence_document_id, source_id, relationship, target_id, value, evidence_start
