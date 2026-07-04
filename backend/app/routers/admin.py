"""
Admin router — GET users and GET all attempts (admin-only).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Attempt
from app.schemas import UserResponse, AdminAttemptResponse
from app.routers.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
def list_all_users(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Return all registered users. Admin only."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.get("/attempts", response_model=List[AdminAttemptResponse])
def list_all_attempts(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Return all attempts across all users, including the user's email.
    Admin only."""
    attempts = (
        db.query(Attempt)
        .join(User, Attempt.user_id == User.id)
        .order_by(Attempt.created_at.desc())
        .all()
    )

    result = []
    for a in attempts:
        result.append(AdminAttemptResponse(
            id=a.id,
            question_id=a.question_id,
            type=a.type,
            score=a.score,
            max_score=a.max_score,
            detail=a.detail,
            created_at=a.created_at,
            user_email=a.user.email if a.user else "N/A",
        ))
    return result
