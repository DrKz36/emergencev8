#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration des alertes GCP pour monitoring mémoire Cloud Run.

Configure une alerte qui se déclenche quand l'utilisation mémoire
dépasse 80% de la limite configurée (2Gi).

Usage:
    python scripts/setup_gcp_memory_alerts.py
    python scripts/setup_gcp_memory_alerts.py --dry-run
    python scripts/setup_gcp_memory_alerts.py --email admin@example.com
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Fix encoding Windows
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

# Configuration
PROJECT_ID = "emergence-469005"
SERVICE_NAME = "emergence-app"
REGION = "europe-west1"
MEMORY_THRESHOLD = 0.80  # 80%
MEMORY_LIMIT_GB = 2  # 2Gi


def run_command(cmd: list[str], dry_run: bool = False) -> dict[str, Any]:
    """Exécute une commande gcloud et retourne le résultat."""
    if dry_run:
        print(f"[DRY-RUN] Would run: {' '.join(cmd)}")
        return {"dry_run": True}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        if result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"output": result.stdout.strip()}
        return {"success": True}
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur: {e.stderr}", file=sys.stderr)
        return {"error": str(e)}
    except subprocess.TimeoutExpired:
        print("❌ Timeout (60s)", file=sys.stderr)
        return {"error": "timeout"}


def create_notification_channel(email: str, dry_run: bool = False) -> str | None:
    """Crée un canal de notification email."""
    print(f"\n📧 Création canal de notification: {email}")

    # Vérifier si le canal existe déjà
    cmd_list = [
        "gcloud", "alpha", "monitoring", "channels", "list",
        f"--project={PROJECT_ID}",
        "--format=json",
    ]
    result = run_command(cmd_list, dry_run=False)

    if isinstance(result, dict) and "error" not in result and isinstance(result, list):
        for channel in result:
            if channel.get("type") == "email" and email in str(channel.get("labels", {})):
                channel_id = channel.get("name", "").split("/")[-1]
                print(f"✅ Canal existant trouvé: {channel_id}")
                return channel_id

    # Créer le canal
    channel_config = {
        "type": "email",
        "displayName": f"Emergence Memory Alert - {email}",
        "labels": {
            "email_address": email,
        },
        "enabled": True,
    }

    config_file = Path("temp_channel_config.json")
    if not dry_run:
        config_file.write_text(json.dumps(channel_config, indent=2))

    cmd_create = [
        "gcloud", "alpha", "monitoring", "channels", "create",
        f"--project={PROJECT_ID}",
        f"--channel-content-from-file={config_file}",
        "--format=json",
    ]

    result = run_command(cmd_create, dry_run)

    if not dry_run:
        config_file.unlink(missing_ok=True)

    if isinstance(result, dict) and "name" in result:
        channel_id = result["name"].split("/")[-1]
        print(f"✅ Canal créé: {channel_id}")
        return channel_id

    if dry_run:
        return "DRY_RUN_CHANNEL_ID"

    return None


def create_memory_alert_policy(
    channel_id: str,
    dry_run: bool = False,
) -> bool:
    """Crée une politique d'alerte pour l'utilisation mémoire."""
    print(f"\n🔔 Création politique d'alerte mémoire > {MEMORY_THRESHOLD*100}%")

    # Configuration de la politique d'alerte
    alert_policy = {
        "displayName": f"Emergence Cloud Run - Memory > {MEMORY_THRESHOLD*100}%",
        "documentation": {
            "content": f"""
# Alerte Mémoire Cloud Run

**Service:** {SERVICE_NAME}
**Région:** {REGION}
**Seuil:** {MEMORY_THRESHOLD*100}% de {MEMORY_LIMIT_GB}Gi ({MEMORY_LIMIT_GB * MEMORY_THRESHOLD:.1f}Gi)

## Actions recommandées

1. **Vérifier les métriques détaillées:**
   ```bash
   gcloud run services describe {SERVICE_NAME} --region={REGION} --format=json
   ```

2. **Consulter les logs récents:**
   ```bash
   python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
   ```

3. **Analyser les rapports Guardian:**
   - Rapport prod: `reports/prod_report.json`
   - Résumé: `reports/codex_summary.md`

4. **Si utilisation > 90% persistante:**
   ```bash
   # Augmenter à 4Gi
   gcloud run services update {SERVICE_NAME} --memory=4Gi --region={REGION}
   ```

## Contexte

Alerte configurée après résolution OOM (2025-10-21).
Limite actuelle: 2Gi (upgrade depuis 1Gi après crashs).
""",
            "mimeType": "text/markdown",
        },
        "conditions": [
            {
                "displayName": f"Memory utilization > {MEMORY_THRESHOLD*100}%",
                "conditionThreshold": {
                    "filter": f'resource.type="cloud_run_revision" AND resource.labels.service_name="{SERVICE_NAME}" AND metric.type="run.googleapis.com/container/memory/utilizations"',
                    "comparison": "COMPARISON_GT",
                    "thresholdValue": MEMORY_THRESHOLD,
                    "duration": "300s",  # 5 minutes
                    "aggregations": [
                        {
                            "alignmentPeriod": "60s",
                            "perSeriesAligner": "ALIGN_MEAN",
                        },
                    ],
                },
            },
        ],
        "combiner": "OR",
        "enabled": True,
        "notificationChannels": [
            f"projects/{PROJECT_ID}/notificationChannels/{channel_id}",
        ],
        "alertStrategy": {
            "autoClose": "604800s",  # 7 jours
            "notificationRateLimit": {
                "period": "3600s",  # Max 1 notification par heure
            },
        },
    }

    policy_file = Path("temp_alert_policy.json")
    if not dry_run:
        policy_file.write_text(json.dumps(alert_policy, indent=2))

    cmd_create = [
        "gcloud", "alpha", "monitoring", "policies", "create",
        f"--project={PROJECT_ID}",
        f"--policy-from-file={policy_file}",
        "--format=json",
    ]

    result = run_command(cmd_create, dry_run)

    if not dry_run:
        policy_file.unlink(missing_ok=True)

    if isinstance(result, dict) and ("name" in result or dry_run):
        print(f"✅ Politique d'alerte créée: {result.get('name', 'DRY_RUN')}")
        return True

    return False


def verify_alert_setup(dry_run: bool = False) -> None:
    """Vérifie la configuration des alertes."""
    if dry_run:
        print("\n[DRY-RUN] Skip verification")
        return

    print("\n🔍 Vérification de la configuration...")

    # Lister les politiques d'alerte
    cmd_list = [
        "gcloud", "alpha", "monitoring", "policies", "list",
        f"--project={PROJECT_ID}",
        "--format=json",
    ]
    result = run_command(cmd_list, dry_run=False)

    if isinstance(result, list):
        memory_alerts = [
            p for p in result
            if "Memory" in p.get("displayName", "")
            and SERVICE_NAME in str(p.get("conditions", []))
        ]
        print(f"✅ {len(memory_alerts)} alerte(s) mémoire configurée(s)")

        for alert in memory_alerts:
            print(f"   - {alert.get('displayName')}")
            print(f"     État: {'✅ Activée' if alert.get('enabled') else '❌ Désactivée'}")
    else:
        print("⚠️  Impossible de vérifier les alertes")


def main() -> None:
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Configure alertes GCP mémoire Cloud Run",
    )
    parser.add_argument(
        "--email",
        default="gonzalefernando@gmail.com",
        help="Email pour notifications (défaut: gonzalefernando@gmail.com)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulation sans modifications",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🔔 Configuration Alertes GCP - Mémoire Cloud Run")
    print("=" * 60)
    print(f"Projet: {PROJECT_ID}")
    print(f"Service: {SERVICE_NAME}")
    print(f"Région: {REGION}")
    print(f"Seuil: {MEMORY_THRESHOLD*100}% de {MEMORY_LIMIT_GB}Gi")
    print(f"Email: {args.email}")
    print(f"Mode: {'🧪 DRY-RUN' if args.dry_run else '🚀 PRODUCTION'}")
    print("=" * 60)

    # 1. Créer canal de notification
    channel_id = create_notification_channel(args.email, args.dry_run)
    if not channel_id:
        print("\n❌ Échec création canal de notification")
        sys.exit(1)

    # 2. Créer politique d'alerte
    success = create_memory_alert_policy(channel_id, args.dry_run)
    if not success:
        print("\n❌ Échec création politique d'alerte")
        sys.exit(1)

    # 3. Vérifier configuration
    verify_alert_setup(args.dry_run)

    print("\n" + "=" * 60)
    if args.dry_run:
        print("✅ DRY-RUN terminé - Aucune modification effectuée")
        print("\nPour appliquer réellement:")
        print(f"  python {__file__} --email {args.email}")
    else:
        print("✅ Alertes GCP configurées avec succès")
        print("\nProchaines étapes:")
        print("1. Vérifier réception email test (peut prendre quelques minutes)")
        print("2. Consulter alertes: https://console.cloud.google.com/monitoring/alerting")
        print(f"3. Tester: Pousser memory > {MEMORY_THRESHOLD*100}% pendant 5 min")
    print("=" * 60)


if __name__ == "__main__":
    main()
