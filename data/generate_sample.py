"""Generate the synthetic sample: invented oncology notes and the rows extracted from them.

Everything here is invented. No real patient, note or record is used. The notes are put together
from sentence templates and small oncology vocabularies (ten cancer types, their sites, drugs,
procedures, symptoms and treatment side effects). The answers a text model would give for each
note are written from the same templates, so they are exact. Run it from the repository root:

    uv run python data/generate_sample.py

It writes data/sample/*.parquet (notes, icd10_hcc, billable_codes, rxnorm_drugs, procedure_codes,
assertions, temporal_relations, bodypart_relations, graph_nodes, graph_edges) and
tests/recorded_answers.json. The same seed always gives the same files.

How the tables are made:

- The generator writes the notes and, per note and per extraction task, the JSON answer a model
  would return. The extraction jobs then read those answers through the recorded text model, so
  every extracted table has the rows and the row order the jobs produce, and nothing is rejected.
- graph_nodes and graph_edges are built from the extracted tables by the `build_knowledge_graph`
  job.
- Every chunk an answer names stands in the note exactly as written, and the first place it
  stands is the sentence that mentions it, so the graph's evidence spans can be found by text
  search. The generator stops when that does not hold.

What is real and what is not:

- The ICD-10-CM codes are real, public codes with their descriptions as the generator's author
  knows them; they are not checked against the current release of the code set.
- The HCC scores are illustrative: they follow the pattern of the CMS-HCC relative factors per
  cancer group (version 24, community, aged), and the mapping from code to group is not verified.
- The RxNorm codes are illustrative identifiers, not verified against RxNorm.
- The procedure codes are illustrative: seven-character identifiers in ICD-10-PCS shape, not
  verified against the vocabulary. CPT codes are not used.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from oncology_real_world_data_extractor.jobs import REGISTRY, call_run
from oncology_real_world_data_extractor.schemas import NOTES
from oncology_real_world_data_extractor.text.recorded import RecordedTextModel

SEED = 20251114
REPO = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO / "data" / "sample"

# How many generated notes each profile writes, beside the five hand-written ones.
MIX = {
    "breast": 20,
    "lung": 20,
    "colon": 20,
    "pancreas": 14,
    "prostate": 16,
    "hodgkin": 8,
    "dlbcl": 12,
    "follicular": 6,
    "melanoma": 16,
    "kidney": 13,
}

# ICD-10-CM: code -> (description, billable). A code that is not billable is a category whose
# more specific codes a coder has to pick from; a model may answer with it.
# fmt: off
ICD10: dict[str, tuple[str, bool]] = {
    "C50.41": ("Malignant neoplasm of upper-outer quadrant of female breast", False),
    "C50.411": ("Malignant neoplasm of upper-outer quadrant of right female breast", True),
    "C50.412": ("Malignant neoplasm of upper-outer quadrant of left female breast", True),
    "C50.91": ("Malignant neoplasm of unspecified site of female breast", False),
    "C50.911": ("Malignant neoplasm of unspecified site of right female breast", True),
    "C50.912": ("Malignant neoplasm of unspecified site of left female breast", True),
    "C50.919": ("Malignant neoplasm of unspecified site of unspecified female breast", True),
    "C34.1": ("Malignant neoplasm of upper lobe, bronchus or lung", False),
    "C34.11": ("Malignant neoplasm of upper lobe, right bronchus or lung", True),
    "C34.12": ("Malignant neoplasm of upper lobe, left bronchus or lung", True),
    "C34.3": ("Malignant neoplasm of lower lobe, bronchus or lung", False),
    "C34.31": ("Malignant neoplasm of lower lobe, right bronchus or lung", True),
    "C34.32": ("Malignant neoplasm of lower lobe, left bronchus or lung", True),
    "C18": ("Malignant neoplasm of colon", False),
    "C18.0": ("Malignant neoplasm of cecum", True),
    "C18.2": ("Malignant neoplasm of ascending colon", True),
    "C18.4": ("Malignant neoplasm of transverse colon", True),
    "C18.6": ("Malignant neoplasm of descending colon", True),
    "C18.7": ("Malignant neoplasm of sigmoid colon", True),
    "C18.9": ("Malignant neoplasm of colon, unspecified", True),
    "C20": ("Malignant neoplasm of rectum", True),
    "C25": ("Malignant neoplasm of pancreas", False),
    "C25.0": ("Malignant neoplasm of head of pancreas", True),
    "C25.1": ("Malignant neoplasm of body of pancreas", True),
    "C25.2": ("Malignant neoplasm of tail of pancreas", True),
    "C25.9": ("Malignant neoplasm of pancreas, unspecified", True),
    "C61": ("Malignant neoplasm of prostate", True),
    "C64": ("Malignant neoplasm of kidney, except renal pelvis", False),
    "C64.1": ("Malignant neoplasm of right kidney, except renal pelvis", True),
    "C64.2": ("Malignant neoplasm of left kidney, except renal pelvis", True),
    "C64.9": ("Malignant neoplasm of unspecified kidney, except renal pelvis", True),
    "C81.1": ("Nodular sclerosis classical Hodgkin lymphoma", False),
    "C81.11": ("Nodular sclerosis classical Hodgkin lymphoma, lymph nodes of head, face, and neck", True),
    "C81.12": ("Nodular sclerosis classical Hodgkin lymphoma, intrathoracic lymph nodes", True),
    "C81.14": ("Nodular sclerosis classical Hodgkin lymphoma, lymph nodes of axilla and upper limb", True),
    "C81.10": ("Nodular sclerosis classical Hodgkin lymphoma, unspecified site", True),
    "C83.3": ("Diffuse large B-cell lymphoma", False),
    "C83.30": ("Diffuse large B-cell lymphoma, unspecified site", True),
    "C83.31": ("Diffuse large B-cell lymphoma, lymph nodes of head, face, and neck", True),
    "C83.32": ("Diffuse large B-cell lymphoma, intrathoracic lymph nodes", True),
    "C83.33": ("Diffuse large B-cell lymphoma, intra-abdominal lymph nodes", True),
    "C82.9": ("Follicular lymphoma, unspecified", False),
    "C82.90": ("Follicular lymphoma, unspecified, unspecified site", True),
    "C82.91": ("Follicular lymphoma, unspecified, lymph nodes of head, face, and neck", True),
    "C82.92": ("Follicular lymphoma, unspecified, intrathoracic lymph nodes", True),
    "C82.93": ("Follicular lymphoma, unspecified, intra-abdominal lymph nodes", True),
    "C43.4": ("Malignant melanoma of scalp and neck", True),
    "C43.5": ("Malignant melanoma of trunk", False),
    "C43.59": ("Malignant melanoma of other part of trunk", True),
    "C43.6": ("Malignant melanoma of upper limb, including shoulder", False),
    "C43.61": ("Malignant melanoma of right upper limb, including shoulder", True),
    "C43.62": ("Malignant melanoma of left upper limb, including shoulder", True),
    "C43.7": ("Malignant melanoma of lower limb, including hip", False),
    "C43.71": ("Malignant melanoma of right lower limb, including hip", True),
    "C43.72": ("Malignant melanoma of left lower limb, including hip", True),
    "C78.00": ("Secondary malignant neoplasm of unspecified lung", True),
    "C78.7": ("Secondary malignant neoplasm of liver and intrahepatic bile duct", True),
    "C79.31": ("Secondary malignant neoplasm of brain", True),
    "C79.51": ("Secondary malignant neoplasm of bone", True),
    "C79.52": ("Secondary malignant neoplasm of bone marrow", True),
    "C79.9": ("Secondary malignant neoplasm of unspecified site", True),
    "Z80.0": ("Family history of malignant neoplasm of digestive organs", True),
    "Z80.1": ("Family history of malignant neoplasm of trachea, bronchus and lung", True),
    "Z80.3": ("Family history of malignant neoplasm of breast", True),
    "Z80.42": ("Family history of malignant neoplasm of prostate", True),
    "Z80.51": ("Family history of malignant neoplasm of kidney", True),
    "Z80.6": ("Family history of leukemia", True),
    "Z80.8": ("Family history of malignant neoplasm of other organs or systems", True),
    "Z51.0": ("Encounter for antineoplastic radiation therapy", True),
    "Z51.11": ("Encounter for antineoplastic chemotherapy", True),
    "Z51.12": ("Encounter for antineoplastic immunotherapy", True),
    "R53.83": ("Other fatigue", True),
    "R07.9": ("Chest pain, unspecified", True),
    "R63.4": ("Abnormal weight loss", True),
    "R63.0": ("Anorexia", True),
    "R11.0": ("Nausea", True),
    "R11.10": ("Vomiting, unspecified", True),
    "R61": ("Generalized hyperhidrosis", True),
    "R06.02": ("Shortness of breath", True),
    "R04.2": ("Hemoptysis", True),
    "R05.9": ("Cough, unspecified", True),
    "R50.9": ("Fever, unspecified", True),
    "R10.9": ("Unspecified abdominal pain", True),
    "R19.7": ("Diarrhea, unspecified", True),
    "K59.00": ("Constipation, unspecified", True),
    "R17": ("Unspecified jaundice", True),
    "R59.0": ("Localized enlarged lymph nodes", True),
    "R59.9": ("Enlarged lymph nodes, unspecified", True),
    "R31.9": ("Hematuria, unspecified", True),
    "R35.1": ("Nocturia", True),
    "R39.15": ("Urgency of urination", True),
    "R20.2": ("Paresthesia of skin", True),
    "K62.5": ("Hemorrhage of anus and rectum", True),
    "R51.9": ("Headache, unspecified", True),
    "R52": ("Pain, unspecified", True),
    "M25.50": ("Pain in unspecified joint", True),
    "M54.9": ("Dorsalgia, unspecified", True),
    "L29.9": ("Pruritus, unspecified", True),
    "R21": ("Rash and other nonspecific skin eruption", True),
    "N63.0": ("Unspecified lump in unspecified breast", True),
    "G62.0": ("Drug-induced polyneuropathy", True),
    "D70.1": ("Agranulocytosis secondary to cancer chemotherapy", True),
    "D64.81": ("Anemia due to antineoplastic chemotherapy", True),
    "D63.0": ("Anemia in neoplastic disease", True),
}
# fmt: on

# Not-billable parent of a billable code, which a model answers with now and then.
PARENTS = {
    "C50.411": "C50.41", "C50.412": "C50.41", "C50.911": "C50.91", "C50.912": "C50.91",
    "C34.11": "C34.1", "C34.12": "C34.1", "C34.31": "C34.3", "C34.32": "C34.3",
    "C18.0": "C18", "C18.2": "C18", "C18.4": "C18", "C18.6": "C18", "C18.7": "C18",
    "C25.0": "C25", "C25.1": "C25", "C25.2": "C25",
    "C64.1": "C64", "C64.2": "C64",
    "C81.11": "C81.1", "C81.12": "C81.1", "C81.14": "C81.1",
    "C83.31": "C83.3", "C83.32": "C83.3", "C83.33": "C83.3",
    "C82.91": "C82.9", "C82.92": "C82.9", "C82.93": "C82.9",
    "C43.59": "C43.5", "C43.61": "C43.6", "C43.62": "C43.6", "C43.71": "C43.7",
}  # fmt: skip

# HCC scores by cancer group: illustrative values in the pattern of the CMS-HCC relative factors
# (version 24, community, aged): metastatic cancer; lung and pancreas; lymphoma; colorectal and
# kidney; breast, prostate and skin.
HCC_GROUPS: tuple[tuple[tuple[str, ...], float], ...] = (
    (("C78", "C79"), 2.659),
    (("C34", "C25"), 1.024),
    (("C81", "C82", "C83"), 0.675),
    (("C18", "C20", "C64"), 0.307),
    (("C50", "C61", "C43"), 0.150),
)

# Symptoms and signs a note can name: text -> ICD-10-CM code.
SYMPTOMS = {
    "fatigue": "R53.83",
    "chest pain": "R07.9",
    "weight loss": "R63.4",
    "loss of appetite": "R63.0",
    "nausea": "R11.0",
    "vomiting": "R11.10",
    "night sweats": "R61",
    "shortness of breath": "R06.02",
    "dyspnea": "R06.02",
    "hemoptysis": "R04.2",
    "cough": "R05.9",
    "fever": "R50.9",
    "abdominal pain": "R10.9",
    "diarrhea": "R19.7",
    "constipation": "K59.00",
    "jaundice": "R17",
    "lymphadenopathy": "R59.9",
    "hematuria": "R31.9",
    "nocturia": "R35.1",
    "urinary urgency": "R39.15",
    "rectal bleeding": "K62.5",
    "headache": "R51.9",
    "bone pain": "R52",
    "joint pain": "M25.50",
    "back pain": "M54.9",
    "itching": "L29.9",
    "breast lump": "N63.0",
    "anemia": "D63.0",
}

# Metastatic findings: text -> ICD-10-CM code.
METASTASES = {
    "distant metastasis": "C79.9",
    "bone metastases": "C79.51",
    "liver metastases": "C78.7",
    "brain metastases": "C79.31",
    "lung metastases": "C78.00",
    "bone marrow involvement": "C79.52",
}

# Side effects of treatment: (text, ICD-10-CM code, drugs that cause it).
ADVERSE = (
    ("peripheral neuropathy", "G62.0",
     {"paclitaxel", "docetaxel", "carboplatin", "cisplatin", "oxaliplatin", "vincristine"}),
    ("neutropenia", "D70.1",
     {"doxorubicin", "cyclophosphamide", "paclitaxel", "docetaxel", "carboplatin", "cisplatin",
      "etoposide", "gemcitabine", "irinotecan", "dacarbazine"}),
    ("anemia", "D64.81", {"carboplatin", "cisplatin", "gemcitabine", "doxorubicin"}),
    ("diarrhea", "R19.7", {"capecitabine", "irinotecan", "fluorouracil", "pembrolizumab", "nivolumab"}),
    ("rash", "R21", {"pembrolizumab", "nivolumab", "enzalutamide", "sunitinib"}),
    ("joint pain", "M25.50", {"anastrozole", "letrozole"}),
    ("nausea", "R11.0", {"cisplatin", "doxorubicin", "cyclophosphamide", "irinotecan", "dacarbazine", "carboplatin"}),
)  # fmt: skip

# Drugs: key -> (illustrative RxNorm code, class, how a note can write it, taken by mouth).
# Class "chemo" and "io" (immunotherapy) give the note's therapy word.
DRUGS: dict[str, tuple[str, str, tuple[str, ...], bool]] = {
    "tamoxifen": ("10382", "hormone", ("tamoxifen",), True),
    "anastrozole": ("84857", "hormone", ("anastrozole",), True),
    "letrozole": ("72965", "hormone", ("letrozole",), True),
    "trastuzumab": ("224905", "targeted", ("trastuzumab",), False),
    "doxorubicin": ("3639", "chemo", ("doxorubicin",), False),
    "cyclophosphamide": ("3002", "chemo", ("cyclophosphamide",), False),
    "paclitaxel": ("56946", "chemo", ("paclitaxel",), False),
    "docetaxel": ("72962", "chemo", ("docetaxel",), False),
    "carboplatin": ("2264", "chemo", ("carboplatin",), False),
    "cisplatin": ("2555", "chemo", ("cisplatin",), False),
    "etoposide": ("4179", "chemo", ("etoposide",), False),
    "pembrolizumab": ("1657568", "io", ("pembrolizumab",), False),
    "nivolumab": ("1597876", "io", ("nivolumab",), False),
    "oxaliplatin": ("40919", "chemo", ("oxaliplatin",), False),
    "capecitabine": ("194000", "chemo", ("capecitabine",), True),
    "fluorouracil": ("4492", "chemo", ("fluorouracil", "5-FU"), False),
    "irinotecan": ("51499", "chemo", ("irinotecan",), False),
    "bevacizumab": ("253337", "targeted", ("bevacizumab",), False),
    "gemcitabine": ("12574", "chemo", ("gemcitabine",), False),
    "abiraterone": ("1100076", "hormone", ("abiraterone",), True),
    "enzalutamide": ("1307298", "hormone", ("enzalutamide",), True),
    "prednisone": ("8640", "steroid", ("prednisone",), True),
    "rituximab": ("121191", "targeted", ("rituximab",), False),
    "vincristine": ("11202", "chemo", ("vincristine",), False),
    "vinblastine": ("11199", "chemo", ("vinblastine",), False),
    "dacarbazine": ("3098", "chemo", ("dacarbazine",), False),
    "sunitinib": ("649894", "targeted", ("sunitinib",), True),
}

# Procedure codes: illustrative seven-character identifiers in ICD-10-PCS shape.
PROCEDURES = {
    "0HBT3ZX": "Excision of Right Breast, Percutaneous Approach, Diagnostic",
    "0HBU3ZX": "Excision of Left Breast, Percutaneous Approach, Diagnostic",
    "0HBT0ZZ": "Excision of Right Breast, Open Approach",
    "0HBU0ZZ": "Excision of Left Breast, Open Approach",
    "0HTT0ZZ": "Resection of Right Breast, Open Approach",
    "0HTU0ZZ": "Resection of Left Breast, Open Approach",
    "07B53ZX": "Excision of Right Axillary Lymphatic, Percutaneous Approach, Diagnostic",
    "07B63ZX": "Excision of Left Axillary Lymphatic, Percutaneous Approach, Diagnostic",
    "BH02ZZZ": "Plain Radiography of Bilateral Breasts",
    "0BBC3ZX": "Excision of Right Upper Lung Lobe, Percutaneous Approach, Diagnostic",
    "0BBG3ZX": "Excision of Left Upper Lung Lobe, Percutaneous Approach, Diagnostic",
    "0BBF3ZX": "Excision of Right Lower Lung Lobe, Percutaneous Approach, Diagnostic",
    "0BBJ3ZX": "Excision of Left Lower Lung Lobe, Percutaneous Approach, Diagnostic",
    "0BTC0ZZ": "Resection of Right Upper Lung Lobe, Open Approach",
    "0BTG0ZZ": "Resection of Left Upper Lung Lobe, Open Approach",
    "0BTF0ZZ": "Resection of Right Lower Lung Lobe, Open Approach",
    "0BTJ0ZZ": "Resection of Left Lower Lung Lobe, Open Approach",
    "0DBN8ZX": "Excision of Sigmoid Colon, Via Natural or Artificial Opening Endoscopic, Diagnostic",
    "0DBH8ZX": "Excision of Cecum, Via Natural or Artificial Opening Endoscopic, Diagnostic",
    "0DBK8ZX": "Excision of Ascending Colon, Via Natural or Artificial Opening Endoscopic, Diagnostic",
    "0DBL8ZX": "Excision of Transverse Colon, Via Natural or Artificial Opening Endoscopic, Diagnostic",
    "0DBM8ZX": "Excision of Descending Colon, Via Natural or Artificial Opening Endoscopic, Diagnostic",
    "0DBP8ZX": "Excision of Rectum, Via Natural or Artificial Opening Endoscopic, Diagnostic",
    "0DTN0ZZ": "Resection of Sigmoid Colon, Open Approach",
    "0DTF0ZZ": "Resection of Right Large Intestine, Open Approach",
    "0DTG0ZZ": "Resection of Left Large Intestine, Open Approach",
    "0DTL0ZZ": "Resection of Transverse Colon, Open Approach",
    "0DTP0ZZ": "Resection of Rectum, Open Approach",
    "0FBG8ZX": "Excision of Pancreas, Via Natural or Artificial Opening Endoscopic, Diagnostic",
    "0FTG0ZZ": "Resection of Pancreas, Open Approach",
    "0F798DZ": "Dilation of Common Bile Duct with Intraluminal Device, Via Natural or Artificial Opening Endoscopic",
    "0VB03ZX": "Excision of Prostate, Percutaneous Approach, Diagnostic",
    "0VT00ZZ": "Resection of Prostate, Open Approach",
    "07B10ZX": "Excision of Right Neck Lymphatic, Open Approach, Diagnostic",
    "07B50ZX": "Excision of Right Axillary Lymphatic, Open Approach, Diagnostic",
    "07B70ZX": "Excision of Thorax Lymphatic, Open Approach, Diagnostic",
    "07BD3ZX": "Excision of Aortic Lymphatic, Percutaneous Approach, Diagnostic",
    "07DR3ZX": "Extraction of Iliac Bone Marrow, Percutaneous Approach, Diagnostic",
    "0HBBXZZ": "Excision of Right Upper Arm Skin, External Approach",
    "0HBEXZZ": "Excision of Left Lower Arm Skin, External Approach",
    "0HB6XZZ": "Excision of Back Skin, External Approach",
    "0HBKXZZ": "Excision of Right Lower Leg Skin, External Approach",
    "07BH3ZX": "Excision of Right Inguinal Lymphatic, Percutaneous Approach, Diagnostic",
    "0TB03ZX": "Excision of Right Kidney, Percutaneous Approach, Diagnostic",
    "0TB13ZX": "Excision of Left Kidney, Percutaneous Approach, Diagnostic",
    "0TB00ZZ": "Excision of Right Kidney, Open Approach",
    "0TB10ZZ": "Excision of Left Kidney, Open Approach",
    "0TT00ZZ": "Resection of Right Kidney, Open Approach",
    "0TT10ZZ": "Resection of Left Kidney, Open Approach",
}  # fmt: skip

# A relative's cancer, as a note writes it: text -> ICD-10-CM family-history code.
FAMILY = {
    "breast": ("breast cancer", "Z80.3"),
    "colon": ("colon cancer", "Z80.0"),
    "lung": ("bronchogenic carcinoma", "Z80.1"),
    "pancreas": ("pancreatic cancer", "Z80.0"),
    "prostate": ("prostate cancer", "Z80.42"),
    "lymphoma": ("leukemia", "Z80.6"),
    "melanoma": ("skin cancer", "Z80.8"),
    "kidney": ("kidney cancer", "Z80.51"),
}

# A procedure at a site: the phrase as written, its code, its kind ("biopsy" or "surgery"), and
# the organ it was done on when that is not the site (a lymph node, for example).
Procedure = tuple[str, str, str, str]


@dataclass(frozen=True)
class Site:
    """Where a cancer sits: the text, its ICD-10-CM code and the procedures done there."""

    text: str
    icd: str
    procedures: tuple[Procedure, ...]
    histologies: tuple[str, ...] = ()


@dataclass(frozen=True)
class Profile:
    """One cancer type: how its notes are written."""

    service: str
    family: str
    histologies: tuple[str, ...]
    sites: tuple[Site, ...]
    regimens: tuple[tuple[str, ...], ...]
    symptoms: tuple[str, ...]
    metastases: tuple[str, ...]
    sex: str = ""
    link: str = "of the"
    suffix: str = ""
    extras: tuple[str, ...] = ("",)
    ages: tuple[int, int] = (38, 84)


def _bone_marrow() -> Procedure:
    return ("bone marrow biopsy", "07DR3ZX", "biopsy", "iliac crest")


# fmt: off
PROFILES: dict[str, Profile] = {
    "breast": Profile(
        service="Breast Service", family="breast", sex="woman",
        histologies=("invasive ductal carcinoma", "invasive lobular carcinoma"),
        sites=(
            Site("left breast", "C50.912", (
                ("core needle biopsy", "0HBU3ZX", "biopsy", ""),
                ("lumpectomy", "0HBU0ZZ", "surgery", ""),
                ("mastectomy", "0HTU0ZZ", "surgery", ""),
                ("sentinel lymph node biopsy", "07B63ZX", "biopsy", "left axillary lymph node"),
            )),
            Site("right breast", "C50.911", (
                ("core needle biopsy", "0HBT3ZX", "biopsy", ""),
                ("lumpectomy", "0HBT0ZZ", "surgery", ""),
                ("mastectomy", "0HTT0ZZ", "surgery", ""),
                ("sentinel lymph node biopsy", "07B53ZX", "biopsy", "right axillary lymph node"),
            )),
            Site("upper outer quadrant of the left breast", "C50.412", (
                ("core needle biopsy", "0HBU3ZX", "biopsy", ""),
                ("lumpectomy", "0HBU0ZZ", "surgery", ""),
            )),
            Site("upper outer quadrant of the right breast", "C50.411", (
                ("core needle biopsy", "0HBT3ZX", "biopsy", ""),
                ("lumpectomy", "0HBT0ZZ", "surgery", ""),
            )),
        ),
        regimens=(("tamoxifen",), ("anastrozole",), ("letrozole",), ("doxorubicin", "cyclophosphamide"),
                  ("paclitaxel", "trastuzumab"), ("docetaxel", "cyclophosphamide")),
        symptoms=("fatigue", "joint pain", "breast lump", "chest pain", "bone pain", "headache", "nausea"),
        metastases=("bone metastases", "liver metastases", "brain metastases"),
        extras=("", "", ", diagnosed four months ago", ", diagnosed two years ago"),
    ),
    "lung": Profile(
        service="Thoracic Oncology", family="lung",
        histologies=("non-small cell lung cancer", "small cell lung cancer", "lung adenocarcinoma"),
        sites=(
            Site("right upper lobe", "C34.11", (
                ("CT-guided core biopsy", "0BBC3ZX", "biopsy", ""), ("lobectomy", "0BTC0ZZ", "surgery", ""))),
            Site("left upper lobe", "C34.12", (
                ("CT-guided core biopsy", "0BBG3ZX", "biopsy", ""), ("lobectomy", "0BTG0ZZ", "surgery", ""))),
            Site("right lower lobe", "C34.31", (
                ("CT-guided core biopsy", "0BBF3ZX", "biopsy", ""), ("lobectomy", "0BTF0ZZ", "surgery", ""))),
            Site("left lower lobe", "C34.32", (
                ("CT-guided core biopsy", "0BBJ3ZX", "biopsy", ""), ("lobectomy", "0BTJ0ZZ", "surgery", ""))),
        ),
        regimens=(("carboplatin", "paclitaxel"), ("cisplatin", "etoposide"), ("pembrolizumab",),
                  ("carboplatin", "pembrolizumab"), ("docetaxel",)),
        symptoms=("cough", "shortness of breath", "dyspnea", "hemoptysis", "chest pain", "weight loss", "fatigue"),
        metastases=("brain metastases", "liver metastases", "bone metastases"),
        extras=("", "", ", on second-line therapy"),
        ages=(52, 84),
    ),
    "colon": Profile(
        service="Gastroenterology and Oncology", family="colon",
        histologies=("colon adenocarcinoma",),
        sites=(
            Site("sigmoid colon", "C18.7", (
                ("colonoscopy with biopsy", "0DBN8ZX", "biopsy", ""), ("sigmoid colectomy", "0DTN0ZZ", "surgery", ""))),
            Site("cecum", "C18.0", (
                ("colonoscopy with biopsy", "0DBH8ZX", "biopsy", ""), ("right hemicolectomy", "0DTF0ZZ", "surgery", ""))),
            Site("ascending colon", "C18.2", (
                ("colonoscopy with biopsy", "0DBK8ZX", "biopsy", ""), ("right hemicolectomy", "0DTF0ZZ", "surgery", ""))),
            Site("transverse colon", "C18.4", (
                ("colonoscopy with biopsy", "0DBL8ZX", "biopsy", ""), ("transverse colectomy", "0DTL0ZZ", "surgery", ""))),
            Site("descending colon", "C18.6", (
                ("colonoscopy with biopsy", "0DBM8ZX", "biopsy", ""), ("left hemicolectomy", "0DTG0ZZ", "surgery", ""))),
            Site("rectum", "C20", (
                ("colonoscopy with biopsy", "0DBP8ZX", "biopsy", ""), ("low anterior resection", "0DTP0ZZ", "surgery", "")),
                 histologies=("adenocarcinoma",)),
        ),
        regimens=(("oxaliplatin", "capecitabine"), ("fluorouracil", "oxaliplatin"), ("capecitabine",),
                  ("irinotecan", "bevacizumab"), ("fluorouracil", "irinotecan")),
        symptoms=("rectal bleeding", "abdominal pain", "weight loss", "nausea", "diarrhea", "constipation", "fatigue"),
        metastases=("liver metastases", "lung metastases"),
    ),
    "pancreas": Profile(
        service="Hepatobiliary and Pancreatic Oncology", family="pancreas",
        histologies=("ductal adenocarcinoma", "pancreatic ductal adenocarcinoma"),
        sites=(
            Site("head of the pancreas", "C25.0", (
                ("endoscopic ultrasound-guided biopsy", "0FBG8ZX", "biopsy", "pancreas"),
                ("biliary stenting", "0F798DZ", "surgery", "common bile duct"))),
            Site("body of the pancreas", "C25.1", (
                ("endoscopic ultrasound-guided biopsy", "0FBG8ZX", "biopsy", "pancreas"),
                ("distal pancreatectomy", "0FTG0ZZ", "surgery", "pancreas"))),
            Site("tail of the pancreas", "C25.2", (
                ("endoscopic ultrasound-guided biopsy", "0FBG8ZX", "biopsy", "pancreas"),
                ("distal pancreatectomy", "0FTG0ZZ", "surgery", "pancreas"))),
        ),
        regimens=(("gemcitabine", "capecitabine"), ("fluorouracil", "irinotecan", "oxaliplatin"), ("gemcitabine",)),
        symptoms=("abdominal pain", "jaundice", "weight loss", "nausea", "back pain", "loss of appetite", "fatigue"),
        metastases=("liver metastases",),
        ages=(50, 84),
    ),
    "prostate": Profile(
        service="Urologic Oncology", family="prostate", sex="man",
        histologies=("adenocarcinoma",),
        sites=(
            Site("prostate", "C61", (
                ("ultrasound-guided biopsy", "0VB03ZX", "biopsy", ""),
                ("radical prostatectomy", "0VT00ZZ", "surgery", ""))),
        ),
        regimens=(("abiraterone",), ("enzalutamide",), ("docetaxel",), ("abiraterone", "prednisone")),
        symptoms=("urinary urgency", "nocturia", "hematuria", "bone pain", "fatigue", "back pain"),
        metastases=("bone metastases",),
        ages=(55, 86),
    ),
    "hodgkin": Profile(
        service="Hematology", family="lymphoma",
        histologies=("classic Hodgkin lymphoma",), suffix=", nodular sclerosis subtype,",
        sites=(
            Site("mediastinum", "C81.12", (
                ("excisional biopsy", "07B70ZX", "biopsy", "mediastinal lymph node"), _bone_marrow())),
            Site("cervical lymph nodes", "C81.11", (
                ("excisional biopsy", "07B10ZX", "biopsy", "right cervical lymph node"), _bone_marrow())),
            Site("axillary lymph nodes", "C81.14", (
                ("excisional biopsy", "07B50ZX", "biopsy", "right axillary lymph node"), _bone_marrow())),
        ),
        link="involving the",
        regimens=(("doxorubicin", "vinblastine", "dacarbazine"), ("doxorubicin", "vinblastine"), ("pembrolizumab",)),
        symptoms=("night sweats", "fatigue", "fever", "itching", "weight loss", "lymphadenopathy"),
        metastases=("bone marrow involvement",),
        ages=(18, 70),
    ),
    "dlbcl": Profile(
        service="Hematology", family="lymphoma",
        histologies=("diffuse large B-cell lymphoma",),
        sites=(
            Site("cervical lymph nodes", "C83.31", (
                ("excisional biopsy", "07B10ZX", "biopsy", "right cervical lymph node"), _bone_marrow())),
            Site("mediastinum", "C83.32", (
                ("excisional biopsy", "07B70ZX", "biopsy", "mediastinal lymph node"), _bone_marrow())),
            Site("retroperitoneal lymph nodes", "C83.33", (
                ("excisional biopsy", "07BD3ZX", "biopsy", "aortic lymph node"), _bone_marrow())),
        ),
        link="involving the",
        regimens=(("rituximab", "cyclophosphamide", "doxorubicin", "vincristine", "prednisone"),
                  ("rituximab", "cyclophosphamide", "doxorubicin")),
        symptoms=("night sweats", "fever", "weight loss", "fatigue", "abdominal pain", "lymphadenopathy"),
        metastases=("bone marrow involvement",),
        ages=(45, 86),
    ),
    "follicular": Profile(
        service="Hematology", family="lymphoma",
        histologies=("follicular lymphoma",),
        sites=(
            Site("cervical lymph nodes", "C82.91", (
                ("excisional biopsy", "07B10ZX", "biopsy", "right cervical lymph node"), _bone_marrow())),
            Site("mediastinum", "C82.92", (
                ("excisional biopsy", "07B70ZX", "biopsy", "mediastinal lymph node"), _bone_marrow())),
            Site("intra-abdominal lymph nodes", "C82.93", (
                ("excisional biopsy", "07BD3ZX", "biopsy", "aortic lymph node"), _bone_marrow())),
        ),
        link="involving the",
        regimens=(("rituximab",), ("rituximab", "cyclophosphamide")),
        symptoms=("fatigue", "lymphadenopathy", "night sweats", "weight loss", "abdominal pain"),
        metastases=("bone marrow involvement",),
        ages=(45, 86),
    ),
    "melanoma": Profile(
        service="Dermatology Oncology", family="melanoma",
        histologies=("nodular melanoma", "superficial spreading melanoma"),
        sites=(
            Site("right shoulder", "C43.61", (
                ("wide local excision", "0HBBXZZ", "surgery", ""),
                ("sentinel lymph node biopsy", "07B53ZX", "biopsy", "right axillary lymph node"))),
            Site("left forearm", "C43.62", (
                ("wide local excision", "0HBEXZZ", "surgery", ""),
                ("sentinel lymph node biopsy", "07B63ZX", "biopsy", "left axillary lymph node"))),
            Site("back", "C43.59", (("wide local excision", "0HB6XZZ", "surgery", ""),)),
            Site("right calf", "C43.71", (
                ("wide local excision", "0HBKXZZ", "surgery", ""),
                ("sentinel lymph node biopsy", "07BH3ZX", "biopsy", "right inguinal lymph node"))),
        ),
        regimens=(("pembrolizumab",), ("nivolumab",), ("dacarbazine",)),
        symptoms=("itching", "fatigue", "headache", "lymphadenopathy", "nausea"),
        metastases=("brain metastases", "lung metastases", "liver metastases"),
        extras=(", Breslow thickness 1.2 mm", ", Breslow thickness 2.4 mm", ", Breslow thickness 3.1 mm", ""),
        ages=(30, 86),
    ),
    "kidney": Profile(
        service="Genitourinary Oncology", family="kidney",
        histologies=("clear cell renal cell carcinoma", "papillary renal cell carcinoma"),
        sites=(
            Site("right kidney", "C64.1", (
                ("renal mass biopsy", "0TB03ZX", "biopsy", ""),
                ("partial nephrectomy", "0TB00ZZ", "surgery", ""),
                ("radical nephrectomy", "0TT00ZZ", "surgery", ""))),
            Site("left kidney", "C64.2", (
                ("renal mass biopsy", "0TB13ZX", "biopsy", ""),
                ("partial nephrectomy", "0TB10ZZ", "surgery", ""),
                ("radical nephrectomy", "0TT10ZZ", "surgery", ""))),
        ),
        regimens=(("sunitinib",), ("nivolumab",), ("pembrolizumab",)),
        symptoms=("hematuria", "abdominal pain", "fatigue", "weight loss", "anemia", "back pain"),
        metastases=("lung metastases", "bone metastases"),
        ages=(40, 86),
    ),
}
# fmt: on

TITLE_KINDS = ("Follow-up", "Progress Note", "Consultation", "Clinic Note")
WORDS = {2: "two", 3: "three", 4: "four", 6: "six"}
RELATIVES = ("mother", "father", "sister", "brother")
PLANS = (
    "repeat imaging in three months",
    "review in four weeks",
    "genetic counselling",
    "palliative care referral",
    "review at the tumour board",
)


def hcc_score(code: str) -> float:
    """Return the illustrative HCC score of an ICD-10-CM code."""
    for prefixes, score in HCC_GROUPS:
        if code.startswith(prefixes):
            return score
    return 0.0


def _list_text(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _cap(text: str) -> str:
    return text[0].upper() + text[1:]


class Builder:
    """One note and the answers a model would give for it, written together."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.sentences: list[str] = []
        self.answers: dict[str, list[dict]] = {
            "extract_oncology": [],
            "extract_drugs": [],
            "extract_procedure_codes": [],
            "extract_assertions": [],
            "extract_temporal_relations": [],
            "extract_bodypart_relations": [],
        }
        self.where: dict[str, int] = {}  # chunk -> index of the sentence that first names it
        self.drug_chunks: dict[str, str] = {}  # drug key -> the way the note writes it
        self.relation_chunks: list[str] = []

    def has(self, chunk: str) -> bool:
        return chunk in self.where

    def add(self, sentence: str) -> None:
        self.sentences.append(sentence)

    def confidence(self, low: float = 0.84, high: float = 0.99) -> float:
        return round(self.rng.uniform(low, high), 2)

    def finding(self, chunk: str, entity: str, code: str, status: str = "", leaf: str = "") -> str:
        """Register a coded finding (and its assertion status) for the sentence about to be added.

        When the code is a category that is not billable, `leaf` is the code the model would offer
        first among the billable ones.
        """
        self.where.setdefault(chunk, len(self.sentences))
        name, billable = ICD10[code]
        candidates: list[dict] = []
        if not billable:
            children = [c for c in ICD10 if c.startswith(code) and c != code and ICD10[c][1]]
            children.sort(key=lambda c: c != leaf)
            candidates = [
                {"code": c, "name": ICD10[c][0], "billable": True, "hcc_score": hcc_score(c)}
                for c in children[:3]
            ]
        self.answers["extract_oncology"].append(
            {
                "chunk": chunk,
                "entity": entity,
                "icd10_code": code,
                "code_name": name,
                "billable": billable,
                "hcc_score": hcc_score(code),
                "candidates": candidates,
                "confidence": self.confidence(),
            }
        )
        if status:
            self.answers["extract_assertions"].append(
                {
                    "chunk": chunk,
                    "entity": entity,
                    "assertion": status,
                    "confidence": self.confidence(0.82, 0.97),
                }
            )
        return chunk

    def diagnosis(self, chunk: str, code: str, status: str = "Present") -> str:
        """Register a cancer finding, sometimes coded to its not-billable category."""
        leaf = ""
        if code in PARENTS and self.rng.random() < 0.15:
            leaf, code = code, PARENTS[code]
        return self.finding(chunk, "Oncological", code, status, leaf)

    def drug(self, key: str) -> str:
        """Register a drug mention once per note and return the way the note writes it."""
        if key in self.drug_chunks:
            return self.drug_chunks[key]
        code, _drug_class, aliases, _oral = DRUGS[key]
        chunk = self.rng.choice(aliases)
        self.where.setdefault(chunk, len(self.sentences))
        self.drug_chunks[key] = chunk
        self.answers["extract_drugs"].append(
            {"chunk": chunk, "rxnorm_code": code, "drug_name": key, "confidence": self.confidence()}
        )
        return chunk

    def procedure(self, chunk: str, code: str) -> str:
        self.where.setdefault(chunk, len(self.sentences))
        self.answers["extract_procedure_codes"].append(
            {
                "chunk": chunk,
                "procedure_code": code,
                "procedure_name": PROCEDURES[code],
                "code_system": "ICD-10-PCS",
                "confidence": self.confidence(),
            }
        )
        return chunk

    def temporal(self, relation: str, entity1: str, chunk1: str, entity2: str, chunk2: str) -> None:
        self.relation_chunks.extend((chunk1, chunk2))
        self.answers["extract_temporal_relations"].append(
            {
                "relation": relation,
                "entity1": entity1,
                "chunk1": chunk1,
                "entity2": entity2,
                "chunk2": chunk2,
                "confidence": self.confidence(0.8, 0.96),
            }
        )

    def bodypart(self, organ: str, entity: str, chunk: str) -> None:
        self.relation_chunks.extend((organ, chunk))
        self.answers["extract_bodypart_relations"].append(
            {
                "relation": "in",
                "entity1": "Internal_organ_or_component",
                "chunk1": organ,
                "entity2": entity,
                "chunk2": chunk,
                "confidence": self.confidence(0.82, 0.96),
            }
        )

    def text(self) -> str:
        return " ".join(self.sentences)

    def check(self) -> None:
        """Every chunk stands in the note, and its first place is the sentence that names it."""
        text = self.text()
        starts = []
        position = 0
        for sentence in self.sentences:
            starts.append((position, position + len(sentence)))
            position += len(sentence) + 1
        for chunk, index in self.where.items():
            found = text.find(chunk)
            low, high = starts[index]
            assert low <= found < high, (chunk, index, text)
        for chunk in self.relation_chunks:
            assert chunk in text, (chunk, text)


def _generated_note(rng: random.Random, profile: Profile) -> Builder:
    """Write one note of a cancer type, with the answers a model would give for it."""
    b = Builder(rng)
    sex = profile.sex or rng.choice(["woman", "man"])
    pron, poss = ("She", "Her") if sex == "woman" else ("He", "His")
    age = rng.randint(*profile.ages)
    a_age = f"{'an' if str(age).startswith('8') or age in (11, 18) else 'a'} {age}-year-old"
    site = rng.choice(profile.sites)
    hist = rng.choice(site.histologies or profile.histologies)
    stage = rng.choice(["stage I", "stage II", "stage III", "stage IV"])
    extra = rng.choice(profile.extras)

    # Title and introduction: the cancer, its site and the first temporal clue.
    b.add(f"{profile.service} {rng.choice(TITLE_KINDS)}.")
    variant = rng.randrange(3)
    if profile.suffix and variant == 1:
        variant = 0
    if variant == 1:
        chunk = b.diagnosis(_cap(hist), site.icd)
        b.add(
            f"{chunk}{profile.suffix} {profile.link} {site.text} was diagnosed {rng.choice(['two', 'four', 'six'])} months ago in {a_age} {sex}."
        )
    else:
        chunk = b.diagnosis(hist, site.icd)
        if variant == 0:
            b.add(
                f"The patient is {a_age} {sex} with {stage} {chunk}{profile.suffix} {profile.link} {site.text}{extra}."
            )
        else:
            b.add(
                f"This {age}-year-old {sex} is followed for {stage} {chunk}{profile.suffix} {profile.link} {site.text}{extra}."
            )
    dx = chunk
    b.bodypart(site.text, "Problem", dx)

    # Procedures: a biopsy and, often, an operation.
    biopsies = [p for p in site.procedures if p[2] == "biopsy"]
    surgeries = [p for p in site.procedures if p[2] == "surgery"]
    surgery_chunk = ""
    biopsy_chunk = ""
    if biopsies and rng.random() < 0.8:
        phrase, code, _kind, organ = rng.choice(biopsies)
        organ = organ or site.text
        article = "An" if phrase[0] in "aeiouAEIOU" else "A"
        biopsy_chunk = phrase
        if rng.random() < 0.5:
            b.procedure(phrase, code)
            b.add(f"{article} {phrase} of the {organ} was performed at diagnosis.")
            b.bodypart(organ, "Procedure", phrase)
        else:
            b.procedure(phrase, code)
            b.add(f"The diagnosis was established after {article.lower()} {phrase} of the {organ}.")
            b.bodypart(organ, "Procedure", phrase)
            b.temporal("AFTER", "Problem", dx, "Test", phrase)
    if surgeries and rng.random() < 0.6:
        phrase, code, _kind, organ = rng.choice(surgeries)
        organ = organ or site.text
        b.procedure(phrase, code)
        surgery_chunk = phrase
        if rng.random() < 0.5:
            weeks = rng.choice([3, 4, 6])
            b.add(
                f"{pron} underwent {phrase} of the {organ} {WORDS[weeks]} weeks after the diagnosis."
            )
            b.temporal("AFTER", "Treatment", phrase, "Problem", dx)
        else:
            b.add(
                f"{pron} underwent {phrase} of the {organ} {rng.choice(['last year', 'last month', 'in the spring'])}."
            )
        b.bodypart(organ, "Procedure", phrase)

    # Therapy.
    regimen = list(rng.choice(profile.regimens))
    classes = {DRUGS[k][1] for k in regimen}
    word = ""
    if classes == {"chemo"}:
        word, word_code = "chemotherapy", "Z51.11"
    elif classes == {"io"}:
        word, word_code = "immunotherapy", "Z51.12"
    options = ["every", "current", "started"]
    if word:
        options.append("continues")
    if len(regimen) == 1 and DRUGS[regimen[0]][3]:
        options.append("oral")
    if surgery_chunk:
        options.append("adjuvant")
    kind = rng.choice(options)
    first = regimen[0]
    if kind == "oral":
        cycles = WORDS[rng.choice([2, 3, 4, 6])]
        therapy = b.finding("chemotherapy", "Treatment", "Z51.11")
        chunk = b.drug(first)
        b.add(f"{pron} completed {cycles} cycles of {therapy} and is now taking {chunk} daily.")
        b.temporal("AFTER", "Treatment", chunk, "Treatment", therapy)
    else:
        if kind == "continues":
            therapy = b.finding(word, "Treatment", word_code)
            phrase = _list_text([b.drug(k) for k in regimen])
            b.add(f"{pron} continues {therapy} with {phrase}.")
        else:
            phrase = _list_text([b.drug(k) for k in regimen])
            if kind == "every":
                b.add(f"{pron} receives {phrase} every {WORDS[rng.choice([2, 3, 4])]} weeks.")
            elif kind == "current":
                b.add(f"{pron} is currently on {phrase}.")
            elif kind == "started":
                b.add(f"Treatment with {phrase} was started after the diagnosis.")
                for key in regimen:
                    b.temporal("AFTER", "Treatment", b.drug_chunks[key], "Problem", dx)
            else:
                weeks = WORDS[rng.choice([3, 4, 6])]
                b.add(f"Adjuvant {phrase} was started {weeks} weeks after {surgery_chunk}.")
                for key in regimen:
                    b.temporal("AFTER", "Treatment", b.drug_chunks[key], "Treatment", surgery_chunk)
    if biopsy_chunk and rng.random() < 0.25:
        b.add(f"The {biopsy_chunk} was done before treatment with {b.drug_chunks[first]}.")
        b.temporal("BEFORE", "Test", biopsy_chunk, "Treatment", b.drug_chunks[first])
    if rng.random() < 0.15 and not b.has("radiation therapy"):
        therapy = b.finding("radiation therapy", "Treatment", "Z51.0")
        b.add(f"{pron} also completed {therapy} to the {site.text}.")

    # A side effect of the treatment, with its temporal clue.
    causes = [a for a in ADVERSE if a[2] & set(regimen) and not b.has(a[0])]
    if causes and rng.random() < 0.55:
        name, code, drugs = rng.choice(causes)
        culprits = [k for k in regimen if k in drugs]
        phrase = _list_text([b.drug_chunks[k] for k in culprits])
        style = rng.randrange(4)
        if style == 0:
            effect = b.finding(name, "Symptom", code, "Present")
            b.add(f"Two weeks after the last cycle of {phrase}, {pron.lower()} developed {effect}.")
        elif style == 1:
            effect = b.finding(_cap(name), "Symptom", code, "Present")
            b.add(
                f"{effect} began {WORDS[rng.choice([2, 3, 4])]} days after the first dose of {b.drug_chunks[culprits[0]]}."
            )
        elif style == 2:
            effect = b.finding(name, "Symptom", code, "Present")
            b.add(f"{pron} developed {effect} after starting {phrase}.")
        else:
            effect = b.finding(name, "Symptom", code, "Present")
            b.add(f"Treatment with {phrase} preceded the onset of {effect}.")
        for key in culprits:
            if style == 3:
                b.temporal("BEFORE", "Treatment", b.drug_chunks[key], "Problem", effect)
            else:
                b.temporal("AFTER", "Problem", effect, "Treatment", b.drug_chunks[key])

    # Staging: metastases found, absent or possible.
    roll = rng.random()
    if roll < 0.4:
        met = "distant metastasis"
        chunk = b.finding(met, "Oncological", METASTASES[met], "Absent")
        b.add(f"Staging CT showed no evidence of {chunk}.")
    elif roll < 0.65:
        met = rng.choice(profile.metastases)
        chunk = b.finding(met, "Oncological", METASTASES[met], "Present")
        b.add(f"Restaging CT shows {chunk}.")
    elif roll < 0.8:
        met = rng.choice(profile.metastases)
        chunk = b.finding(met, "Oncological", METASTASES[met], "Possible")
        b.add(f"The scan suggests possible {chunk}, to be confirmed.")
    else:
        met = rng.choice(profile.metastases)
        chunk = b.finding(met, "Oncological", METASTASES[met], "Absent")
        b.add(f"There is no {chunk}.")

    # Symptoms: reported, denied, and sometimes conditional or only a risk.
    pool = [s for s in profile.symptoms if not b.has(s) and not b.has(_cap(s))]
    rng.shuffle(pool)
    present = [
        b.finding(s, "Symptom", SYMPTOMS[s], "Present") for s in pool[: rng.choice([1, 2, 2, 3])]
    ]
    b.add(
        f"{pron} {rng.choice(['reports', 'presents with', 'complains of'])} {_list_text(present)}."
    )
    if rng.random() < 0.2:
        b.add(f"{pron} has had {present[0]} throughout treatment with {b.drug_chunks[first]}.")
        b.temporal("OVERLAP", "Symptom", present[0], "Treatment", b.drug_chunks[first])
    rest = [s for s in pool[len(present) :] if not b.has(s)]
    if rest and rng.random() < 0.65:
        denied = b.finding(rest[0], "Symptom", SYMPTOMS[rest[0]], "Absent")
        b.add(rng.choice([f"{pron} denies {denied}.", f"{pron} has no {denied}."]))
    if not b.has("nausea") and "nausea" in SYMPTOMS and rng.random() < 0.1:
        chunk = b.finding("nausea", "Symptom", SYMPTOMS["nausea"], "Conditional")
        b.add(f"Antiemetics were prescribed to use if {chunk} develops.")
    risks = [
        a for a in ADVERSE if a[2] & set(regimen) and not b.has(a[0]) and not b.has(_cap(a[0]))
    ]
    if risks and rng.random() < 0.18:
        name, code, _drugs = rng.choice(risks)
        chunk = b.finding(name, "Symptom", code, "Hypothetical")
        b.add(f"{pron} was counselled about the risk of {chunk} with further cycles.")

    # Family history.
    if rng.random() < 0.4:
        key = profile.family if rng.random() < 0.7 else rng.choice(list(FAMILY))
        phrase, code = FAMILY[key]
        if not b.has(phrase):
            relative = rng.choice(RELATIVES)
            chunk = b.finding(phrase, "Oncological", code, "Someone_else")
            tail = rng.choice(["", " at an early age", " in the fifties"])
            verb = rng.choice(["had", "was treated for"])
            b.add(f"{poss} {relative} {verb} {chunk}{tail}.")

    b.add(f"Plan: continue {b.drug_chunks[first]}, {rng.choice(PLANS)}.")
    b.check()
    return b


def _hand_written(rng: random.Random) -> list[Builder]:
    """The five notes written by hand, with their answers."""
    notes: list[Builder] = []

    b = Builder(rng)
    b.add("Breast Service Follow-up.")
    dx = b.finding("invasive ductal carcinoma", "Oncological", "C50.912", "Present")
    b.add(
        f"The patient is a 54-year-old woman with {dx} of the left breast, diagnosed four months ago."
    )
    b.bodypart("left breast", "Problem", dx)
    therapy = b.finding("chemotherapy", "Treatment", "Z51.11")
    tamoxifen = b.drug("tamoxifen")
    b.add(f"She completed four cycles of {therapy} and is now taking {tamoxifen} daily.")
    b.temporal("AFTER", "Treatment", tamoxifen, "Treatment", therapy)
    b.temporal("AFTER", "Treatment", therapy, "Problem", dx)
    nodes = b.finding("axillary lymphadenopathy", "Symptom", "R59.0", "Absent")
    b.add(f"Examination shows a well-healed scar over the left breast with no {nodes}.")
    b.bodypart("left breast", "Problem", "scar")
    fatigue = b.finding("fatigue", "Symptom", "R53.83", "Present")
    pain = b.finding("chest pain", "Symptom", "R07.9", "Absent")
    b.add(f"She reports mild {fatigue} in the afternoons and denies {pain}.")
    relative = b.finding("breast cancer", "Oncological", "Z80.3", "Someone_else")
    b.add(f"Her mother was treated for {relative} at the same age.")
    mammography = b.procedure("mammography", "BH02ZZZ")
    b.add(f"Plan: continue {tamoxifen}, annual {mammography}, and genetic counselling.")
    b.check()
    notes.append(b)

    b = Builder(rng)
    b.add("Oncology Progress Note.")
    dx = b.finding("non-small cell lung cancer", "Oncological", "C34.11", "Present")
    b.add(
        f"The patient is a 61-year-old man with stage III {dx} of the right upper lobe, on second-line therapy."
    )
    b.bodypart("right upper lobe", "Problem", dx)
    carboplatin = b.drug("carboplatin")
    paclitaxel = b.drug("paclitaxel")
    b.add(f"He receives {carboplatin} and {paclitaxel} every three weeks.")
    tingling = b.finding("numbness and tingling", "Symptom", "R20.2", "Present")
    neuropathy = b.finding("peripheral neuropathy", "Symptom", "G62.0", "Present")
    b.add(
        f"Two weeks after the last cycle he developed {tingling} of both hands, consistent with {neuropathy}."
    )
    for drug in (carboplatin, paclitaxel):
        b.temporal("AFTER", "Problem", neuropathy, "Treatment", drug)
        b.temporal("AFTER", "Symptom", tingling, "Treatment", drug)
    biopsy = b.procedure("CT-guided core biopsy", "0BBC3ZX")
    b.add(f"A {biopsy} of the right upper lobe was performed at diagnosis.")
    b.bodypart("right upper lobe", "Procedure", biopsy)
    b.temporal("AFTER", "Problem", dx, "Test", biopsy)
    hemoptysis = b.finding("hemoptysis", "Symptom", "R04.2", "Absent")
    b.add(f"He denies {hemoptysis}.")
    b.check()
    notes.append(b)

    b = Builder(rng)
    b.add("Gastroenterology and Oncology Note.")
    dx = b.finding("Colon adenocarcinoma", "Oncological", "C18.7", "Present")
    colonoscopy = b.procedure("colonoscopy with biopsy", "0DBN8ZX")
    b.add(f"{dx} of the sigmoid colon was diagnosed after {colonoscopy}.")
    b.bodypart("sigmoid colon", "Problem", dx)
    b.bodypart("sigmoid colon", "Procedure", colonoscopy)
    b.temporal("AFTER", "Problem", dx, "Test", colonoscopy)
    loss = b.finding("weight loss", "Symptom", "R63.4", "Present")
    nausea = b.finding("nausea", "Symptom", "R11.0", "Present")
    b.add(f"The patient reports {loss} and {nausea}.")
    relative = b.finding("colon cancer", "Oncological", "Z80.0", "Someone_else")
    b.add(f"Her father had {relative} in his fifties.")
    met = b.finding("distant metastasis", "Oncological", "C79.9", "Absent")
    b.add(f"Staging CT showed no evidence of {met}.")
    oxaliplatin = b.drug("oxaliplatin")
    b.add(f"Adjuvant {oxaliplatin} is planned.")
    b.check()
    notes.append(b)

    b = Builder(rng)
    b.add("Hematology Consultation.")
    dx = b.finding("classic Hodgkin lymphoma", "Oncological", "C81.12", "Present")
    b.add(
        f"The patient is a 38-year-old woman with {dx}, nodular sclerosis subtype, involving the mediastinum."
    )
    b.bodypart("mediastinum", "Problem", dx)
    sweats = b.finding("night sweats", "Symptom", "R61", "Present")
    fatigue = b.finding("fatigue", "Symptom", "R53.83", "Present")
    b.add(f"She reports {sweats} and {fatigue}.")
    biopsy = b.procedure("excisional biopsy", "07B10ZX")
    b.add(f"An {biopsy} of a cervical lymph node established the diagnosis.")
    b.bodypart("cervical lymph node", "Procedure", biopsy)
    b.temporal("AFTER", "Problem", dx, "Test", biopsy)
    marrow = b.finding("bone marrow involvement", "Oncological", "C79.52", "Absent")
    b.add(f"PET scan shows no evidence of {marrow}.")
    b.check()
    notes.append(b)

    b = Builder(rng)
    b.add("Dermatology Oncology Note.")
    dx = b.finding("nodular melanoma", "Oncological", "C43.61", "Present")
    b.add(
        f"The patient is a 67-year-old man with {dx} of the right shoulder, Breslow thickness 2.4 mm."
    )
    b.bodypart("right shoulder", "Problem", dx)
    excision = b.procedure("Wide local excision", "0HBBXZZ")
    node = b.procedure("sentinel lymph node biopsy", "07B53ZX")
    b.add(f"{excision} with {node} was performed.")
    b.bodypart("right shoulder", "Procedure", excision)
    dyspnea = b.finding("dyspnea", "Symptom", "R06.02", "Absent")
    b.add(f"He denies {dyspnea}.")
    pembrolizumab = b.drug("pembrolizumab")
    b.add(f"Adjuvant {pembrolizumab} is recommended.")
    b.temporal("AFTER", "Treatment", pembrolizumab, "Treatment", excision)
    b.check()
    notes.append(b)
    return notes


def generate() -> dict:
    """Return the notes and the recorded answers, from one seed."""
    rng = random.Random(SEED)
    builders = _hand_written(rng)
    texts = {b.text() for b in builders}
    generated: list[Builder] = []
    for name, count in MIX.items():
        for _ in range(count):
            while True:
                b = _generated_note(rng, PROFILES[name])
                if b.text() not in texts:
                    break
            texts.add(b.text())
            generated.append(b)
    rng.shuffle(generated)
    builders.extend(generated)

    notes = []
    answers: dict[str, dict[str, str]] = {task: {} for task in next(iter(builders)).answers}
    for index, b in enumerate(builders, start=1):
        notes.append({"note_id": f"n{index:03d}", "text": b.text()})
        for task, items in b.answers.items():
            answers[task][b.text()] = json.dumps(items)
    return {"notes": notes, "answers": answers}


def _check_task_names(answers: dict[str, dict[str, str]]) -> None:
    """The recorded-answer keys must be the `task:` lines of the prompts."""
    prompts = REPO / "src" / "oncology_real_world_data_extractor" / "text" / "prompts"
    tasks = set()
    for path in prompts.glob("*.md"):
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("task:"), path
        tasks.add(first_line.removeprefix("task:").strip())
    assert tasks == set(answers), (tasks, set(answers))


EXTRACTION_JOBS = (
    "extract_oncology_entities",
    "extract_drugs",
    "extract_procedure_codes",
    "extract_assertions",
    "extract_temporal_relations",
    "extract_bodypart_relations",
)


def main() -> None:
    data = generate()
    _check_task_names(data["answers"])
    tables = {"notes": pa.Table.from_pylist(data["notes"], schema=NOTES)}
    model = RecordedTextModel(data["answers"])
    for name in EXTRACTION_JOBS:
        spec = REGISTRY[name]
        outputs = call_run(spec, {"notes": tables["notes"]}, spec.params_cls(), model)
        for table_name, table in outputs.items():
            if table_name.startswith("rejected_"):
                assert table.num_rows == 0, (table_name, table.to_pylist()[:3])
            else:
                tables[table_name] = table
    spec = REGISTRY["build_knowledge_graph"]
    tables.update(call_run(spec, tables, spec.params_cls(), None))
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        pq.write_table(table, SAMPLE_DIR / f"{name}.parquet")
        print(f"{name}: {table.num_rows} rows")
    answers_path = REPO / "tests" / "recorded_answers.json"
    answers_path.write_text(json.dumps(data["answers"], indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
