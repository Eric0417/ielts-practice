"""
Covert existing .md files to the IELTS meta.json format.

Usage:
    python scripts/convert.py path/to/your/file.md [--type reading|listening|writing]

This script reads a markdown file and produces a meta.json following the
schema expected by the content loader.

The markdown parsing logic is in parse_markdown() — you MUST edit it
to match your actual file format. See the TODO markers below.
"""
import json
import argparse
import re
import os
from pathlib import Path
from typing import Optional


# ============================================================================
# TODO: 依實際 .md 格式調整解析邏輯
# TODO: Adjust the parsing logic below to match YOUR actual .md file format.
#
# The current placeholder parser assumes this format:
#   # Title of the passage
#   ## Questions
#   1. What is the main idea...?
#       A. First option
#       B. Second option
#       C. Third option
#       D. Fourth option
#   Answer: B
#
# If your actual .md files use a different format (different heading levels,
# different answer markers, different choice labels, etc.), you need to
# modify the parsing logic in this function.
# ============================================================================


def parse_markdown(filepath: str) -> dict:
    """Parse a markdown file into the meta.json schema.

    PLACEHOLDER: This parser assumes a specific .md format. If your actual
    .md files are structured differently, adjust the parsing logic below.

    Assumed format (# = heading, Answer: = answer marker):
        # Title
        ## Questions
        1. Question text
            A. Choice
            B. Choice
            ...
        Answer: B

    Returns:
        A dict matching the meta.json schema for reading/listening questions.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # --- Parse title (first # heading) ---
    title = "Untitled"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            break

    # --- Parse questions ---
    questions = []
    current_question: Optional[dict] = None
    # TODO: Adjust these patterns to match your actual .md format
    QUESTION_START = re.compile(r"^\d+\.\s+(.+)")     # "1. Question text"
    CHOICE_LINE = re.compile(r"^\s+([A-D])[\.\)]\s+(.+)")  # "    A. Choice"
    ANSWER_LINE = re.compile(r"^Answer:\s*([A-D])", re.IGNORECASE)  # "Answer: B"

    for line in lines:
        stripped = line.strip()

        # Check for answer line
        ans_match = ANSWER_LINE.match(stripped)
        if ans_match and current_question:
            current_question["answer"] = ans_match.group(1).upper()
            questions.append(current_question)
            current_question = None
            continue

        # Check for question start
        q_match = QUESTION_START.match(stripped)
        if q_match:
            # Save previous question if one is open without an answer
            if current_question:
                print(f"WARNING: Question {current_question.get('number')} has no Answer: line")
                questions.append(current_question)

            current_question = {
                "id": f"q{len(questions) + 1}",
                "number": len(questions) + 1,
                "prompt": q_match.group(1).strip(),
                "choices": [],
                "answer": "",
            }
            continue

        # Check for choice line
        c_match = CHOICE_LINE.match(stripped)
        if c_match and current_question:
            label = c_match.group(1).upper()
            text = f"{label}. {c_match.group(2).strip()}"
            current_question["choices"].append(text)
            continue

    # Handle last question if no answer line
    if current_question:
        print(f"WARNING: Question {current_question.get('number')} has no Answer: line")
        questions.append(current_question)

    return {
        "id": f"converted-{Path(filepath).stem}",
        "type": "reading",  # caller can override
        "title": title,
        "pdf": None,
        "audio": None,
        "questions": questions,
    }


# ============================================================================
# End of TODO section
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Convert a markdown file to IELTS meta.json format"
    )
    parser.add_argument(
        "input",
        help="Path to the input .md file",
    )
    parser.add_argument(
        "--type",
        choices=["reading", "listening", "writing"],
        default="reading",
        help="Question type (default: reading)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory or file path. If a directory, writes INPUT_STEM.json inside it.",
    )
    parser.add_argument(
        "--id",
        default=None,
        help="Override the question ID (default: derived from filename)",
    )
    parser.add_argument(
        "--audio",
        default=None,
        help="Set the audio filename (for listening type)",
    )
    args = parser.parse_args()

    # Parse the markdown
    data = parse_markdown(args.input)
    data["type"] = args.type

    if args.id:
        data["id"] = args.id

    if args.audio:
        data["audio"] = args.audio
        data["pdf"] = None
    elif args.type == "listening":
        data["audio"] = "audio.mp3"
        data["pdf"] = None

    # Figure out output path
    if args.output:
        out_path = Path(args.output)
        if out_path.is_dir():
            out_path = out_path / f"{Path(args.input).stem}.json"
    else:
        out_path = Path(f"{Path(args.input).stem}.json")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[convert] Written: {out_path}")
    print(f"[convert] Type: {args.type}, Questions: {len(data['questions'])}")
    if any(q.get("answer", "") == "" for q in data["questions"]):
        print("[convert] WARNING: Some questions have no answer. Edit the JSON manually.")


if __name__ == "__main__":
    main()
