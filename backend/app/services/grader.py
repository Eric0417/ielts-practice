"""
IELTS Writing grader — sends the user's essay to the Poe API (OpenAI-compatible)
and parses the structured JSON response.

For Task 1: a PDF image is REQUIRED — the model must see the chart/graph/diagram.
For Task 2: a PDF image is optional (the prompt text is usually sufficient).

The prompt is designed to produce conservative, defensible IELTS band scores
anchored to the official public band descriptors.
"""

from __future__ import annotations

import base64
import io
import json
import re
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI

from app.config import settings

# Lazy-initialized OpenAI client pointed at Poe
_client: OpenAI | None = None

# Project root for resolving PDF paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def get_client() -> OpenAI:
    """Get or create the OpenAI client configured for Poe's API endpoint."""
    global _client
    if _client is None:
        api_key = settings.POE_API_KEY
        if not api_key:
            raise RuntimeError(
                "POE_API_KEY is not set. Please configure it in .env or environment variables."
            )
        _client = OpenAI(
            api_key=api_key,
            base_url="https://api.poe.com/v1",
        )
    return _client


# ---------------------------------------------------------------------------
# PDF → image conversion (for vision-capable models)
# ---------------------------------------------------------------------------

def _pdf_page_to_base64_png(pdf_path: str, page: int = 0, scale: float = 1.5) -> str | None:
    """Convert a single PDF page to a base64-encoded PNG data URL.

    Returns ``None`` if PyMuPDF is not installed or the file is missing.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None

    path = Path(pdf_path)
    if not path.is_file():
        return None

    try:
        doc = fitz.open(str(path))
        if page >= len(doc):
            doc.close()
            return None
        pix = doc[page].get_pixmap(dpi=int(150 * scale))
        doc.close()
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None


def _resolve_pdf_path(book: str, test: str, task: str) -> str | None:
    """Find the PDF file for a writing task."""
    # Try both PDF_new and PDF directories
    for content_dir in ("PDF_new", "PDF"):
        # Flat layout
        candidates = [
            _PROJECT_ROOT / "content" / content_dir / "Writing" / test / f"{task}.pdf",
            # Book layout
            _PROJECT_ROOT / "content" / content_dir / "Writing" / book / test / f"{task}.pdf",
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
    return None


# ---------------------------------------------------------------------------
# Essay language detection
# ---------------------------------------------------------------------------

def detect_essay_language(essay: str) -> str:
    """Detect whether the essay is primarily Chinese or English.

    Returns ``"Traditional Chinese"`` if >15% of characters are CJK, else ``"English"``.
    """
    if not essay.strip():
        return "English"
    cjk_count = sum(1 for ch in essay if '一' <= ch <= '鿿' or '㐀' <= ch <= '䶿')
    total_chars = len(essay.replace(' ', '').replace('\n', ''))
    if total_chars == 0:
        return "English"
    ratio = cjk_count / total_chars
    return "Traditional Chinese" if ratio > 0.15 else "English"


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    """Build the system prompt for IELTS writing grading.

    This prompt is anchored to the official public band descriptors and designed
    to produce conservative, defensible scores — never inflated.
    """
    return """You are an experienced IELTS Writing examiner trained on the official public
band descriptors. Your goal is to produce band scores that are conservative,
consistent, and defensible against the descriptors — never inflated.

## YOUR TASK
Grade the student's essay strictly against the official IELTS Writing band
descriptors (public version) for the specified task type (Task 1 or Task 2).
Always justify each band by referring to descriptor-level features, not vague
impressions.

## THE FOUR CRITERIA (each 0–9, in 0.5 increments)

### 1. Task Achievement (Task 1) / Task Response (Task 2)
Use ONLY the descriptor set that matches the task type given in the user prompt.

TASK 1 — Task Achievement anchors:
- Band 5: Recounts detail mechanically; no clear overview; may focus on detail
  with no clear selection of key features; may have inaccuracies in data.
- Band 6: Presents an overview with information appropriately selected; adequately
  highlights key features but details may be irrelevant, inappropriate or inaccurate.
- Band 7: Clear overview of main trends/differences/stages; clearly presents and
  highlights key features but could be more fully extended.
- Band 8: Covers requirements sufficiently; skilfully selects and highlights key
  features; clear, well-organised overview.

TASK 2 — Task Response anchors:
- Band 5: Addresses the task only partially; position expressed but not always
  clear; some main ideas but underdeveloped/unclear; may over-generalise.
- Band 6: Addresses all parts of the task, though some more than others; relevant
  position presented though conclusions may be unclear/repetitive; relevant main
  ideas but some may be inadequately developed.
- Band 7: Addresses all parts; clear position throughout; extends and supports main
  ideas, though there may be a tendency to over-generalise or lack focus.
- Band 8: Sufficiently addresses all parts; well-developed response with relevant,
  extended and supported ideas; clear position throughout.

### 2. Coherence & Cohesion
- Band 5: Some organisation but no clear progression; inadequate/inaccurate/over-use
  of cohesive devices; may be repetitive; paragraphing may be inadequate/missing.
- Band 6: Coherent arrangement with clear overall progression; effective but
  sometimes mechanical cohesion; referencing not always clear; paragraphing present
  but not always logical.
- Band 7: Logical organisation with clear progression; range of cohesive devices
  used appropriately though with some under/over-use; clear central topic in each
  paragraph.
- Band 8: Sequences information logically; manages cohesion well; uses paragraphing
  sufficiently and appropriately.

### 3. Lexical Resource
- Band 5: Limited but minimally adequate range; noticeable errors in spelling/word
  formation that may cause some difficulty.
- Band 6: Adequate range for the task; attempts less common vocabulary with some
  inaccuracy; some errors in spelling/word formation but they don't impede
  communication.
- Band 7: Sufficient range for flexibility and precision; some less common/idiomatic
  items with awareness of style/collocation; occasional errors.
- Band 8: Wide range used fluently and flexibly; skilful use of uncommon items;
  occasional inaccuracies in word choice/collocation only.

### 4. Grammatical Range & Accuracy
- Band 5: Limited range of structures; complex sentences less accurate than simple
  ones; frequent errors causing some difficulty for the reader.
- Band 6: Mix of simple and complex forms; some errors in grammar/punctuation but
  they rarely reduce communication.
- Band 7: Variety of complex structures; frequent error-free sentences; good control
  though some errors remain.
- Band 8: Wide range of structures; majority error-free; occasional non-systematic
  errors/inappropriacies.

## LENGTH GUIDANCE (do NOT apply a fixed penalty)
Do NOT mechanically subtract a fixed band for under-length essays. Instead, judge
the actual impact: under-length essays usually cannot fully develop/highlight key
features, which naturally limits the Task Achievement/Response band. State clearly
in the comment when under-length has limited development, and reflect it in the band
proportionally to how far below the minimum the essay is.

## OVERALL BAND CALCULATION
1. Compute the arithmetic mean of the four criterion bands.
2. Round to the nearest half band. Official rounding rule:
   - If the mean ends in .25 → round UP to the next .5  (e.g., 6.25 → 6.5)
   - If the mean ends in .75 → round UP to the next whole (e.g., 6.75 → 7.0)
   - Otherwise round to the nearest 0.5 in the normal way.
   Examples: 6.125 → 6.0; 6.375 → 6.5; 6.625 → 6.5; 6.875 → 7.0.

## EDGE CASES
- Blank, gibberish, or non-essay content: score all criteria ≤ 2 and explain.
- Essay merely copies the question prompt: Task Response/Achievement ≤ 2.
- Off-topic or fundamentally misunderstands the task: Task Response/Achievement ≤ 3.
- Essay written in the wrong language (not English) for an Academic/GT task: this is
  a fundamental failure to respond; score Task Response/Achievement ≤ 2 and note it.
- If the essay appears memorised, template-heavy, or machine-generated, note this
  explicitly and evaluate only the language actually relevant to the task.

## OUTPUT FORMAT
Output ONLY a valid JSON object. NO markdown fences, NO text outside the JSON.

{
  "overall_band": 6.5,
  "criteria": {
    "task_response": {"band": 6.0, "comment": "..."},
    "coherence_cohesion": {"band": 7.0, "comment": "..."},
    "lexical_resource": {"band": 6.0, "comment": "..."},
    "grammatical_range_accuracy": {"band": 6.5, "comment": "..."}
  },
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "corrected_examples": [
    {"original": "verbatim sentence from the essay",
     "suggestion": "improved version",
     "explanation": "why it is better (grammar/lexis/cohesion)"}
  ]
}

## RULES
1. Each criterion comment: 3–5 sentences, each referencing specific wording,
   structures, or paragraphs from THIS essay. Name the band descriptor feature
   that justifies the score.
2. Provide 2–4 strengths and 2–4 improvements, all tied to concrete examples.
   No generic platitudes.
3. Provide 3–6 corrected_examples. The "original" field MUST be copied verbatim
   from the essay (identical wording, spelling, capitalisation, punctuation).
   NEVER invent or paraphrase the original. If fewer than 3 correctable sentences
   exist, provide as many as genuinely exist.
4. Keep the JSON key "task_response" for BOTH task types (it maps to Task
   Achievement for Task 1 in the UI). Do not rename keys.
5. Be internally consistent: the overall_band must match the rounded mean of the
   four criterion bands.

## FEEDBACK LANGUAGE
Write ALL feedback in the language specified in the user prompt (e.g. "Traditional
Chinese" or "English"), regardless of the language the essay is written in. Do not
mix languages within the response."""


def build_user_prompt(
    task: str,
    prompt_text: str,
    word_minimum: int,
    essay: str,
    feedback_language: str = "English",
) -> list[dict]:
    """Build the user message content for the grading request.

    Returns a multimodal content list. If the prompt_text is available,
    it is included as text. Optionally a PDF image can be attached for
    vision-capable models.
    """
    task_label = "Task 1" if task == "task1" else "Task 2"
    task_desc = (
        "Task 1 (Academic): Describe, summarise or explain information from a graph, table, chart or diagram. "
        "Minimum 150 words. Key features: overview, data description, comparisons, no personal opinion."
        if task == "task1"
        else "Task 2 (Academic/General): Write an essay in response to a point of view, argument or problem. "
        "Minimum 250 words. Key features: clear position, developed ideas, logical argument, conclusion."
    )

    actual_words = len(essay.split())
    under_length = actual_words < word_minimum
    under_length_note = (
        "\n\nNOTE: This essay is below the minimum. Judge the impact on development "
        "per the length guidance; do not apply a fixed penalty."
        if under_length
        else ""
    )

    user_text = f"""Please grade this IELTS {task_label} essay.

## TASK TYPE
{task_desc}

## FEEDBACK LANGUAGE
Write all feedback in: {feedback_language}

## WORD COUNT
Minimum required: {word_minimum} words
Student's word count: {actual_words} words{under_length_note}

## QUESTION PROMPT
{prompt_text if prompt_text else 'See the attached image of the question paper.'}

## STUDENT'S ESSAY
{essay}

## GRADING INSTRUCTIONS
Evaluate against the band descriptors provided in the system prompt. For each
criterion, cite exact words/sentences from the essay and name the descriptor
feature that fixes the band. Then compute the overall band using the official
rounding rule."""

    content: list[dict] = [{"type": "text", "text": user_text}]
    return content


def build_user_prompt_with_image(
    task: str,
    prompt_text: str,
    word_minimum: int,
    essay: str,
    feedback_language: str = "English",
    pdf_path: str | None = None,
) -> list[dict]:
    """Build a multimodal prompt that includes the PDF as a base64 image.

    Falls back to text-only if the PDF cannot be converted.

    For Task 1, the PDF image is REQUIRED — an exception is raised if
    it cannot be attached.
    """
    content = build_user_prompt(task, prompt_text, word_minimum, essay, feedback_language)

    is_task1 = task == "task1"

    if pdf_path:
        b64_url = _pdf_page_to_base64_png(pdf_path, page=0)
        if b64_url:
            # Insert the image before the text
            content.insert(0, {
                "type": "image_url",
                "image_url": {"url": b64_url, "detail": "high"},
            })
            return content
        elif is_task1:
            raise ValueError(
                "Task 1 requires a PDF image of the chart/graph/diagram for the AI to grade accurately. "
                f"The PDF file could not be converted to an image: {pdf_path}"
            )

    # No image available
    if is_task1:
        raise ValueError(
            "Task 1 requires a PDF image of the chart/graph/diagram for the AI to grade accurately. "
            "No PDF file was found for this task. Please ensure the task PDF exists."
        )

    return content


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def parse_grader_response(raw: str) -> dict:
    """Parse the model's JSON response with multi-level fallback handling.

    Strategy:
    1. Direct JSON parse — ideal case
    2. Extract JSON from markdown code fences (```json ... ```)
    3. Regex extract first { to last } block
    4. Raise ValueError with context
    """
    # Attempt 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: markdown code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Attempt 3: regex extract first { to last }
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Failed
    raise ValueError(
        "The AI model returned a response that could not be parsed as JSON. "
        "This can happen with smaller models. Please try again.\n\n"
        f"Raw response (first 500 chars): {raw[:500]}"
    )


# ---------------------------------------------------------------------------
# Main grading function
# ---------------------------------------------------------------------------

def grade_essay(
    task: str,
    prompt: str,
    word_minimum: int,
    essay: str,
    pdf_path: str | None = None,
    feedback_language: str | None = None,
) -> dict:
    """Send the essay to Poe for grading and return the parsed result.

    Args:
        task: ``"task1"`` or ``"task2"``
        prompt: The writing task prompt/question text (from structured_final
                or a fallback).
        word_minimum: Expected minimum word count (150 or 250).
        essay: The user's submitted essay.
        pdf_path: Optional path to the task PDF, which will be converted to
                  an image and attached for vision-capable models.
                  For Task 1, a PDF image is REQUIRED.
        feedback_language: Language for examiner feedback (e.g. "English",
                           "Traditional Chinese"). Auto-detected from essay
                           if not provided.

    Returns:
        Parsed grading result dict.

    Raises:
        RuntimeError: If POE_API_KEY is not set.
        ValueError: If the AI response cannot be parsed, or if Task 1 is
                    submitted without a usable PDF.
    """
    client = get_client()
    model = settings.POE_MODEL

    # Auto-detect feedback language if not explicitly provided
    if feedback_language is None:
        feedback_language = detect_essay_language(essay)

    messages: list[dict] = [
        {"role": "system", "content": _build_system_prompt()},
    ]

    user_content = build_user_prompt_with_image(
        task=task,
        prompt_text=prompt,
        word_minimum=word_minimum,
        essay=essay,
        feedback_language=feedback_language,
        pdf_path=pdf_path,
    )

    messages.append({"role": "user", "content": user_content})

    # Higher temperature for more nuanced grading; still low enough for consistency
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=3000,
    )

    raw = response.choices[0].message.content or ""
    return parse_grader_response(raw)
