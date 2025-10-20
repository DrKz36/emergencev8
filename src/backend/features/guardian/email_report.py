"""
Guardian Email Report Service
Loads Guardian reports and sends them via email using EmailService
Replaces the old standalone scripts (guardian_email_report.py, send_guardian_reports_email.py)

UPDATED 2025-10-20: Now uses Cloud Storage for report persistence (Cloud Run stateless fix)
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
import logging

from backend.features.auth.email_service import EmailService
from backend.features.guardian.storage_service import GuardianStorageService

logger = logging.getLogger("emergence.guardian.email")


class GuardianEmailService:
    """Service for sending Guardian monitoring reports via email"""

    def __init__(self, reports_dir: Optional[Path] = None):
        """
        Initialize Guardian Email Service

        Args:
            reports_dir: Directory containing Guardian JSON reports (fallback only, deprecated)
        """
        # Use Cloud Storage service (with local fallback)
        self.storage_service = GuardianStorageService(use_local_fallback=True)

        # Keep old reports_dir for backward compat (fallback only)
        if reports_dir is None:
            self.reports_dir = Path(__file__).parent.parent.parent.parent.parent / "reports"
        else:
            self.reports_dir = reports_dir

        self.email_service = EmailService()
        logger.info(f"GuardianEmailService initialized with Cloud Storage (fallback: {self.reports_dir})")

    def load_report(self, report_name: str) -> Optional[Dict]:
        """
        Load a single Guardian report from Cloud Storage (or local fallback)

        Args:
            report_name: Name of the report file (e.g., 'prod_report.json')

        Returns:
            Report data as dict, or None if not found or invalid
        """
        # Use Cloud Storage service (handles fallback automatically)
        return self.storage_service.download_report(report_name)

    def load_all_reports(self) -> Dict[str, Optional[Dict]]:
        """
        Load all standard Guardian reports

        Returns:
            Dictionary mapping report filenames to their data
        """
        report_files = [
            'global_report.json',
            'prod_report.json',
            'integrity_report.json',
            'docs_report.json',
            'unified_report.json',
            'orchestration_report.json',
            'usage_report.json',  # Phase 2 - Usage tracking
        ]

        reports = {}
        for report_file in report_files:
            report_data = self.load_report(report_file)
            reports[report_file] = report_data

        loaded_count = sum(1 for r in reports.values() if r is not None)
        logger.info(f"Loaded {loaded_count}/{len(report_files)} Guardian reports")

        return reports

    async def send_report(
        self,
        to_email: Optional[str] = None,
        base_url: str = "https://emergence-app.ch",
    ) -> bool:
        """
        Send Guardian report email to admin

        Args:
            to_email: Admin email (defaults to env var GUARDIAN_ADMIN_EMAIL)
            base_url: Base URL for links in email

        Returns:
            True if email sent successfully
        """
        # Load all reports
        reports = self.load_all_reports()

        if not any(reports.values()):
            logger.error("No valid Guardian reports found to send")
            return False

        # Extract usage_report for special handling in email template
        usage_stats = reports.get('usage_report.json')
        if usage_stats:
            # Pass usage_stats separately for clearer template context
            reports['usage_stats'] = usage_stats
            logger.info("Usage stats loaded successfully for email")

        # Determine recipient
        if not to_email:
            to_email = os.getenv("GUARDIAN_ADMIN_EMAIL", "gonzalefernando@gmail.com")

        logger.info(f"Sending Guardian report to: {to_email}")

        # Send via EmailService
        success = await self.email_service.send_guardian_report(
            to_email=to_email,
            reports=reports,
            base_url=base_url,
        )

        if success:
            logger.info("Guardian report email sent successfully")
        else:
            logger.error("Failed to send Guardian report email")

        return success


async def send_guardian_email_report(to_email: Optional[str] = None) -> bool:
    """
    Convenience function to send Guardian report email

    Args:
        to_email: Admin email (optional, uses env var if not provided)

    Returns:
        True if sent successfully
    """
    service = GuardianEmailService()
    return await service.send_report(to_email=to_email)


# For backward compatibility with old scripts
if __name__ == "__main__":
    import asyncio

    async def main():
        """Send Guardian report email"""
        print("=" * 60)
        print("GUARDIAN EMAIL REPORT")
        print("=" * 60)
        print()

        service = GuardianEmailService()
        success = await service.send_report()

        print()
        print("=" * 60)
        if success:
            print("✅ Guardian report sent successfully")
        else:
            print("❌ Failed to send Guardian report")
        print("=" * 60)

        return success

    result = asyncio.run(main())
    exit(0 if result else 1)
