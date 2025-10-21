# 🛡️ PROMPT - GUARDIAN PHASE 2 : Documentation & CI/CD

**Date de création :** 2025-10-21
**Contexte :** Suite immédiate Phase 1 (Quick Wins terminée)
**Durée estimée Phase 2 :** 5-7h
**Agent recommandé :** Claude Code

---

## 📋 CONTEXTE : CE QUI A ÉTÉ FAIT (Phase 1)

### ✅ Phase 1 complétée (2025-10-21 09:30 CET)

**Commits :**
- `1583a92` - refactor(guardian): Phase 1 - Unification structure rapports (Quick Wins)
- `1ff832f` - fix(guardian): auto_update_docs.py use unified reports/ path

**Actions réalisées :**

1. **Unification rapports** → 1 seul emplacement
   - Modifié 6 scripts Guardian pour écrire dans `reports/` (racine)
   - Supprimé `claude-plugins/integrity-docs-guardian/reports/`
   - Plus de duplication (était 13 fichiers × 2)

2. **Nettoyage rapports**
   - Créé `reports/archive/`
   - Archivé 9 rapports obsolètes
   - Structure propre : 7 rapports actifs + archive

3. **Unification Task Scheduler**
   - Supprimé 3 tâches redondantes
   - Gardé uniquement : `EMERGENCE_Guardian_ProdMonitor`

4. **Documentation mise à jour**
   - `README_GUARDIAN.md` : emplacements + Task Scheduler
   - Audit complet : `docs/GUARDIAN_AUDIT_RECOMMENDATIONS.md` (626 lignes)

5. **Tests complets**
   - ✅ Tous agents Guardian fonctionnels
   - ✅ Hooks Git (pre-commit, post-commit, pre-push) OK

**Résultat actuel :**
- 1 seul emplacement : `reports/` (racine)
- 0 duplication, 0 confusion
- Structure propre et testée

---

## 🎯 TON OBJECTIF : PHASE 2

Implémenter la **Phase 2** du plan d'optimisation Guardian :
1. **Consolidation documentation** (1 guide unique)
2. **GitHub Actions CI/CD** (tests + déploiement automatisés)

**Référence complète :** [docs/GUARDIAN_AUDIT_RECOMMENDATIONS.md](docs/GUARDIAN_AUDIT_RECOMMENDATIONS.md)
- Sections "Priorité 4" et "Priorité 5"

---

## 📚 PHASE 2.1 : CONSOLIDATION DOCUMENTATION

### Objectif

Créer **1 seul guide complet** au lieu de 10+ docs fragmentées.

### Problème actuel

**Documentation Guardian fragmentée :**
- `README_GUARDIAN.md`
- `PRODGUARDIAN_README.md`
- `PRODGUARDIAN_SETUP.md`
- `PROD_MONITORING_ACTIVATED.md`
- `PROD_AUTO_MONITOR_SETUP.md`
- `GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md`
- `GUARDIAN_CLOUD_MIGRATION.md`
- `GUARDIAN_AUTOMATION.md`
- etc.

**Impact :**
- Difficile de savoir par où commencer
- Information fragmentée
- Redondances dans les explications

### Actions à faire

#### 1. Créer `docs/GUARDIAN_COMPLETE_GUIDE.md`

**Structure recommandée :**

```markdown
# 🛡️ GUARDIAN - GUIDE COMPLET

## Table des matières
1. Vue d'ensemble
2. Agents Guardian (descriptions détaillées)
3. Installation & Activation
4. Workflows automatiques
5. Rapports (emplacements, formats, accès)
6. Commandes utiles
7. Troubleshooting
8. Plans Cloud (futur)
9. FAQ

## 1. Vue d'ensemble
[Tableau des 6 agents : Anima, Neo, Nexus, ProdGuardian, Argus, Theia]
[Architecture globale]

## 2. Agents Guardian

### 2.1 ANIMA (DocKeeper)
- Rôle : Documentation gaps, versioning
- Trigger : Pre-commit, Manuel
- Rapport : docs_report.json
- Configuration : ...
- Détails techniques : ...

### 2.2 NEO (IntegrityWatcher)
[...]

### 2.3 NEXUS (Coordinator)
[...]

### 2.4 PRODGUARDIAN
[...]

### 2.5 ARGUS (DevLogs Analyzer)
[...]

### 2.6 THEIA (Cost Analyzer)
[...]

## 3. Installation & Activation

### 3.1 Installation rapide
```powershell
cd claude-plugins/integrity-docs-guardian/scripts
.\setup_guardian.ps1
```

### 3.2 Configuration avancée
[Options : --IntervalHours, --EmailTo, etc.]

### 3.3 Vérification installation
[Commandes de test]

## 4. Workflows automatiques

### 4.1 Pre-Commit Hook (BLOQUANT)
[Détails : Anima + Neo, quand ça bloque, comment bypass]

### 4.2 Post-Commit Hook (Non-bloquant)
[Détails : Nexus + Codex Summary + Auto-update docs]

### 4.3 Pre-Push Hook (BLOQUANT Production)
[Détails : ProdGuardian, quand ça bloque]

### 4.4 Task Scheduler (Background)
[Tâche : EMERGENCE_Guardian_ProdMonitor]
[Fréquence : 6h]
[Modifier fréquence : ...]

## 5. Rapports

### 5.1 Emplacements (IMPORTANT !)

**Tous les rapports sont dans `reports/` (racine) :**

| Fichier | Agent | Contenu |
|---------|-------|---------|
| prod_report.json | PRODGUARDIAN | État production |
| docs_report.json | ANIMA | Documentation gaps |
| integrity_report.json | NEO | Intégrité backend/frontend |
| unified_report.json | NEXUS | Vue unifiée |
| global_report.json | Master Orchestrator | Rapport global |
| codex_summary.md | Auto | Résumé pour Codex GPT |

**Rapports archivés :** `reports/archive/`

### 5.2 Formats des rapports
[Structure JSON de chaque type de rapport]

### 5.3 Accès rapports (pour agents IA)
```python
# Recommandé : Résumé markdown
with open('reports/codex_summary.md', 'r', encoding='utf-8') as f:
    print(f.read())

# Détails : JSON bruts
import json
with open('reports/prod_report.json', 'r', encoding='utf-8') as f:
    prod = json.load(f)
```

## 6. Commandes utiles

### 6.1 Audit manuel global
```powershell
.\run_audit.ps1
```

### 6.2 Tests individuels agents
```bash
python claude-plugins/.../scripts/scan_docs.py
python claude-plugins/.../scripts/check_integrity.py
...
```

### 6.3 Régénérer Codex Summary
```bash
python scripts/generate_codex_summary.py
```

## 7. Troubleshooting

### 7.1 Hooks Git ne se déclenchent pas
[Solutions]

### 7.2 Rapports pas générés
[Solutions]

### 7.3 Task Scheduler ne s'exécute pas
[Solutions]

### 7.4 ProdGuardian timeout
[Solutions]

## 8. Plans Cloud (futur)

**Documents de référence :**
- [GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md](GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md) (v2.0.0)
- [GUARDIAN_CLOUD_MIGRATION.md](GUARDIAN_CLOUD_MIGRATION.md) (v1.0.0)

**Fonctionnalités prévues :**
- Service Cloud Run `emergence-guardian-service`
- Monitoring 24/7 (toutes les 2h)
- Cloud Storage pour rapports
- Gmail API pour Codex
- Usage Tracking
- Trigger manuel depuis Admin UI

**Status :** 📋 PLANIFICATION (pas encore implémenté)

## 9. FAQ

### Pourquoi il y a plusieurs emplacements de rapports ?
[Réponse : c'était le cas avant, maintenant unifié dans reports/]

### Comment Codex GPT accède aux rapports ?
[Réponse : lit reports/codex_summary.md localement]

### Puis-je désactiver Guardian ?
[Réponse : oui, setup_guardian.ps1 -Disable]

### Quelle est la différence entre les agents ?
[Tableau comparatif]
```

#### 2. Consolider les informations

**Sources à fusionner dans le guide complet :**
1. `claude-plugins/integrity-docs-guardian/README_GUARDIAN.md` ✅ (base principale)
2. `claude-plugins/integrity-docs-guardian/PRODGUARDIAN_README.md`
3. `claude-plugins/integrity-docs-guardian/PRODGUARDIAN_SETUP.md`
4. `claude-plugins/integrity-docs-guardian/PROD_MONITORING_ACTIVATED.md`
5. `claude-plugins/integrity-docs-guardian/PROD_AUTO_MONITOR_SETUP.md`
6. `claude-plugins/integrity-docs-guardian/GUARDIAN_AUTOMATION.md`
7. `docs/GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md` (référence seulement)
8. `docs/GUARDIAN_CLOUD_MIGRATION.md` (référence seulement)
9. `PROMPT_CODEX_RAPPORTS.md` (section accès rapports)

**Méthode :**
- Lire chaque fichier source
- Extraire les sections uniques (pas de duplication)
- Organiser dans la structure du guide complet
- Ajouter références croisées vers plans cloud

#### 3. Archiver les docs fragmentées

```bash
mkdir -p claude-plugins/integrity-docs-guardian/docs/archive

# Déplacer les docs fragmentées
mv claude-plugins/integrity-docs-guardian/PRODGUARDIAN_*.md \
   claude-plugins/integrity-docs-guardian/docs/archive/

mv claude-plugins/integrity-docs-guardian/PROD_*.md \
   claude-plugins/integrity-docs-guardian/docs/archive/

mv claude-plugins/integrity-docs-guardian/GUARDIAN_AUTOMATION.md \
   claude-plugins/integrity-docs-guardian/docs/archive/
```

**Créer `claude-plugins/integrity-docs-guardian/docs/archive/README.md` :**
```markdown
# Docs Guardian archivées

Ces documents ont été consolidés dans **docs/GUARDIAN_COMPLETE_GUIDE.md**.

Conservés ici pour référence historique.

Liste :
- PRODGUARDIAN_README.md
- PRODGUARDIAN_SETUP.md
- PROD_MONITORING_ACTIVATED.md
- PROD_AUTO_MONITOR_SETUP.md
- GUARDIAN_AUTOMATION.md
```

#### 4. Mettre à jour les liens

**Fichiers à modifier :**
1. `CLAUDE.md` → pointer vers `docs/GUARDIAN_COMPLETE_GUIDE.md`
2. `CODEX_GPT_SYSTEM_PROMPT.md` → pointer vers guide complet
3. `PROMPT_CODEX_RAPPORTS.md` → référence au guide complet
4. `README_GUARDIAN.md` → devenir alias/lien vers guide complet

**Exemple modification `CLAUDE.md` :**
```markdown
## 🤖 SYSTÈME GUARDIAN (AUTOMATIQUE)

**Documentation complète :** [docs/GUARDIAN_COMPLETE_GUIDE.md](docs/GUARDIAN_COMPLETE_GUIDE.md)

**Version 3.1.0 - Unifié et optimisé (2025-10-21)**
```

### Livrables Phase 2.1

- [ ] `docs/GUARDIAN_COMPLETE_GUIDE.md` créé (~500-800 lignes)
- [ ] Docs fragmentées archivées dans `docs/archive/`
- [ ] Liens mis à jour (CLAUDE.md, CODEX_GPT_SYSTEM_PROMPT.md, etc.)
- [ ] `README_GUARDIAN.md` converti en alias

**Temps estimé :** 2-3h

---

## 🔧 PHASE 2.2 : GITHUB ACTIONS CI/CD

### Objectif

Automatiser tests, validation Guardian, et déploiement Cloud Run.

### Problème actuel

**1 seul workflow GitHub Actions :**
- `.github/workflows/bootstrap-smoke.yml` (24 lignes, basique)

**Manquants :**
- Tests automatiques sur PR
- Validation Guardian sur push
- Déploiement automatique Cloud Run
- Rapports Guardian dans artifacts

### Actions à faire

#### 1. Créer `.github/workflows/tests.yml`

**Tests & Guardian Validation**

```yaml
name: Tests & Guardian Validation

on:
  push:
    branches: ['**']
  pull_request:
    branches: [main]

jobs:
  # Job 1 : Tests Backend
  test-backend:
    name: Backend Tests (Python 3.11)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run pytest
        run: pytest tests/backend/ -v --tb=short

      - name: Ruff check
        run: ruff check src/backend/

      - name: Mypy type checking
        run: mypy src/backend/ --ignore-missing-imports

  # Job 2 : Tests Frontend
  test-frontend:
    name: Frontend Tests (Node 18)
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build frontend
        run: npm run build

  # Job 3 : Guardian Validation
  guardian:
    name: Guardian Validation
    runs-on: ubuntu-latest
    needs: [test-backend, test-frontend]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Anima (DocKeeper)
        run: python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

      - name: Run Neo (IntegrityWatcher)
        run: python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

      - name: Run Nexus (Coordinator)
        run: python claude-plugins/integrity-docs-guardian/scripts/generate_report.py

      - name: Generate Codex Summary
        run: python scripts/generate_codex_summary.py

      - name: Upload Guardian Reports
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: guardian-reports
          path: |
            reports/*.json
            reports/codex_summary.md
          retention-days: 30

      - name: Check for Guardian failures
        run: |
          if grep -q '"status": "error"' reports/*.json; then
            echo "❌ Guardian détecté des erreurs"
            exit 1
          fi
          echo "✅ Guardian validation OK"
```

#### 2. Créer `.github/workflows/deploy.yml`

**Déploiement automatique Cloud Run**

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

env:
  GCP_PROJECT_ID: emergence-469005
  GCP_REGION: europe-west1
  SERVICE_NAME: emergence-app
  IMAGE_NAME: gcr.io/emergence-469005/emergence-app

jobs:
  deploy:
    name: Build & Deploy to Cloud Run
    runs-on: ubuntu-latest

    # Only run if tests pass
    needs: []  # Optionnel : ajouter dependency sur workflow tests

    steps:
      - uses: actions/checkout@v4

      # Setup gcloud CLI
      - uses: google-github-actions/setup-gcloud@v1
        with:
          service_account_key: ${{ secrets.GCP_SA_KEY }}
          project_id: ${{ env.GCP_PROJECT_ID }}
          export_default_credentials: true

      # Configure Docker to use gcloud as credential helper
      - name: Configure Docker
        run: gcloud auth configure-docker

      # Build Docker image
      - name: Build Docker image
        run: |
          docker build -t ${{ env.IMAGE_NAME }}:${{ github.sha }} .
          docker tag ${{ env.IMAGE_NAME }}:${{ github.sha }} ${{ env.IMAGE_NAME }}:latest

      # Push to Google Container Registry
      - name: Push to GCR
        run: |
          docker push ${{ env.IMAGE_NAME }}:${{ github.sha }}
          docker push ${{ env.IMAGE_NAME }}:latest

      # Deploy to Cloud Run
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy ${{ env.SERVICE_NAME }} \
            --image ${{ env.IMAGE_NAME }}:${{ github.sha }} \
            --region ${{ env.GCP_REGION }} \
            --platform managed \
            --allow-unauthenticated \
            --memory 2Gi \
            --cpu 2 \
            --min-instances 0 \
            --max-instances 10 \
            --timeout 300s \
            --quiet

      # Get service URL
      - name: Get Service URL
        id: service-url
        run: |
          SERVICE_URL=$(gcloud run services describe ${{ env.SERVICE_NAME }} \
            --region ${{ env.GCP_REGION }} \
            --format 'value(status.url)')
          echo "url=$SERVICE_URL" >> $GITHUB_OUTPUT
          echo "✅ Deployed to: $SERVICE_URL"

      # Health check
      - name: Health Check
        run: |
          sleep 10  # Wait for service to be ready
          curl -f ${{ steps.service-url.outputs.url }}/health || exit 1
          echo "✅ Health check passed"
```

#### 3. Configurer secrets GitHub

**Secrets nécessaires :**

1. `GCP_SA_KEY` - Service Account Key pour déploiement

   **Comment l'obtenir :**
   ```bash
   # Créer service account
   gcloud iam service-accounts create github-actions \
     --display-name "GitHub Actions"

   # Donner permissions
   gcloud projects add-iam-policy-binding emergence-469005 \
     --member "serviceAccount:github-actions@emergence-469005.iam.gserviceaccount.com" \
     --role "roles/run.admin"

   gcloud projects add-iam-policy-binding emergence-469005 \
     --member "serviceAccount:github-actions@emergence-469005.iam.gserviceaccount.com" \
     --role "roles/storage.admin"

   # Créer clé JSON
   gcloud iam service-accounts keys create key.json \
     --iam-account github-actions@emergence-469005.iam.gserviceaccount.com

   # Copier contenu de key.json dans GitHub secret GCP_SA_KEY
   cat key.json
   ```

2. Ajouter dans GitHub : Settings → Secrets and variables → Actions → New repository secret
   - Name: `GCP_SA_KEY`
   - Secret: [contenu de key.json]

#### 4. Tester les workflows

**Test local avec act (optionnel) :**
```bash
# Installer act
brew install act  # macOS
# ou
choco install act  # Windows

# Tester workflow tests
act pull_request -W .github/workflows/tests.yml

# Tester workflow deploy (dry-run)
act push -W .github/workflows/deploy.yml --secret-file .secrets
```

**Test sur GitHub :**
1. Push sur une branche feature
2. Créer PR vers main
3. Vérifier que `tests.yml` s'exécute
4. Merger PR
5. Vérifier que `deploy.yml` s'exécute et déploie

### Livrables Phase 2.2

- [ ] `.github/workflows/tests.yml` créé
- [ ] `.github/workflows/deploy.yml` créé
- [ ] Secret `GCP_SA_KEY` configuré dans GitHub
- [ ] Tests workflow sur PR
- [ ] Déploiement automatique testé

**Temps estimé :** 3-4h

---

## 📝 CHECKLIST COMPLÈTE PHASE 2

### Phase 2.1 : Documentation

- [ ] Créer `docs/GUARDIAN_COMPLETE_GUIDE.md`
  - [ ] Structure complète (9 sections)
  - [ ] Consolidation de 8+ docs fragmentées
  - [ ] Références aux plans cloud
  - [ ] FAQ complète
- [ ] Archiver docs fragmentées
  - [ ] Créer `claude-plugins/.../docs/archive/`
  - [ ] Déplacer 5+ fichiers
  - [ ] README.md dans archive
- [ ] Mettre à jour liens
  - [ ] CLAUDE.md
  - [ ] CODEX_GPT_SYSTEM_PROMPT.md
  - [ ] PROMPT_CODEX_RAPPORTS.md
  - [ ] README_GUARDIAN.md

### Phase 2.2 : CI/CD

- [ ] Créer `.github/workflows/tests.yml`
  - [ ] Job test-backend (pytest, ruff, mypy)
  - [ ] Job test-frontend (npm build)
  - [ ] Job guardian (4 agents + upload artifacts)
- [ ] Créer `.github/workflows/deploy.yml`
  - [ ] Build Docker image
  - [ ] Push to GCR
  - [ ] Deploy Cloud Run
  - [ ] Health check
- [ ] Configuration GitHub
  - [ ] Service Account GCP créé
  - [ ] Secret GCP_SA_KEY ajouté
  - [ ] Permissions IAM configurées
- [ ] Tests
  - [ ] Workflow tests sur PR
  - [ ] Workflow deploy sur push main
  - [ ] Déploiement production vérifié

### Validation finale

- [ ] Documentation accessible et claire
- [ ] Workflows GitHub Actions fonctionnels
- [ ] Déploiement automatique OK
- [ ] Rapports Guardian dans artifacts
- [ ] Commit + push Phase 2
- [ ] Mise à jour AGENT_SYNC.md

---

## 🎯 COMMANDES RAPIDES

### Tester la documentation

```bash
# Vérifier tous les liens markdown
grep -r "\[.*\](.*.md)" docs/GUARDIAN_COMPLETE_GUIDE.md

# Vérifier structure
head -50 docs/GUARDIAN_COMPLETE_GUIDE.md
```

### Tester les workflows

```bash
# Valider syntaxe YAML
yamllint .github/workflows/*.yml

# Test local (si act installé)
act pull_request -W .github/workflows/tests.yml --list
```

### Commit Phase 2

```bash
git add -A
git commit -m "feat(guardian): Phase 2 - Documentation consolidée + CI/CD GitHub Actions

Phase 2.1 - Documentation consolidée :
- Créé docs/GUARDIAN_COMPLETE_GUIDE.md (guide unique complet)
- Archivé 5+ docs fragmentées
- Mis à jour tous liens (CLAUDE.md, CODEX_GPT_SYSTEM_PROMPT.md, etc.)
- Structure claire : 9 sections, FAQ, références cloud

Phase 2.2 - CI/CD GitHub Actions :
- Workflow tests.yml : pytest + ruff + mypy + Guardian validation
- Workflow deploy.yml : build Docker + push GCR + deploy Cloud Run
- Rapports Guardian dans artifacts (rétention 30j)
- Déploiement automatique sur push main

Résultat :
- 1 seul guide au lieu de 10+ docs
- Tests automatiques sur chaque PR
- Déploiement automatisé Cloud Run
- Validation Guardian intégrée CI/CD

Temps Phase 2 : ~5-7h

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

---

## 📚 RÉFÉRENCES

### Documents essentiels à lire

1. **Audit complet (Phase 1) :**
   - [docs/GUARDIAN_AUDIT_RECOMMENDATIONS.md](docs/GUARDIAN_AUDIT_RECOMMENDATIONS.md)
   - Sections Priorité 4-5

2. **État actuel Guardian :**
   - [claude-plugins/integrity-docs-guardian/README_GUARDIAN.md](claude-plugins/integrity-docs-guardian/README_GUARDIAN.md)
   - Emplacements rapports, workflows, agents

3. **Docs fragmentées à consolider :**
   - `claude-plugins/integrity-docs-guardian/PRODGUARDIAN_*.md`
   - `claude-plugins/integrity-docs-guardian/PROD_*.md`
   - `claude-plugins/integrity-docs-guardian/GUARDIAN_AUTOMATION.md`

4. **Plans cloud (référence future) :**
   - [docs/GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md](docs/GUARDIAN_CLOUD_IMPLEMENTATION_PLAN.md)
   - [docs/GUARDIAN_CLOUD_MIGRATION.md](docs/GUARDIAN_CLOUD_MIGRATION.md)

### Structure actuelle projet

```
emergenceV8/
├── .github/
│   └── workflows/
│       └── bootstrap-smoke.yml  ← À compléter avec tests.yml + deploy.yml
├── claude-plugins/
│   └── integrity-docs-guardian/
│       ├── README_GUARDIAN.md   ← Base pour guide complet
│       ├── scripts/
│       │   ├── scan_docs.py     (Anima)
│       │   ├── check_integrity.py (Neo)
│       │   ├── generate_report.py (Nexus)
│       │   ├── check_prod_logs.py (ProdGuardian)
│       │   └── master_orchestrator.py
│       └── [docs fragmentées à consolider]
├── docs/
│   ├── GUARDIAN_AUDIT_RECOMMENDATIONS.md  ← Audit complet
│   ├── GUARDIAN_COMPLETE_GUIDE.md  ← À CRÉER (Phase 2.1)
│   ├── GUARDIAN_CLOUD_*.md  ← Plans futur
│   └── passation.md
├── reports/                     ← UNIFIÉ (Phase 1 ✅)
│   ├── prod_report.json
│   ├── docs_report.json
│   ├── integrity_report.json
│   ├── unified_report.json
│   ├── global_report.json
│   ├── codex_summary.md
│   └── archive/
├── scripts/
│   ├── generate_codex_summary.py
│   └── analyze_guardian_structure.py
├── CLAUDE.md                    ← Liens à mettre à jour
├── CODEX_GPT_SYSTEM_PROMPT.md   ← Liens à mettre à jour
└── PROMPT_CODEX_RAPPORTS.md     ← Liens à mettre à jour
```

---

## ⚙️ CONFIGURATION GCP (pour deploy.yml)

### Projet GCP actuel

- **Project ID :** `emergence-469005`
- **Région :** `europe-west1`
- **Service Cloud Run :** `emergence-app`
- **Container Registry :** `gcr.io/emergence-469005`

### Ressources Cloud Run actuelles

```bash
# Vérifier service actuel
gcloud run services describe emergence-app --region europe-west1

# Config actuelle (ref)
Memory: 2Gi
CPU: 2
Min instances: 0
Max instances: 10
Timeout: 300s
```

---

## 💡 CONSEILS POUR L'IMPLÉMENTATION

### Documentation (Phase 2.1)

1. **Commence par la structure** : Crée le squelette du guide complet d'abord
2. **Consolide section par section** : Ne fais pas tout d'un coup
3. **Vérifie les liens** : Teste que tous les liens internes fonctionnent
4. **Garde concis** : Élimine les redondances entre docs sources

### CI/CD (Phase 2.2)

1. **Teste localement d'abord** : Valide la syntaxe YAML
2. **Service Account** : Assure-toi que les permissions IAM sont OK
3. **Secrets** : Vérifie que GCP_SA_KEY est bien configuré
4. **Teste sur branche** : Ne push pas direct sur main
5. **Health check** : Assure-toi que l'endpoint /health existe

### Si tu bloques

**Problème : Workflow GitHub Actions ne se déclenche pas**
- Vérifie que le fichier est dans `.github/workflows/`
- Vérifie syntaxe YAML (yamllint)
- Vérifie permissions repo (Settings → Actions)

**Problème : Déploiement Cloud Run échoue**
- Vérifie Service Account permissions
- Vérifie que le projet GCP est le bon
- Vérifie que l'image Docker build correctement

**Problème : Guardian agents échouent dans CI**
- Assure-toi que requirements.txt est installé
- Vérifie que chemins vers scripts sont corrects
- Regarde les logs dans artifacts

---

## ✅ RÉSULTAT ATTENDU PHASE 2

**Après Phase 2, tu auras :**

### Documentation
- ✅ 1 seul guide complet au lieu de 10+ docs
- ✅ Structure claire : 9 sections, FAQ, troubleshooting
- ✅ Docs fragmentées archivées
- ✅ Liens mis à jour partout
- ✅ Facile à maintenir

### CI/CD
- ✅ Tests automatiques sur chaque PR
- ✅ Validation Guardian intégrée
- ✅ Déploiement automatique Cloud Run sur push main
- ✅ Rapports Guardian dans artifacts GitHub
- ✅ Health check post-déploiement

### Impact
- ✅ Processus de dev robuste
- ✅ Moins d'erreurs en production
- ✅ Déploiements plus rapides (automatisés)
- ✅ Documentation centralisée et accessible

**Temps total Phase 2 : 5-7h**

**Prochaine étape : Phase 3 (Cloud Integration)** - Si besoin

---

**🎯 TU ES PRÊT À DÉMARRER LA PHASE 2 !**

Lis d'abord :
1. `docs/GUARDIAN_AUDIT_RECOMMENDATIONS.md` (sections Priorité 4-5)
2. `claude-plugins/integrity-docs-guardian/README_GUARDIAN.md`
3. Ce prompt

Puis commence par Phase 2.1 (Documentation).

Bonne chance ! 🚀
