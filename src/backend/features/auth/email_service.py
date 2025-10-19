"""
Email Service for authentication-related emails
Handles password reset emails, beta invitations, Guardian reports
Uses Jinja2 templates for clean HTML/text email generation
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

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
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    # Diagnostic logging
    logger.info(f"Email config: enabled={enabled}, smtp_host={os.getenv('SMTP_HOST', 'NOT_SET')}, "
                f"smtp_user={os.getenv('SMTP_USER', 'NOT_SET')}, smtp_password={'SET' if smtp_password else 'NOT_SET'}")

    return EmailConfig(
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=smtp_password,
        from_email=os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", "")),
        from_name=os.getenv("SMTP_FROM_NAME", "ÉMERGENCE"),
        use_tls=os.getenv("SMTP_USE_TLS", "1").strip().lower() in {"1", "true", "yes", "on"},
        enabled=enabled,
    )


class EmailService:
    """Service for sending emails using Jinja2 templates"""

    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or build_email_config_from_env()

        # Setup Jinja2 environment for email templates
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        logger.info(f"Jinja2 templates loaded from: {templates_dir}")

    def is_enabled(self) -> bool:
        """Check if email service is properly configured and enabled"""
        return (
            self.config.enabled
            and bool(self.config.smtp_host)
            and bool(self.config.smtp_user)
            and bool(self.config.smtp_password)
        )

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template with given context"""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise

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

        context = {
            'to_email': to_email,
            'app_url': base_url,
            'report_url': f"{base_url}/beta_report.html",
        }

        subject = "🎉 Bienvenue dans le programme Beta ÉMERGENCE V8"
        html_body = self._render_template('beta_invitation_email.html', context)
        text_body = self._render_template('beta_invitation_email.txt', context)

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    async def send_custom_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """
        Send a custom email with provided subject and body

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML version of the email body
            text_body: Plain text version of the email body

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Email service is not enabled or not configured")
            return False

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    async def send_auth_issue_notification_email(
        self,
        to_email: str,
        base_url: str,
    ) -> bool:
        """
        Send a notification about authentication issues and password reset

        Args:
            to_email: Recipient email address
            base_url: Base URL of the application (e.g., https://emergence-app.ch)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Email service is not enabled or not configured")
            return False

        context = {
            'to_email': to_email,
            'reset_url': f"{base_url}/reset-password.html",
            'report_url': f"{base_url}/beta_report.html",
        }

        subject = "🔧 ÉMERGENCE Beta - Mise à jour importante sur l'authentification"
        html_body = self._render_template('auth_issue_email.html', context)
        text_body = self._render_template('beta_invitation_email.txt', context)  # Reuse text template

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

        context = {
            'reset_link': f"{base_url}/reset-password.html?token={reset_token}",
        }

        subject = "Réinitialisation de votre mot de passe ÉMERGENCE"
        html_body = self._render_template('password_reset_email.html', context)
        text_body = self._render_template('password_reset_email.txt', context)

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    async def send_guardian_report(
        self,
        to_email: str,
        reports: Dict[str, Optional[Dict]],
        base_url: str = "https://emergence-app.ch",
    ) -> bool:
        """
        Send Guardian monitoring report email

        Args:
            to_email: Admin email address
            reports: Dictionary of Guardian reports (prod, docs, integrity, unified, global)
            base_url: Base URL for links

        Returns:
            True if sent successfully
        """
        if not self.is_enabled():
            logger.warning("Email service is not enabled or not configured")
            return False

        # Determine global status
        global_status = self._determine_global_status(reports)

        # Prepare summary
        summary = self._prepare_summary(reports)

        # Collect all problems for details section
        all_problems = self._collect_all_problems(reports)

        # Build context for template
        context = {
            'timestamp': datetime.now().strftime("%d/%m/%Y à %H:%M:%S"),
            'global_status': global_status,
            'summary': summary,
            'prod_report': reports.get('prod_report.json'),
            'docs_report': reports.get('docs_report.json'),
            'integrity_report': reports.get('integrity_report.json'),
            'unified_report': reports.get('unified_report.json'),
            'usage_stats': reports.get('usage_stats'),  # For Phase 2
            'all_problems': all_problems,
            'admin_ui_url': f"{base_url}/admin",
            'cloud_storage_url': f"{base_url}/api/guardian/reports",
            'cloud_logging_url': "https://console.cloud.google.com/logs/query",
        }

        subject = f"🛡️ Guardian ÉMERGENCE - {global_status} - {datetime.now().strftime('%d/%m %H:%M')}"
        html_body = self._render_template('guardian_report_email.html', context)
        text_body = self._render_template('guardian_report_email.txt', context)

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )

    def _determine_global_status(self, reports: Dict[str, Optional[Dict]]) -> str:
        """Determine global status from all reports"""
        # Try global_report first
        global_report = reports.get('global_report.json')
        if global_report and isinstance(global_report, dict):
            return global_report.get('status', 'UNKNOWN')

        # Otherwise aggregate from individual reports
        has_critical = False
        has_warning = False

        for report_data in reports.values():
            if report_data and isinstance(report_data, dict):
                status = report_data.get('status', '').upper()
                if status in ['CRITICAL', 'ERROR', 'FAILED']:
                    has_critical = True
                elif status in ['WARNING', 'DEGRADED', 'NEEDS_UPDATE']:
                    has_warning = True

        if has_critical:
            return 'CRITICAL'
        elif has_warning:
            return 'WARNING'
        else:
            return 'OK'

    def _prepare_summary(self, reports: Dict[str, Optional[Dict]]) -> Dict[str, int]:
        """Prepare summary metrics from all reports"""
        summary = {
            'critical_count': 0,
            'warning_count': 0,
            'active_users': 0,
        }

        for report_data in reports.values():
            if report_data and isinstance(report_data, dict):
                report_summary = report_data.get('summary')
                if report_summary and isinstance(report_summary, dict):
                    summary['critical_count'] += report_summary.get('critical_count', 0)
                    summary['warning_count'] += report_summary.get('warning_count', 0)

        return summary

    def _collect_all_problems(self, reports: Dict[str, Optional[Dict]]) -> list:
        """Collect all problems/recommendations from reports"""
        all_problems = []

        # Map report keys to source names
        source_map = {
            'prod_report.json': '☁️ Production',
            'docs_report.json': '📚 Documentation',
            'integrity_report.json': '🔐 Intégrité',
        }

        for report_key, source_name in source_map.items():
            report_data = reports.get(report_key)
            if report_data and isinstance(report_data, dict):
                recs = report_data.get('recommendations', [])
                if recs and isinstance(recs, list):
                    for rec in recs:
                        if isinstance(rec, dict):
                            all_problems.append({
                                'source': source_name,
                                'priority': rec.get('priority', 'MEDIUM'),
                                'action': rec.get('action', 'N/A'),
                                'file': rec.get('file', ''),
                                'details': rec.get('details', '')
                            })

        return all_problems

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

            logger.info(f"Email sent successfully to {to_email}")
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
