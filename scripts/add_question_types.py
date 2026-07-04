#!/usr/bin/env python3
"""
One-shot: add per-question ``type`` fields to every answers.json in
content/PDF/Reading/test*/.

Type inference rules:
  - "A" | "B" | "C" | "D" | "E" | "F" → "multiple-choice"
  - "TRUE" | "FALSE" | "NOT GIVEN"      → "true-false-not-given"
  - "YES" | "NO"                        → "yes-no-not-given"
  - everything else                     → "note-completion"

Runs in-place; backs up originals to ``answers.json.bak`` on first run.
"""
import json, shutil, sys
from pathlib import Path

READING_DIR = Path(__file__).resolve().parent.parent / "content" / "PDF" / "Reading"

TFNG = frozenset({"TRUE", "FALSE", "NOT GIVEN", "NOTGIVEN", "NOT_GIVEN"})
YNNG = frozenset({"YES", "NO"})
LETTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def infer_type(answer: str) -> str:
    a = answer.strip().upper()
    if a in TFNG:
        return "true-false-not-given"
    if a in YNNG:
        return "yes-no-not-given"
    if len(a) == 1 and a in LETTERS:
        return "multiple-choice"
    return "note-completion"


def process_test(answers_path: Path) -> int:
    data = json.loads(answers_path.read_text(encoding="utf-8"))
    reading = data.get("reading", {})
    changed = 0

    for passage_val in reading.values():
        if not isinstance(passage_val, dict):
            continue
        for q in passage_val.get("questions", []):
            if isinstance(q, dict) and "type" not in q:
                q["type"] = infer_type(str(q.get("a", "")))
                changed += 1

    if changed:
        bak = answers_path.with_suffix(".json.bak")
        if not bak.exists():
            shutil.copy2(answers_path, bak)
        answers_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return changed


def main():
    total = 0
    for json_file in sorted(READING_DIR.glob("test*/answers.json")):
        n = process_test(json_file)
        print(f"  {json_file.parent.name}: {n} questions updated")
        total += n
    print(f"\nTotal: {total} questions across all tests")


if __name__ == "__main__":
    main()
