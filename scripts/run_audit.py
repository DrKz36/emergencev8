#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÉMERGENCE V8 - Guardian Verification & Audit System
Vérifie l'intégrité complète du système et génère un rapport de vérification
Usage: python scripts/run_audit.py --target emergence-app-00501-zon --mode full
"""

import os
import sys
import json
import asyncio
import argparse
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Fix encoding Windows
if sys.platform == 'win32':
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass  # Déjà wrappé ou pas de buffer

# Charger les variables d'environnement
try:
    from dotenv import load_dotenv
    repo_root = Path(__file__).parent.parent
    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    print("⚠️  python-dotenv non installé")

# Ajouter le chemin backend
backend_path = Path(__file__).parent.parent / "src" / "backend"
sys.path.insert(0, str(backend_path))

# Imports Guardian
guardian_scripts_path = Path(__file__).parent.parent / "claude-plugins" / "integrity-docs-guardian" / "scripts"
sys.path.insert(0, str(guardian_scripts_path))

# Configuration
REPORTS_DIR = Path(__file__).parent.parent / "reports"
CLAUDE_PLUGINS_REPORTS_DIR = Path(__file__).parent.parent / "claude-plugins" / "integrity-docs-guardian" / "scripts" / "reports"
ADMIN_EMAIL = "gonzalefernando@gmail.com"


class AuditOrchestrator:
    """Orchestre l'audit complet du système ÉMERGENCE"""

    def __init__(self, target_revision: str = "emergence-app-00501-zon", mode: str = "full"):
        self.target_revision = target_revision
        self.mode = mode
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.results = {}
        self.repo_root = Path(__file__).parent.parent

    async def run_full_audit(self) -> Dict:
        """Lance l'audit complet du système"""
        print(f"🔍 Démarrage de l'audit complet pour {self.target_revision}")
        print(f"⏰ Timestamp: {self.timestamp}")
        print(f"📂 Mode: {self.mode}\n")

        # 1. Vérifier l'existence des rapports Guardian
        print("📊 [1/6] Vérification des rapports Guardian existants...")
        guardian_reports = await self._check_guardian_reports()
        self.results['guardian_reports'] = guardian_reports

        # 2. Vérifier la production Cloud Run
        print("\n☁️  [2/6] Vérification de la production Cloud Run...")
        prod_status = await self._check_production_cloudrun()
        self.results['production'] = prod_status

        # 3. Vérifier l'intégrité backend/frontend
        print("\n🔧 [3/6] Vérification de l'intégrité backend/frontend...")
        integrity_status = await self._check_integrity()
        self.results['integrity'] = integrity_status

        # 4. Vérifier les endpoints API
        print("\n🌐 [4/6] Vérification des endpoints API...")
        endpoints_status = await self._check_endpoints()
        self.results['endpoints'] = endpoints_status

        # 5. Vérifier la documentation
        print("\n📚 [5/6] Vérification de la documentation...")
        docs_status = await self._check_documentation()
        self.results['documentation'] = docs_status

        # 6. Générer le rapport de synthèse
        print("\n📝 [6/6] Génération du rapport de synthèse...")
        verification_report = await self._generate_verification_report()
        self.results['verification_report'] = verification_report

        return self.results

    async def _check_guardian_reports(self) -> Dict:
        """Vérifie l'existence et le statut des rapports Guardian"""

        def normalize_status(raw_status: Any) -> str:
            if raw_status is None:
                return 'UNKNOWN'
            status_str = str(raw_status).strip()
            if not status_str:
                return 'UNKNOWN'
            upper = status_str.upper()
            if upper in {'OK', 'HEALTHY', 'SUCCESS'}:
                return 'OK'
            if upper in {'WARNING', 'WARN'}:
                return 'WARNING'
            if upper in {'NEEDS_UPDATE', 'STALE'}:
                return 'NEEDS_UPDATE'
            if upper in {'ERROR', 'FAILED', 'FAILURE'}:
                return 'ERROR'
            if upper in {'CRITICAL', 'SEVERE'}:
                return 'CRITICAL'
            return upper

        def extract_status(report_name: str, report_data: Dict[str, Any]) -> Tuple[str, str]:
            candidates = [report_data.get('status')]

            executive_summary = report_data.get('executive_summary')
            if isinstance(executive_summary, dict):
                candidates.append(executive_summary.get('status'))

            if report_name == 'orchestration_report.json':
                candidates.append(report_data.get('global_status'))

            status = 'UNKNOWN'
            for candidate in candidates:
                normalized = normalize_status(candidate)
                if normalized != 'UNKNOWN':
                    status = normalized
                    break

            timestamp = report_data.get('timestamp')
            if not timestamp:
                metadata = report_data.get('metadata')
                if isinstance(metadata, dict):
                    timestamp = metadata.get('timestamp')

            return status, timestamp or 'N/A'

        reports_status = {}
        expected_reports = [
            'global_report.json',
            'prod_report.json',
            'integrity_report.json',
            'docs_report.json',
            'unified_report.json',
            'orchestration_report.json'
        ]

        for report_name in expected_reports:
            # Chercher dans les 2 répertoires possibles
            main_path = REPORTS_DIR / report_name
            plugin_path = CLAUDE_PLUGINS_REPORTS_DIR / report_name

            report_path = None
            if main_path.exists():
                report_path = main_path
            elif plugin_path.exists():
                report_path = plugin_path

            if report_path:
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)

                    if isinstance(report_data, dict):
                        status, timestamp = extract_status(report_name, report_data)
                    else:
                        status, timestamp = 'UNKNOWN', 'N/A'

                    reports_status[report_name] = {
                        'status': status,
                        'path': str(report_path),
                        'timestamp': timestamp
                    }
                    emoji = '✅' if status == 'OK' else '⚠️'
                    print(f"  {emoji} {report_name}: {status} (màj: {timestamp})")
                except Exception as e:
                    reports_status[report_name] = {
                        'status': 'ERROR',
                        'error': str(e)
                    }
                    print(f"  ❌ {report_name}: Erreur de lecture - {e}")
            else:
                reports_status[report_name] = {
                    'status': 'MISSING',
                    'checked_paths': [str(main_path), str(plugin_path)]
                }
                print(f"  ❌ {report_name}: MANQUANT")

        return reports_status

    async def _check_production_cloudrun(self) -> Dict:
        """Vérifie l'état de la production Cloud Run"""
        prod_report_path = REPORTS_DIR / 'prod_report.json'

        if not prod_report_path.exists():
            return {
                'status': 'UNKNOWN',
                'error': 'prod_report.json non trouvé'
            }

        try:
            with open(prod_report_path, 'r', encoding='utf-8') as f:
                prod_data = json.load(f)

            status = prod_data.get('status', 'UNKNOWN')
            summary = prod_data.get('summary', {})

            print(f"  Service: {prod_data.get('service', 'N/A')}")
            print(f"  Région: {prod_data.get('region', 'N/A')}")
            print(f"  Statut: {status}")
            print(f"  Logs analysés: {prod_data.get('logs_analyzed', 0)}")
            print(f"  Fraîcheur: {prod_data.get('freshness', 'N/A')}")

            if isinstance(summary, dict):
                print(f"  Erreurs: {summary.get('errors', 0)}")
                print(f"  Warnings: {summary.get('warnings', 0)}")
                print(f"  Signaux critiques: {summary.get('critical_signals', 0)}")

            return {
                'status': status,
                'service': prod_data.get('service'),
                'region': prod_data.get('region'),
                'summary': summary,
                'revision_checked': self.target_revision,
                'timestamp': prod_data.get('timestamp')
            }

        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e)
            }

    async def _check_integrity(self) -> Dict:
        """Vérifie l'intégrité backend/frontend"""
        # Vérifier les fichiers critiques
        critical_files = [
            'src/backend/main.py',
            'src/backend/features/chat/service.py',
            'src/frontend/features/chat/chat.js',
            'src/backend/features/auth/router.py',
            'src/backend/features/memory/router.py',
            'src/backend/features/memory/vector_service.py',
            'src/backend/features/dashboard/admin_router.py',
        ]

        files_check = {}
        all_ok = True

        for file_path in critical_files:
            full_path = self.repo_root / file_path
            exists = full_path.exists()
            files_check[file_path] = {
                'exists': exists,
                'size': full_path.stat().st_size if exists else 0
            }
            if not exists:
                all_ok = False
                print(f"  ❌ {file_path}: MANQUANT")
            else:
                print(f"  ✅ {file_path}: OK ({files_check[file_path]['size']} bytes)")

        return {
            'status': 'OK' if all_ok else 'CRITICAL',
            'files_checked': len(critical_files),
            'files_ok': sum(1 for f in files_check.values() if f['exists']),
            'details': files_check
        }

    async def _check_endpoints(self) -> Dict:
        """Vérifie la cohérence des endpoints API"""
        # Vérifier que les routes backend existent
        backend_main = self.repo_root / 'src' / 'backend' / 'main.py'

        if not backend_main.exists():
            return {
                'status': 'ERROR',
                'error': 'main.py non trouvé'
            }

        try:
            with open(backend_main, 'r', encoding='utf-8') as f:
                main_content = f.read()

            # Chercher les includes de routers
            expected_routers = [
                'auth.router',
                'chat.router',
                'memory.router',
                'documents.router',
                'dashboard.admin_router'
            ]

            routers_found = {}
            for router in expected_routers:
                found = router in main_content
                routers_found[router] = found
                emoji = '✅' if found else '❌'
                print(f"  {emoji} {router}: {'OK' if found else 'MANQUANT'}")

            all_found = all(routers_found.values())

            return {
                'status': 'OK' if all_found else 'WARNING',
                'routers_checked': len(expected_routers),
                'routers_found': sum(routers_found.values()),
                'details': routers_found
            }

        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e)
            }

    async def _check_documentation(self) -> Dict:
        """Vérifie la présence de la documentation"""
        critical_docs = [
            'AGENT_SYNC.md',
            'AGENTS.md',
            'CODEV_PROTOCOL.md',
            'docs/passation.md',
            'docs/architecture/00-Overview.md',
            'ROADMAP_OFFICIELLE.md'
        ]

        docs_check = {}
        all_ok = True

        for doc_path in critical_docs:
            full_path = self.repo_root / doc_path
            exists = full_path.exists()
            docs_check[doc_path] = exists
            if not exists:
                all_ok = False
                print(f"  ❌ {doc_path}: MANQUANT")
            else:
                print(f"  ✅ {doc_path}: OK")

        return {
            'status': 'OK' if all_ok else 'WARNING',
            'docs_checked': len(critical_docs),
            'docs_found': sum(docs_check.values()),
            'details': docs_check
        }

    async def _generate_verification_report(self) -> Dict:
        """Génère le rapport de vérification final"""
        # Calculer le statut global
        global_status = 'OK'
        issues = []

        # Vérifier les rapports Guardian
        guardian = self.results.get('guardian_reports', {})
        missing_reports = [name for name, status in guardian.items() if status.get('status') == 'MISSING']
        if missing_reports:
            issues.append(f"Rapports Guardian manquants: {', '.join(missing_reports)}")
            global_status = 'WARNING'

        # Vérifier la production
        prod = self.results.get('production', {})
        if prod.get('status') not in ['OK', 'ok', 'healthy']:
            issues.append(f"Production status: {prod.get('status')}")
            global_status = 'CRITICAL'

        # Vérifier l'intégrité
        integrity = self.results.get('integrity', {})
        if integrity.get('status') != 'OK':
            issues.append(f"Intégrité: {integrity.get('status')}")
            if integrity.get('status') == 'CRITICAL':
                global_status = 'CRITICAL'
            elif global_status == 'OK':
                global_status = 'WARNING'

        # Vérifier les endpoints
        endpoints = self.results.get('endpoints', {})
        if endpoints.get('status') != 'OK':
            issues.append(f"Endpoints: {endpoints.get('status')}")
            if global_status == 'OK':
                global_status = 'WARNING'

        # Calculer le score d'intégrité
        total_checks = 0
        passed_checks = 0

        # Guardian reports
        total_checks += len(guardian)
        passed_checks += sum(1 for s in guardian.values() if s.get('status') in ['OK', 'ok', 'healthy'])

        # Integrity files
        if 'files_checked' in integrity:
            total_checks += integrity['files_checked']
            passed_checks += integrity.get('files_ok', 0)

        # Endpoints
        if 'routers_checked' in endpoints:
            total_checks += endpoints['routers_checked']
            passed_checks += endpoints.get('routers_found', 0)

        # Documentation
        docs = self.results.get('documentation', {})
        if 'docs_checked' in docs:
            total_checks += docs['docs_checked']
            passed_checks += docs.get('docs_found', 0)

        integrity_score = int((passed_checks / total_checks * 100)) if total_checks > 0 else 0

        report = {
            'timestamp': self.timestamp,
            'revision_checked': self.target_revision,
            'previous_revision': 'emergence-app-00298-g8j',
            'status': global_status,
            'integrity_score': f"{integrity_score}%",
            'checks': {
                'total': total_checks,
                'passed': passed_checks,
                'failed': total_checks - passed_checks
            },
            'files': {
                'global_report.json': guardian.get('global_report.json', {}).get('status', 'MISSING'),
                'unified_report.json': guardian.get('unified_report.json', {}).get('status', 'MISSING'),
                'orchestration_report.json': guardian.get('orchestration_report.json', {}).get('status', 'MISSING'),
                'prod_report.json': guardian.get('prod_report.json', {}).get('status', 'MISSING')
            },
            'summary': {
                'backend_integrity': integrity.get('status', 'UNKNOWN'),
                'frontend_integrity': integrity.get('status', 'UNKNOWN'),
                'ws_health': prod.get('status', 'UNKNOWN'),
                'prod_status': prod.get('status', 'UNKNOWN'),
                'endpoints_health': endpoints.get('status', 'UNKNOWN'),
                'documentation_health': docs.get('status', 'UNKNOWN')
            },
            'issues': issues,
            'details': {
                'guardian_reports': guardian,
                'production': prod,
                'integrity': integrity,
                'endpoints': endpoints,
                'documentation': docs
            }
        }

        # Sauvegarder le rapport
        output_path = REPORTS_DIR / 'guardian_verification_report.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n📝 Rapport de vérification sauvegardé: {output_path}")
        print(f"\n{'='*60}")
        print(f"🎯 RÉSUMÉ DE L'AUDIT")
        print(f"{'='*60}")
        print(f"Révision vérifiée: {self.target_revision}")
        print(f"Statut global: {self._format_status_emoji(global_status)} {global_status}")
        print(f"Intégrité: {integrity_score}%")
        print(f"Checks: {passed_checks}/{total_checks} passés")

        if issues:
            print(f"\n⚠️  Problèmes détectés:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"\n✅ Aucun problème détecté")

        print(f"\n{'='*60}\n")

        return report

    def _format_status_emoji(self, status: str) -> str:
        """Retourne un emoji selon le statut"""
        status_lower = status.lower()
        if status_lower in ['ok', 'healthy', 'success']:
            return '✅'
        elif status_lower in ['warning', 'degraded']:
            return '⚠️'
        elif status_lower in ['error', 'critical', 'failed']:
            return '🚨'
        else:
            return '📊'


async def send_email_report():
    """Envoie le rapport par email en utilisant le script existant"""
    print("\n📧 Envoi du rapport par email...")

    try:
        import subprocess

        # Appeler le script d'envoi d'email via subprocess pour éviter les conflits d'encodage
        script_path = guardian_scripts_path / "send_guardian_reports_email.py"

        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60
        )

        success = result.returncode == 0

        if success:
            print(f"✅ Rapport envoyé avec succès à {ADMIN_EMAIL}")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ Échec de l'envoi du rapport (code: {result.returncode})")
            if result.stderr:
                print(f"Erreur: {result.stderr}")

        return success

    except subprocess.TimeoutExpired:
        print(f"⏱️  Timeout lors de l'envoi d'email (> 60s)")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi d'email: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description='ÉMERGENCE V8 Guardian Verification & Audit System'
    )
    parser.add_argument(
        '--target',
        default='emergence-app-00501-zon',
        help='Révision Cloud Run cible (défaut: emergence-app-00501-zon)'
    )
    parser.add_argument(
        '--mode',
        choices=['quick', 'full'],
        default='full',
        help='Mode d\'audit (quick ou full)'
    )
    parser.add_argument(
        '--no-email',
        action='store_true',
        help='Ne pas envoyer d\'email après l\'audit'
    )

    args = parser.parse_args()

    print(f"""
============================================================
  EMERGENCE V8 - Guardian Verification System
============================================================

Target: {args.target}
Mode: {args.mode.upper()}
Email: {'Desactive' if args.no_email else f'Active ({ADMIN_EMAIL})'}

""")

    try:
        # Créer le répertoire reports s'il n'existe pas
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        # Lancer l'audit
        orchestrator = AuditOrchestrator(
            target_revision=args.target,
            mode=args.mode
        )

        results = await orchestrator.run_full_audit()

        # Envoyer l'email si demandé
        if not args.no_email:
            await send_email_report()
        else:
            print("\n📧 Envoi d'email désactivé (--no-email)")

        # Déterminer le code de sortie
        verification_report = results.get('verification_report', {})
        status = verification_report.get('status', 'UNKNOWN')

        if status == 'OK':
            print("\n✅ Audit terminé avec succès - Système sain")
            sys.exit(0)
        elif status == 'WARNING':
            print("\n⚠️  Audit terminé - Avertissements détectés")
            sys.exit(1)
        else:
            print("\n🚨 Audit terminé - Problèmes critiques détectés")
            sys.exit(2)

    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())
