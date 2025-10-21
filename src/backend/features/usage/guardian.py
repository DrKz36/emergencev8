# src/backend/features/usage/guardian.py
"""
Phase 2 Guardian Cloud - UsageGuardian Agent
Agrège statistiques d'usage utilisateurs toutes les N heures
Génère rapports JSON pour dashboard admin + email Guardian
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from pathlib import Path
from collections import defaultdict

from .repository import UsageRepository
from .models import UsageReport, UsageReportUser

logger = logging.getLogger(__name__)


class UsageGuardian:
    """
    Agent qui agrège stats d'usage sur une période
    Génère rapport JSON pour dashboard admin
    """

    def __init__(self, repository: UsageRepository):
        self.repository = repository

    async def generate_report(
        self,
        hours: int = 2,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict:
        """
        Génère rapport d'usage sur période donnée

        Args:
            hours: Nombre d'heures à analyser (par défaut 2h)
            start_time: Date début (optionnel, sinon now - hours)
            end_time: Date fin (optionnel, sinon now)

        Returns:
            dict avec structure UsageReport
        """
        try:
            # Déterminer période
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            if start_time is None:
                start_time = end_time - timedelta(hours=hours)

            logger.info(
                f"Génération rapport usage: "
                f"{start_time.isoformat()} -> {end_time.isoformat()}"
            )

            # Récupérer données brutes
            feature_usages = await self.repository.get_feature_usage_period(
                start_time, end_time
            )
            user_errors = await self.repository.get_user_errors_period(
                start_time, end_time
            )

            # Agréger par utilisateur
            user_stats: defaultdict[str, dict[str, Any]] = defaultdict(
                lambda: {
                    "email": "",
                    "requests_count": 0,
                    "errors_count": 0,
                    "features_used": set(),
                    "errors": [],
                    "total_time_ms": 0,
                }
            )

            # Process feature usage
            for usage in feature_usages:
                email = usage.user_email or "anonymous"
                user = user_stats[email]
                user["email"] = email
                user["requests_count"] += 1
                user["features_used"].add(usage.feature_name)
                if usage.duration_ms:
                    user["total_time_ms"] += usage.duration_ms

            # Process errors
            for error in user_errors:
                email = error.user_email or "anonymous"
                user = user_stats[email]
                user["email"] = email
                user["errors_count"] += 1
                user["errors"].append(
                    {
                        "endpoint": error.endpoint,
                        "error": error.error_message,
                        "timestamp": error.timestamp.isoformat(),
                        "code": error.error_code,
                    }
                )

            # Construire liste utilisateurs
            users_list = []
            for email, stats in user_stats.items():
                users_list.append(
                    UsageReportUser(
                        email=email,
                        total_time_minutes=int(stats["total_time_ms"] / 60000),
                        features_used=list(stats["features_used"]),
                        requests_count=stats["requests_count"],
                        errors_count=stats["errors_count"],
                        errors=stats["errors"],
                    )
                )

            # Stats globales
            active_users = len(user_stats)
            total_requests = len(feature_usages)
            total_errors = len(user_errors)

            # Top features
            top_features = await self.repository.get_top_features(
                start_time, end_time, limit=10
            )

            # Error breakdown
            error_breakdown = await self.repository.get_error_breakdown(
                start_time, end_time
            )

            # Construire rapport
            report = UsageReport(
                period_start=start_time,
                period_end=end_time,
                active_users=active_users,
                total_requests=total_requests,
                total_errors=total_errors,
                users=users_list,
                top_features=top_features,
                error_breakdown=error_breakdown,
            )

            # Convertir en dict pour JSON
            report_dict = report.dict()

            logger.info(
                f"Rapport généré: {active_users} users, "
                f"{total_requests} requests, {total_errors} errors"
            )

            return report_dict

        except Exception as e:
            logger.error(f"Erreur génération rapport usage: {e}")
            return {
                "period_start": start_time.isoformat() if start_time else None,
                "period_end": end_time.isoformat() if end_time else None,
                "active_users": 0,
                "total_requests": 0,
                "total_errors": 0,
                "users": [],
                "top_features": [],
                "error_breakdown": {},
                "error": str(e),
            }

    async def save_report_to_file(
        self,
        report: dict,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Sauvegarde rapport JSON dans fichier

        Args:
            report: Rapport dict
            output_path: Chemin fichier (défaut: reports/usage_report.json)

        Returns:
            Path du fichier créé
        """
        try:
            if output_path is None:
                # Dossier reports à la racine du projet
                reports_dir = Path(__file__).resolve().parents[4] / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                output_path = reports_dir / "usage_report.json"

            # Sauvegarder JSON
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            logger.info(f"Rapport sauvegardé: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Erreur sauvegarde rapport: {e}")
            raise

    async def generate_and_save_report(
        self,
        hours: int = 2,
        output_path: Optional[Path] = None,
    ) -> tuple[dict, Path]:
        """
        Génère rapport ET le sauvegarde dans fichier

        Returns:
            (rapport_dict, path_fichier)
        """
        report = await self.generate_report(hours=hours)
        path = await self.save_report_to_file(report, output_path)
        return report, path
