"""Critical failure detection for generated images.

Detects gender swap, missing subject, and count mismatch by comparing
prompt subject tags against high-confidence WD14 detections.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from config import CRITICAL_FAILURE_SUBJECT_THRESHOLD

# --- Subject tag sets (derived from CATEGORY_PATTERNS["subject"]) ---

FEMALE_SUBJECT_TAGS = {"1girl", "2girls", "3girls", "4girls", "5girls", "6+girls", "multiple_girls"}
MALE_SUBJECT_TAGS = {"1boy", "2boys", "3boys", "4boys", "5boys", "6+boys", "multiple_boys"}
ALL_SUBJECT_TAGS = (
    FEMALE_SUBJECT_TAGS | MALE_SUBJECT_TAGS | {"solo", "duo", "trio", "group", "crowd", "everyone", "couple", "1other"}
)

COUNT_MAP: dict[str, int] = {
    "solo": 1,
    "1girl": 1,
    "1boy": 1,
    "1other": 1,
    "duo": 2,
    "couple": 2,
    "2girls": 2,
    "2boys": 2,
    "trio": 3,
    "3girls": 3,
    "3boys": 3,
    "4girls": 4,
    "4boys": 4,
    "5girls": 5,
    "5boys": 5,
}

# Regex to strip SD weight syntax: (tag:1.3) → tag
_WEIGHT_RE = re.compile(r"\(([^:)]+)(?::[^)]+)?\)")


def _compute_subject_count(subject_tags: set[str], gender: str | None) -> int | None:
    """Compute total person count from subject tags.

    For mixed gender (1girl + 1boy), sums female and male counts.
    For single gender, takes the max count tag.
    """
    if not subject_tags:
        return None

    if gender == "mixed":
        female_count = 0
        male_count = 0
        for tag in subject_tags:
            tc = COUNT_MAP.get(tag)
            if tc is None:
                continue
            if tag in FEMALE_SUBJECT_TAGS:
                female_count = max(female_count, tc)
            elif tag in MALE_SUBJECT_TAGS:
                male_count = max(male_count, tc)
        total = female_count + male_count
        return total if total > 0 else None

    count: int | None = None
    for tag in subject_tags:
        tc = COUNT_MAP.get(tag)
        if tc is not None:
            count = max(count or 0, tc)
    return count


def _infer_gender(subject_tags: set[str]) -> str | None:
    """Infer gender from subject tags."""
    has_female = bool(subject_tags & FEMALE_SUBJECT_TAGS)
    has_male = bool(subject_tags & MALE_SUBJECT_TAGS)
    if has_female and has_male:
        return "mixed"
    if has_female:
        return "female"
    if has_male:
        return "male"
    return None


@dataclass
class CriticalFailure:
    failure_type: str  # "gender_swap" | "no_subject" | "count_mismatch"
    expected: str
    detected: str
    confidence: float


@dataclass
class CriticalFailureResult:
    has_failure: bool = False
    failures: list[CriticalFailure] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "has_failure": self.has_failure,
            "failures": [
                {
                    "failure_type": f.failure_type,
                    "expected": f.expected,
                    "detected": f.detected,
                    "confidence": f.confidence,
                }
                for f in self.failures
            ],
        }


def extract_expected_subjects(prompt: str) -> dict[str, Any]:
    """Parse prompt to extract expected subject info.

    Returns dict with keys: gender ("female"|"male"|"mixed"|None),
    count (int|None), subject_tags (set of matched tags).
    """
    if not prompt:
        return {"gender": None, "count": None, "subject_tags": set()}

    # Strip weight syntax and normalize
    cleaned = _WEIGHT_RE.sub(r"\1", prompt)
    tokens = {t.strip().lower().replace(" ", "_") for t in cleaned.split(",")}

    subject_tags = tokens & ALL_SUBJECT_TAGS
    if not subject_tags:
        return {"gender": None, "count": None, "subject_tags": set()}

    gender = _infer_gender(subject_tags)
    count = _compute_subject_count(subject_tags, gender)
    return {"gender": gender, "count": count, "subject_tags": subject_tags}


def extract_detected_subjects(
    tags: list[dict[str, Any]],
    threshold: float | None = None,
) -> dict[str, Any]:
    """Extract subject info from WD14 high-confidence tags.

    Returns dict with keys: gender, count, subject_tags (same structure as expected).
    """
    if threshold is None:
        threshold = CRITICAL_FAILURE_SUBJECT_THRESHOLD

    subject_tags: set[str] = set()
    max_confidence = 0.0

    for item in tags:
        tag = item["tag"].lower().replace(" ", "_")
        score = item["score"]
        if score >= threshold and tag in ALL_SUBJECT_TAGS:
            subject_tags.add(tag)
            max_confidence = max(max_confidence, score)

    if not subject_tags:
        return {"gender": None, "count": None, "subject_tags": set(), "confidence": 0.0}

    gender = _infer_gender(subject_tags)
    count = _compute_subject_count(subject_tags, gender)

    return {
        "gender": gender,
        "count": count,
        "subject_tags": subject_tags,
        "confidence": max_confidence,
    }


def detect_critical_failure(
    prompt: str,
    tags: list[dict[str, Any]],
) -> CriticalFailureResult:
    """Detect critical generation failures by comparing prompt vs WD14 subjects.

    Checks for: gender_swap, no_subject, count_mismatch.
    """
    expected = extract_expected_subjects(prompt)
    if not expected["subject_tags"]:
        # Background/narration scene — no subject expected
        return CriticalFailureResult()

    detected = extract_detected_subjects(tags)
    failures: list[CriticalFailure] = []
    confidence = detected.get("confidence", 0.0)

    # 1) No subject detected at all
    if not detected["subject_tags"]:
        failures.append(
            CriticalFailure(
                failure_type="no_subject",
                expected=", ".join(sorted(expected["subject_tags"])),
                detected="none",
                confidence=0.0,
            )
        )
        return CriticalFailureResult(has_failure=True, failures=failures)

    # 2) Gender swap (only when both sides have clear single gender)
    if (
        expected["gender"] in ("female", "male")
        and detected["gender"] in ("female", "male")
        and expected["gender"] != detected["gender"]
    ):
        failures.append(
            CriticalFailure(
                failure_type="gender_swap",
                expected=expected["gender"],
                detected=detected["gender"],
                confidence=confidence,
            )
        )

    # 3) Count mismatch
    if expected["count"] is not None and detected["count"] is not None and expected["count"] != detected["count"]:
        failures.append(
            CriticalFailure(
                failure_type="count_mismatch",
                expected=str(expected["count"]),
                detected=str(detected["count"]),
                confidence=confidence,
            )
        )

    return CriticalFailureResult(has_failure=bool(failures), failures=failures)
