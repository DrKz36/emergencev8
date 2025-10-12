"""
Email Service for authentication-related emails
Handles password reset emails
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("emergence.auth.email")


@dataclass
class EmailConfig:
    """Configuration for email service"""
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_email: str
    from_name: str = "ÉMERGENCE"
    use_tls: bool = True
    enabled: bool = True


def build_email_config_from_env() -> EmailConfig:
    """Build email configuration from environment variables"""
    enabled = os.getenv("EMAIL_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}

    return EmailConfig(
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        from_email=os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", "")),
        from_name=os.getenv("SMTP_FROM_NAME", "ÉMERGENCE"),
        use_tls=os.getenv("SMTP_USE_TLS", "1").strip().lower() in {"1", "true", "yes", "on"},
        enabled=enabled,
    )


class EmailService:
    """Service for sending authentication-related emails"""

    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or build_email_config_from_env()

    def is_enabled(self) -> bool:
        """Check if email service is properly configured and enabled"""
        return (
            self.config.enabled
            and bool(self.config.smtp_host)
            and bool(self.config.smtp_user)
            and bool(self.config.smtp_password)
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        base_url: str,
    ) -> bool:
        """
        Send a password reset email with a verification link

        Args:
            to_email: Recipient email address
            reset_token: Token for password reset
            base_url: Base URL of the application (e.g., https://emergence.example.com)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Email service is not enabled or not configured")
            return False

        reset_link = f"{base_url}/reset-password?token={reset_token}"

        subject = "Réinitialisation de votre mot de passe ÉMERGENCE"

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 40px;
            color: #e2e8f0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header img {{
            max-width: 120px;
            margin-bottom: 15px;
        }}
        .header h1 {{
            color: #3b82f6;
            margin: 0;
            font-size: 28px;
        }}
        .content {{
            margin: 20px 0;
        }}
        .button {{
            display: inline-block;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white !important;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 8px;
            font-weight: 600;
            margin: 20px 0;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }}
        .button:hover {{
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 14px;
            color: #94a3b8;
        }}
        .signature {{
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            font-style: italic;
            color: #cbd5e1;
        }}
        .warning {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
            padding: 12px;
            margin: 20px 0;
            color: #fca5a5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="https://emergence-app.ch/assets/emergence_logo.png" alt="ÉMERGENCE Logo">
            <h1>🔒 ÉMERGENCE</h1>
            <p>Réinitialisation de mot de passe</p>
        </div>

        <div class="content">
            <p>Bonjour,</p>

            <p>Vous avez demandé la réinitialisation de votre mot de passe pour votre compte ÉMERGENCE.</p>

            <p>Pour créer un nouveau mot de passe, veuillez cliquer sur le bouton ci-dessous :</p>

            <div style="text-align: center;">
                <a href="{reset_link}" class="button">Réinitialiser mon mot de passe</a>
            </div>

            <p>Ou copiez ce lien dans votre navigateur :</p>
            <p style="word-break: break-all; background: rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 4px;">
                {reset_link}
            </p>

            <div class="warning">
                ⚠️ <strong>Important :</strong> Ce lien est valable pendant 1 heure seulement.
            </div>

            <p>Si vous n'avez pas demandé cette réinitialisation, vous pouvez ignorer cet email en toute sécurité.</p>

            <div class="signature">
                <p>L'équipe d'Émergence<br>
                <strong>FG, Claude et Codex</strong></p>
            </div>
        </div>

        <div class="footer">
            <p>Cet email a été envoyé automatiquement par ÉMERGENCE.<br>
            Merci de ne pas répondre à cet email.</p>
        </div>
    </div>
</body>
</html>
        """

        text_body = f"""
Réinitialisation de votre mot de passe ÉMERGENCE

Bonjour,

Vous avez demandé la réinitialisation de votre mot de passe pour votre compte ÉMERGENCE.

Pour créer un nouveau mot de passe, veuillez cliquer sur le lien ci-dessous :

{reset_link}

⚠️ Important : Ce lien est valable pendant 1 heure seulement.

Si vous n'avez pas demandé cette réinitialisation, vous pouvez ignorer cet email en toute sécurité.

L'équipe d'Émergence
FG, Claude et Codex

---
Cet email a été envoyé automatiquement par ÉMERGENCE.
Merci de ne pas répondre à cet email.
        """

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """
        Internal method to send an email via SMTP

        Args:
            to_email: Recipient email
            subject: Email subject
            html_body: HTML version of the email
            text_body: Plain text version of the email

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.from_name} <{self.config.from_email}>"
            msg["To"] = to_email

            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, "plain", "utf-8")
            part2 = MIMEText(html_body, "html", "utf-8")

            msg.attach(part1)
            msg.attach(part2)

            # Connect to SMTP server
            if self.config.use_tls:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port, timeout=10)

            # Login and send
            server.login(self.config.smtp_user, self.config.smtp_password)
            server.send_message(msg)
            server.quit()

            logger.info(f"Password reset email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error while sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while sending email: {e}")
            return False
