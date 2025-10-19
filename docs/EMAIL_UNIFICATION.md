# 📧 UNIFICATION SYSTÈME EMAIL - PHASE 1 GUARDIAN CLOUD

**Date:** 2025-10-19
**Objectif:** Identifier et unifier les 2 systèmes d'email actuellement en place
**Status:** ✅ AUDIT COMPLET - Prêt pour unification

---

## 🔍 AUDIT COMPLET - 2 SYSTÈMES EMAIL IDENTIFIÉS

### **Système #1: EmailService Principal (Backend)**
**Fichier:** `src/backend/features/auth/email_service.py`
**Lignes:** 881 lignes (gros fichier)
**Type:** Service backend production

#### Caractéristiques:
- ✅ Classe `EmailService` propre et structurée
- ✅ Configuration via `EmailConfig` dataclass
- ✅ Lecture env vars (SMTP_HOST, SMTP_USER, SMTP_PASSWORD, etc.)
- ✅ Méthode `is_enabled()` pour vérifier config
- ✅ TLS support (SMTP + STARTTLS)
- ✅ Timeout 10s
- ✅ Error handling complet (SMTPAuthenticationError, SMTPException)

#### Méthodes disponibles:
```python
async def send_beta_invitation_email(to_email, base_url) -> bool
async def send_custom_email(to_email, subject, html_body, text_body) -> bool
async def send_auth_issue_notification_email(to_email, base_url) -> bool
async def send_password_reset_email(to_email, reset_token, base_url) -> bool
async def _send_email(to_email, subject, html_body, text_body) -> bool  # Méthode interne
```

#### Templates inclus (inline HTML):
1. **Beta Invitation** (lignes 89-265)
   - Style moderne (gradient background, blue theme)
   - 8 phases de test détaillées
   - Links: app_url, report_url
   - Email destination: variable `to_email`

2. **Auth Issue Notification** (lignes 382-575)
   - Notification problèmes auth
   - Lien reset password
   - Formulaire beta

3. **Password Reset** (lignes 675-792)
   - Lien reset avec token
   - Validité 1h
   - Warning si pas demandé

#### Configuration actuelle:
```python
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = env var
SMTP_PASSWORD = env var (SECRET)
SMTP_FROM_EMAIL = env var (default: SMTP_USER)
SMTP_FROM_NAME = "ÉMERGENCE" (default)
SMTP_USE_TLS = True
EMAIL_ENABLED = 0/1 (feature flag)
```

#### Utilisé par:
- Backend auth router (password reset)
- Beta invitation system
- Test scripts (nombreux dans `scripts/test/`)

---

### **Système #2: Guardian Email Scripts (Scripts standalone)**
**Fichiers:**
1. `scripts/guardian_email_report.py` (750 lignes)
2. `claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py` (470 lignes)

#### Caractéristiques:
- ⚠️ **DOUBLONS** - 2 fichiers font exactement la même chose
- ⚠️ Standalone scripts (pas intégrés au backend)
- ⚠️ Réimportent `EmailService` depuis backend
- ⚠️ Génèrent leur propre HTML template inline
- ⚠️ Chargent rapports depuis `reports/` dir
- ⚠️ Logique email dupliquée

#### `guardian_email_report.py` (Système 2A):
**Fonctionnalités:**
- Lance tous les guardians (prod, anima, neo, nexus)
- Charge rapports JSON (prod, docs, integrity, unified, global)
- Génère HTML email Guardian custom
- Template Guardian complet (lignes 130-643):
  - Executive summary (status badge)
  - Production section (logs, errors, warnings)
  - Documentation section (Anima gaps)
  - Intégrité section (Neo issues)
  - Rapport unifié section (Nexus)
  - Section détails corrections (priority badges)
  - Bouton "Auto-fix" avec token sécurisé
- Envoie via `EmailService.send_custom_email()`
- Destination: `gonzalefernando@gmail.com` (hardcodé)

**HTML Template Guardian spécifique:**
- Gradient dark background (#1a1a2e → #16213e)
- Status badges colorés (OK=green, WARNING=orange, CRITICAL=red)
- Sections par agent (ProdGuardian, Anima, Neo, Nexus)
- Metrics cards (logs, errors, warnings, gaps)
- Recommendations lists avec priorités
- Auto-fix button avec JavaScript onclick
- Footer avec contact info

#### `send_guardian_reports_email.py` (Système 2B):
**Fonctionnalités:**
- Charge rapports JSON (global, prod, integrity, docs, unified, orchestration)
- Génère HTML email Guardian similaire
- Template Guardian simplifié (lignes 142-330):
  - Executive summary (status badge)
  - Sections par rapport (prod, integrity, docs, unified, orchestration)
  - Recommendations (max 3 par rapport)
  - Timestamp dernier scan
  - Footer simple
- Envoie via `EmailService.send_custom_email()`
- Destination: `gonzalefernando@gmail.com` (hardcodé via ADMIN_EMAIL constant)

**Différences avec 2A:**
- Plus simple (pas de bouton auto-fix)
- Pas de section "détails corrections"
- Pas de JavaScript
- Support UTF-8 encoding fix pour Windows
- Load .env manuelle si dotenv absent
- Template text/plain plus simple

---

## 📊 COMPARAISON DES 2 SYSTÈMES

| Aspect | Système #1 (Backend) | Système #2A | Système #2B |
|--------|----------------------|-------------|-------------|
| **Fichier** | `email_service.py` | `guardian_email_report.py` | `send_guardian_reports_email.py` |
| **LOC** | 881 | 750 | 470 |
| **Type** | Service backend prod | Script standalone | Script standalone |
| **Templates** | Beta, Auth, Reset | Guardian complet | Guardian simple |
| **Config** | Env vars clean | Import EmailService | Import EmailService |
| **Destinations** | Variable | Hardcodé admin | Hardcodé admin (const) |
| **Use case** | Auth emails | Guardian rapports | Guardian rapports |
| **Auto-fix** | ❌ | ✅ (avec token) | ❌ |
| **HTML quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Maintenance** | ✅ Backend | ⚠️ Script isolé | ⚠️ Script isolé |

---

## 🚨 PROBLÈMES IDENTIFIÉS

### 1. **Duplication de code**
- ❌ 2 scripts Guardian font la même chose (2A et 2B)
- ❌ Templates HTML dupliqués inline (pas de fichiers Jinja2)
- ❌ Logique génération email dupliquée

### 2. **Maintenance difficile**
- ❌ Modifier un template = modifier code Python
- ❌ Pas de séparation HTML/Python
- ❌ 2 versions du même template Guardian

### 3. **Inconsistance**
- ❌ EmailService backend != Guardian scripts
- ❌ Destinations hardcodées dans scripts
- ❌ Pas de méthode `send_guardian_report()` dans EmailService

### 4. **Manque de flexibilité**
- ❌ Templates inline difficiles à tester
- ❌ Pas de preview email sans envoyer
- ❌ Pas de templates Jinja2 réutilisables

### 5. **Secrets management**
- ⚠️ Email admin hardcodé (`gonzalefernando@gmail.com`)
- ⚠️ SMTP password en env var (OK) mais pas Secret Manager

---

## ✅ PLAN D'UNIFICATION

### **Objectif:**
Un seul système email unifié dans `EmailService` avec templates Jinja2 propres.

### **Phase 1.1 - Unifier EmailService** (CETTE PHASE)

#### 1.1.1 - Créer méthode `send_guardian_report()`
**Fichier:** `src/backend/features/auth/email_service.py`

Ajouter méthode:
```python
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
```

#### 1.1.2 - Créer template Jinja2 Guardian
**Fichier:** `src/backend/templates/guardian_report_email.html`

Template unifié avec toutes les sections:
- Executive Summary (status global)
- Production Errors (ProdGuardian)
- Documentation Gaps (Anima)
- Integrity Issues (Neo)
- Unified Report (Nexus)
- Recommendations (priority actions)
- Links (admin UI, Cloud Storage, Cloud Logging)

#### 1.1.3 - Supprimer scripts doublons
**Fichiers à supprimer:**
- ❌ `scripts/guardian_email_report.py`
- ❌ `claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py`

**Remplacer par:**
- ✅ Backend endpoint `/api/guardian/send-report` (Phase 5)
- ✅ Cloud Scheduler trigger (Phase 6)

#### 1.1.4 - Migrer logique scripts → Backend
**Créer:** `src/backend/features/guardian/email_report.py`

Service pour:
- Charger rapports depuis `reports/` dir ou Cloud Storage
- Préparer données pour template
- Appeler `EmailService.send_guardian_report()`

---

### **Phase 1.2 - Templates Jinja2** (CETTE PHASE)

#### Structure templates:
```
src/backend/templates/
├── guardian_report_email.html     (nouveau - Guardian complet)
├── beta_invitation_email.html     (extrait de email_service.py)
├── auth_issue_email.html          (extrait de email_service.py)
├── password_reset_email.html      (extrait de email_service.py)
└── email_base.html                (template base commun)
```

#### Avantages Jinja2:
- ✅ Séparation HTML/Python
- ✅ Héritage templates (DRY)
- ✅ Testable indépendamment
- ✅ Preview facile
- ✅ Maintenance simplifiée

---

### **Phase 1.3 - Configuration unifiée**

#### Variables environnement:
```env
# SMTP Config (existant)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=gonzalefernando@gmail.com
SMTP_PASSWORD=<SECRET>
SMTP_FROM_EMAIL=gonzalefernando@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
EMAIL_ENABLED=1

# Guardian Config (nouveau)
GUARDIAN_ADMIN_EMAIL=gonzalefernando@gmail.com
GUARDIAN_REPORT_FREQUENCY=2h  # Pour Cloud Scheduler Phase 6
BACKEND_URL=https://emergence-app.ch
```

#### Migration Secret Manager (optionnel Phase 6):
```bash
gcloud secrets create smtp-password --data-file=<(echo -n "$SMTP_PASSWORD")
gcloud secrets create guardian-admin-email --data-file=<(echo -n "gonzalefernando@gmail.com")
```

---

## 🎯 LIVRABLES PHASE 1

### Fichiers modifiés:
- ✅ `src/backend/features/auth/email_service.py`
  - Ajouter méthode `send_guardian_report()`
  - Refactor templates inline → Jinja2 loading

### Fichiers créés:
- ✅ `src/backend/templates/guardian_report_email.html`
- ✅ `src/backend/templates/beta_invitation_email.html`
- ✅ `src/backend/templates/auth_issue_email.html`
- ✅ `src/backend/templates/password_reset_email.html`
- ✅ `src/backend/templates/email_base.html`
- ✅ `src/backend/features/guardian/email_report.py` (nouveau service)

### Fichiers supprimés:
- ❌ `scripts/guardian_email_report.py`
- ❌ `claude-plugins/integrity-docs-guardian/scripts/send_guardian_reports_email.py`

### Documentation:
- ✅ `docs/EMAIL_UNIFICATION.md` (ce fichier)

---

## 📋 CHECKLIST PHASE 1

### Audit (COMPLET ✅)
- [x] Identifier tous les `send_email` / `EmailService`
- [x] Identifier les 2 systèmes différents
- [x] Lister différences (templates, triggers, config)
- [x] Documenter architecture actuelle

### Unification (EN COURS 🚧)
- [ ] Créer templates Jinja2
  - [ ] `email_base.html` (template base)
  - [ ] `guardian_report_email.html` (Guardian complet)
  - [ ] `beta_invitation_email.html` (migrer inline)
  - [ ] `auth_issue_email.html` (migrer inline)
  - [ ] `password_reset_email.html` (migrer inline)
- [ ] Modifier `EmailService`
  - [ ] Ajouter Jinja2 loader
  - [ ] Refactor méthodes pour utiliser templates
  - [ ] Ajouter `send_guardian_report()`
- [ ] Créer `GuardianEmailService`
  - [ ] Load rapports
  - [ ] Préparer data template
  - [ ] Call EmailService
- [ ] Supprimer doublons
  - [ ] Delete `guardian_email_report.py`
  - [ ] Delete `send_guardian_reports_email.py`
- [ ] Tests
  - [ ] Test envoi Guardian complet
  - [ ] Test tous templates
  - [ ] Vérifier rendu HTML

---

## 🔧 IMPLÉMENTATION TECHNIQUE

### Jinja2 Integration

#### Installation:
```bash
pip install jinja2
```

#### EmailService modifications:
```python
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

class EmailService:
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or build_email_config_from_env()

        # Setup Jinja2
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def _render_template(self, template_name: str, context: dict) -> str:
        """Render Jinja2 template with context"""
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    async def send_guardian_report(
        self,
        to_email: str,
        reports: Dict[str, Optional[Dict]],
        base_url: str = "https://emergence-app.ch",
    ) -> bool:
        """Send Guardian monitoring report"""
        if not self.is_enabled():
            logger.warning("Email service is not enabled")
            return False

        # Préparer context
        context = {
            'timestamp': datetime.now().strftime("%d/%m/%Y à %H:%M:%S"),
            'reports': reports,
            'base_url': base_url,
            'admin_ui_url': f"{base_url}/admin",
            'cloud_storage_url': f"{base_url}/api/guardian/reports",
            'cloud_logging_url': "https://console.cloud.google.com/logs",
        }

        # Render template
        html_body = self._render_template('guardian_report_email.html', context)
        text_body = self._render_template('guardian_report_email.txt', context)

        subject = f"🛡️ Guardian ÉMERGENCE - {context['timestamp']}"

        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
```

### GuardianEmailService

**Fichier:** `src/backend/features/guardian/email_report.py`

```python
"""Guardian Email Report Service"""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from features.auth.email_service import EmailService

class GuardianEmailService:
    """Service for sending Guardian monitoring reports via email"""

    def __init__(self, reports_dir: Path = None):
        self.reports_dir = reports_dir or Path(__file__).parent.parent.parent.parent / "reports"
        self.email_service = EmailService()

    def load_report(self, report_name: str) -> Optional[Dict]:
        """Load a Guardian report JSON file"""
        report_path = self.reports_dir / report_name
        if not report_path.exists():
            return None

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {report_name}: {e}")
            return None

    def load_all_reports(self) -> Dict[str, Optional[Dict]]:
        """Load all Guardian reports"""
        report_files = [
            'global_report.json',
            'prod_report.json',
            'integrity_report.json',
            'docs_report.json',
            'unified_report.json',
        ]

        return {
            name: self.load_report(name)
            for name in report_files
        }

    async def send_report(self, to_email: str = None) -> bool:
        """Send Guardian report email"""
        # Load all reports
        reports = self.load_all_reports()

        # Default admin email
        if not to_email:
            to_email = os.getenv("GUARDIAN_ADMIN_EMAIL", "gonzalefernando@gmail.com")

        # Send via EmailService
        return await self.email_service.send_guardian_report(
            to_email=to_email,
            reports=reports,
        )
```

---

## 🚀 PROCHAINES ÉTAPES

### Phase 1 (EN COURS - 2j):
1. ✅ Audit complet (FAIT)
2. 🚧 Créer templates Jinja2 (EN COURS)
3. ⏳ Unifier EmailService (NEXT)
4. ⏳ Tester envoi Guardian (NEXT)

### Phase 2 (3j):
- Usage Tracking System
- Middleware tracking requêtes
- UsageGuardian agent

### Phase 3 (4j):
- Gmail API Integration
- OAuth2 flow
- Codex read reports

### Phase 4 (2j):
- Admin UI trigger audit
- Frontend admin-guardian.js

### Phase 5 (2j):
- Unified Email Reporting
- Cloud Scheduler config

### Phase 6 (2j):
- Cloud Run deployment
- Tests E2E

---

## 📞 CONTACT

**Questions/Issues:**
- Email: gonzalefernando@gmail.com
- Agent: Claude Code
- Date: 2025-10-19

---

**🤖 Document généré par Claude Code dans le cadre de la Phase 1 - Guardian Cloud Implementation**
