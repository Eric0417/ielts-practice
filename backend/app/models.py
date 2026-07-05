"""
ORM models for the IELTS practice platform.

Three tables:
- users: accounts (email, hashed password, admin flag)
- questions: content cache (id from meta.json, type, title, payload as JSONB)
- attempts: user submission records (score, detail JSONB)
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base

# JSONB on PostgreSQL, JSON on SQLite — both mapped from the same Column type.
# Use `.with_variant()` so the correct type is selected per dialect.
PayloadJSON = JSONB().with_variant(JSON(), "sqlite")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(6), nullable=True)
    verification_code_expires = Column(DateTime(timezone=True), nullable=True)
    reset_token = Column(String(6), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    attempts = relationship("Attempt", back_populates="user", cascade="all, delete-orphan")


class Question(Base):
    """Stores content meta.json synced from the filesystem on startup.

    The full meta.json is stored in `payload` as JSONB so the schema
    is flexible — new fields in meta.json don't require migrations.
    """
    __tablename__ = "questions"

    id = Column(String(255), primary_key=True)  # from meta.json "id" field
    type = Column(String(50), nullable=False, index=True)   # reading / listening / writing
    title = Column(String(500), nullable=False)
    payload = Column(PayloadJSON, nullable=False)   # the full meta.json content
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Attempt(Base):
    """Records each user submission.

    For reading/listening: score is raw correct count, max_score is total questions.
    For writing: score is AI band score, max_score is 9.0.
    ``detail`` stores per-question results (objective) or full AI feedback JSON (writing).

    ``question_id`` stores the test identifier (e.g. ``_flat_/test001/reading/passage1``)
    and no longer has a FK to ``questions`` because the v2 PDF-based content system
    does not populate that table.
    """
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)   # reading / listening / writing
    score = Column(Float, nullable=False, default=0.0)
    max_score = Column(Float, nullable=False, default=0.0)
    detail = Column(PayloadJSON, nullable=True)       # per-question results or AI feedback
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="attempts")
