# 🚀 PROMPT POUR PROCHAINE SESSION - ÉMERGENCE V8

**Date de création** : 2025-10-21
**Dernière session** : Audit complet + Correctifs Guardian + Docker Compose
**Prochaines priorités** : Tests + Mypy + Déploiement

---

## 📋 CONTEXTE RAPIDE

### État Actuel (Post-Audit 2025-10-21)

**✅ Ce qui est BON** :
- Backend : 95+ endpoints, tests 45/45 passent ✅
- Frontend : 53 modules, build OK ✅
- Production GCP : Stable (0 erreurs réelles) ✅
- Guardian : ProdGuardian faux positifs corrigés ✅
- Guardian : Pre-commit hook V2 amélioré ✅
- Docker : docker-compose.yml complet créé ✅
- Roadmap : 61% complétée (P0 + P1 done) ✅

**⚠️ Ce qui RESTE À FAIRE** :
- Mypy : 95 erreurs (désactivé temporairement)
- Docker Compose : Pas encore testé
- Frontend : 2 warnings build (admin-icons, vendor chunk)
- Tests : Endpoints HTTP désactivés
- Docs Guardian : 45 fichiers (surchargée)
- Phase P2 roadmap : 0% (admin avancé, 2FA, multi-sessions)

**📄 Documents clés** :
- `AUDIT_COMPLET_2025-10-21.md` - Audit complet 400+ lignes
- `docker-compose.yml` - Stack dev complète (nouveau)
- `docs/passation.md` - Entrée session 2025-10-21 16:45
- `ROADMAP_OFFICIELLE.md` - Roadmap features
- `ROADMAP_PROGRESS.md` - Suivi progression 61%

---

## 🎯 ACTIONS IMMÉDIATES (Priorité 1)

### 1️⃣ Tester Docker Compose (30 min)

**Objectif** : Vérifier que la stack dev complète fonctionne.

**Commandes** :
```bash
# Lancer la stack
docker-compose up -d

# Vérifier les services
docker-compose ps

# Vérifier les logs
docker-compose logs backend
docker-compose logs frontend

# Tester l'app
curl http://localhost:8000/api/health
curl http://localhost:8000/api/ready

# Accéder frontend
# Navigateur: http://localhost:5173
```

**Critères de succès** :
- ✅ Tous les services démarrent (backend, frontend, mongo, chromadb)
- ✅ Backend répond sur http://localhost:8000
- ✅ Frontend sert sur http://localhost:5173
- ✅ MongoDB accessible (port 27017)
- ✅ ChromaDB accessible (port 8001)
- ✅ Logs propres (pas d'erreurs critiques)

**Si problème** :
- Vérifier les logs : `docker-compose logs -f [service]`
- Vérifier variables env : `.env` correctement configuré
- Vérifier ports : pas de conflit (8000, 5173, 27017, 8001)

---

### 2️⃣ Tester Guardian ProdGuardian (15 min)

**Objectif** : Vérifier que le filtre faux positifs 404 fonctionne.

**Commandes** :
```bash
# Lancer ProdGuardian manuellement
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py

# Vérifier le rapport
cat reports/prod_report.json | grep -A 5 "status"
cat reports/prod_report.json | grep -A 5 "warnings"
```

**Critères de succès** :
- ✅ Status = "OK" (pas DEGRADED si pas de vraies erreurs)
- ✅ Warnings = 0 ou très peu (scans bots filtrés)
- ✅ Si warnings, vérifier que ce sont de vraies erreurs applicatives

**Si status DEGRADED** :
- Lire `reports/prod_report.json` section `warnings_detailed`
- Vérifier si ce sont des 404 de bots (ajouter dans filtre si besoin)
- Vérifier si ce sont de vraies erreurs 5xx (à corriger)

---

### 3️⃣ Corriger Mypy Batch 1 (4 heures)

**Objectif** : Réduire erreurs Mypy de 95 → ~65.

**Stratégie** :
1. Lancer Mypy sur `src/backend/core/` d'abord (le plus critique)
2. Fixer les erreurs les plus simples (missing type hints, imports)
3. Fixer les erreurs de compatibilité Pydantic v2
4. Re-lancer les tests après chaque correctif

**Commandes** :
```bash
# Lancer Mypy sur core/
cd src/backend
mypy core/ --show-error-codes --pretty

# Fixer erreurs + relancer
mypy core/

# Une fois core/ OK, passer à features/
mypy features/auth/
mypy features/chat/
# etc.

# Vérifier que tests passent toujours
pytest -v
```

**Types d'erreurs courants** :
- `error: Missing type annotation` → Ajouter `: Type`
- `error: Incompatible return value` → Fixer le type de retour
- `error: Argument X to Y has incompatible type` → Caster ou fixer signature
- `error: Module has no attribute` → Import manquant

**Critères de succès** :
- ✅ Mypy errors passent de 95 → ~65 (-30 erreurs)
- ✅ Tests backend : 45/45 passent toujours ✅
- ✅ Build frontend : OK toujours ✅

---

## 🔄 ACTIONS SUIVANTES (Priorité 2)

### 4️⃣ Nettoyer Documentation Guardian (2 heures)

**Objectif** : Réduire 45 fichiers → 5 fichiers essentiels.

**Fichiers à GARDER** :
1. `README.md` - Vue d'ensemble
2. `SYSTEM_STATUS.md` - État actuel
3. `CONFIGURATION.md` - Config Guardian
4. `TROUBLESHOOTING.md` - Debug
5. `CHANGELOG.md` - Historique

**Fichiers à ARCHIVER** :
- Tout le reste dans `docs/archive/`
- Garder structure pour référence historique

**Commandes** :
```bash
cd claude-plugins/integrity-docs-guardian

# Créer dossier archive
mkdir -p docs/archive

# Déplacer fichiers obsolètes
mv docs/*.md docs/archive/ (sauf les 5 à garder)

# Commit
git add .
git commit -m "docs(guardian): Nettoyer documentation (45 → 5 fichiers essentiels)"
```

---

### 5️⃣ Corriger Warnings Build Frontend (2 heures)

**Objectif** : Éliminer warnings Vite.

**5.1. Fix admin-icons.js (import mixte)**

Fichier : `src/frontend/features/admin/admin-dashboard.js`

```javascript
// Remplacer import statique
// import { ICONS } from './admin-icons.js';

// Par import dynamique
const { ICONS } = await import('./admin-icons.js');
```

**5.2. Code-split vendor chunk**

Créer fichier : `vite.config.js`

```javascript
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-core': ['jspdf', 'jspdf-autotable', 'papaparse'],
        }
      }
    },
    chunkSizeWarningLimit: 600
  }
});
```

**Tests** :
```bash
npm run build

# Vérifier aucun warning
# Vérifier chunks < 500 KB
```

---

### 6️⃣ Réactiver Tests HTTP Endpoints (4 heures)

**Objectif** : Augmenter couverture tests backend.

**Actions** :
1. Fixer mocks obsolètes dans `test_debate_service.py`
2. Re-enable `test_concept_recall_tracker.py`
3. Ajouter tests pour endpoints `/api/auth`, `/api/threads`, `/api/memory`

**Commandes** :
```bash
cd src/backend

# Identifier tests désactivés
pytest --co -q | grep -i skip

# Re-enable un par un
# Éditer fichiers test_*.py

# Lancer tests
pytest -v

# Vérifier couverture
pytest --cov=. --cov-report=term
```

**Objectif** : Passer de 45 tests → 65+ tests

---

## 🚀 DÉPLOIEMENT DOCKER → GCP (2-3 jours)

### Phase D1 : Docker Local (1-2 jours)

**Actions** :
1. ✅ Docker Compose testé (action 1 ci-dessus)
2. Build image production locale :
   ```bash
   docker build -t emergence-v8:local .
   docker run -p 8080:8080 emergence-v8:local
   curl http://localhost:8080/api/health
   ```
3. Optimiser taille image (multi-stage build)

### Phase D2 : Préparer GCP (1 jour)

**Actions** :
1. Vérifier secrets GCP :
   ```bash
   gcloud secrets list
   gcloud secrets versions access latest --secret="OPENAI_API_KEY"
   ```
2. Vérifier Firestore collections
3. Vérifier `stable-service.yaml`

### Phase D3 : Build + Push (30 min)

**Actions** :
```bash
gcloud config set project emergence-469005

gcloud builds submit \
  --tag gcr.io/emergence-469005/emergence-app:beta-2.1.6 \
  --timeout=20m
```

### Phase D4 : Canary 10% (1h + 2h observation)

**Actions** :
```powershell
.\scripts\deploy-canary.ps1 -ImageTag "beta-2.1.6" -TrafficPercent 10
```

**Monitoring** : 2 heures, vérifier :
- Latence P95 < 2s
- Taux d'erreur < 1%
- Logs propres
- Guardian status OK

### Phase D5 : Stable 100% (30 min)

**Actions** :
```bash
gcloud run services update emergence-app \
  --image gcr.io/emergence-469005/emergence-app:beta-2.1.6 \
  --region europe-west1

gcloud run services update-traffic emergence-app \
  --to-revisions emergence-app-00042-stable=100 \
  --region europe-west1
```

**Monitoring** : 24 heures

---

## 📝 CHECKLIST SESSION

**Avant de commencer** :
- [ ] Lire `AGENT_SYNC.md` (état sync)
- [ ] Lire `docs/passation.md` (dernière entrée)
- [ ] Lire `AUDIT_COMPLET_2025-10-21.md` (contexte)
- [ ] `git status` propre
- [ ] `git pull` pour sync
- [ ] Virtualenv Python activé

**Pendant la session** :
- [ ] Utiliser TodoWrite pour tracker les tâches
- [ ] Tester après chaque modification
- [ ] Commiter régulièrement (commits atomiques)

**Fin de session** :
- [ ] Tests backend : `pytest` ✅
- [ ] Build frontend : `npm run build` ✅
- [ ] Mypy : Réduction erreurs visible
- [ ] `AGENT_SYNC.md` mis à jour
- [ ] `docs/passation.md` nouvelle entrée
- [ ] Commit + push

---

## 🎯 PRIORITÉS PAR URGENCE

**IMMÉDIAT (cette semaine)** :
1. 🔥 **Tester Docker Compose** (30 min) - Critique
2. 🔥 **Tester ProdGuardian** (15 min) - Critique
3. ⚙️ **Corriger Mypy batch 1** (4h) - Important

**COURT TERME (semaine prochaine)** :
4. 📋 **Nettoyer docs Guardian** (2h) - Important
5. 📋 **Fix warnings build** (2h) - Important
6. 📋 **Tests HTTP endpoints** (4h) - Optionnel

**MOYEN TERME (2-3 semaines)** :
7. 🚀 **Déploiement Docker → GCP** (2-3 jours) - Planifié
8. 🎨 **Phase P2 roadmap** (5-7 jours) - Planifié

---

## 🔗 FICHIERS DE RÉFÉRENCE

**Documentation** :
- [AUDIT_COMPLET_2025-10-21.md](AUDIT_COMPLET_2025-10-21.md) - Audit complet
- [ROADMAP_OFFICIELLE.md](ROADMAP_OFFICIELLE.md) - Roadmap features
- [ROADMAP_PROGRESS.md](ROADMAP_PROGRESS.md) - Progression 61%
- [docker-compose.yml](docker-compose.yml) - Stack dev
- [AGENT_SYNC.md](AGENT_SYNC.md) - État sync
- [docs/passation.md](docs/passation.md) - Journal sessions

**Guardian** :
- [claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py](claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py) - ProdGuardian
- [.git/hooks/pre-commit](.git/hooks/pre-commit) - Hook V2
- [reports/prod_report.json](reports/prod_report.json) - Rapport production
- [reports/unified_report.json](reports/unified_report.json) - Rapport unifié

**Tests** :
- [src/backend/tests/](src/backend/tests/) - Tests backend
- [pytest.ini](pytest.ini) - Config pytest

---

## 💡 COMMANDES UTILES

**Tests** :
```bash
# Tests backend
cd src/backend && pytest -v

# Build frontend
npm run build

# Mypy
cd src/backend && mypy . --show-error-codes

# Ruff
ruff check src/backend/
```

**Docker** :
```bash
# Stack complète
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild
docker-compose up -d --build
```

**Guardian** :
```bash
# ProdGuardian
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py

# Tous les agents
pwsh -File claude-plugins/integrity-docs-guardian/scripts/run_audit.ps1
```

**Git** :
```bash
# Status
git status

# Sync
git fetch --all --prune
git pull

# Commit
git add .
git commit -m "fix: Description des changements"
git push
```

---

## ⚠️ PIÈGES À ÉVITER

1. **Ne pas** lancer `docker-compose up` sans avoir configuré `.env` (API keys)
2. **Ne pas** modifier Guardian sans tester les hooks après
3. **Ne pas** corriger Mypy sans relancer les tests backend
4. **Ne pas** push vers GCP sans tester canary d'abord
5. **Ne pas** oublier de mettre à jour `AGENT_SYNC.md` et `docs/passation.md`

---

## 🤝 COLLABORATION CODEX GPT

**Si Codex a travaillé** :
1. Lire `AGENT_SYNC.md` section "Codex GPT"
2. Lire `docs/passation.md` dernières entrées Codex
3. Vérifier fichiers modifiés : `git log --oneline -10 | grep Codex`
4. Compléter ou corriger le travail si nécessaire

**Zones Codex** (indicatif) :
- Frontend JavaScript (features/, components/)
- Scripts PowerShell
- UI/UX responsive
- Documentation utilisateur

**Zones Claude Code** (indicatif) :
- Backend Python (core/, features/)
- Tests backend (pytest)
- Architecture & refactoring
- Documentation technique

---

## 📞 CONTACT

**Si bloqué** :
- Architecte : Fernando Gonzalez (gonzalefernando@gmail.com)
- Docs : Lire `TROUBLESHOOTING.md`, `AUDIT_COMPLET_2025-10-21.md`
- Slack : #emergence-v8 (si configuré)

---

**Créé par** : Claude Code (Sonnet 4.5)
**Date** : 2025-10-21
**Dernière session** : Audit complet + Guardian + Docker Compose
**Prochaine session** : Tests + Mypy + Déploiement

🚀 **Fonce !**
