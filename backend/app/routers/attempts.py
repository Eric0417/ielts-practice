"""
Attempts router — GET user's own attempt history.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Attempt
from app.schemas import AttemptResponse
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/attempts", tags=["attempts"])


@router.get("", response_model=List[AttemptResponse])
def list_my_attempts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all attempts for the currently authenticated user,
    ordered by most recent first."""
    attempts = (
        db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.created_at.desc())
        .all()
    )
    return attempts
