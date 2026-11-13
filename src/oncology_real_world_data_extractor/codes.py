"""ICD-10-CM block titles used to group oncology codes into reporting categories."""

from __future__ import annotations

# Low and high code of each block, inclusive, with the block's standard title.
ICD10_ONCOLOGY_BLOCKS: tuple[tuple[str, str, str], ...] = (
    ("C00", "C14", "Malignant neoplasms of lip, oral cavity and pharynx"),
    ("C15", "C26", "Malignant neoplasms of digestive organs"),
    ("C30", "C39", "Malignant neoplasms of respiratory and intrathoracic organs"),
    ("C40", "C41", "Malignant neoplasms of bone and articular cartilage"),
    ("C43", "C44", "Melanoma and other malignant neoplasms of skin"),
    ("C45", "C49", "Malignant neoplasms of mesothelial and soft tissue"),
    ("C50", "C50", "Malignant neoplasms of breast"),
    ("C51", "C58", "Malignant neoplasms of female genital organs"),
    ("C60", "C63", "Malignant neoplasms of male genital organs"),
    ("C64", "C68", "Malignant neoplasms of urinary tract"),
    ("C69", "C72", "Malignant neoplasms of eye, brain and other parts of central nervous system"),
    ("C73", "C75", "Malignant neoplasms of thyroid and other endocrine glands"),
    ("C76", "C80", "Malignant neoplasms of ill-defined, other secondary and unspecified sites"),
    ("C81", "C96", "Malignant neoplasms of lymphoid, hematopoietic and related tissue"),
    ("D00", "D09", "In situ neoplasms"),
    ("D60", "D64", "Aplastic and other anemias and other bone marrow failure syndromes"),
    ("E70", "E88", "Metabolic disorders"),
    ("G89", "G99", "Other disorders of the nervous system"),
    ("R10", "R19", "Symptoms and signs involving the digestive system and abdomen"),
    ("R50", "R69", "General symptoms and signs"),
    ("Z00", "Z13", "Persons encountering health services for examinations"),
)


def oncology_category(code: str) -> str:
    """Return the ICD-10-CM block title a code falls in, or "" when it falls in none."""
    if not code:
        return ""
    prefix = code.strip().upper()[:3]
    for low, high, title in ICD10_ONCOLOGY_BLOCKS:
        if low <= prefix <= high:
            return title
    return ""
