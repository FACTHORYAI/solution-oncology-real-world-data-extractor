-- Nodes of the oncology knowledge graph (graph tables, draft 0).
-- node_id = node_type || ':' || key, stable across runs. There are four node types:
--   Condition  key 'icd10:<code>', label the code's description. Every cancer, metastasis and
--              symptom coded in icd10_hcc, the family-history codes included. The Treatment rows
--              of icd10_hcc (encounter codes such as Z51.11) are not nodes: the drug or the
--              procedure behind a treatment is.
--   Drug       key 'rxnorm:<code>', label the resolved drug name.
--   Procedure  key '<code system>:<code>', for example 'icd10pcs:0HBU0ZZ', label the code's
--              description.
--   Body_Part  key the lower-cased, trimmed organ text, label the text as written.
-- A node is one row however many notes mention it.
WITH mentions AS (
    SELECT 'Condition' AS node_type,
           'icd10:' || trim(icd10_code) AS key,
           trim(code_name) AS label
    FROM icd10_hcc
    WHERE entity IN ('Oncological', 'Symptom') AND trim(icd10_code) <> ''

    UNION ALL

    SELECT 'Drug',
           'rxnorm:' || trim(rxnorm_code),
           trim(drug_name)
    FROM rxnorm_drugs
    WHERE trim(rxnorm_code) <> ''

    UNION ALL

    SELECT 'Procedure',
           lower(replace(trim(code_system), '-', '')) || ':' || trim(procedure_code),
           trim(procedure_name)
    FROM procedure_codes
    WHERE trim(procedure_code) <> '' AND trim(code_system) <> ''

    UNION ALL

    SELECT 'Body_Part',
           lower(trim(chunk1)),
           trim(chunk1)
    FROM bodypart_relations
    WHERE entity1 = 'Internal_organ_or_component' AND trim(chunk1) <> ''

    UNION ALL

    SELECT 'Body_Part',
           lower(trim(chunk2)),
           trim(chunk2)
    FROM bodypart_relations
    WHERE entity2 = 'Internal_organ_or_component' AND trim(chunk2) <> ''
)
SELECT node_type || ':' || key AS node_id,
       node_type,
       key,
       min(label) AS label,
       NULL::VARCHAR AS properties
FROM mentions
GROUP BY node_type, key
ORDER BY node_id
