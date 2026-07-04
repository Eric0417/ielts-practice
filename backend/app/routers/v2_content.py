"""
V2 Content Router — new PDF-driven API for book/test listing and test detail.

Replaces the old meta.json-driven questions.py router. All content is
discovered from the filesystem; no database involved.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional

from app.schemas import (
    BooksResponse,
    BookTestsResponse,
    TestDetailResponse,
    SectionInfo,
    QuestionItem,
)
from app.services import content_scanner

router = APIRouter(prefix="/api/v2", tags=["v2-content"])


@router.get("/books", response_model=BooksResponse)
def get_books():
    """List all available Cambridge books with skill availability flags."""
    books = content_scanner.list_books()
    return BooksResponse(books=books)


@router.get("/books/{book}/tests", response_model=BookTestsResponse)
def get_book_tests(
    book: str,
    type: str = Query(..., description="Skill type: reading, listening, or writing"),
):
    """List available tests for a given book and skill type."""
    if type not in ("reading", "listening", "writing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown type: {type}. Valid types: reading, listening, writing",
        )

    tests = content_scanner.list_book_tests(book, type)
    return BookTestsResponse(book=book, type=type, tests=tests)


@router.get("/tests/{book}/{test}/{test_type}", response_model=TestDetailResponse)
def get_test_detail(
    book: str,
    test: str,
    test_type: str,
):
    """Get full detail for a specific test: PDFs, audio, question types, etc.

    Question types are inferred from the answer key WITHOUT exposing correct
    answers.  The frontend uses this to render the answer form.
    """
    if test_type not in ("reading", "listening", "writing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown type: {test_type}. Valid types: reading, listening, writing",
        )

    detail = content_scanner.get_test_detail(book, test, test_type)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test not found: {book}/{test}/{test_type}",
        )

    # Convert sections dict to use SectionInfo/QuestionItem models
    if detail.get("sections"):
        converted_sections = {}
        for sec_name, sec_data in detail["sections"].items():
            questions = [QuestionItem(**q) for q in sec_data.get("questions", [])]
            converted_sections[sec_name] = SectionInfo(
                type=sec_data["type"],
                label=sec_data["label"],
                questions=questions,
            )
        detail["sections"] = converted_sections

    return TestDetailResponse(**detail)


@router.get("/tests/{book}/{test}/{test_type}/{passage}", response_model=TestDetailResponse)
def get_passage_detail(
    book: str,
    test: str,
    test_type: str,
    passage: str,
):
    """Get detail for a single passage/section within a test.

    Returns only the specified passage's PDF, questions, and metadata.
    Question IDs are bare (1, 2, ...) since each passage is self-contained.
    """
    if test_type not in ("reading", "listening", "writing"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown type: {test_type}. Valid types: reading, listening, writing",
        )

    detail = content_scanner.get_test_detail(book, test, test_type, passage=passage)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passage not found: {book}/{test}/{test_type}/{passage}",
        )

    # Convert sections dict to use SectionInfo/QuestionItem models
    if detail.get("sections"):
        converted_sections = {}
        for sec_name, sec_data in detail["sections"].items():
            questions = [QuestionItem(**q) for q in sec_data.get("questions", [])]
            converted_sections[sec_name] = SectionInfo(
                type=sec_data["type"],
                label=sec_data["label"],
                questions=questions,
            )
        detail["sections"] = converted_sections

    return TestDetailResponse(**detail)
