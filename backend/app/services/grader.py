"""
IELTS Writing grader — sends the user's essay to the Poe API (OpenAI-compatible)
and parses the structured JSON response.

For Task 1: a PDF image is REQUIRED — the model must see the chart/graph/diagram.
For Task 2: the question text is used directly (no image needed), saving tokens.
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
    to produce scores that are accurate, consistent, and faithfully aligned with
    what a trained IELTS examiner would award.
    """
    return """You are an experienced IELTS Writing examiner trained on the official public
band descriptors. Your goal is to produce band scores that are accurate,
consistent, and faithfully aligned with what a trained IELTS examiner would
award.

## YOUR TASK
Grade the student's essay strictly against the official IELTS Writing band
descriptors (public version) for the specified task type (Task 1 or Task 2).
Always justify each band by referring to descriptor-level features, not vague
impressions.

## THE FOUR CRITERIA (each 0–9, in 0.5 increments)

### 1. Task Achievement (Task 1) / Task Response (Task 2)
Use ONLY the descriptor set that matches the task type given in the user prompt.

TASK 1 — Task Achievement anchors:
- Band 4: Attempts the task but does not cover all key features; format may be
  inappropriate; details are mostly mechanical; no clear overview.
- Band 5: Recounts detail mechanically; no clear overview; may focus on detail
  with no clear selection of key features; may have inaccuracies in data.
- Band 6: Presents an overview with information appropriately selected; adequately
  highlights key features but details may be irrelevant, inappropriate or inaccurate.
- Band 7: Clear overview of main trends/differences/stages; clearly presents and
  highlights key features but could be more fully extended.
- Band 8: Covers requirements sufficiently; skilfully selects and highlights key
  features; clear, well-organised overview.
- Band 9: Fully satisfies all task requirements; clear, comprehensive overview;
  all key features are fully and appropriately developed.

TASK 1 chart-type awareness:
- Trend graphs (line/bar): expect overview of overall direction + key features
  (peaks, troughs, crossovers, periods of stability).
- Comparative charts (pie/table/bar): expect overview of ranking/grouping; not
  just listing each category one by one.
- Maps: expect description of changes over time (new, removed, expanded, replaced)
  with clear spatial organisation.
- Process diagrams: expect sequential description with appropriate sequencing
  language; overview = number of stages + beginning/end points.

TASK 2 — Task Response anchors:
- Band 4: Responds to the task only minimally; position is unclear; few ideas,
  largely undeveloped; may repeat prompt or rely on memorised material.
- Band 5: Addresses the task only partially; position expressed but not always
  clear; some main ideas but underdeveloped/unclear; may over-generalise.
- Band 6: Addresses all parts of the task, though some more than others; relevant
  position presented though conclusions may be unclear/repetitive; relevant main
  ideas but some may be inadequately developed.
- Band 7: Addresses all parts; clear position throughout; extends and supports main
  ideas, though there may be a tendency to over-generalise or lack focus.
- Band 8: Sufficiently addresses all parts; well-developed response with relevant,
  extended and supported ideas; clear position throughout.
- Band 9: Fully addresses all parts of the task with a clear, fully developed
  position; ideas are relevant, extended, and well-supported throughout.

### 2. Coherence & Cohesion
- Band 4: Information and ideas are arranged coherently at a basic level; limited
  range of cohesive devices; may be repetitive; paragraphing may be absent or
  confusing.
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
- Band 9: Uses cohesion in such a way that it attracts no attention; skilfully
  manages paragraphing; ideas flow naturally with sophisticated referencing.

### 3. Lexical Resource
- Band 4: Basic vocabulary adequate for simple information; significant errors in
  word choice/spelling cause strain for the reader.
- Band 5: Limited but minimally adequate range; noticeable errors in spelling/word
  formation that may cause some difficulty.
- Band 6: Adequate range for the task; attempts less common vocabulary with some
  inaccuracy; some errors in spelling/word formation but they don't impede
  communication.
- Band 7: Sufficient range for flexibility and precision; some less common/idiomatic
  items with awareness of style/collocation; occasional errors.
- Band 8: Wide range used fluently and flexibly; skilful use of uncommon items;
  occasional inaccuracies in word choice/collocation only.
- Band 9: Full flexibility and precision in word choice; natural and sophisticated
  control of lexical features; rare minor errors ("slips") only.

### 4. Grammatical Range & Accuracy
- Band 4: Very limited range of structures; subordinate clauses are rare; frequent
  errors that cause difficulty for the reader.
- Band 5: Limited range of structures; complex sentences less accurate than simple
  ones; frequent errors causing some difficulty for the reader.
- Band 6: Mix of simple and complex forms; some errors in grammar/punctuation but
  they rarely reduce communication.
- Band 7: Variety of complex structures; frequent error-free sentences; good control
  though some errors remain.
- Band 8: Wide range of structures; majority error-free; occasional non-systematic
  errors/inappropriacies.
- Band 9: Wide range of structures with full flexibility and accuracy; rare minor
  errors only; meaning is precise and nuanced.

## CALIBRATION EXAMPLE

This is roughly Band 6.0 for Task 2. Use it as a calibration anchor:

Essay: "In modern society, technology is very important for education. Many schools
now use computers and tablets for teaching. I agree that technology has many benefits.
First, students can find information easily on internet. They don't need to go library
and search many books. Second, technology make learning more interesting. Students can
watch videos and play educational games. However, there are some disadvantages. Too much
screen time is not good for eyes. Also some students play games instead of study. In
conclusion, technology is good for education but we must use it carefully. Schools
should balance technology and traditional methods."

Expected scores for this sample: TR 6.0 (addresses both sides but ideas are thin
and generalised; conclusion is present but underdeveloped), CC 6.0 (clear progression
but mechanical cohesion — "First"/"Second"/"However"/"In conclusion"; paragraphing
absent), LR 5.5 (adequate for simple ideas but limited range; some errors: "make"
for "makes", "on internet" missing article, "study" for "studying"), GR 6.0 (mix of
simple and complex; some error-free sentences but also errors in subject-verb
agreement and articles).

## LENGTH GUIDANCE (do NOT apply a fixed penalty)
Do NOT mechanically subtract a fixed band for under-length essays. Instead, judge
the actual impact: under-length essays usually cannot fully develop/highlight key
features, which naturally limits the Task Achievement/Response band. State clearly
in the comment when under-length has limited development, and reflect it in the band
proportionally to how far below the minimum the essay is.

## OVERALL BAND CALCULATION
1. Compute the arithmetic mean of the four criterion bands.
2. Round to the nearest half band using the official IELTS rounding rule:
   - Mean ends in .25 → round UP to the next .5  (e.g., 6.25 → 6.5)
   - Mean ends in .75 → round UP to the next whole  (e.g., 6.75 → 7.0)
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
   NEVER invent or paraphrase the original. If you cannot recall a sentence
   verbatim, quote the closest identifiable fragment (e.g., "...the government
   should to invest...") rather than fabricating. If fewer than 3 genuinely
   correctable sentences exist, provide as many as genuinely exist.
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
) -> str:
    """Build the user prompt text for the grading request.

    Returns a plain text string. For Task 1, an image is appended separately
    via build_user_prompt_with_image().
    """
    task_label = "Task 1" if task == "task1" else "Task 2"
    task_desc = (
        "Task 1 (Academic): Describe, summarise or explain information from a graph, "
        "table, chart or diagram. Minimum 150 words. Key features: overview, data "
        "description, comparisons, no personal opinion."
        if task == "task1"
        else "Task 2 (Academic/General): Write an essay in response to a point of view, "
        "argument or problem. Minimum 250 words. Key features: clear position, developed "
        "ideas, logical argument, conclusion."
    )

    actual_words = len(essay.split())
    under_length = actual_words < word_minimum
    under_length_note = (
        "\n\nNOTE: This essay is below the minimum. Judge the impact on development "
        "per the length guidance; do not apply a fixed penalty."
        if under_length
        else ""
    )

    return f"""Please grade this IELTS {task_label} essay.

## TASK TYPE
{task_desc}

## FEEDBACK LANGUAGE
Write all feedback in: {feedback_language}

## WORD COUNT
Minimum required: {word_minimum} words
Student's word count: {actual_words} words{under_length_note}

## QUESTION PROMPT
(Note: the question text below may contain minor formatting artifacts from
PDF extraction. Focus on the semantic content, not formatting issues.)

{prompt_text if prompt_text else 'No question text available.'}

## STUDENT'S ESSAY
{essay}"""


def build_user_prompt_with_image(
    task: str,
    prompt_text: str,
    word_minimum: int,
    essay: str,
    feedback_language: str = "English",
    pdf_path: str | None = None,
) -> list[dict]:
    """Build a multimodal prompt.

    For Task 1: the PDF image is REQUIRED (the model must see the chart/graph).
    For Task 2: uses text-only by default (saves tokens); image is skipped
    even if a PDF path is provided.

    Returns a multimodal content list (text + optional image for Task 1).
    """
    user_text = build_user_prompt(task, prompt_text, word_minimum, essay, feedback_language)
    content: list[dict] = [{"type": "text", "text": user_text}]
    is_task1 = task == "task1"

    if not is_task1:
        # Task 2: text-only, no image needed
        return content

    # Task 1: PDF image is REQUIRED
    if pdf_path:
        b64_url = _pdf_page_to_base64_png(pdf_path, page=0)
        if b64_url:
            content.insert(0, {
                "type": "image_url",
                "image_url": {"url": b64_url, "detail": "high"},
            })
            return content
        else:
            raise ValueError(
                "Task 1 requires a PDF image of the chart/graph/diagram for the AI to grade accurately. "
                f"The PDF file could not be converted to an image: {pdf_path}"
            )

    raise ValueError(
        "Task 1 requires a PDF image of the chart/graph/diagram for the AI to grade accurately. "
        "No PDF file was found for this task. Please ensure the task PDF exists."
    )


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
        pdf_path: Optional path to the task PDF. For Task 1, a PDF image is
                  REQUIRED — the model must see the chart/graph. For Task 2,
                  the image is skipped (text-only saves tokens).
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
