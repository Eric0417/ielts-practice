# IELTS Reading Database Structure

## Overview

This directory contains 100 IELTS Reading practice tests (`test001`–`test100`), each consisting of three reading passages with their corresponding question sets and answer keys.

## Directory Layout

```
Reading/
├── test001/
│   ├── passage1.pdf          # Reading passage 1 (PDF)
│   ├── passage2.pdf          # Reading passage 2 (PDF)
│   ├── passage3.pdf          # Reading passage 3 (PDF)
│   ├── answers.json          # Question types, questions, and answer key
│   ├── passage1.md           # Text version of passage 1 (optional, tests 1–4 only)
│   ├── passage2.md           # Text version of passage 2 (optional, tests 1–3 only)
│   └── passage3.md           # Text version of passage 3 (optional, tests 1–3 only)
├── test002/
│   └── ...
├── ...
└── test100/
    └── ...
```

- **100 test folders** named `test001` through `test100` (zero-padded, 3 digits).
- Every test has exactly 4 required files: `passage1.pdf`, `passage2.pdf`, `passage3.pdf`, `answers.json`.
- Tests 1–4 additionally contain `.md` text versions of some passages (used during content generation).

## answers.json Schema

Each `answers.json` file has the following structure:

```json
{
  "book": "new_content",
  "test": "test001",
  "year": 2026,
  "reading": {
    "passage1": { ... },
    "passage2": { ... },
    "passage3": { ... }
  }
}
```

| Field      | Type   | Description                                      |
|------------|--------|--------------------------------------------------|
| `book`     | string | Always `"new_content"`                           |
| `test`     | string | Test folder name (e.g., `"test001"`)             |
| `year`     | number | Publication year (2026 for all current tests)    |
| `reading`  | object | Contains 3 passage objects: `passage1`, `passage2`, `passage3` |

### Passage Object

Each passage under `reading` has:

```json
{
  "type": "multiple-choice",
  "questions": [
    {
      "q": "1",
      "a": "B",
      "type": "multiple-choice"
    }
  ]
}
```

| Field       | Type   | Description                                                |
|-------------|--------|------------------------------------------------------------|
| `type`      | string | Dominant question type for the passage (informational)     |
| `questions` | array  | Array of 13 question objects (one per question in passage) |

### Question Object

Each question in the `questions` array:

| Field  | Type   | Description                                                              |
|--------|--------|--------------------------------------------------------------------------|
| `q`     | string | Question number (1–13)                                                   |
| `a`     | string | Correct answer: letter (A–D) for multiple-choice, word/phrase for note-completion, or `TRUE`/`FALSE`/`NOT GIVEN` for true-false-not-given |
| `type`  | string | Question type — one of: `"multiple-choice"`, `"note-completion"`, `"true-false-not-given"` |

## Question Types

Three question types appear across all tests, mixed within each passage:

- **multiple-choice**: 4-option questions (A/B/C/D)
- **note-completion**: Fill-in-the-blank with a word or short phrase
- **true-false-not-given**: Statement evaluation (TRUE / FALSE / NOT GIVEN)

Each passage contains exactly 13 questions, mixing these 3 types in varying proportions.

## Usage Notes

- The `PDF_new/Reading` directory sits under `/content/PDF_new/Reading` relative to the project root.
- Test numbering is sequential from 001 to 100 with no gaps.
- All passages are independently usable — there is no dependency between tests.
- The `.md` files in tests 1–4 are plain-text transcriptions of the PDF passages and may be incomplete (not all passages have them).
