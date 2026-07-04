"""
Pydantic schemas for request/response validation.

Every API endpoint uses these schemas. Naming convention:
- <Name>Request: what the client sends
- <Name>Response: what the server returns
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


# ========== Auth ==========

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    verification_code: Optional[str] = None  # dev mode only — remove in production


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=6, max_length=128)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


# ========== Questions ==========

class QuestionListItem(BaseModel):
    id: str
    type: str
    title: str


class ListeningTestItem(BaseModel):
    id: str
    type: str
    title: str
    section_count: int


class QuestionDetail(BaseModel):
    """Returned to the frontend — answers are STRIPPED for reading/listening."""
    id: str
    type: str
    title: str
    payload: Dict[str, Any]   # the meta.json content


# ========== Grading ==========

class ObjectiveAnswer(BaseModel):
    question_id: str
    answers: Dict[str, Any]   # {"q1": "B", "q2": ["B","D"], "q3": "physical activity"}


class ObjectiveQuestionResult(BaseModel):
    question_id: str
    user_answer: str
    correct_answer: str
    is_correct: bool


class ObjectiveGradeResponse(BaseModel):
    score: float
    max_score: float
    results: List[ObjectiveQuestionResult]


class WritingGradeRequest(BaseModel):
    question_id: str
    essay: str = Field(min_length=1)


class CriteriaDetail(BaseModel):
    band: float
    comment: str


class CorrectedExample(BaseModel):
    original: str
    suggestion: str
    explanation: Optional[str] = None


class WritingGradeResponse(BaseModel):
    overall_band: float
    criteria: Dict[str, CriteriaDetail]
    strengths: List[str]
    improvements: List[str]
    corrected_examples: List[CorrectedExample]


# ========== Attempts ==========

class AttemptResponse(BaseModel):
    id: int
    question_id: str
    type: str
    score: float
    max_score: float
    detail: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Admin ==========

class AdminAttemptResponse(AttemptResponse):
    user_email: str


# ========== V2 Content API ==========

class BookItem(BaseModel):
    id: str          # "cambridge04"
    label: str       # "Cambridge 4"
    has_reading: bool
    has_listening: bool
    has_writing: bool


class BooksResponse(BaseModel):
    books: List[BookItem]


class TestItem(BaseModel):
    test: str                              # "test1"
    passages: Optional[List[str]] = None   # for reading
    sections: Optional[List[str]] = None   # for listening
    tasks: Optional[List[str]] = None      # for writing
    has_answers: bool


class BookTestsResponse(BaseModel):
    book: str
    type: str
    tests: List[TestItem]


class QuestionItem(BaseModel):
    """A single question in a section — UI info only, no answer exposed."""
    q: str                                    # question number e.g. "1", "15&16"
    ui: str                                   # "text" | "radio" | "tfng" | "paired" | "checkbox" | "dropdown"
    choices: Optional[List[str]] = None       # for radio / tfng / checkbox / dropdown
    type: Optional[str] = None                # original question type e.g. "multiple-choice"
    meta: Optional[dict] = None               # extra metadata e.g. {"min": 2, "max": 3} for checkbox


class SectionInfo(BaseModel):
    """One section/passage within a test."""
    type: str                                 # e.g. "note-completion", "multiple-choice"
    label: str                                # e.g. "Note Completion"
    questions: List[QuestionItem]


class TestDetailResponse(BaseModel):
    book: str
    test: str
    type: str
    label: str
    pdfs: Dict[str, str]
    audio: Optional[Dict[str, str]] = None
    sections: Optional[Dict[str, SectionInfo]] = None   # keyed by passage1/section1 etc.
    total_questions: Optional[int] = None
    has_answers: bool
    writing_prompts: Optional[Dict[str, str]] = None
    word_limits: Optional[Dict[str, int]] = None


class V2ObjectiveAnswer(BaseModel):
    book: str
    test: str
    type: str                                # "reading" | "listening"
    answers: Dict[str, Any]


class V2PassageAnswer(BaseModel):
    book: str
    test: str
    type: str                                # "reading" | "listening"
    passage: str                             # "passage2" or "section3"
    answers: Dict[str, Any]


class V2WritingGradeRequest(BaseModel):
    book: str
    test: str
    task: str                                # "task1" | "task2"
    essay: str = Field(min_length=1)
