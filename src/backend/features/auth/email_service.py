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

    async def send_beta_invitation_email(
        self,
        to_email: str,
        base_url: str,
    ) -> bool:
        """
        Send a beta invitation email

        Args:
            to_email: Recipient email address
            base_url: Base URL of the application (e.g., https://emergence-app.ch)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Email service is not enabled or not configured")
            return False

        app_url = base_url
        report_url = f"{base_url}/beta_report.html"

        subject = "🎉 Bienvenue dans le programme Beta ÉMERGENCE V8"

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
            margin: 10px 5px;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }}
        .button:hover {{
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        }}
        .button-secondary {{
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }}
        .button-secondary:hover {{
            background: linear-gradient(135deg, #059669 0%, #047857 100%);
        }}
        .highlight {{
            background: rgba(59, 130, 246, 0.1);
            border-left: 4px solid #3b82f6;
            border-radius: 4px;
            padding: 15px;
            margin: 20px 0;
        }}
        .phases {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .phase-item {{
            margin: 10px 0;
            padding-left: 20px;
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
        ul {{
            margin: 10px 0;
            padding-left: 20px;
        }}
        li {{
            margin: 8px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="https://emergence-app.ch/assets/emergence_logo.png" alt="ÉMERGENCE Logo">
            <h1>🎉 ÉMERGENCE V8</h1>
            <p>Programme Beta 1.0</p>
        </div>

        <div class="content">
            <p>Bonjour,</p>

            <p>Nous sommes ravis de vous inviter à participer au <strong>programme Beta ÉMERGENCE V8</strong> ! 🚀</p>

            <div class="highlight">
                <strong>📅 Dates de la beta :</strong> 13 octobre - 3 novembre 2025<br>
                <strong>🎯 Objectif :</strong> Tester la plateforme et nous aider à l'améliorer avant le lancement public
            </div>

            <h2 style="color: #3b82f6; margin-top: 30px;">🔑 Accès à la plateforme</h2>
            <p>Votre email <strong>{to_email}</strong> a été ajouté à l'allowlist. Vous pouvez maintenant accéder à la plateforme :</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{app_url}" class="button">🚀 Accéder à ÉMERGENCE</a>
            </div>

            <h2 style="color: #3b82f6; margin-top: 30px;">✅ Que tester ?</h2>
            <div class="phases">
                <p><strong>8 phases de test à explorer :</strong></p>
                <div class="phase-item">📝 Phase 1 : Authentification & Onboarding</div>
                <div class="phase-item">💬 Phase 2 : Chat avec les agents (Anima, Neo, Nexus)</div>
                <div class="phase-item">🧠 Phase 3 : Système de mémoire</div>
                <div class="phase-item">📄 Phase 4 : Documents & RAG</div>
                <div class="phase-item">🎭 Phase 5 : Débats autonomes</div>
                <div class="phase-item">📊 Phase 6 : Cockpit & Analytics</div>
                <div class="phase-item">⚡ Phase 7 : Tests de robustesse</div>
                <div class="phase-item">🐛 Phase 8 : Edge cases</div>
            </div>

            <h2 style="color: #3b82f6; margin-top: 30px;">📋 Formulaire de rapport</h2>
            <p>Une fois vos tests effectués (ou en cours), merci de remplir le formulaire de rapport beta pour nous faire part de vos retours :</p>

            <div style="text-align: center; margin: 30px 0;">
                <a href="{report_url}" class="button button-secondary">📝 Remplir le formulaire de test</a>
            </div>

            <h2 style="color: #3b82f6; margin-top: 30px;">💡 Conseils</h2>
            <ul>
                <li>Prenez le temps d'explorer chaque fonctionnalité</li>
                <li>Notez tous les bugs, même mineurs</li>
                <li>N'hésitez pas à nous faire part de vos suggestions</li>
                <li>Testez sur différents navigateurs si possible</li>
                <li>Le formulaire sauvegarde votre progression automatiquement</li>
            </ul>

            <div class="highlight">
                <strong>🐛 Bugs connus :</strong><br>
                Consultez la documentation beta pour connaître les bugs déjà identifiés et leurs workarounds.
            </div>

            <div class="signature">
                <p>Merci infiniment pour votre participation ! 🙏<br><br>
                L'équipe d'Émergence<br>
                <strong>FG, Claude et Codex</strong></p>
            </div>
        </div>

        <div class="footer">
            <p><strong>Besoin d'aide ?</strong><br>
            📧 Email : gonzalefernando@gmail.com<br>
            📝 Formulaire : <a href="{report_url}" style="color: #3b82f6;">beta_report.html</a></p>

            <p style="margin-top: 20px;">Cet email a été envoyé automatiquement par ÉMERGENCE.<br>
            Merci de ne pas répondre à cet email.</p>
        </div>
    </div>
</body>
</html>
        """

        text_body = f"""
🎉 BIENVENUE DANS LE PROGRAMME BETA ÉMERGENCE V8

Bonjour,

Nous sommes ravis de vous inviter à participer au programme Beta ÉMERGENCE V8 !

📅 DATES DE LA BETA
Du 13 octobre au 3 novembre 2025

🎯 OBJECTIF
Tester la plateforme et nous aider à l'améliorer avant le lancement public

🔑 ACCÈS À LA PLATEFORME
Votre email {to_email} a été ajouté à l'allowlist.
Accédez à la plateforme : {app_url}

✅ QUE TESTER ?

8 phases de test à explorer :
- Phase 1 : Authentification & Onboarding
- Phase 2 : Chat avec les agents (Anima, Neo, Nexus)
- Phase 3 : Système de mémoire
- Phase 4 : Documents & RAG
- Phase 5 : Débats autonomes
- Phase 6 : Cockpit & Analytics
- Phase 7 : Tests de robustesse
- Phase 8 : Edge cases

📋 FORMULAIRE DE RAPPORT
Une fois vos tests effectués, merci de remplir le formulaire :
{report_url}

💡 CONSEILS
- Prenez le temps d'explorer chaque fonctionnalité
- Notez tous les bugs, même mineurs
- N'hésitez pas à nous faire part de vos suggestions
- Testez sur différents navigateurs si possible
- Le formulaire sauvegarde votre progression automatiquement

BESOIN D'AIDE ?
Email : gonzalefernando@gmail.com
Formulaire : {report_url}

Merci infiniment pour votre participation ! 🙏

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

        reset_link = f"{base_url}/reset-password.html?token={reset_token}"

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
