"""
Email sending utility.

Primary: Resend API (https://resend.com) — best deliverability to all email providers.
Fallback: Gmail SMTP — only works reliably for Gmail-to-Gmail internal delivery.

Configuration priority:
1. RESEND_API_KEY  → use Resend (recommended, delivers to any address)
2. GMAIL_APP_PASSWORD + EMAIL_FROM → use Gmail SMTP (fallback)
3. Neither configured → console print (dev mode)
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


def _send_via_resend(to: str, subject: str, html_body: str) -> bool:
    """Send email via Resend API. Best deliverability to all email providers."""
    try:
        import resend
    except ImportError:
        print("[email] resend package not installed. Falling back.")
        return False

    try:
        resend.api_key = settings.RESEND_API_KEY
        params = {
            "from": settings.EMAIL_FROM,
            "to": [to],
            "subject": subject,
            "html": html_body,
        }
        resend.Emails.send(params)
        print(f"[email:resend] Sent to {to}: {subject}")
        return True
    except Exception as exc:
        print(f"[email:resend] Failed to send to {to}: {exc}")
        return False


def _send_via_gmail(to: str, subject: str, html_body: str) -> bool:
    """Send email via Gmail SMTP. May have delivery issues to non-Gmail addresses."""
    app_password = settings.GMAIL_APP_PASSWORD
    from_addr = settings.EMAIL_FROM

    if not app_password or not from_addr:
        print(f"[email:gmail] GMAIL_APP_PASSWORD or EMAIL_FROM not configured. Skipping.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
            server.login(from_addr, app_password)
            server.sendmail(from_addr, to, msg.as_string())
        print(f"[email:gmail] Sent to {to}: {subject}")
        return True
    except Exception as exc:
        print(f"[email:gmail] Failed to send to {to}: {exc}")
        return False


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email. Tries Resend first, falls back to Gmail SMTP.

    Args:
        to: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email

    Returns:
        True if sent successfully, False otherwise.
    """
    # 1. Try Resend first (best deliverability)
    if settings.RESEND_API_KEY and settings.EMAIL_FROM:
        if _send_via_resend(to, subject, html_body):
            return True

    # 2. Fall back to Gmail SMTP
    if settings.GMAIL_APP_PASSWORD and settings.EMAIL_FROM:
        if _send_via_gmail(to, subject, html_body):
            return True

    # 3. Nothing configured — dev fallback
    print(f"[email] No email provider configured. Would have sent to {to}: {subject}")
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


def send_reset_code_email(to: str, code: str) -> bool:
    """Send password reset code (same format as verification code)."""
    subject = "IELTS Practice - Password Reset Code"
    html = f"""<div style="max-width:480px;margin:0 auto;padding:24px;font-family:sans-serif">
<h2 style="color:#15803d">IELTS Practice Platform</h2>
<p>You requested a password reset. Your reset code is:</p>
<div style="background:#f0fdf4;border:2px solid #16a34a;border-radius:12px;padding:20px;text-align:center;margin:24px 0">
  <span style="font-size:36px;font-weight:bold;color:#166534;letter-spacing:12px">{code}</span>
</div>
<p style="color:#6b7280;font-size:14px">This code expires in 30 minutes. If you didn't request this, please ignore this email.</p>
</div>"""
    return send_email(to, subject, html)
