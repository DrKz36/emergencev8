# 🔧 Guardian Auto-Fix - Documentation

**Système d'auto-correction automatisé des problèmes détectés par les Guardians**

---

## 🎯 Vue d'ensemble

Le système Guardian Auto-Fix permet d'appliquer automatiquement les corrections recommandées par les Guardians directement depuis l'email de rapport.

### Workflow complet

```
1. Guardian Email Report envoyé toutes les 2h
   ↓
2. Email contient:
   - Résumé des statuts (Production, Docs, Intégrité, Unified)
   - Détails des 10 premiers problèmes détectés
   - Bouton "🔧 Appliquer les corrections automatiquement"
   ↓
3. Clic sur le bouton
   ↓
4. JavaScript fait POST /api/guardian/auto-fix avec token HMAC
   ↓
5. Backend vérifie token (valide 24h)
   ↓
6. Backend applique corrections automatiques
   ↓
7. Retour JSON avec résultat (fixed, skipped, failed)
   ↓
8. Alert affiche le résumé des corrections
```

---

## 🔐 Sécurité

### Token HMAC avec expiration

Chaque email contient un **token unique HMAC-SHA256** avec:
- **Report ID**: `guardian-YYYYMMDD-HHMMSS`
- **Timestamp**: Unix timestamp de génération
- **Signature**: HMAC du report_id:timestamp avec secret

**Format token:**
```
guardian-20251019-153000:1734621000:a3f8b2c...
```

**Secret:** Défini dans `.env` avec `GUARDIAN_SECRET` (doit être identique backend + scripts)

**Expiration:** 24 heures max (vérifié côté backend)

---

## 📁 Architecture

### Backend: `/api/guardian/*`

**Fichiers:**
- `src/backend/features/guardian/router.py` - Routes FastAPI
- `src/backend/features/guardian/__init__.py` - Module init

**Endpoints:**

#### `POST /api/guardian/auto-fix`
Applique automatiquement les corrections Guardian

**Headers requis:**
```
X-Guardian-Token: <token-hmac>
```

**Réponse succès (200):**
```json
{
  "status": "success",
  "message": "Corrections Guardian appliquées",
  "details": {
    "timestamp": "2025-10-19T15:30:00",
    "anima": {
      "fixed": [...],
      "failed": [...],
      "skipped": [...]
    },
    "neo": { ... },
    "prod": { ... },
    "total_fixed": 5,
    "total_failed": 0,
    "total_skipped": 3
  }
}
```

**Erreurs:**
- `401`: Token manquant
- `403`: Token invalide ou expiré
- `404`: Aucun rapport Guardian trouvé
- `500`: Erreur interne

#### `GET /api/guardian/status`
Récupère le statut actuel des Guardians (sans auth)

**Réponse:**
```json
{
  "timestamp": "2025-10-19T15:30:00",
  "reports_available": ["prod", "docs", "integrity", "unified"],
  "reports_missing": []
}
```

### Scripts: Email + Token Generation

**Fichiers:**
- `scripts/guardian_email_report.py` - Génération email avec bouton
- `scripts/run_guardian_emails_2h.ps1` - Loop 2h automatique

**Fonction clé:**
```python
def generate_fix_token(report_id: str) -> str:
    """Génère un token sécurisé HMAC-SHA256"""
    timestamp = str(int(datetime.now().timestamp()))
    data = f"{report_id}:{timestamp}"
    signature = hmac.new(
        GUARDIAN_SECRET.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{data}:{signature}"
```

---

## 🛠️ Logique Auto-Fix

### Anima (Documentation)

**Corrections supportées:**
- Mise à jour automatique de documentation (TODO: implémenter)
- Génération de sections manquantes (TODO: implémenter)

**Actuellement:** Simule les corrections (safe)

### Neo (Intégrité)

**Corrections supportées:**
- Fix imports manquants (TODO: implémenter)
- Fix dependencies (TODO: implémenter)

**Actuellement:** Simule les corrections (safe)

### ProdGuardian (Production)

**Corrections supportées:**
- **AUCUNE AUTOMATIQUE** pour l'instant

**Raison:** Trop risqué de modifier la production sans validation humaine

**Toutes les recommandations Prod sont SKIP avec raison:**
> "Corrections production nécessitent validation manuelle"

---

## 📧 Email HTML - Sections

### 1. Header
- Titre Guardian
- Timestamp du rapport
- Badge de statut global (OK/NEEDS_UPDATE/UNKNOWN)

### 2. Sections Metrics
- **☁️ Production Cloud Run**: Logs, erreurs, warnings, critiques
- **📚 Documentation (Anima)**: Gaps, updates proposés
- **🔐 Intégrité (Neo)**: Problèmes critiques, warnings
- **🎯 Rapport Unifié (Nexus)**: Actions prioritaires

### 3. Détails des corrections (si problèmes)
- Liste des 10 premiers problèmes
- Pour chaque problème:
  - Badge de priorité (CRITICAL/HIGH/MEDIUM/LOW)
  - Source (Production/Documentation/Intégrité)
  - Action recommandée
  - Fichier concerné (si applicable)
- Indication "... et X autres problèmes" si > 10

### 4. Bouton Auto-Fix (si problèmes)
- Bouton stylé "🔧 Appliquer les corrections automatiquement"
- Indication "Token valide 24h"
- JavaScript inline pour confirmation + appel API

### 5. Footer
- Branding Guardian
- Fréquence (toutes les 2h)
- Email contact

---

## 🚀 Déploiement

### Environnement Variables (.env)

```env
# Guardian Auto-Fix Configuration
GUARDIAN_SECRET=d3v-5ecr3t-ch4ng3-1n-pr0d-gu4rd14n-2025
BACKEND_URL=http://localhost:8000

# Email Configuration (required)
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=gonzalefernando@gmail.com
SMTP_PASSWORD=dfshbvvsmyqrfkja
SMTP_FROM_EMAIL=gonzalefernando@gmail.com
```

**⚠️ Production:** Changer `GUARDIAN_SECRET` et `BACKEND_URL`

### Cloud Deployment (TODO)

Pour déployer sur Cloud Run:
1. Modifier `BACKEND_URL=https://emergence-app-prod-xxxxx.run.app`
2. Créer secret GCP pour `GUARDIAN_SECRET`
3. Mettre à jour `scripts/cloud_audit_job.py` pour inclure auto-fix

---

## 🧪 Tests

### Test local endpoint

```bash
# Démarrer le backend
pwsh -File scripts/run-backend.ps1

# Tester le status
curl http://localhost:8000/api/guardian/status

# Générer un token de test
python -c "
import hashlib, hmac
from datetime import datetime
secret = 'd3v-5ecr3t-ch4ng3-1n-pr0d-gu4rd14n-2025'
report_id = 'guardian-test'
timestamp = str(int(datetime.now().timestamp()))
data = f'{report_id}:{timestamp}'
sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
print(f'{data}:{sig}')
"

# Tester l'auto-fix avec le token
curl -X POST http://localhost:8000/api/guardian/auto-fix \
  -H "X-Guardian-Token: <token-généré>" \
  -H "Content-Type: application/json"
```

### Test email complet

```bash
# Générer et envoyer email avec bouton
python scripts/guardian_email_report.py

# Vérifier email dans Gmail
# Cliquer sur le bouton "Appliquer corrections"
```

---

## 📝 TODO - Améliorations futures

### Phase 1 - Auto-Fix Réel (actuellement simulation)
- [ ] Anima: Implémenter mise à jour auto docs
- [ ] Neo: Implémenter fix imports auto
- [ ] Ajouter git commit automatique après corrections

### Phase 2 - Interface Web
- [ ] Créer page `/guardian-dashboard`
- [ ] Afficher historique des corrections
- [ ] Permettre rollback des corrections

### Phase 3 - Production Cautious
- [ ] Système de "dry-run" avant vraie correction
- [ ] Demande de confirmation pour corrections critiques
- [ ] Slack/Discord notification après auto-fix

### Phase 4 - Intelligence
- [ ] Apprendre des corrections ignorées (ML)
- [ ] Suggérer nouvelles règles Guardian
- [ ] Auto-amélioration des seuils de détection

---

## 🐛 Troubleshooting

### "Token manquant" (401)
- Vérifier que le header `X-Guardian-Token` est présent
- Vérifier que le JavaScript s'exécute correctement

### "Token invalide ou expiré" (403)
- Vérifier que `GUARDIAN_SECRET` est identique dans `.env` et backend
- Token expire après 24h - régénérer email

### "Aucun rapport trouvé" (404)
- Exécuter les Guardians manuellement:
  ```bash
  python claude-plugins/integrity-docs-guardian/scripts/anima.py
  python claude-plugins/integrity-docs-guardian/scripts/neo.py
  python claude-plugins/integrity-docs-guardian/scripts/nexus_coordinator.py
  ```

### JavaScript ne fonctionne pas dans Gmail
- Gmail bloque parfois le JavaScript inline
- Solution: Ouvrir l'email dans un navigateur (clic "Afficher l'original")

### CORS error lors de l'appel API
- Vérifier que CORS est configuré dans `main.py`:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

---

## 📚 Références

- **Architecture Guardian:** `docs/architecture/guardian-system.md`
- **Email Service:** `src/backend/features/auth/email_service.py`
- **Rapports JSON:** `reports/prod_report.json`, `reports/docs_report.json`, etc.
- **Cloud Deployment:** `AUDIT_CLOUD_SETUP.md`

---

**🤖 Guardian Auto-Fix - Making ÉMERGENCE V8 self-healing since 2025**
