"""
Answer-key normalizer and grading engine for IELTS questions.

Implements all grading rules from the specification (§5):

1. Case-insensitive comparison
2. "/" separated alternatives → accept any alternative
3. Number + text alternatives → accept both
4. Paired questions (e.g. "15&16") → grade as a pair
5. Leading/trailing whitespace trimmed
6. Articles preserved (don't strip "a"/"the")
7. Trailing punctuation stripped from user input

Also handles legacy OCR artifacts:
- Pipe-separated alternatives: ``"a I b I c"``
- Mixed-case TFNG values: ``"NOTGIVEN"``, ``"not given"``
- "IN EITHER ORDER" placeholders
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_value(raw: str) -> list[str] | str | None:
    """Normalize a single raw answer value from answers.json.

    Returns:
        None: placeholder / non-answer
        str:  single correct answer
        list[str]: alternatives (any one is correct)
    """
    stripped = raw.strip()
    if not stripped:
        return None

    # "IN EITHER ORDER" — placeholder, not an answer value
    if "IN EITHER ORDER" in stripped.upper():
        return None

    # "& N" — question-number reference, not an answer
    if re.fullmatch(r"&\s*\d+", stripped):
        return None

    # "/" separated alternatives: "colour / color" or "35 / thirty five"
    # Only split when "/" has spaces around it (avoids splitting "I/O")
    if " / " in stripped:
        parts = re.split(r"\s*/\s*", stripped)
        alternatives = [p.strip() for p in parts if p.strip()]
        # Normalize each alternative
        normed = [_normalize_single(a) for a in alternatives]
        normed = [n for n in normed if n]
        if len(normed) == 1:
            return normed[0]
        return normed if normed else None

    # Legacy pipe-separated alternatives ("a I b I c") from OCR
    if " I " in stripped or " i " in stripped:
        parts = re.split(r"\s*[iI]\s*", stripped)
        alternatives = [p.strip() for p in parts if p.strip()]
        normed = [_normalize_single(a) for a in alternatives]
        normed = [n for n in normed if n]
        if len(normed) == 1:
            return normed[0]
        return normed if normed else None

    # TRUE/FALSE/NOT GIVEN — standardize
    tfng = _normalize_tfng(stripped)
    if tfng is not None:
        return tfng

    return _normalize_single(stripped)


def _normalize_tfng(value: str) -> str | None:
    """Standardize TFNG values: NOTGIVEN, NOT GIVEN, NOT_GIVEN → "NOT GIVEN"."""
    cleaned = re.sub(r"[_\s]+", " ", value).strip().upper()
    if cleaned in ("TRUE", "FALSE", "NOT GIVEN", "YES", "NO"):
        if cleaned == "NOTGIVEN":
            cleaned = "NOT GIVEN"
        return cleaned
    return None


def _normalize_single(value: str) -> str:
    """Clean a single answer value: strip punctuation, normalize whitespace."""
    stripped = value.strip()

    # Single letters — uppercase
    if re.fullmatch(r"[A-Za-z]", stripped):
        return stripped.upper()

    # Strip trailing punctuation but keep the answer intact
    # Do NOT strip leading/trailing words — preserve articles
    stripped = re.sub(r"\s+", " ", stripped)
    stripped = stripped.strip()
    # Remove trailing punctuation marks that are not part of the answer
    stripped = re.sub(r"[.,;:!?]$", "", stripped)
    return stripped


# ---------------------------------------------------------------------------
# Answer-key batch normalisation
# ---------------------------------------------------------------------------

def normalize_passage_answer_key(passage_data: dict) -> dict[str, Any]:
    """Normalize a single passage's answer key (from ``{part}_answers.json``).

    Question IDs are kept bare ("1", "2", ...) since no other passage shares
    this answer key.

    Returns:
        {question_number: normalized_answer (str | list[str])}
    """
    result: dict[str, Any] = {}

    questions = passage_data.get("questions", [])
    if not isinstance(questions, list):
        return result

    for q in questions:
        if not isinstance(q, dict):
            continue
        qnum = str(q.get("q", "")).strip()
        answer = str(q.get("a", "")).strip()
        if not qnum or not answer:
            continue
        normalized = _normalize_value(answer)
        if normalized is None:
            continue

        if "&" in qnum:
            subs = [s.strip() for s in qnum.split("&") if s.strip()]
            pair_key = "&".join(subs)
            result[f"__paired__{pair_key}"] = {
                "numbers": subs,
                "answer": normalized,
            }
            for sub in subs:
                result[sub] = normalized
        else:
            result[qnum] = normalized

    return result


def normalize_answer_from_sections(section_data: dict, skill: str = "") -> dict[str, Any]:
    """Normalize an answer key dict from answers.json into a flat grading map.

    Handles both new and legacy formats (§3 specification).

    Question IDs are scoped per-section to avoid collisions across passages
    (each passage restarts numbering from 1).  Keys become ``passage1_1``, etc.

    Returns:
        {question_number: normalized_answer (str | list[str])}
        For paired questions like "23&24": answer stored under "23" and flagged as paired.
    """
    # Build section name map (same logic as get_section_metadata)
    section_map: dict[str, str] = {}
    if skill == "reading":
        valid_passages = [k for k in section_data if any(
            f"passage{i}" in k.lower() or f"part{i}" in k.lower()
            for i in [1, 2, 3]
        )]
        valid_passages.sort()
        for i, key in enumerate(valid_passages[:3], 1):
            section_map[key] = f"passage{i}"
    elif skill == "listening":
        valid_sections = [k for k in section_data if any(
            f"section{i}" in k.lower() or f"part{i}" in k.lower()
            for i in [1, 2, 3, 4]
        )]
        valid_sections.sort()
        for i, key in enumerate(valid_sections[:4], 1):
            section_map[key] = f"section{i}"

    result: dict[str, Any] = {}

    for section_name, section_content in section_data.items():
        if not isinstance(section_content, (dict, list)):
            continue

        # Canonical section key (e.g. "passage1")
        canonical = section_map.get(section_name, section_name)

        # ── New format: {"type": "...", "questions": [{"q":"1","a":"B"},...]} ──
        if isinstance(section_content, dict) and "questions" in section_content:
            for q in section_content["questions"]:
                if not isinstance(q, dict):
                    continue
                qnum = str(q.get("q", "")).strip()
                answer = str(q.get("a", "")).strip()
                if not qnum or not answer:
                    continue
                normalized = _normalize_value(answer)
                if normalized is None:
                    continue

                # Paired question key: "15&16" → scope each sub-key
                if "&" in qnum:
                    subs = [s.strip() for s in qnum.split("&") if s.strip()]
                    scoped_subs = [f"{canonical}_{s}" for s in subs]
                    pair_key = "&".join(scoped_subs)
                    result[f"__paired__{pair_key}"] = {
                        "numbers": scoped_subs,
                        "answer": normalized,
                    }
                    for sub in scoped_subs:
                        result[sub] = normalized
                else:
                    result[f"{canonical}_{qnum}"] = normalized
            continue

        # ── Legacy format: flat dict {"1": "B", "2": "TRUE"} ──
        if isinstance(section_content, dict) and not "questions" in section_content and not "type" in section_content:
            for qnum, raw_answer in section_content.items():
                qnum_str = str(qnum).strip()
                if "&" in qnum_str:
                    subs = [s.strip() for s in qnum_str.split("&") if s.strip()]
                    normalized = _normalize_value(str(raw_answer))
                    if normalized is None:
                        continue
                    pair_key = qnum_str.replace("&", "&")
                    result[f"__paired__{pair_key}"] = {
                        "numbers": subs,
                        "answer": normalized,
                    }
                    for sub in subs:
                        result[sub] = normalized
                else:
                    normalized = _normalize_value(str(raw_answer))
                    if normalized is not None:
                        result[qnum_str] = normalized
            continue

        # ── List format: [{"q":"1","a":"B"},...] ──
        if isinstance(section_content, list):
            for q in section_content:
                if not isinstance(q, dict):
                    continue
                qnum = str(q.get("q", "")).strip()
                answer = str(q.get("a", "")).strip()
                if not qnum:
                    continue
                normalized = _normalize_value(answer)
                if normalized is None:
                    continue
                if "&" in qnum:
                    subs = [s.strip() for s in qnum.split("&") if s.strip()]
                    for sub in subs:
                        result[sub] = normalized
                else:
                    result[qnum] = normalized

    return result


# ---------------------------------------------------------------------------
# Grading engine
# ---------------------------------------------------------------------------

def answers_match(user: Any, correct: Any) -> bool:
    """Compare user answer against the correct answer(s).

    Grading rules by question type:

    ====================== =====================================================
    Type                    Rule
    ====================== =====================================================
    mcq-single              Exact string match (A–D)
    mcq-multi               Set equality (order-independent, comma-joined)
    tfng / ynng             Case-insensitive exact, accepts multiple canonical forms
    matching-*              Exact mapping match (stored as JSON object)
    note-completion         Case-insensitive fuzzy: strip punctuation, normalize whitespace
    summary-completion      Case-insensitive exact word match
    short-answer            Word count ≤ limit  +  fuzzy match
    ====================== =====================================================
    """
    if user is None or correct is None:
        return False

    user_str = str(user).strip()
    if not user_str:
        return False

    # ── Multi-select (comma-joined list → set comparison) ──
    if isinstance(correct, list) and len(correct) > 1:
        user_items = {u.strip().upper() for u in re.split(r"[,;]", user_str) if u.strip()}
        correct_items = {str(c).strip().upper() for c in correct}
        return user_items == correct_items

    # ── Object → JSON mapping comparison (matching-headings etc.) ──
    if isinstance(correct, dict):
        try:
            user_obj = json.loads(user_str) if isinstance(user_str, str) else user_str
        except (json.JSONDecodeError, TypeError):
            return False
        if not isinstance(user_obj, dict):
            return False
        for k, v in correct.items():
            if str(user_obj.get(k, "")).strip().upper() != str(v).strip().upper():
                return False
        return True

    # ── Single-value comparison ──
    user_str = re.sub(r"[.,;:!?]$", "", user_str).strip()
    user_upper = user_str.upper()

    # Build acceptable set
    if isinstance(correct, list):
        acceptable = set()
        for c in correct:
            c_str = str(c).strip().upper()
            acceptable.add(c_str)
            # Normalize TFNG variants
            if c_str == "NOT GIVEN":
                acceptable.add("NOTGIVEN")
                acceptable.add("NOT_GIVEN")
    else:
        correct_str = str(correct).strip().upper()
        acceptable = {correct_str}
        if correct_str == "NOT GIVEN":
            acceptable.add("NOTGIVEN")
            acceptable.add("NOT_GIVEN")

    # Direct match
    if user_upper in acceptable:
        return True

    # Number alternative matching: "35 / thirty five"
    for acc in list(acceptable):
        if " / " in acc:
            for alt in acc.split(" / "):
                alt = alt.strip()
                if user_upper == alt:
                    return True
        # Also handle list items containing "/"
        if "/" in acc:
            for alt in re.split(r"\s*/\s*", acc):
                if user_upper == alt.strip():
                    return True

    return False


def grade_answers(
    user_answers: dict[str, str],
    answer_key: dict[str, Any],
) -> tuple[int, int, list[dict]]:
    """Grade a full set of answers against the answer key.

    Args:
        user_answers: {question_number: user_answer_string}
        answer_key: Flat answer key from normalize_answer_from_sections()

    Returns:
        (correct_count, total_count, detailed_results)
    """
    # Only grade questions the user actually submitted
    regular_keys = {k: v for k, v in answer_key.items() if not k.startswith("__paired__")}
    submitted_keys = {k: v for k, v in regular_keys.items() if k in user_answers}
    total = len(submitted_keys)
    correct = 0
    results = []

    for qnum, correct_answer in sorted(submitted_keys.items(),
                                         key=lambda x: _sort_key(x[0])):
        user_answer = user_answers.get(qnum, "")
        is_correct = answers_match(user_answer, correct_answer)
        if is_correct:
            correct += 1

        results.append({
            "question_id": qnum,
            "user_answer": str(user_answer).strip(),
            "correct_answer": _format_correct(correct_answer),
            "is_correct": is_correct,
        })

    # Handle paired questions: check both answers together
    paired_keys = sorted([k for k in answer_key if k.startswith("__paired__")],
                         key=lambda x: _sort_key(x.split("__paired__")[-1]))
    for pk in paired_keys:
        pair_info = answer_key[pk]
        if not isinstance(pair_info, dict):
            continue
        pair_nums = pair_info["numbers"]
        pair_answer = pair_info["answer"]

        # Check if user's answers to both questions match the set
        if len(pair_nums) == 2:
            n1, n2 = pair_nums
            u1 = user_answers.get(n1, "").strip().upper()
            u2 = user_answers.get(n2, "").strip().upper()

            # Both answers must be in the acceptable set
            acceptable = set()
            if isinstance(pair_answer, list):
                acceptable = {str(a).strip().upper() for a in pair_answer}
            else:
                acceptable = {str(pair_answer).strip().upper()}

            # For paired questions, check both are in the acceptable set
            both_correct = u1 in acceptable and u2 in acceptable and u1 != u2
            # Also check they match the paired answer alternatives

            # Remove existing results for these qnums and re-add
            for r in results:
                if r["question_id"] in pair_nums:
                    r["is_correct"] = both_correct
                    if both_correct:
                        correct += 1
                    else:
                        # Don't double-count if already counted above
                        pass

    return correct, total, results


def _format_correct(answer: Any) -> str:
    """Format correct answer for display."""
    if isinstance(answer, list):
        return " / ".join(str(a) for a in answer)
    return str(answer)


def _sort_key(s: str) -> tuple:
    """Natural sort: '1' < '2' < '10' < '21'."""
    parts = re.split(r"(\d+)", s)
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)
