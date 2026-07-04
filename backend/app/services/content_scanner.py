"""
Content scanner — filesystem-driven content discovery for PDF-based IELTS tests.

Two source directories are supported (newer `PDF_new` takes priority):

**New layout** (PDF_new — per-passage answer files)::

    content/PDF_new/Reading/test001/passage1.pdf
    content/PDF_new/Reading/test001/passage1_answers.json   ← self-contained
    content/PDF_new/Reading/test001/passage2.pdf
    content/PDF_new/Reading/test001/passage2_answers.json
    content/PDF_new/Reading/test001/passage3.pdf
    content/PDF_new/Reading/test001/passage3_answers.json

**Legacy layout** (PDF — single unified answers.json)::

    content/PDF/Reading/test001/passage1.pdf
    content/PDF/Reading/test001/passage2.pdf
    content/PDF/Reading/test001/passage3.pdf
    content/PDF/Reading/test001/answers.json       ← all 3 passages nested

**Book layout** (Listening — legacy Cambridge book structure)::

    content/PDF/Listening/cambridge04/test1/section1.pdf
    content/PDF/Listening/cambridge04/test1/answers.json
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional, Union

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PDF_DIR = PROJECT_ROOT / "content" / "PDF"
PDF_NEW_DIR = PROJECT_ROOT / "content" / "PDF_new"

READING_PARTS = ["passage1", "passage2", "passage3"]
LISTENING_PARTS = ["section1", "section2", "section3", "section4"]
WRITING_PARTS = ["task1", "task2"]

# Skills that use flat layout (tests directly under PDF/{Skill}/)
FLAT_SKILLS = frozenset({"reading", "writing"})

# Virtual "book" id used for flat skills
FLAT_BOOK_ID = "_flat_"

# Determine which content root to use for each skill
def _content_root(skill: str) -> Path:
    """Return PDF_NEW_DIR if it has content for this skill, else PDF_DIR."""
    skill_dir = PDF_NEW_DIR / skill.capitalize()
    if skill_dir.is_dir() and any(skill_dir.iterdir()):
        return PDF_NEW_DIR
    return PDF_DIR


# ---------------------------------------------------------------------------
# UI type → input kind  (12 IELTS question types)
# ---------------------------------------------------------------------------

# Pure text-input types (no choices)
_TEXT_TYPES = frozenset({
    "note-completion",
    "table-completion",
    "flow-chart-completion",
    "diagram-labelling",
    "sentence-completion",
    "short-answer",
    "fill-in-the-blank",
    "summary-completion",
    "sentence-endings",
    "unknown",
})

# TFNG / YNNG  — three-button groups
_TFNG_TYPES = frozenset({
    "true-false-not-given",
    "yes-no-not-given",
})

# Single-select radio (one of N choices)
_MCQ_SINGLE_TYPES = frozenset({
    "multiple-choice",       # traditional 1-of-4 A–D
    "mcq-single",            # alternative label
})

# Multi-select checkbox (2–3 of 5–6 choices)
_MCQ_MULTI_TYPES = frozenset({
    "multiple-choice-multi", # pick 2+ from e.g. A–F
    "mcq-multi",
})

# Matching types — map one set to another
_MATCHING_HEADINGS_TYPES = frozenset({
    "matching-headings",     # paragraphs A–H → headings i–viii
})

_MATCHING_FEATURES_TYPES = frozenset({
    "matching-features",     # items → options A–F
})

_MATCHING_SENTENCE_TYPES = frozenset({
    "matching-sentence-endings",  # sentence starts → ends A–F
})


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _is_flat(skill_lower: str) -> bool:
    return skill_lower in FLAT_SKILLS


def _test_dir(skill: str, book: str, test: str) -> Path:
    """Return the directory holding a test's PDFs and answers."""
    root = _content_root(skill)
    if _is_flat(skill.lower()):
        return root / skill.capitalize() / test
    return root / skill.capitalize() / book / test


def _test_pdf_url(skill: str, test: str) -> str:
    """Return the web-accessible path to the test directory."""
    root = _content_root(skill)
    # Determine the URL prefix based on whether we're using PDF or PDF_new
    if root == PDF_DIR:
        return f"/content/PDF/{skill.capitalize()}/{test}"
    return f"/content/PDF_new/{skill.capitalize()}/{test}"


def _test_pdf_url_booked(skill: str, book: str, test: str) -> str:
    """Return the web-accessible path to the test directory (book layout)."""
    root = _content_root(skill)
    prefix = "PDF_new" if root == PDF_NEW_DIR else "PDF"
    return f"/content/{prefix}/{skill.capitalize()}/{book}/{test}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sorted_books() -> list[str]:
    """Return sorted book ids. Flat skills get a single virtual book."""
    books: set[str] = set()
    for content_root in (PDF_DIR, PDF_NEW_DIR):
        for skill in ("Reading", "Listening", "Writing"):
            skill_dir = content_root / skill
            if not skill_dir.is_dir():
                continue
            if skill.lower() in ("reading", "writing"):
                for entry in skill_dir.iterdir():
                    if entry.is_dir() and entry.name.startswith("test"):
                        books.add(FLAT_BOOK_ID)
                        break
            else:
                for entry in skill_dir.iterdir():
                    if entry.is_dir() and entry.name.startswith("cambridge"):
                        books.add(entry.name)
    return sorted(books,
                  key=lambda n: 0 if n == FLAT_BOOK_ID else int(re.search(r"(\d+)$", n).group(1)))


def _has_skill_dir(skill: str, book: str) -> bool:
    """Check whether a book has content for a given skill."""
    if _is_flat(skill):
        skill_dir = _content_root(skill) / skill.capitalize()
        if not skill_dir.is_dir():
            return False
        for entry in skill_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("test"):
                return True
        return False
    return (_content_root(skill) / skill.capitalize() / book).is_dir()


def _existing_parts(skill: str, test: str, candidates: list[str], book: str = "") -> list[str]:
    base = _test_dir(skill, book or FLAT_BOOK_ID, test)
    return [c for c in candidates if (base / f"{c}.pdf").is_file()]


def _existing_audio(skill: str, book: str, test: str) -> dict[str, str]:
    audio: dict[str, str] = {}
    base = PDF_DIR / skill.capitalize() / book / test
    if not base.is_dir():
        return audio
    for mp3 in sorted(base.glob("*.mp3")):
        stem = mp3.stem
        audio[stem] = f"{_test_pdf_url_booked(skill, book, test)}/{mp3.name}"
    return audio


def _label(book: str, test: str | None = None, skill: str | None = None) -> str:
    if book == FLAT_BOOK_ID:
        # Flat layout — test-only label
        if test:
            tn = re.search(r"(\d+)$", test)
            test_num = int(tn.group(1)) if tn else 0
            parts = []
            if skill:
                parts.append(skill.capitalize())
            parts.append(f"Test {test_num}")
            return " ".join(parts)
        return "All Tests"
    # Book layout
    num = re.search(r"(\d+)$", book)
    book_num = num.group(1) if num else book
    parts = [f"Cambridge {int(book_num)}"]
    if test:
        tn = re.search(r"(\d+)$", test)
        if tn:
            parts.append(f"Test {int(tn.group(1))}")
    if skill:
        parts.append(skill.capitalize())
    return " ".join(parts)


def _natural_sort_key(s: str) -> tuple:
    return tuple(int(part) if part.isdigit() else part.lower()
                 for part in re.split(r"(\d+)", s))


# ---------------------------------------------------------------------------
# Answer-key loading
# ---------------------------------------------------------------------------

def _has_new_style_answers(base: Path) -> bool:
    """Check if a test directory uses per-passage answer files (PDF_new style)."""
    for part in READING_PARTS + LISTENING_PARTS + WRITING_PARTS:
        if (base / f"{part}_answers.json").is_file():
            return True
    return False


def _answers_json_path(book: str, test: str, skill: str, passage: str = "") -> Path | None:
    """Return the path to the answers file, or None.

    For new-style dirs (PDF_new): ``{passage}_answers.json``
    For legacy dirs (PDF): ``answers.json``
    """
    base = _test_dir(skill, book, test)
    if passage:
        p = base / f"{passage}_answers.json"
        return p if p.is_file() else None
    # Legacy unified file
    p = base / "answers.json"
    return p if p.is_file() else None


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def load_answer_key(book: str, test: str, skill: str, passage: str = "") -> dict[str, Any] | None:
    """Load and flatten the answer key for grading.

    Args:
        passage: If provided (e.g. "passage2"), loads only that passage's
                 answers from ``{passage}_answers.json``.  Question IDs are bare
                 ("1", "2", ...) in this mode.

    Returns ``{question_number: correct_answer, ...}`` or ``None``.
    """
    base = _test_dir(skill, book, test)

    # --- Per-passage mode (PDF_new) ---
    if passage:
        path = base / f"{passage}_answers.json"
        if not path.is_file():
            return None
        raw = _load_json(path)
        if not raw or "questions" not in raw:
            return None
        from app.services.answer_normalizer import normalize_passage_answer_key
        return normalize_passage_answer_key(raw)

    # --- Legacy unified answers.json ---
    path = base / "answers.json"
    if not path.is_file():
        return None

    raw = _load_json(path)
    skill_data = raw.get(skill, {})
    if not skill_data or not isinstance(skill_data, dict):
        return None

    # Check if this is new-style (per-passage files without unified wrapper)
    if _has_new_style_answers(base):
        # Load first passage's answers as default
        for part in READING_PARTS + LISTENING_PARTS + WRITING_PARTS:
            part_path = base / f"{part}_answers.json"
            if part_path.is_file():
                pr = _load_json(part_path)
                if pr and "questions" in pr:
                    from app.services.answer_normalizer import normalize_passage_answer_key
                    return normalize_passage_answer_key(pr)
        return None

    from app.services.answer_normalizer import normalize_answer_from_sections
    return normalize_answer_from_sections(skill_data, skill)


# ---------------------------------------------------------------------------
# Section metadata
# ---------------------------------------------------------------------------

def get_section_metadata(book: str, test: str, skill: str, passage: str = "") -> dict | None:
    """Return per-section metadata for the frontend (NO answers exposed).

    Args:
        passage: If provided, loads only that passage's metadata.
    """
    base = _test_dir(skill, book, test)

    if _has_new_style_answers(base):
        return _get_section_metadata_new(base, skill, passage)
    else:
        return _get_section_metadata_legacy(base, skill)


def _get_section_metadata_new(base: Path, skill: str, passage: str = "") -> dict | None:
    """Load section metadata from per-passage ``{part}_answers.json`` files.

    Question IDs are kept bare (1, 2, ... 13) since each passage file is isolated.
    """
    candidates = {"reading": READING_PARTS, "listening": LISTENING_PARTS, "writing": WRITING_PARTS}
    part_names = candidates.get(skill, READING_PARTS)

    available = []
    for part in part_names:
        ans = base / f"{part}_answers.json"
        if ans.is_file() and (base / f"{part}.pdf").is_file():
            available.append(part)

    if passage:
        available = [p for p in available if p == passage]

    if not available:
        return None

    result: dict[str, dict] = {}
    total_questions = 0

    canonical_map = {}
    for i, part in enumerate(available, 1):
        canonical_map[part] = part  # passage1 stays passage1, etc.

    for part in available:
        raw = _load_json(base / f"{part}_answers.json")
        if not raw:
            continue

        qtype = raw.get("type", "unknown")
        questions = raw.get("questions", [])
        total_questions += len(questions)

        ui_questions = []
        for q in questions:
            q_num = str(q.get("q", "")).strip()
            if not q_num:
                continue
            ui_info = _ui_for_question(q, qtype, questions)
            ui_questions.append({"q": q_num, **ui_info, "type": q.get("type")})

        ui_questions.sort(key=lambda x: _natural_sort_key(x["q"]))

        result[part] = {
            "type": qtype,
            "label": _type_label(qtype),
            "questions": ui_questions,
        }

    if total_questions == 0:
        return None

    return result


def _get_section_metadata_legacy(base: Path, skill: str) -> dict | None:
    """Load section metadata from legacy unified ``answers.json``.

    Question IDs are scoped per-section (e.g. ``passage1_1``) to avoid collisions.
    """
    path = base / "answers.json"
    if not path.is_file():
        return None

    raw = _load_json(path)
    skill_data = raw.get(skill, {})
    if not skill_data or not isinstance(skill_data, dict):
        return None

    result: dict[str, dict] = {}
    total_questions = 0

    section_map = {}
    if skill == "reading":
        valid_passages = [k for k in skill_data if any(
            f"passage{i}" in k.lower() or f"part{i}" in k.lower()
            for i in [1, 2, 3]
        )]
        valid_passages.sort()
        for i, key in enumerate(valid_passages[:3], 1):
            section_map[key] = f"passage{i}"
    elif skill == "listening":
        valid_sections = [k for k in skill_data if any(
            f"section{i}" in k.lower() or f"part{i}" in k.lower()
            for i in [1, 2, 3, 4]
        )]
        valid_sections.sort()
        for i, key in enumerate(valid_sections[:4], 1):
            section_map[key] = f"section{i}"
    else:
        section_map = {k: k for k in skill_data}

    for section_name, section_data in skill_data.items():
        if not isinstance(section_data, (dict, list)):
            continue

        qtype = _extract_type(section_data, skill)
        questions = _extract_question_list(section_data, qtype)
        total_questions += len(questions)

        ui_questions = []
        canonical = section_map.get(section_name, section_name)
        for q in questions:
            q_num = str(q.get("q", "")).strip()
            if not q_num:
                continue
            scoped_q = f"{canonical}_{q_num}"
            ui_info = _ui_for_question(q, qtype, questions)
            ui_questions.append({"q": scoped_q, **ui_info, "type": q.get("type")})

        ui_questions.sort(key=lambda x: _natural_sort_key(x["q"]))

        result[canonical] = {
            "type": qtype,
            "label": _type_label(qtype),
            "questions": ui_questions,
        }

    if total_questions == 0:
        return None

    return result


def _extract_type(section_data: Union[dict, list], skill: str = "") -> str:
    if isinstance(section_data, dict):
        if "type" in section_data:
            return section_data["type"]
        if "questions" in section_data:
            return _infer_type_from_values(
                [q.get("a", "") for q in section_data["questions"] if isinstance(q, dict)]
            )
        return _infer_type_from_values(list(section_data.values()))
    if isinstance(section_data, list):
        return _infer_type_from_values(
            [q.get("a", "") for q in section_data if isinstance(q, dict)]
        )
    return "unknown"


def _extract_question_list(section_data: Union[dict, list], qtype: str) -> list[dict]:
    if isinstance(section_data, dict):
        if "questions" in section_data:
            return [q for q in section_data["questions"] if isinstance(q, dict)]
        return [{"q": str(q), "a": str(a)} for q, a in section_data.items()
                if q.strip()]
    if isinstance(section_data, list):
        return [q for q in section_data if isinstance(q, dict)]
    return []


def _infer_type_from_values(values: list) -> str:
    if not values:
        return "unknown"
    letters = tfng = ynng = text = 0
    for v in values:
        s = str(v).strip().upper()
        if not s:
            continue
        if s in ("TRUE", "FALSE", "NOT GIVEN", "NOTGIVEN", "NOT_GIVEN"):
            tfng += 1
        elif s in ("YES", "NO"):
            ynng += 1
        elif re.fullmatch(r"[A-Z]", s):
            letters += 1
        else:
            text += 1
    total = letters + tfng + ynng + text
    if total == 0:
        return "unknown"
    if tfng / total >= 0.4:
        return "true-false-not-given"
    if ynng / total >= 0.4:
        return "yes-no-not-given"
    if letters / total >= 0.4:
        return "matching"
    return "fill-in-the-blank"


def _ui_for_question(q: dict, section_type: str, all_questions: list[dict]) -> dict:
    """Map a question to its frontend UI component and choices.

    Returns ``{"ui": "<kind>", "choices": [...] | None, "meta": {...} | None}``.

    UI kinds returned (→ React component):
      - ``"radio"``       → single-select radio group
      - ``"checkbox"``    → multi-select checkbox group
      - ``"tfng"``        → TRUE / FALSE / NOT GIVEN buttons
      - ``"dropdown"``    → single-select dropdown (per item)
      - ``"drag-drop"``   → mapping via drag-and-drop / dual-list
      - ``"text"``        → free-text input (fuzzy-graded)
    """
    answer = str(q.get("a", "")).strip()
    q_num = str(q.get("q", ""))

    # ── Paired questions ──
    if "&" in q_num:
        return {"ui": "paired"}
    if "IN EITHER ORDER" in answer.upper():
        return {"ui": "paired"}

    # ── Per-question type (preferred) ──
    qtype = str(q.get("type", "")).strip().lower()

    # -- TFNG / YNNG --
    if qtype in _TFNG_TYPES:
        if qtype == "yes-no-not-given":
            return {"ui": "tfng", "choices": ["YES", "NO", "NOT GIVEN"]}
        return {"ui": "tfng", "choices": ["TRUE", "FALSE", "NOT GIVEN"]}

    # -- MCQ single --
    if qtype in _MCQ_SINGLE_TYPES:
        return {"ui": "radio", "choices": ["A", "B", "C", "D"]}

    # -- MCQ multi --
    if qtype in _MCQ_MULTI_TYPES:
        return {"ui": "checkbox", "choices": ["A", "B", "C", "D", "E", "F"],
                "meta": {"min": 2, "max": 3}}

    # -- Matching headings --
    if qtype in _MATCHING_HEADINGS_TYPES:
        return {"ui": "drag-drop",
                "meta": {"kind": "matching-headings"}}

    # -- Matching features --
    if qtype in _MATCHING_FEATURES_TYPES:
        return {"ui": "dropdown",
                "meta": {"kind": "matching-features"}}

    # -- Matching sentence endings --
    if qtype in _MATCHING_SENTENCE_TYPES:
        return {"ui": "dropdown",
                "meta": {"kind": "matching-sentence-endings"}}

    # -- Summary / table / flow-chart / diagram / note completion --
    if qtype in _TEXT_TYPES:
        return {"ui": "text"}

    # ── Section-level type fallback ──
    if section_type in _TFNG_TYPES:
        if section_type == "yes-no-not-given":
            return {"ui": "tfng", "choices": ["YES", "NO", "NOT GIVEN"]}
        return {"ui": "tfng", "choices": ["TRUE", "FALSE", "NOT GIVEN"]}

    if section_type in _MCQ_SINGLE_TYPES:
        return {"ui": "radio", "choices": ["A", "B", "C", "D"]}

    if section_type in _MCQ_MULTI_TYPES:
        return {"ui": "checkbox", "choices": ["A", "B", "C", "D", "E", "F"],
                "meta": {"min": 2, "max": 3}}

    if section_type in _TEXT_TYPES:
        if re.fullmatch(r"[A-Z]", answer.upper()):
            letters = _collect_letters(all_questions)
            if len(letters) >= 3:
                return {"ui": "radio", "choices": letters}
        return {"ui": "text"}

    # ── Value-based fallback ──
    if not answer:
        return {"ui": "text"}

    upper = answer.upper()
    if upper in ("TRUE", "FALSE", "NOT GIVEN", "NOTGIVEN", "NOT_GIVEN"):
        return {"ui": "tfng", "choices": ["TRUE", "FALSE", "NOT GIVEN"]}
    if upper in ("YES", "NO"):
        return {"ui": "tfng", "choices": ["YES", "NO", "NOT GIVEN"]}
    if re.fullmatch(r"[A-Z]", upper):
        letters = _collect_letters(all_questions)
        if len(letters) >= 2:
            return {"ui": "radio", "choices": letters}

    return {"ui": "text"}


def _collect_letters(questions: list[dict]) -> list[str]:
    seen = set()
    for q in questions:
        a = str(q.get("a", "")).strip().upper()
        if re.fullmatch(r"[A-Z]", a):
            seen.add(a)
    return sorted(seen)


def _type_label(qtype: str) -> str:
    return qtype.replace("-", " ").title()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_content_dirs() -> None:
    for content_root in (PDF_DIR, PDF_NEW_DIR):
        if not content_root.is_dir():
            print(f"[content_scanner] WARNING: content directory not found: {content_root}")


# ── Books ──────────────────────────────────────────────────────────────────

def list_books() -> list[dict]:
    """List all available books.

    Flat skill sets (reading, writing) appear as a single virtual book ``_flat_``.
    """
    books: list[dict] = []

    # Scan both PDF and PDF_new
    has_flat_reading = False
    has_flat_writing = False
    listening_books: set[str] = set()

    for content_root in (PDF_DIR, PDF_NEW_DIR):
        reading_dir = content_root / "Reading"
        if reading_dir.is_dir():
            for entry in reading_dir.iterdir():
                if entry.is_dir() and entry.name.startswith("test"):
                    has_flat_reading = True
                    break

        writing_dir = content_root / "Writing"
        if writing_dir.is_dir():
            for entry in writing_dir.iterdir():
                if entry.is_dir() and entry.name.startswith("test"):
                    has_flat_writing = True
                    break

        listening_dir = content_root / "Listening"
        if listening_dir.is_dir():
            for entry in listening_dir.iterdir():
                if entry.is_dir() and entry.name.startswith("cambridge"):
                    listening_books.add(entry.name)

    if has_flat_reading or has_flat_writing:
        books.append({
            "id": FLAT_BOOK_ID,
            "label": "Practice Tests",
            "has_reading": has_flat_reading,
            "has_listening": False,
            "has_writing": has_flat_writing,
        })

    for book_id in sorted(listening_books,
                          key=lambda n: int(re.search(r"(\d+)$", n).group(1))):
        books.append({
            "id": book_id,
            "label": _label(book_id),
            "has_reading": False,
            "has_listening": True,
            "has_writing": False,
        })

    return books


# ── Tests ──────────────────────────────────────────────────────────────────

def list_book_tests(book: str, test_type: str) -> list[dict]:
    """List available tests for a given book and skill type."""
    skill = test_type.capitalize()
    candidates = {"reading": READING_PARTS, "listening": LISTENING_PARTS, "writing": WRITING_PARTS}
    part_names = candidates.get(test_type, [])

    tests: list[dict] = []

    if _is_flat(test_type):
        skill_dir = _content_root(test_type) / skill
        if not skill_dir.is_dir():
            return []
        for entry in sorted(skill_dir.iterdir(), key=lambda e: e.name):
            if not entry.is_dir() or not entry.name.startswith("test"):
                continue
            test_name = entry.name
            available = [c for c in part_names if (entry / f"{c}.pdf").is_file()]
            if not available:
                continue
            # Check for new-style per-part answers OR legacy unified answers.json
            has_ans = _has_new_style_answers(entry) or (entry / "answers.json").is_file()
            item: dict[str, Any] = {"test": test_name, "has_answers": has_ans}
            if test_type == "reading":
                item["passages"] = available
            elif test_type == "writing":
                item["tasks"] = available
            tests.append(item)
    else:
        skill_dir = _content_root(test_type) / skill / book
        if not skill_dir.is_dir():
            return []
        for entry in sorted(skill_dir.iterdir(), key=lambda e: e.name):
            if not entry.is_dir() or not entry.name.startswith("test"):
                continue
            test_name = entry.name
            available = [c for c in part_names if (entry / f"{c}.pdf").is_file()]
            if not available:
                continue
            has_ans = _has_new_style_answers(entry) or (entry / "answers.json").is_file()
            item: dict[str, Any] = {"test": test_name, "has_answers": has_ans}
            if test_type == "listening":
                item["sections"] = available
            tests.append(item)

    return tests


def get_test_detail(book: str, test: str, test_type: str, passage: str = "") -> dict | None:
    """Get full detail for a specific test: PDFs, audio, question types, etc.

    Args:
        passage: If provided, returns detail for a single passage only.
    """
    skill = test_type.capitalize()

    root = _content_root(test_type)
    if _is_flat(test_type):
        base = root / skill / test
    else:
        base = root / skill / book / test

    if not base.is_dir():
        return None

    candidates = {"reading": READING_PARTS, "listening": LISTENING_PARTS, "writing": WRITING_PARTS}
    part_names = candidates.get(test_type, [])
    available = [c for c in part_names if (base / f"{c}.pdf").is_file()]
    if not available:
        return None

    if passage:
        if passage in available:
            available = [passage]
        else:
            return None

    pdfs: dict[str, str] = {}
    for part in available:
        if _is_flat(test_type):
            pdfs[part] = f"{_test_pdf_url(skill, test)}/{part}.pdf"
        else:
            pdfs[part] = f"{_test_pdf_url_booked(skill, book, test)}/{part}.pdf"

    audio: dict[str, str] | None = None
    if test_type == "listening":
        a = _existing_audio(skill, book, test)
        if a:
            audio = a

    sections = get_section_metadata(book, test, test_type, passage=passage)
    total_questions = sum(len(s["questions"]) for s in (sections or {}).values()) if sections else None

    writing_prompts: dict[str, str] | None = None
    word_limits: dict[str, int] | None = None
    if test_type == "writing":
        writing_prompts = {}
        word_limits = {}
        for task in available:
            prompt = _load_writing_prompt(book, test, task)
            if prompt:
                writing_prompts[task] = prompt
            word_limits[task] = 150 if task == "task1" else 250

    result: dict[str, Any] = {
        "book": book,
        "test": test,
        "type": test_type,
        "label": _label(book, test, test_type),
        "pdfs": pdfs,
        "audio": audio,
        "sections": sections,
        "total_questions": total_questions,
        "has_answers": sections is not None,
    }

    if test_type == "writing":
        result["writing_prompts"] = writing_prompts
        result["word_limits"] = word_limits

    return result


def _load_writing_prompt(book: str, test: str, task: str) -> str | None:
    """Load writing prompt from raw structured_final MD files."""
    from pathlib import Path as P
    book_dir = book if book != FLAT_BOOK_ID else "cambridge20"
    structured_base = PROJECT_ROOT / "content" / "raw" / "structured_final" / book_dir / test / "writing"
    md_path = structured_base / f"{task}.md"
    if md_path.is_file():
        try:
            return md_path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    return None


def get_writing_prompt(book: str, test: str, task: str) -> str:
    text = _load_writing_prompt(book, test, task)
    if text:
        return text
    task_label = "Task 1" if task == "task1" else "Task 2"
    return f"IELTS Writing {task_label}. Please refer to the question PDF for the complete prompt."


def _resolve_pdf_path(book: str, test: str, task: str) -> str | None:
    root = _content_root("writing")
    if _is_flat("writing"):
        candidates = [root / "Writing" / test / f"{task}.pdf"]
    else:
        candidates = [root / "Writing" / book / test / f"{task}.pdf"]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None
