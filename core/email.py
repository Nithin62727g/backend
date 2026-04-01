"""
SMTP email helper — used to send OTP codes.
Uses Python's built-in smtplib, no extra package needed.
Supports Gmail (App Password), Outlook, or any SMTP provider.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from core.config import settings

logger = logging.getLogger(__name__)


def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Send a 6-digit OTP to `to_email`.
    Returns True on success, False on failure.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        # Fallback: just log the OTP (dev mode)
        logger.warning(
            f"[DEV] SMTP not configured — OTP for {to_email}: {otp}  "
            "(Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env to send real emails)"
        )
        return True   # treat as success so the flow continues in dev

    subject = "Your LearnFlow AI Verification Code"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:40px 0;">
          <table width="480" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border-radius:16px;overflow:hidden;
                        box-shadow:0 4px 24px rgba(0,0,0,0.08);">
            <!-- Header -->
            <tr>
              <td align="center"
                  style="background:#0d0d0d;padding:32px 40px;">
                <h1 style="margin:0;color:#ffffff;font-size:24px;
                           font-weight:700;letter-spacing:-0.5px;">
                  LearnFlow AI
                </h1>
              </td>
            </tr>
            <!-- Body -->
            <tr>
              <td style="padding:40px;">
                <p style="margin:0 0 8px;color:#6b7280;font-size:14px;">
                  Your verification code
                </p>
                <p style="margin:0 0 32px;font-size:48px;font-weight:800;
                          letter-spacing:12px;color:#0d0d0d;text-align:center;">
                  {otp}
                </p>
                <p style="margin:0 0 8px;color:#374151;font-size:14px;
                          line-height:1.6;">
                  This code is valid for <strong>10 minutes</strong>.
                  Do not share it with anyone.
                </p>
                <p style="margin:24px 0 0;color:#9ca3af;font-size:12px;">
                  If you didn't request this, you can safely ignore this email.
                </p>
              </td>
            </tr>
            <!-- Footer -->
            <tr>
              <td style="padding:16px 40px;background:#f9fafb;
                         border-top:1px solid #e5e7eb;">
                <p style="margin:0;color:#9ca3af;font-size:11px;text-align:center;">
                  &copy; 2025 LearnFlow AI. All rights reserved.
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"LearnFlow AI <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        port = settings.SMTP_PORT
        if settings.SMTP_USE_TLS:
            # STARTTLS (Gmail port 587, Outlook port 587)
            with smtplib.SMTP(settings.SMTP_HOST, port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        else:
            # SSL (Gmail port 465)
            with smtplib.SMTP_SSL(settings.SMTP_HOST, port, timeout=10) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, to_email, msg.as_string())

        logger.info(f"OTP email sent to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            f"SMTP authentication failed for {settings.SMTP_USER}. "
            "If using Gmail, make sure you're using an App Password, not your regular password."
        )
        return False
    except Exception as e:
        logger.error(f"Failed to send OTP email to {to_email}: {e}")
        return False
