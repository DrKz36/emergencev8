"""
Router pour les endpoints Guardian - Auto-fix et monitoring
"""
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from typing import Optional
import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path

router = APIRouter(prefix="/api/guardian", tags=["guardian"])

# Secret pour signer les tokens (doit être en .env en prod)
GUARDIAN_SECRET = os.getenv("GUARDIAN_SECRET", "dev-secret-change-in-prod")


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
