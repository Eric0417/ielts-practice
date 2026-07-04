"""
Grading router — POST objective (reading/listening) and POST writing (AI).

All grading endpoints require authentication. Results are written to the
attempts table for the user's history.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from app.database import get_db
from app.models import User, Question, Attempt
from app.schemas import (
    ObjectiveAnswer,
    ObjectiveGradeResponse,
    ObjectiveQuestionResult,
    WritingGradeRequest,
    WritingGradeResponse,
    CriteriaDetail,
    CorrectedExample,
    V2ObjectiveAnswer,
    V2PassageAnswer,
    V2WritingGradeRequest,
)
from app.routers.auth import get_current_user
from app.services.grader import grade_essay, detect_essay_language
from app.services.content_scanner import load_answer_key, get_writing_prompt, _resolve_pdf_path
from app.services.answer_normalizer import answers_match, grade_answers

router = APIRouter(prefix="/api/grade", tags=["grading"])


def compare_answers(user_answer: Any, correct_answer: Any) -> bool:
    """Compare a user's answer with the correct answer.

    Handles multiple formats:
    - String: case-insensitive trimmed comparison
    - List: compare as sets (for multi-select questions)
    - None: always false
    """
    if user_answer is None or correct_answer is None:
        return False

    # Normalize correct answer
    if isinstance(correct_answer, list):
        correct_set = {str(x).strip().upper() for x in correct_answer}
    else:
        correct_set = {str(correct_answer).strip().upper()}

    # Normalize user answer
    if isinstance(user_answer, list):
        user_set = {str(x).strip().upper() for x in user_answer}
    else:
        user_set = {str(user_answer).strip().upper()}

    return user_set == correct_set


def format_answer_for_display(answer: Any) -> str:
    """Format an answer for display in the response."""
    if answer is None:
        return ""
    if isinstance(answer, list):
        return ", ".join(str(x) for x in answer)
    return str(answer)


@router.post("/objective", response_model=ObjectiveGradeResponse)
def grade_objective(
    body: ObjectiveAnswer,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grade reading or listening answers by comparing against the stored answer key.

    Supports all question types: MC (radio), fill-in-blank (text input),
    TRUE/FALSE/NOT GIVEN, YES/NO/NOT GIVEN, multi-select (checkbox),
    heading matching, table completion, map labeling.

    For listening tests (grouped by test name), all sections of the test
    are merged and graded together.
    """
    question = db.query(Question).filter(Question.id == body.question_id).first()

    if not question:
        # Check if it's a listening test name (e.g. "Cambridge 15 Test 1")
        all_listening = (
            db.query(Question)
            .filter(Question.type == "listening")
            .order_by(Question.id)
            .all()
        )
        matched = [s for s in all_listening if s.title.startswith(body.question_id)]
        if matched:
            # Merge all sections for grading
            merged_answers = {}
            for sec in matched:
                for q in sec.payload.get("questions", []):
                    merged_answers[q["id"]] = q.get("answer", "")

            if merged_answers:
                return _grade_with_answer_key(
                    body, current_user, db,
                    question_type="listening",
                    question_id=body.question_id,
                    answer_key=merged_answers,
                )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question not found: {body.question_id}",
        )

    if question.type not in ("reading", "listening"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Objective grading is only for reading/listening, not {question.type}",
        )

    questions_meta = question.payload.get("questions", [])
    if not questions_meta:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This question has no answer key.",
        )

    answer_key = {}
    for q in questions_meta:
        answer_key[q["id"]] = q.get("answer", "")

    return _grade_with_answer_key(
        body, current_user, db,
        question_type=question.type,
        question_id=body.question_id,
        answer_key=answer_key,
    )


def _grade_with_answer_key(
    body: ObjectiveAnswer,
    current_user: User,
    db: Session,
    question_type: str,
    question_id: str,
    answer_key: dict,
) -> ObjectiveGradeResponse:
    """Core grading logic shared between single questions and grouped tests."""
    results = []
    correct_count = 0
    total_count = len(answer_key)

    for qid, correct in answer_key.items():
        user_answer = body.answers.get(qid, "")
        is_correct = compare_answers(user_answer, correct)
        if is_correct:
            correct_count += 1

        results.append(ObjectiveQuestionResult(
            question_id=qid,
            user_answer=format_answer_for_display(user_answer),
            correct_answer=format_answer_for_display(correct),
            is_correct=is_correct,
        ))

    attempt = Attempt(
        user_id=current_user.id,
        question_id=question_id,
        type=question_type,
        score=float(correct_count),
        max_score=float(total_count),
        detail={
            "results": [r.model_dump() for r in results],
        },
    )
    db.add(attempt)
    db.commit()

    return ObjectiveGradeResponse(
        score=float(correct_count),
        max_score=float(total_count),
        results=results,
    )


# =========================================================================
# V2 Grading endpoints  (PDF-based, filesystem answer keys)
# =========================================================================


@router.post("/v2/objective", response_model=ObjectiveGradeResponse)
def grade_objective_v2(
    body: V2ObjectiveAnswer,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grade reading or listening answers using filesystem answer keys.

    Loads answer key from ``content/structured_final/{book}/{test}/answers.json``,
    compares against user-submitted answers, and records the attempt.
    """
    if body.type not in ("reading", "listening"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Objective grading is only for reading/listening, not {body.type}",
        )

    answer_key = load_answer_key(body.book, body.test, body.type)
    if answer_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No answer key found for {body.book}/{body.test}/{body.type}",
        )

    question_id = f"{body.book}/{body.test}/{body.type}"

    correct_count, total_count, graded = grade_answers(body.answers, answer_key)

    results = [
        ObjectiveQuestionResult(
            question_id=r["question_id"],
            user_answer=r["user_answer"],
            correct_answer=r["correct_answer"],
            is_correct=r["is_correct"],
        )
        for r in graded
    ]

    attempt = Attempt(
        user_id=current_user.id,
        question_id=question_id,
        type=body.type,
        score=float(correct_count),
        max_score=float(total_count),
        detail={
            "results": [r.model_dump() for r in results],
            "band_score": _ielts_band_score(correct_count, total_count),
        },
    )
    db.add(attempt)
    db.commit()

    return ObjectiveGradeResponse(
        score=float(correct_count),
        max_score=float(total_count),
        results=results,
    )


@router.post("/v2/passage", response_model=ObjectiveGradeResponse)
def grade_passage(
    body: V2PassageAnswer,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grade a single passage/section's answers.

    Loads only the specified passage's answer key (e.g. ``passage2_answers.json``),
    compares against user-submitted answers, and records the attempt.

    This is the primary grading endpoint for the PDF_new-based frontend —
    each passage is submitted independently.
    """
    if body.type not in ("reading", "listening"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Objective grading is only for reading/listening, not {body.type}",
        )

    answer_key = load_answer_key(body.book, body.test, body.type, passage=body.passage)
    if answer_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No answer key found for {body.book}/{body.test}/{body.type}/{body.passage}",
        )

    question_id = f"{body.book}/{body.test}/{body.type}/{body.passage}"

    correct_count, total_count, graded = grade_answers(body.answers, answer_key)

    results = [
        ObjectiveQuestionResult(
            question_id=r["question_id"],
            user_answer=r["user_answer"],
            correct_answer=r["correct_answer"],
            is_correct=r["is_correct"],
        )
        for r in graded
    ]

    attempt = Attempt(
        user_id=current_user.id,
        question_id=question_id,
        type=body.type,
        score=float(correct_count),
        max_score=float(total_count),
        detail={
            "results": [r.model_dump() for r in results],
            "passage": body.passage,
        },
    )
    db.add(attempt)
    db.commit()

    return ObjectiveGradeResponse(
        score=float(correct_count),
        max_score=float(total_count),
        results=results,
    )


@router.post("/v2/writing", response_model=WritingGradeResponse)
def grade_writing_v2(
    body: V2WritingGradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Grade a writing essay using AI (Poe/compatible API).

    Loads the writing prompt from structured_final if available, otherwise
    falls back to a generic prompt. Task 1 MUST have a PDF — the AI needs
    to see the chart/graph/diagram to grade accurately.
    Feedback language is auto-detected from the essay content.
    """
    if body.task not in ("task1", "task2"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task must be 'task1' or 'task2'",
        )

    word_minimum = 150 if body.task == "task1" else 250
    prompt = get_writing_prompt(body.book, body.test, body.task)
    pdf_path = _resolve_pdf_path(body.book, body.test, body.task)
    feedback_language = detect_essay_language(body.essay)

    try:
        result = grade_essay(
            task=body.task,
            prompt=prompt,
            word_minimum=word_minimum,
            essay=body.essay,
            pdf_path=pdf_path,
            feedback_language=feedback_language,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    # Record attempt
    question_id = f"{body.book}/{body.test}/writing/{body.task}"
    attempt = Attempt(
        user_id=current_user.id,
        question_id=question_id,
        type="writing",
        score=result["overall_band"],
        max_score=9.0,
        detail=result,
    )
    db.add(attempt)
    db.commit()

    # 將 dict 轉成對應 schema
    return WritingGradeResponse(
        overall_band=result["overall_band"],
        criteria={
            k: CriteriaDetail(**v)
            for k, v in result.get("criteria", {}).items()
        },
        strengths=result.get("strengths", []),
        improvements=result.get("improvements", []),
        corrected_examples=[
            CorrectedExample(**ex)
            for ex in result.get("corrected_examples", [])
        ],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ielts_band_score(raw: float, total: float) -> float:
    """Convert raw score to IELTS band score (Academic Reading/Listening).

    Standard conversion table (40 questions):
      39-40 → 9.0
      37-38 → 8.5
      35-36 → 8.0
      33-34 → 7.5
      30-32 → 7.0
      27-29 → 6.5
      23-26 → 6.0
      20-22 → 5.5
      16-19 → 5.0
      13-15 → 4.5
      10-12 → 4.0
      8-9   → 3.5
      6-7   → 3.0
      4-5   → 2.5
    """
    if total != 40:
        # Scale to 40 for non-standard total
        scaled = (raw / total) * 40
    else:
        scaled = raw

    if scaled >= 39: return 9.0
    if scaled >= 37: return 8.5
    if scaled >= 35: return 8.0
    if scaled >= 33: return 7.5
    if scaled >= 30: return 7.0
    if scaled >= 27: return 6.5
    if scaled >= 23: return 6.0
    if scaled >= 20: return 5.5
    if scaled >= 16: return 5.0
    if scaled >= 13: return 4.5
    if scaled >= 10: return 4.0
    if scaled >= 8:  return 3.5
    if scaled >= 6:  return 3.0
    if scaled >= 4:  return 2.5
    return 2.0

def _sort_key(s: str):
    """Sort question numbers naturally: '1', '2', '10', not '1', '10', '2'."""
    import re
    parts = re.split(r"(\d+)", s)
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)


def _format_user_answer(answer) -> str:
    """Format user answer for display in response."""
    if answer is None:
        return ""
    if isinstance(answer, list):
        return ", ".join(str(x) for x in answer)
    return str(answer)


def _format_correct_answer(answer) -> str:
    """Format correct answer for display in response."""
    if answer is None:
        return ""
    if isinstance(answer, list):
        return ", ".join(str(x) for x in answer)
    return str(answer)
