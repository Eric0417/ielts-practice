"""
Questions router — list questions by type, get question detail,
and group listening sections into complete tests.

IMPORTANT: For reading/listening questions, the GET /{id} endpoint
STRIPS answer fields from the payload before returning, so users
cannot see correct answers by inspecting network traffic.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import copy
from collections import defaultdict

from app.database import get_db
from app.models import Question
from app.schemas import QuestionListItem, QuestionDetail

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.get("", response_model=List[QuestionListItem])
def list_questions(
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List all questions, optionally filtered by type.

    For 'listening' type, returns grouped tests (one entry per complete test,
    not one per section). The ID is the test base name (e.g. "Cambridge 15 Test 1").
    """
    if type and type not in ("reading", "listening", "writing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown question type: {type}. Valid types: reading, listening, writing",
        )

    if type == "listening":
        # Group listening sections into complete tests
        sections = (
            db.query(Question)
            .filter(Question.type == "listening")
            .order_by(Question.id)
            .all()
        )

        # Group by test name (everything before " - Section")
        tests: dict[str, list[Question]] = defaultdict(list)
        for s in sections:
            title = s.title
            test_name = title.rsplit(" - Section", 1)[0] if " - Section" in title else title
            tests[test_name].append(s)

        # Return one entry per test — use the first section's ID as the list ID
        result = []
        for test_name, secs in sorted(tests.items()):
            result.append(QuestionListItem(
                id=test_name,
                type="listening",
                title=test_name,
            ))
        return result

    query = db.query(Question)
    if type:
        query = query.filter(Question.type == type)

    questions = query.order_by(Question.type, Question.title).all()
    return questions


@router.get("/listening-test/{test_name:path}", response_model=QuestionDetail)
def get_listening_test(test_name: str, db: Session = Depends(get_db)):
    """Get a complete listening test by name.

    Returns all sections of a test merged into one response.
    All section questions are combined, answers are stripped.
    """
    all_sections = (
        db.query(Question)
        .filter(Question.type == "listening")
        .order_by(Question.id)
        .all()
    )

    # Find matching sections
    matched = [s for s in all_sections if s.title.startswith(test_name)]
    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listening test not found: {test_name}",
        )

    # Merge all sections' questions
    all_questions = []
    audio = None
    for sec in sorted(matched, key=lambda s: s.id):
        payload = copy.deepcopy(sec.payload)
        for q in payload.get("questions", []):
            q.pop("answer", None)  # strip answers
        all_questions.extend(payload.get("questions", []))
        # Use the first section's audio
        if audio is None:
            audio = payload.get("audio")

    # Use first section's ID for audio path
    first_section = sorted(matched, key=lambda s: s.id)[0]

    merged_payload = {
        "id": test_name,
        "type": "listening",
        "title": test_name,
        "audio": audio,
        "pdf": None,
        "questions": all_questions,
        "sections": [s.title for s in matched],
        "audio_dir": first_section.id,  # e.g. "listening-section-0001"
    }

    return QuestionDetail(
        id=test_name,
        type="listening",
        title=test_name,
        payload=merged_payload,
    )


@router.get("/{question_id:path}", response_model=QuestionDetail)
def get_question(question_id: str, db: Session = Depends(get_db)):
    """Get a single question by ID.

    For reading and listening types, the `answer` field is stripped
    from each question in the payload before returning, so users
    cannot see correct answers in the browser's network tab.
    """
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question not found: {question_id}",
        )

    # Strip answers for reading/listening to prevent cheating
    safe_payload = copy.deepcopy(question.payload)
    if question.type in ("reading", "listening"):
        for q in safe_payload.get("questions", []):
            q.pop("answer", None)

    return QuestionDetail(
        id=question.id,
        type=question.type,
        title=question.title,
        payload=safe_payload,
    )
