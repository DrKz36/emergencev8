# src/backend/features/beta_report/router.py
"""
Beta report endpoint - sends user feedback via email
"""
from __future__ import annotations

import logging
import json
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..auth.email_service import EmailService, build_email_config_from_env

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Beta"])

# Initialize email service
email_service = EmailService(build_email_config_from_env())


class BetaReportRequest(BaseModel):
    email: str
    browserInfo: str | None = None
    checklist: Dict[str, bool]
    completion: str
    completionPercentage: int
    comments1: str | None = None
    comments2: str | None = None
    comments3: str | None = None
    comments4: str | None = None
    comments5: str | None = None
    comments6: str | None = None
    comments7: str | None = None
    comments8: str | None = None
    bugs: str | None = None
    suggestions: str | None = None
    generalComments: str | None = None


def format_beta_report_email(data: BetaReportRequest) -> str:
    """Format beta report as email body"""

    # Count by phase
    phase_counts = {
        1: sum(1 for k, v in data.checklist.items() if k.startswith('test1_') and v),
        2: sum(1 for k, v in data.checklist.items() if k.startswith('test2_') and v),
        3: sum(1 for k, v in data.checklist.items() if k.startswith('test3_') and v),
        4: sum(1 for k, v in data.checklist.items() if k.startswith('test4_') and v),
        5: sum(1 for k, v in data.checklist.items() if k.startswith('test5_') and v),
        6: sum(1 for k, v in data.checklist.items() if k.startswith('test6_') and v),
        7: sum(1 for k, v in data.checklist.items() if k.startswith('test7_') and v),
        8: sum(1 for k, v in data.checklist.items() if k.startswith('test8_') and v),
    }

    phase_totals = {1: 5, 2: 5, 3: 5, 4: 6, 5: 5, 6: 5, 7: 5, 8: 5}

    email_body = f"""
EMERGENCE Beta 1.0 - Rapport de Test
=====================================

Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Utilisateur: {data.email}
Navigateur/OS: {data.browserInfo or 'Non spécifié'}

PROGRESSION GLOBALE
-------------------
Complété: {data.completion} ({data.completionPercentage}%)

DÉTAIL PAR PHASE
----------------
"""

    phase_names = {
        1: "Authentification & Onboarding",
        2: "Chat simple avec agents",
        3: "Système de mémoire",
        4: "Documents & RAG",
        5: "Débats autonomes",
        6: "Cockpit & Analytics",
        7: "Tests de robustesse",
        8: "Edge cases & bugs connus"
    }

    for phase_num in range(1, 9):
        count = phase_counts[phase_num]
        total = phase_totals[phase_num]
        percentage = int((count / total) * 100) if total > 0 else 0

        email_body += f"\nPhase {phase_num}: {phase_names[phase_num]}\n"
        email_body += f"  Complété: {count}/{total} ({percentage}%)\n"

        # Add phase comments if present
        comment_field = f"comments{phase_num}"
        comment = getattr(data, comment_field, None)
        if comment and comment.strip():
            email_body += f"  Commentaires:\n    {comment}\n"

    email_body += "\n\nCHECKLIST DÉTAILLÉE\n-------------------\n"

    test_labels = {
        # Phase 1
        "test1_1": "Créer un compte / Se connecter",
        "test1_2": "Vérifier l'affichage du dashboard initial + consulter le tutoriel",
        "test1_3": "Tester le lien 'Mot de passe oublié'",
        "test1_4": "Se déconnecter et se reconnecter",
        "test1_5": "Vérifier la persistance de session",

        # Phase 2
        "test2_1": "Lancer une conversation avec Anima",
        "test2_2": "Lancer une conversation avec Neo",
        "test2_3": "Lancer une conversation avec Nexus",
        "test2_4": "Créer plusieurs threads et basculer entre eux",
        "test2_5": "Supprimer un thread",

        # Phase 3
        "test3_1": "Activer l'analyse mémoire",
        "test3_2": "Ouvrir le Centre Mémoire",
        "test3_3": "Faire référence à une information passée",
        "test3_4": "Tester le 'Clear' mémoire",
        "test3_5": "Tester la détection de topic shift",

        # Phase 4
        "test4_1": "Uploader un document PDF simple",
        "test4_2": "Uploader un document TXT contenant un poème",
        "test4_3": "Activer le RAG et poser des questions",
        "test4_4": "Tester avec document volumineux",
        "test4_5": "Supprimer un document",
        "test4_6": "Tester isolation documents",

        # Phase 5
        "test5_1": "Lancer un débat simple",
        "test5_2": "Vérifier la synthèse finale",
        "test5_3": "Lancer un débat avec RAG",
        "test5_4": "Tester débat long (4+ tours)",
        "test5_5": "Consulter les métriques du débat",

        # Phase 6
        "test6_1": "Ouvrir le Cockpit et consulter résumé coûts",
        "test6_2": "Filtrer par période",
        "test6_3": "Consulter répartition par agent",
        "test6_4": "Monitoring santé",
        "test6_5": "Dashboard admin",

        # Phase 7
        "test7_1": "Envoyer 10 messages rapidement",
        "test7_2": "Uploader 3 documents simultanément",
        "test7_3": "Forcer une déconnexion WebSocket",
        "test7_4": "Tester sur connexion lente",
        "test7_5": "Session très longue (50+ messages)",

        # Phase 8
        "test8_1": "Tester cache mémoire intensif",
        "test8_2": "Accès concurrents (2 onglets)",
        "test8_3": "Document corrompu",
        "test8_4": "Débat sans sujet",
        "test8_5": "Clear pendant consolidation",
    }

    for test_id, completed in data.checklist.items():
        label = test_labels.get(test_id, test_id)
        status = "✅" if completed else "❌"
        email_body += f"{status} {label}\n"

    email_body += "\n\nFEEDBACK GÉNÉRAL\n----------------\n"

    if data.bugs and data.bugs.strip():
        email_body += f"\nBUGS CRITIQUES:\n{data.bugs}\n"

    if data.suggestions and data.suggestions.strip():
        email_body += f"\nSUGGESTIONS:\n{data.suggestions}\n"

    if data.generalComments and data.generalComments.strip():
        email_body += f"\nCOMMENTAIRES LIBRES:\n{data.generalComments}\n"

    email_body += "\n\n---\nRapport généré automatiquement par EMERGENCE Beta Report System"

    return email_body


class BetaInvitationRequest(BaseModel):
    emails: List[str]
    base_url: str = "https://emergence-app.ch"


@router.post("/beta-invite")
async def send_beta_invitations(request: BetaInvitationRequest):
    """
    Send beta invitation emails to a list of users

    Args:
        emails: List of email addresses to invite
        base_url: Base URL of the application (default: https://emergence-app.ch)

    Returns:
        Summary of sent invitations
    """
    if not email_service.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Email service is not configured. Please set EMAIL_ENABLED=1 and configure SMTP settings."
        )

    results = {
        "total": len(request.emails),
        "sent": [],
        "failed": []
    }

    for email in request.emails:
        try:
            success = await email_service.send_beta_invitation_email(
                to_email=email,
                base_url=request.base_url
            )

            if success:
                results["sent"].append(email)
                logger.info(f"Beta invitation sent to {email}")
            else:
                results["failed"].append({"email": email, "reason": "Email service returned false"})
                logger.error(f"Failed to send beta invitation to {email}")

        except Exception as e:
            results["failed"].append({"email": email, "reason": str(e)})
            logger.error(f"Error sending beta invitation to {email}: {e}", exc_info=True)

    return {
        "status": "completed",
        "total": results["total"],
        "sent": len(results["sent"]),
        "failed": len(results["failed"]),
        "sent_to": results["sent"],
        "failed_emails": results["failed"],
        "timestamp": datetime.now().isoformat()
    }


@router.post("/beta-report")
async def submit_beta_report(report: BetaReportRequest):
    """
    Endpoint to submit beta test report.
    Sends the report via email to gonzalefernando@gmail.com
    """
    try:
        # Format email body
        email_body = format_beta_report_email(report)

        # Log the report
        logger.info(f"Beta report received from {report.email}")
        logger.info(f"Completion: {report.completion} ({report.completionPercentage}%)")

        # Save to file for backup
        try:
            from pathlib import Path
            reports_dir = Path("data/beta_reports")
            reports_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_email = report.email.replace("@", "_at_").replace(".", "_")
            filename = reports_dir / f"report_{timestamp}_{safe_email}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                f.write(email_body)

            logger.info(f"Beta report saved to {filename}")

            # Also save JSON version for potential processing
            json_filename = reports_dir / f"report_{timestamp}_{safe_email}.json"
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(report.dict(), f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save beta report to file: {e}")

        # Send email if service is enabled
        email_sent = False
        if email_service.is_enabled():
            try:
                email_sent = await email_service._send_email(
                    to_email="gonzalefernando@gmail.com",
                    subject=f"EMERGENCE Beta Report - {report.email} ({report.completionPercentage}%)",
                    html_body=f"<pre>{email_body}</pre>",
                    text_body=email_body
                )

                if email_sent:
                    logger.info("Beta report emailed successfully")
                else:
                    logger.warning("Email service returned false when sending beta report")

            except Exception as e:
                logger.error(f"Failed to email beta report: {e}", exc_info=True)
        else:
            logger.warning("Email service not enabled - report saved to file only")

        return {
            "status": "success",
            "message": "Merci pour votre rapport! Il a été transmis à l'équipe.",
            "email_sent": email_sent,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error processing beta report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'envoi du rapport. Veuillez réessayer."
        )
