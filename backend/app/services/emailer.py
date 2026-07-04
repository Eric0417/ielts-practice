"""
Email sending utility using Resend.com API.

Resend free tier: 100 emails/day.
API key stored in RESEND_API_KEY environment variable.
Sender address configured via EMAIL_FROM env var (default: onboarding@resend.dev).
"""
from app.config import settings


def _get_resend():
    """Lazy-load resend module."""
    try:
        import resend
        return resend
    except ImportError:
        return None


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via Resend.

    Args:
        to: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email

    Returns:
        True if sent successfully, False otherwise.
    """
    resend = _get_resend()
    if resend is None:
        print("[email] resend package not installed. Run: pip install resend-python")
        print(f"[email] Would have sent to {to}: {subject}")
        return False

    api_key = settings.RESEND_API_KEY
    if not api_key:
        print("[email] RESEND_API_KEY not configured. Skipping email send.")
        print(f"[email] Would have sent to {to}: {subject}")
        return False

    try:
        resend.api_key = api_key
        params = {
            "from": settings.EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html_body,
        }
        resend.Emails.send(params)
        print(f"[email] Sent to {to}: {subject}")
        return True
    except Exception as exc:
        print(f"[email] Failed to send to {to}: {exc}")
        return False


def send_verification_email(to: str, code: str) -> bool:
    """Send email verification code."""
    subject = "IELTS Practice - Email Verification Code"
    html = f"""<div style="max-width:480px;margin:0 auto;padding:24px;font-family:sans-serif">
<h2 style="color:#15803d">IELTS Practice Platform</h2>
<p>Thank you for registering! Your verification code is:</p>
<div style="background:#f0fdf4;border:2px solid #16a34a;border-radius:12px;padding:20px;text-align:center;margin:24px 0">
  <span style="font-size:36px;font-weight:bold;color:#166534;letter-spacing:12px">{code}</span>
</div>
<p style="color:#6b7280;font-size:14px">This code expires in 30 minutes. If you didn't create this account, please ignore this email.</p>
</div>"""
    return send_email(to, subject, html)


def send_reset_email(to: str, token: str) -> bool:
    """Send password reset link."""
    subject = "IELTS Practice - Password Reset"
    # Construct reset URL — in production this would be your frontend URL
    reset_url = f"{settings.CORS_ORIGINS.split(',')[0].strip()}/login?token={token}"

    html = f"""<div style="max-width:480px;margin:0 auto;padding:24px;font-family:sans-serif">
<h2 style="color:#15803d">IELTS Practice Platform</h2>
<p>You requested a password reset. Click the button below to reset your password:</p>
<div style="text-align:center;margin:24px 0">
  <a href="{reset_url}" style="display:inline-block;background:#16a34a;color:white;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:bold">Reset Password</a>
</div>
<p style="color:#6b7280;font-size:14px">Or copy this link:<br/><code>{reset_url}</code></p>
<p style="color:#6b7280;font-size:14px">This link expires in 30 minutes. If you didn't request this, please ignore this email.</p>
</div>"""
    return send_email(to, subject, html)