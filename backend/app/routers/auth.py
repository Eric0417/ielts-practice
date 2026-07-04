"""
Auth router — POST register, POST login, GET me,
POST change-password, POST forgot-password, POST reset-password.

Authentication dependency pattern:
    current_user: User = Depends(get_current_user)

The dependency reads the Authorization: Bearer <token> header, validates the JWT,
and returns the User ORM object. Raises 401 if the token is missing/invalid.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserResponse,
    RegisterResponse,
    ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.auth import (
    hash_password, verify_password, create_access_token,
    decode_access_token, generate_reset_token,
    generate_verification_code,
)
from app.services.emailer import send_verification_email, send_reset_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: validate Bearer token and return the authenticated User.

    Raises 401 if the header is missing, malformed, or the token is invalid/expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    token = authorization[len("Bearer "):]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency: require that the authenticated user is an admin.

    Use this for admin-only endpoints. Raises 403 if the user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account.

    Email must be unique. Password is bcrypt-hashed before storage.
    The user is NOT verified yet — they must verify their email first.
    A 6-digit verification code is returned (dev mode).
    """
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    code = generate_verification_code()
    print(f"\n[DEV] Verification code for {body.email}: {code}\n")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        is_admin=False,
        is_verified=False,
        verification_code=code,
        verification_code_expires=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})

    # Try to send real email. Fallback to console print if not configured.
    email_sent = send_verification_email(to=body.email, code=code)

    return RegisterResponse(
        access_token=token,
        verification_code=code if not email_sent else None,  # Only show code if email not sent
    )


@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email with a 6-digit code sent during registration."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.is_verified:
        return {"message": "Email already verified."}

    if user.verification_code != body.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    if user.verification_code_expires is None or user.verification_code_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one.",
        )

    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    db.commit()

    return {"message": "Email verified successfully."}


@router.post("/resend-verification")
def resend_verification(email: str, db: Session = Depends(get_db)):
    """Resend verification code for a given email."""
    # Accept email query param
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.is_verified:
        return {"message": "Email already verified."}

    code = generate_verification_code()
    user.verification_code = code
    user.verification_code_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()

    email_sent = send_verification_email(to=email, code=code)
    return {
        "message": "Verification code sent. Check your email.",
        "verification_code": code if not email_sent else None,
    }


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email/password and return a JWT token.

    Only verified users can log in.
    """
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in. Check your email for the verification code.",
        )

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password.

    Requires the current password for verification.
    The new password must be at least 6 characters.
    """
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    current_user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Send a password reset email.

    Generates a reset token and returns it. In production, this would send
    an email. For local development, the token is returned directly so the
    user can reset their password via the /reset-password endpoint.

    NOTE: In a production deployment, replace the token return with an
    email-sending service (e.g., SendGrid, Resend, AWS SES).
    """
    user = db.query(User).filter(User.email == body.email).first()

    # Always return success even if email not found (prevents email enumeration)
    if not user:
        return {"message": "If the email exists, a reset link has been sent."}

    # Generate reset token (valid for 30 minutes)
    reset_token = generate_reset_token()
    user.reset_token = reset_token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()

    email_sent = send_reset_email(to=body.email, token=reset_token)
    return {
        "message": "If the email exists, a reset link has been sent.",
        "reset_token": reset_token if not email_sent else None,
    }


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Reset password using a reset token.

    The token must be valid and not expired (30 minute window).
    """
    user = db.query(User).filter(User.reset_token == body.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    # Check expiration
    if user.reset_token_expires is None or user.reset_token_expires.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        # Clean up expired token
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one.",
        )

    # Update password and clear reset token
    user.password_hash = hash_password(body.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password has been reset successfully. You can now log in."}
