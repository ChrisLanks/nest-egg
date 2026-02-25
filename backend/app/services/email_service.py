"""Email sending service using SMTP (aiosmtplib).

Emails are silently skipped when SMTP_HOST is not configured — the application
works fully without email; it just cannot send verification emails or invite
notifications.  Callers check ``email_service.is_configured`` when they need
to surface a different UX path (e.g. expose a join link instead of an email).
"""

import hashlib
import html
import logging
import secrets
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from uuid import UUID

import aiosmtplib
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as _settings
from app.models.user import EmailVerificationToken, PasswordResetToken
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token helpers (shared with auth.py and settings.py endpoints)
# ---------------------------------------------------------------------------


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_verification_token(db: AsyncSession, user_id: UUID) -> str:
    """
    Generate a new email-verification token for *user_id*.

    Any existing unused tokens for the same user are invalidated first so
    that only the most-recently requested token is valid.  Returns the raw
    (unhashed) token — the caller must pass it to the email template.
    """
    # Invalidate any existing unused tokens for this user
    await db.execute(
        update(EmailVerificationToken)
        .where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used_at.is_(None),
        )
        .values(used_at=utc_now())
    )

    raw_token = secrets.token_urlsafe(32)
    token_record = EmailVerificationToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(hours=24),
    )
    db.add(token_record)
    await db.commit()
    return raw_token


async def create_password_reset_token(db: AsyncSession, user_id: UUID) -> str:
    """
    Generate a new password-reset token for *user_id*.

    Any existing unused tokens for the same user are invalidated first so
    that only the most-recently requested token is valid.  Returns the raw
    (unhashed) token — the caller must pass it to the email template.
    Token expires in 1 hour (shorter window than email verification).
    """
    # Invalidate any existing unused tokens for this user
    await db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=utc_now())
    )

    raw_token = secrets.token_urlsafe(32)
    token_record = PasswordResetToken(
        user_id=user_id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(hours=1),
    )
    db.add(token_record)
    await db.commit()
    return raw_token


# ---------------------------------------------------------------------------
# EmailService
# ---------------------------------------------------------------------------


class EmailService:
    """Thin wrapper around aiosmtplib for sending transactional emails."""

    def __init__(self, smtp_host: Optional[str], smtp_port: int, smtp_username: Optional[str],
                 smtp_password: Optional[str], from_email: str, from_name: str,
                 use_tls: bool, app_base_url: str):
        self._host = smtp_host
        self._port = smtp_port
        self._username = smtp_username or ""
        self._password = smtp_password or ""
        self._from_email = from_email
        self._from_name = from_name
        self._use_tls = use_tls
        self._base_url = app_base_url.rstrip("/")

    @property
    def is_configured(self) -> bool:
        """Return True when SMTP credentials are present."""
        return bool(self._host)

    async def send_email(self, to_email: str, subject: str, html_body: str,
                         text_body: str) -> bool:
        """
        Send an email.  Returns True on success, False otherwise (never raises).
        When SMTP is not configured the call is a no-op that returns False.
        """
        if not self.is_configured:
            logger.info("Email not configured — skipping send to %s: %s", to_email, subject)
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self._from_name} <{self._from_email}>"
        msg["To"] = to_email
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                use_tls=False,       # SSL on port 465
                start_tls=self._use_tls,  # STARTTLS on port 587 (default)
            )
            logger.info("Email sent to %s: %s", to_email, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to_email, exc)
            return False

    async def send_verification_email(self, to_email: str, token: str,
                                      display_name: str) -> bool:
        """Send an email-address verification link."""
        verify_url = f"{self._base_url}/verify-email?token={token}"
        greeting = html.escape(display_name or to_email)

        subject = "Verify your Nest Egg email address"
        html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2D3748;">Verify your email address</h2>
  <p>Hi {greeting},</p>
  <p>Please verify your email address to secure your Nest Egg account.</p>
  <p style="margin: 30px 0;">
    <a href="{verify_url}"
       style="background-color: #3182CE; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 6px; display: inline-block;">
      Verify Email Address
    </a>
  </p>
  <p style="color: #718096; font-size: 14px;">
    This link expires in 24 hours. If you didn't request this, you can safely ignore it.
  </p>
  <p style="color: #718096; font-size: 12px;">
    Or copy and paste this URL: {verify_url}
  </p>
</body>
</html>"""
        text_body = (
            f"Hi {greeting},\n\n"
            f"Please verify your email address by visiting:\n{verify_url}\n\n"
            f"This link expires in 24 hours.\n\n"
            f"If you didn't request this, you can safely ignore it."
        )
        return await self.send_email(to_email, subject, html_body, text_body)

    async def send_password_reset_email(self, to_email: str, token: str,
                                        display_name: str) -> bool:
        """Send a password-reset link."""
        reset_url = f"{self._base_url}/reset-password?token={token}"
        greeting = html.escape(display_name or to_email)

        subject = "Reset your Nest Egg password"
        html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2D3748;">Reset your password</h2>
  <p>Hi {greeting},</p>
  <p>We received a request to reset your Nest Egg password. Click the button below to choose a new one.</p>
  <p style="margin: 30px 0;">
    <a href="{reset_url}"
       style="background-color: #E53E3E; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 6px; display: inline-block;">
      Reset Password
    </a>
  </p>
  <p style="color: #718096; font-size: 14px;">
    This link expires in <strong>1 hour</strong>. If you didn't request a password reset,
    you can safely ignore this email — your password will not change.
  </p>
  <p style="color: #718096; font-size: 12px;">
    Or copy and paste this URL: {reset_url}
  </p>
</body>
</html>"""
        text_body = (
            f"Hi {greeting},\n\n"
            f"Reset your Nest Egg password by visiting:\n{reset_url}\n\n"
            f"This link expires in 1 hour.\n\n"
            f"If you didn't request this, you can safely ignore it."
        )
        return await self.send_email(to_email, subject, html_body, text_body)

    async def send_invitation_email(self, to_email: str, invitation_code: str,
                                    invited_by: str, org_name: str) -> bool:
        """Send a household invitation email with a join link."""
        join_url = f"{self._base_url}/accept-invite?code={invitation_code}"
        safe_invited_by = html.escape(invited_by)
        safe_org_name = html.escape(org_name)

        subject = f"You're invited to join {org_name} on Nest Egg"
        html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2D3748;">You're invited!</h2>
  <p><strong>{safe_invited_by}</strong> has invited you to join <strong>{safe_org_name}</strong>
     on Nest Egg — a personal finance tracker for households.</p>
  <p style="margin: 30px 0;">
    <a href="{join_url}"
       style="background-color: #38A169; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 6px; display: inline-block;">
      Accept Invitation
    </a>
  </p>
  <p style="color: #718096; font-size: 14px;">
    This invitation expires in 7 days.  You'll need to create or sign in to a
    Nest Egg account using the email address this was sent to ({to_email}).
  </p>
  <p style="color: #718096; font-size: 12px;">
    Or copy and paste: {join_url}
  </p>
</body>
</html>"""
        text_body = (
            f"{invited_by} has invited you to join {org_name} on Nest Egg.\n\n"
            f"Accept the invitation:\n{join_url}\n\n"
            f"This invitation expires in 7 days.\n"
            f"You'll need a Nest Egg account using {to_email}."
        )
        return await self.send_email(to_email, subject, html_body, text_body)

    async def send_notification_email(
        self,
        to_email: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
    ) -> bool:
        """Send an in-app notification as an email digest.

        Returns True on success, False on failure (never raises).
        """
        # Build optional action button HTML
        safe_title = html.escape(title)
        safe_message = html.escape(message)
        action_button_html = ""
        action_button_text = ""
        if action_url and action_label:
            full_url = f"{self._base_url}{action_url}" if action_url.startswith("/") else action_url
            safe_action_label = html.escape(action_label)
            action_button_html = f"""
  <p style="margin: 30px 0;">
    <a href="{full_url}"
       style="background-color: #3182CE; color: white; padding: 12px 24px;
              text-decoration: none; border-radius: 6px; display: inline-block;">
      {safe_action_label}
    </a>
  </p>"""
            action_button_text = f"\n{action_label}: {full_url}\n"

        subject = f"Nest Egg: {title}"
        html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #2D3748;">{safe_title}</h2>
  <p>{safe_message}</p>{action_button_html}
  <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 30px 0;" />
  <p style="color: #718096; font-size: 12px;">
    You received this email because you have email notifications enabled in Nest Egg.
    You can disable them in Settings.
  </p>
</body>
</html>"""
        text_body = (
            f"{title}\n\n"
            f"{message}\n"
            f"{action_button_text}\n"
            f"---\n"
            f"You received this email because you have email notifications enabled in Nest Egg.\n"
            f"You can disable them in Settings."
        )
        return await self.send_email(to_email, subject, html_body, text_body)


# Module-level singleton — constructed once from loaded settings
email_service = EmailService(
    smtp_host=_settings.SMTP_HOST,
    smtp_port=_settings.SMTP_PORT,
    smtp_username=_settings.SMTP_USERNAME,
    smtp_password=_settings.SMTP_PASSWORD,
    from_email=_settings.SMTP_FROM_EMAIL,
    from_name=_settings.SMTP_FROM_NAME,
    use_tls=_settings.SMTP_USE_TLS,
    app_base_url=_settings.APP_BASE_URL,
)
