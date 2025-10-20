"""
Router pour les endpoints Guardian - Auto-fix et monitoring
"""
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from typing import Optional
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

from backend.features.guardian.email_report import GuardianEmailService

router = APIRouter(prefix="/api/guardian", tags=["guardian"])
logger = logging.getLogger("emergence.guardian.router")

# Secret pour signer les tokens (doit être en .env en prod)
GUARDIAN_SECRET = os.getenv("GUARDIAN_SECRET", "dev-secret-change-in-prod")

# Token pour Cloud Scheduler (authentification scheduled jobs)
GUARDIAN_SCHEDULER_TOKEN = os.getenv("GUARDIAN_SCHEDULER_TOKEN", "dev-scheduler-token-change-in-prod")


def generate_fix_token(report_id: str) -> str:
    """Génère un token sécurisé pour autoriser l'auto-fix"""
    timestamp = str(int(datetime.now().timestamp()))
    data = f"{report_id}:{timestamp}"
    signature = hmac.new(
        GUARDIAN_SECRET.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{data}:{signature}"


def verify_fix_token(token: str, max_age_seconds: int = 86400) -> bool:
    """Vérifie qu'un token auto-fix est valide (24h max)"""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return False

        report_id, timestamp, signature = parts

        # Vérifier l'âge du token
        token_time = int(timestamp)
        current_time = int(datetime.now().timestamp())
        if current_time - token_time > max_age_seconds:
            return False

        # Vérifier la signature
        data = f"{report_id}:{timestamp}"
        expected_sig = hmac.new(
            GUARDIAN_SECRET.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_sig)
    except Exception:
        return False


async def execute_anima_fixes(recommendations: list) -> dict:
    """Exécute les corrections Anima (Documentation)"""
    results = {
        "fixed": [],
        "failed": [],
        "skipped": []
    }

    for rec in recommendations:
        try:
            action = rec.get("action", "")
            priority = rec.get("priority", "LOW")

            # Exemple: Mettre à jour un fichier de doc
            if "update" in action.lower() and "documentation" in action.lower():
                # TODO: Implémenter la mise à jour automatique
                results["fixed"].append({
                    "action": action,
                    "priority": priority,
                    "status": "simulated"  # Pour l'instant simulation
                })
            else:
                results["skipped"].append({
                    "action": action,
                    "reason": "Type de correction non supporté"
                })
        except Exception as e:
            results["failed"].append({
                "action": rec.get("action", "unknown"),
                "error": str(e)
            })

    return results


async def execute_neo_fixes(recommendations: list) -> dict:
    """Exécute les corrections Neo (Intégrité)"""
    results = {
        "fixed": [],
        "failed": [],
        "skipped": []
    }

    for rec in recommendations:
        try:
            action = rec.get("action", "")
            priority = rec.get("priority", "LOW")

            # Exemple: Fix imports, dependencies
            if "import" in action.lower() or "dependency" in action.lower():
                results["fixed"].append({
                    "action": action,
                    "priority": priority,
                    "status": "simulated"
                })
            else:
                results["skipped"].append({
                    "action": action,
                    "reason": "Correction manuelle requise"
                })
        except Exception as e:
            results["failed"].append({
                "action": rec.get("action", "unknown"),
                "error": str(e)
            })

    return results


async def execute_prod_fixes(recommendations: list) -> dict:
    """Exécute les corrections Production (ATTENTION: très sensible)"""
    results = {
        "fixed": [],
        "failed": [],
        "skipped": []
    }

    # Pour la prod, on ne fait RIEN automatiquement pour l'instant
    # Trop risqué de modifier la prod sans validation humaine
    for rec in recommendations:
        results["skipped"].append({
            "action": rec.get("action", "unknown"),
            "reason": "Corrections production nécessitent validation manuelle"
        })

    return results


async def apply_guardian_fixes(report_data: dict) -> dict:
    """Applique les corrections Guardian selon les rapports"""
    fixes_summary = {
        "timestamp": datetime.now().isoformat(),
        "anima": {},
        "neo": {},
        "prod": {},
        "total_fixed": 0,
        "total_failed": 0,
        "total_skipped": 0
    }

    # Anima (Documentation)
    docs_report = report_data.get("docs")
    if docs_report and isinstance(docs_report, dict):
        recs = docs_report.get("recommendations", [])
        if recs and isinstance(recs, list):
            anima_results = await execute_anima_fixes(recs)
            fixes_summary["anima"] = anima_results
            fixes_summary["total_fixed"] += len(anima_results["fixed"])
            fixes_summary["total_failed"] += len(anima_results["failed"])
            fixes_summary["total_skipped"] += len(anima_results["skipped"])

    # Neo (Intégrité)
    integrity_report = report_data.get("integrity")
    if integrity_report and isinstance(integrity_report, dict):
        recs = integrity_report.get("recommendations", [])
        if recs and isinstance(recs, list):
            neo_results = await execute_neo_fixes(recs)
            fixes_summary["neo"] = neo_results
            fixes_summary["total_fixed"] += len(neo_results["fixed"])
            fixes_summary["total_failed"] += len(neo_results["failed"])
            fixes_summary["total_skipped"] += len(neo_results["skipped"])

    # Prod (Production)
    prod_report = report_data.get("prod")
    if prod_report and isinstance(prod_report, dict):
        recs = prod_report.get("recommendations", [])
        if recs and isinstance(recs, list):
            prod_results = await execute_prod_fixes(recs)
            fixes_summary["prod"] = prod_results
            fixes_summary["total_fixed"] += len(prod_results["fixed"])
            fixes_summary["total_failed"] += len(prod_results["failed"])
            fixes_summary["total_skipped"] += len(prod_results["skipped"])

    return fixes_summary


@router.post("/auto-fix")
async def auto_fix_endpoint(
    background_tasks: BackgroundTasks,
    x_guardian_token: Optional[str] = Header(None)
):
    """
    Endpoint pour appliquer automatiquement les corrections Guardian

    Sécurisé par token HMAC avec expiration 24h
    """
    # Vérifier le token
    if not x_guardian_token:
        raise HTTPException(status_code=401, detail="Token Guardian manquant")

    if not verify_fix_token(x_guardian_token):
        raise HTTPException(status_code=403, detail="Token Guardian invalide ou expiré")

    # Charger les rapports Guardian actuels
    reports_dir = Path(__file__).parent.parent.parent.parent.parent / "reports"

    try:
        # Charger tous les rapports disponibles
        report_files = {
            "prod": "prod_report.json",
            "docs": "docs_report.json",
            "integrity": "integrity_report.json",
            "unified": "unified_report.json"
        }

        reports = {}
        for key, filename in report_files.items():
            filepath = reports_dir / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        reports[key] = data

        if not reports:
            raise HTTPException(status_code=404, detail="Aucun rapport Guardian trouvé")

        # Appliquer les corrections
        fixes_result = await apply_guardian_fixes(reports)

        # TODO: Envoyer email de confirmation avec résultats
        # background_tasks.add_task(send_fix_confirmation_email, fixes_result)

        return {
            "status": "success",
            "message": "Corrections Guardian appliquées",
            "details": fixes_result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'application des corrections: {str(e)}"
        )


@router.get("/status")
async def get_guardian_status():
    """Récupère le statut actuel des Guardians (sans auth requise)"""
    reports_dir = Path(__file__).parent.parent.parent.parent.parent / "reports"

    report_files = {
        "prod": "prod_report.json",
        "docs": "docs_report.json",
        "integrity": "integrity_report.json",
        "unified": "unified_report.json"
    }

    status = {
        "timestamp": datetime.now().isoformat(),
        "reports_available": [],
        "reports_missing": []
    }

    for key, filename in report_files.items():
        filepath = reports_dir / filename
        if filepath.exists():
            status["reports_available"].append(key)
        else:
            status["reports_missing"].append(key)

    return status


@router.post("/scheduled-report")
async def scheduled_guardian_report(
    background_tasks: BackgroundTasks,
    x_guardian_scheduler_token: Optional[str] = Header(None, alias="X-Guardian-Scheduler-Token")
):
    """
    Endpoint appelé par Cloud Scheduler toutes les 2h
    Génère et envoie le rapport Guardian par email

    Authentifié par token (env var GUARDIAN_SCHEDULER_TOKEN)
    """
    # Vérifier le token scheduler
    if not x_guardian_scheduler_token:
        logger.warning("Scheduled report called without token")
        raise HTTPException(
            status_code=401,
            detail="Token scheduler manquant (X-Guardian-Scheduler-Token header)"
        )

    if x_guardian_scheduler_token != GUARDIAN_SCHEDULER_TOKEN:
        logger.warning(f"Invalid scheduler token: {x_guardian_scheduler_token[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Token scheduler invalide"
        )

    logger.info("Scheduled Guardian report triggered by Cloud Scheduler")

    try:
        # Lancer l'envoi du rapport en background
        async def send_report_task():
            try:
                email_service = GuardianEmailService()
                success = await email_service.send_report()
                if success:
                    logger.info("✅ Guardian report email sent successfully (scheduled)")
                else:
                    logger.error("❌ Failed to send Guardian report email (scheduled)")
            except Exception as e:
                logger.error(f"Error in scheduled report task: {e}", exc_info=True)

        background_tasks.add_task(send_report_task)

        return {
            "status": "success",
            "message": "Guardian report génération lancée",
            "timestamp": datetime.now().isoformat(),
            "trigger": "cloud_scheduler"
        }

    except Exception as e:
        logger.error(f"Error in scheduled_guardian_report endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du rapport: {str(e)}"
        )


@router.post("/generate-reports")
async def generate_guardian_reports():
    """
    Endpoint pour générer rapports Guardian en temps réel (Production logs)
    Upload les rapports vers Cloud Storage pour persistence

    Accessible sans auth pour l'instant (TODO: require admin)
    """
    logger.info("Manual Guardian report generation triggered from Admin UI")

    try:
        from google.cloud import logging as cloud_logging
        from backend.features.guardian.storage_service import GuardianStorageService

        # Initialize services
        storage = GuardianStorageService()
        log_client = cloud_logging.Client()

        # Fetch recent production logs (last 1 hour)
        logger.info("Fetching production logs from Cloud Logging...")
        filter_str = '''
            resource.type="cloud_run_revision"
            AND resource.labels.service_name="emergence-app"
            AND timestamp>="{}Z"
        '''.format((datetime.now() - timedelta(hours=1)).isoformat())

        entries = list(log_client.list_entries(filter_=filter_str, max_results=100))

        # Analyze logs
        errors = []
        warnings = []
        for entry in entries:
            if entry.severity in ["ERROR", "CRITICAL"]:
                errors.append({
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                    "severity": entry.severity,
                    "message": str(entry.payload)[:500]
                })
            elif entry.severity == "WARNING":
                warnings.append({
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                    "message": str(entry.payload)[:500]
                })

        # Generate prod report
        prod_report = {
            "timestamp": datetime.now().isoformat(),
            "status": "CRITICAL" if len(errors) >= 5 else ("DEGRADED" if len(errors) > 0 else "OK"),
            "logs_analyzed": len(entries),
            "summary": {
                "errors": len(errors),
                "warnings": len(warnings),
                "critical_signals": sum(1 for e in errors if e["severity"] == "CRITICAL")
            },
            "errors": errors[:10],  # Top 10 errors
            "warnings": warnings[:5]  # Top 5 warnings
        }

        # Upload to Cloud Storage
        upload_success = storage.upload_report("prod_report.json", prod_report)

        if upload_success:
            logger.info("✅ Production report generated and uploaded to Cloud Storage")
            return {
                "status": "success",
                "message": "Rapport production généré et uploadé",
                "timestamp": datetime.now().isoformat(),
                "report": prod_report
            }
        else:
            logger.error("Failed to upload report to Cloud Storage")
            return {
                "status": "error",
                "message": "Erreur lors de l'upload vers Cloud Storage",
                "timestamp": datetime.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Error generating Guardian reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération des rapports: {str(e)}"
        )


@router.post("/run-audit")
async def run_guardian_audit():
    """
    Endpoint pour lancer audit Guardian manuellement (Admin UI)
    Charge tous les rapports disponibles depuis Cloud Storage et retourne summary

    Accessible sans auth pour l'instant (TODO: require admin)
    """
    logger.info("Manual Guardian audit triggered from Admin UI")

    try:
        # Charger tous les rapports Guardian depuis Cloud Storage
        email_service = GuardianEmailService()
        reports = email_service.load_all_reports()

        if not any(reports.values()):
            logger.warning("No Guardian reports found in Cloud Storage")
            return {
                "status": "warning",
                "message": "Aucun rapport Guardian trouvé (générez-les d'abord avec /generate-reports)",
                "timestamp": datetime.now().isoformat(),
                "reports": {}
            }

        # Extraire summary de chaque rapport
        summary = {
            "timestamp": datetime.now().isoformat(),
            "status": "unknown",
            "reports_loaded": [],
            "reports_missing": [],
            "global_status": "OK",
            "total_critical": 0,
            "total_warnings": 0,
            "total_recommendations": 0,
            "details": {}
        }

        report_names = [
            'prod_report.json',
            'docs_report.json',
            'integrity_report.json',
            'unified_report.json',
            'usage_report.json'
        ]

        for report_name in report_names:
            report_data = reports.get(report_name)

            if report_data and isinstance(report_data, dict):
                summary["reports_loaded"].append(report_name)

                # Extract status
                status = report_data.get("status", "UNKNOWN").upper()
                report_summary = report_data.get("summary", {})

                # Aggregate counts
                if isinstance(report_summary, dict):
                    summary["total_critical"] += report_summary.get("critical_count", 0)
                    summary["total_warnings"] += report_summary.get("warning_count", 0)

                # Count recommendations
                recs = report_data.get("recommendations", [])
                if isinstance(recs, list):
                    summary["total_recommendations"] += len(recs)

                # Store details
                summary["details"][report_name] = {
                    "status": status,
                    "summary": report_summary,
                    "recommendations_count": len(recs) if isinstance(recs, list) else 0
                }

                # Update global status
                if status in ["CRITICAL", "ERROR", "FAILED"]:
                    summary["global_status"] = "CRITICAL"
                elif status in ["WARNING", "NEEDS_UPDATE"] and summary["global_status"] != "CRITICAL":
                    summary["global_status"] = "WARNING"

            else:
                summary["reports_missing"].append(report_name)

        summary["status"] = "success"
        logger.info(f"Guardian audit completed: {summary['global_status']} - {len(summary['reports_loaded'])} reports loaded")

        return summary

    except Exception as e:
        logger.error(f"Error in run_guardian_audit: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de l'audit Guardian: {str(e)}"
        )
