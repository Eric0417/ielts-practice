"""
Email sending utility using Gmail SMTP.

Gmail free tier: 500 emails/day.
Requires GMAIL_APP_PASSWORD env var (16-char app password from Google Account).
Sender is configured via EMAIL_FROM env var.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via Gmail SMTP.

    Args:
        to: Recipient email address
        subject: Email subject line
        html_body: HTML content of the email

    Returns:
        True if sent successfully, False otherwise.
    """
    app_password = settings.GMAIL_APP_PASSWORD
    from_addr = settings.EMAIL_FROM

    if not app_password or not from_addr:
        print(f"[email] GMAIL_APP_PASSWORD or EMAIL_FROM not configured. Skipping email send.")
        print(f"[email] Would have sent to {to}: {subject}")
        return False

    # Build MIME message
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
