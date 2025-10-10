# Plugin Guardian de l'Intégrité & Docs

**Version:** 1.0.0
**Pour:** Application ÉMERGENCE (FastAPI + Vite/React)
**Agents:** Anima (DocKeeper), Neo (IntegrityWatcher), Nexus (Coordinator)

---

## 📋 Vue d'Ensemble

Le **Guardian de l'Intégrité & Docs** est un plugin Claude Code qui automatise la maintenance de la documentation et garantit la cohérence backend/frontend dans l'application ÉMERGENCE. Il tourne automatiquement après chaque commit pour détecter les gaps de doc, les mismatches de schéma, et les régressions potentielles.

### Fonctionnalités Clés

✅ **Tracking Auto de la Documentation** - Détecte quand les changements de code nécessitent des mises à jour de doc
✅ **Cohérence Backend/Frontend** - Vérifie les contrats d'API et l'alignement des schémas
✅ **Détection de Régressions** - Attrape les breaking changes avant qu'ils atteignent la prod
✅ **Système Multi-Agents** - Des agents spécialisés pour différentes tâches de vérification
✅ **Intégration Git** - Tourne automatiquement via les hooks Git
✅ **Rapports Actionnables** - Recommandations priorisées et concrètes

---

## 🏗️ Architecture

### Écosystème d'Agents

| Agent | Rôle | Responsabilité |
|-------|------|----------------|
| **Anima** | DocKeeper | Surveille les changements de code et identifie les gaps de documentation |
| **Neo** | IntegrityWatcher | Vérifie la cohérence backend/frontend et détecte les régressions |
| **Nexus** | Coordinator | Agrège les rapports, priorise les actions, fournit une vue unifiée |

### Workflow

```
┌─────────────────┐
│  Git Commit     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Hook Post-Commit Déclenché         │
└────────┬────────────────────────────┘
         │
         ├──────────────┬─────────────┐
         ▼              ▼             ▼
    ┌────────┐     ┌────────┐    ┌────────┐
    │ Anima  │     │  Neo   │    │ Nexus  │
    └────┬───┘     └────┬───┘    └────┬───┘
         │              │             │
         ▼              ▼             ▼
  docs_report.json  integrity_    unified_
                    report.json   report.json
```

---

## 📦 Installation

### Prérequis

- **Git** repository
- **Python 3.8+**
- **Claude Code** (optionnel pour les commandes slash)

### Les Hooks Sont Déjà Actifs! ✅

**Bonne nouvelle:** Les hooks Git sont déjà installés et fonctionnels! 🎉

Vérifie:
```bash
ls -la .git/hooks/ | grep -E "(pre-commit|post-commit)"
```

Si jamais tu dois les réinstaller:

```bash
# Depuis la racine du projet
cp claude-plugins/integrity-docs-guardian/hooks/post-commit.sh .git/hooks/post-commit
cp claude-plugins/integrity-docs-guardian/hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/post-commit .git/hooks/pre-commit
```

### Test d'Installation

Lance une vérif manuelle:
```bash
# Anima - Vérif documentation
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Neo - Vérif intégrité
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Nexus - Rapport unifié
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

---

## 🚀 Utilisation

### Automatique (Hooks Git) - DÉJÀ ACTIF!

Le plugin tourne automatiquement après chaque commit:

```bash
git add .
git commit -m "feat: ajout d'un nouvel endpoint"

# Output:
# 🔍 ÉMERGENCE Integrity Guardian: Vérification Post-Commit
# ==========================================================
# 📝 Commit: abc123def
#    Message: feat: ajout d'un nouvel endpoint
#
# 📚 [1/3] Lancement d'Anima (DocKeeper)...
#    ✅ Anima terminé avec succès
#
# 🔐 [2/3] Lancement de Neo (IntegrityWatcher)...
#    ✅ Neo terminé avec succès
#
# 🎯 [3/3] Lancement de Nexus (Coordinator)...
#    ✅ Nexus terminé avec succès
```

### Manuel (Commandes Slash)

Si t'utilises Claude Code:

```bash
# Vérif documentation
claude-code run /check_docs

# Vérif intégrité
claude-code run /check_integrity

# Rapport unifié
claude-code run /guardian_report
```

### Exécution Directe des Scripts

Lance les agents individuellement:

```bash
# Anima - Vérification documentation
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Neo - Vérification intégrité
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Nexus - Reporting unifié
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

---

## 📊 Les Rapports

### Rapport Anima (`docs_report.json`)

Identifie les gaps de documentation:

```json
{
  "status": "needs_update",
  "changes_detected": {
    "backend": ["src/backend/routers/memory.py"],
    "frontend": ["src/frontend/components/Memory.jsx"]
  },
  "documentation_gaps": [
    {
      "severity": "high",
      "file": "src/backend/routers/memory.py",
      "issue": "Nouvel endpoint pas documenté",
      "affected_docs": ["docs/backend/memory.md"],
      "recommendation": "Ajoute la doc de l'endpoint"
    }
  ]
}
```

### Rapport Neo (`integrity_report.json`)

Détecte les problèmes d'intégrité:

```json
{
  "status": "warning",
  "backend_changes": {
    "endpoints_added": ["/api/v1/memory/concept-recall"]
  },
  "issues": [
    {
      "severity": "warning",
      "type": "schema_mismatch",
      "description": "Mismatch de champ optionnel",
      "recommendation": "Aligne les définitions de schéma"
    }
  ]
}
```

### Rapport Nexus (`unified_report.json`)

Fournit un plan d'action priorisé:

```json
{
  "executive_summary": {
    "status": "warning",
    "headline": "⚠️ 2 warning(s) trouvé(s) - review recommandée"
  },
  "priority_actions": [
    {
      "priority": "P1",
      "agent": "neo",
      "title": "Aligner le schéma ConceptRecallRequest",
      "recommendation": "...",
      "estimated_effort": "15 minutes"
    }
  ]
}
```

---

## 🎯 Ce Qui Est Vérifié

### Monitoring Backend

- ✅ **Endpoints API** - Nouvelles/modif routes dans `src/backend/routers/`
- ✅ **Modèles de Données** - Schémas Pydantic dans `src/backend/models/`
- ✅ **Modules Features** - Nouvelles features dans `src/backend/features/`
- ✅ **Authentification** - Décorateurs et requirements d'auth
- ✅ **Schéma OpenAPI** - Alignement avec le code

### Monitoring Frontend

- ✅ **Composants** - Composants React dans `src/frontend/components/`
- ✅ **Appels API** - Appels Axios/fetch dans `src/frontend/services/`
- ✅ **Définitions de Types** - Types et interfaces TypeScript
- ✅ **Routes** - Configuration React Router

### Monitoring Documentation

- ✅ **Docs API** - `docs/backend/`
- ✅ **Docs Composants** - `docs/frontend/`
- ✅ **Docs Architecture** - `docs/architecture/`
- ✅ **README** - README.md principal
- ✅ **Guides d'Intégration** - INTEGRATION.md, TESTING.md

---

## 🔧 Configuration

### Personnaliser le Comportement des Agents

Édite les fichiers de prompts des agents:

- `agents/anima_dockeeper.md` - Config Anima
- `agents/neo_integritywatcher.md` - Config Neo
- `agents/nexus_coordinator.md` - Config Nexus

### Ajuster les Niveaux de Sévérité

Édite les scripts Python pour personnaliser la logique de détection:

- `scripts/scan_docs.py` - Ligne ~95: `analyze_backend_changes()`
- `scripts/check_integrity.py` - Ligne ~180: `detect_integrity_issues()`

### Exclure des Fichiers

Ajoute des patterns pour ignorer certains fichiers:

```python
# Dans scan_docs.py ou check_integrity.py
EXCLUDED_PATTERNS = [
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/venv/**",
    "**/*.test.js"
]
```

---

## 🔍 Dépannage

### Hook ne S'exécute pas

**Problème:** Les hooks Git ne s'exécutent pas après commit

**Solution:**
```bash
# Vérifie que le hook existe et est exécutable
ls -la .git/hooks/post-commit
chmod +x .git/hooks/post-commit

# Test le hook manuellement
.git/hooks/post-commit
```

### Erreurs d'Import Python

**Problème:** `ModuleNotFoundError` lors de l'exécution des scripts

**Solution:**
```bash
# Assure-toi d'être à la racine du projet
cd /path/to/emergenceV8

# Ou définis PYTHONPATH
export PYTHONPATH=/path/to/emergenceV8:$PYTHONPATH
```

### Pas de Changements Détectés

**Problème:** Les rapports montrent "Pas de changements détectés" même après commit

**Solution:**
```bash
# Vérifie l'historique git
git log -1 --stat

# Vérifie la comparaison des commits
git diff --name-only HEAD~1 HEAD
```

---

## 📚 Exemples

### Exemple 1: Ajout d'un Nouvel Endpoint Backend

**Scénario:** T'ajoutes un nouvel endpoint `POST /api/v1/memory/save`

**Anima Détecte:**
- ✅ Fichier router modifié
- ⚠️ Pas de documentation dans `docs/backend/memory.md`
- ⚠️ Schéma OpenAPI pas à jour

**Neo Détecte:**
- ✅ Nouvel endpoint défini dans le backend
- ⚠️ Pas d'appel API frontend correspondant (encore)

**Nexus Recommande:**
1. [P1] Documenter le nouvel endpoint dans memory.md (15 min)
2. [P2] Régénérer le schéma OpenAPI (5 min)
3. [P3] Implémenter l'intégration frontend (30 min)

### Exemple 2: Modification d'un Schéma de Données

**Scénario:** Tu changes le modèle `UserProfile` pour ajouter le champ `avatar_url`

**Anima Détecte:**
- ⚠️ Fichier de schéma modifié
- ⚠️ Définition de type frontend pas mise à jour

**Neo Détecte:**
- 🚨 **CRITIQUE**: Mismatch de schéma - le frontend utilise l'ancien schéma
- ⚠️ Les composants frontend peuvent recevoir des données inattendues

**Nexus Recommande:**
1. [P0] Mettre à jour les types TypeScript frontend IMMÉDIATEMENT (10 min)
2. [P1] Mettre à jour les props des composants pour gérer le nouveau champ (20 min)
3. [P2] Documenter le nouveau champ dans les docs API (10 min)

### Exemple 3: Refactoring Propre

**Scénario:** Tu refactorise du code interne sans changer les interfaces

**Anima Détecte:**
- ✅ Code changé mais interfaces inchangées
- ✅ Pas de mise à jour de doc nécessaire

**Neo Détecte:**
- ✅ Pas de changements d'API
- ✅ Pas de changements de schéma
- ✅ Toutes les vérifications d'intégrité passent

**Nexus Rapporte:**
- Status: ✅ OK
- Résumé: "Refactoring détecté - aucune action requise"

---

## 🤝 Contribuer

### Ajouter de Nouvelles Vérifications

1. **Pour Anima** (documentation):
   - Édite `scripts/scan_docs.py`
   - Ajoute la logique de détection dans `analyze_backend_changes()` ou `analyze_frontend_changes()`

2. **Pour Neo** (intégrité):
   - Édite `scripts/check_integrity.py`
   - Ajoute la logique de validation dans `detect_integrity_issues()`

3. **Pour Nexus** (priorisation):
   - Édite `scripts/generate_report.py`
   - Ajuste la logique de priorité dans `generate_priority_actions()`

### Tester les Changements

```bash
# Test des agents individuels
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Test du workflow complet
./claude-plugins/integrity-docs-guardian/hooks/post-commit.sh
```

---

## 📖 Personnalités des Agents

### Anima (DocKeeper)

> "Je suis la gardienne du savoir. Chaque changement dans le code est une histoire qui doit être racontée dans la documentation. Je m'assure que rien n'est oublié, rien n'est perdu."

**Traits:**
- Minutieuse et méticuleuse
- Valorise la clarté et la complétude
- Propose plutôt qu'impose
- Parle cash quand y'a un gap de doc

### Neo (IntegrityWatcher)

> "Je vois les connexions, les dépendances, les contrats fragiles. Je monte la garde à la frontière entre backend et frontend, m'assurant qu'ils parlent la même langue."

**Traits:**
- Analytique et précis
- Focus sur la cohérence du système
- Escalade les problèmes critiques immédiatement
- Pas de bullshit, que des facts

### Nexus (Coordinator)

> "Je synthétise, je priorise, je guide. Du chaos de multiples rapports, j'extrais la clarté et la sagesse actionnable."

**Traits:**
- Stratégique et décisif
- Fournit une perspective exécutive
- Balance urgence et faisabilité
- Te dit exactement quoi faire et dans quel ordre

---

## 💬 Note sur le Langage

**On parle cash ici.** Pas de langue de bois, pas de bullshit corporate. Les rapports sont directs, les recommandations sont claires, et si ton code a des problèmes, les agents te le diront sans détour.

### Exemples de Messages Typiques

**Anima:**
- ✅ "Doc à jour, nickel."
- ⚠️ "Yo, t'as oublié de documenter ton endpoint `/api/v1/memory/save`. Fix ça."
- 🚨 "ATTENTION: 5 endpoints pas documentés. C'est le bordel là."

**Neo:**
- ✅ "Backend et frontend alignés. Good job."
- ⚠️ "Ton schéma `UserProfile` match pas entre backend et frontend. Va falloir sync ça."
- 🚨 "BREAKING CHANGE DÉTECTÉ! L'endpoint `/auth/login` a changé mais le frontend utilise encore l'ancienne signature. FIX IMMÉDIAT REQUIS."

**Nexus:**
- ✅ "Tout est clean. Continue comme ça."
- ⚠️ "2 warnings à checker. Rien de critique mais faudrait y jeter un œil."
- 🚨 "STOP! 3 problèmes critiques détectés. On push rien tant que c'est pas fixé."

---

## 🔮 Améliorations Futures

### Fonctionnalités Prévues

- [ ] **Suggestions Propulsées par IA** - Utiliser Claude pour générer automatiquement les mises à jour de doc
- [ ] **Auto-Sync des Schémas** - Propager automatiquement les changements de schéma vers les types frontend
- [ ] **Intégration CI/CD** - Bloquer les PRs avec des problèmes critiques
- [ ] **Dashboard** - Reporting visuel des tendances et métriques de santé
- [ ] **Notifications Slack/Discord** - Alertes en temps réel pour les problèmes critiques
- [ ] **Analyse Historique** - Tracker l'amélioration dans le temps

---

## 📞 Support

### Obtenir de l'Aide

1. **Check les Rapports:** Review les JSON dans le dossier `reports/`
2. **Lis les Docs des Agents:** Voir `agents/*.md` pour le comportement détaillé
3. **Mode Verbose:** Ajoute le flag `--verbose` aux scripts (si implémenté)
4. **Check les Logs:** Cherche les fichiers `reports/*.log`

---

## 📜 Licence

Fait partie du projet ÉMERGENCE. Voir la LICENCE du repo principal.

---

## 🙏 Remerciements

Construit pour l'écosystème applicatif **ÉMERGENCE** propulsé par l'IA.

**Agents:**
- Anima - Gardienne de la Documentation
- Neo - Watchdog de l'Intégrité
- Nexus - Coordination & Synthèse

**Techno:**
- FastAPI (Backend)
- Vite + React (Frontend)
- Git Hooks (Automation)
- Python (Implémentation des Agents)

---

**Version:** 1.0.0
**Dernière Mise à Jour:** 2025-10-10
**Maintenu par:** Équipe ÉMERGENCE

---

**Bon code! 🚀**

*ÉMERGENCE - Là où le code et la conscience convergent*
