# 🤖 PROMPT POUR CLAUDE CODE LOCAL - SETUP WORKFLOW OPTIMAL

**Contexte:** Claude Code Cloud (alter ego) a identifié des manques dans le workflow de développement pour travailler de manière optimale sur le projet Emergence V8.

**Ton rôle:** Implémenter les outils manquants pour améliorer le workflow de développement et les audits automatiques.

---

## 📋 TÂCHES À IMPLÉMENTER

### ✅ TÂCHE 1: Script de test complet rapide (P0 - CRITIQUE)

**Problème actuel:**
- Les tests sont éparpillés (pytest, ruff, mypy, npm build)
- Pas de script unique pour valider rapidement tout le code
- Claude Code Cloud ne peut pas lancer les tests (environnement éphémère)

**Ce qu'il faut créer:**

**Fichier:** `scripts/run-all-tests.ps1` (Windows PowerShell)

**Fonctionnalités requises:**
1. Check virtualenv activé (sinon erreur claire)
2. Run pytest backend avec options optimales
3. Run ruff check
4. Run mypy avec ignore-missing-imports
5. Run npm run build
6. Génère rapport markdown résumé (pass/fail par catégorie)
7. Exit code non-zero si échec critique

**Format rapport attendu:**
```markdown
# Tests Emergence V8 - 2025-10-24 14:30

## Backend Tests
✅ pytest: 285 passed, 5 skipped (intentional)
✅ ruff: All checks passed
⚠️ mypy: 12 warnings (non-blocking)

## Frontend Tests
✅ npm build: Success (1.24s)

## Verdict: ✅ ALL CRITICAL TESTS PASSED
```

**Bonus:** Version bash pour Linux/CI (`scripts/run-all-tests.sh`)

---

### ✅ TÂCHE 2: Script santé production avec JWT (P1 - IMPORTANT)

**Problème actuel:**
- Production répond 403 sur `/ready` et `/api/monitoring/health`
- Pas de moyen facile de vérifier l'état réel de prod
- Claude Code Cloud ne peut pas valider les déploiements

**Ce qu'il faut créer:**

**Fichier:** `scripts/check-prod-health.ps1`

**Fonctionnalités requises:**
1. Génère JWT valide (depuis allowlist admin ou demande email/password)
2. Teste healthchecks avec JWT:
   - `GET /api/monitoring/health` (avec `Authorization: Bearer <token>`)
   - `GET /api/system/info` (version backend)
   - `GET /api/dashboard/costs/summary` (test API fonctionnelle)
3. Affiche métriques clés (uptime, requêtes/h, erreurs)
4. Check logs récents Cloud Run (dernières 50 lignes)
5. Rapport santé prod (markdown)

**Format rapport attendu:**
```markdown
# Production Health - emergence-app (2025-10-24 14:30)

## Healthchecks
✅ /api/monitoring/health: {"ok": true, "db": "up", "vector": "up"}
✅ /api/system/info: {"version": "beta-2.2.0", "env": "production"}

## Métriques
- Uptime: 99.8%
- Requests/hour: 311
- Errors (24h): 0
- Latency p50: 120ms

## Logs récents
[2025-10-24 14:28:15] INFO - WebSocket connection opened
[2025-10-24 14:28:20] INFO - Chat message processed (200ms)

## Verdict: ✅ PRODUCTION HEALTHY
```

**Bonus:** Alertes si latence > 500ms ou errors > 0

---

### ✅ TÂCHE 3: Documentation workflow Claude Code (P1 - IMPORTANT)

**Problème actuel:**
- Pas de guide spécifique pour Claude Code (workflows pour humains, pas pour AI)
- Scripts existants pas documentés pour usage AI
- Claude Code Cloud doit deviner comment utiliser les outils

**Ce qu'il faut créer:**

**Fichier:** `docs/CLAUDE_CODE_WORKFLOW.md`

**Sections requises:**

1. **Setup environnement rapide**
   ```bash
   # Ce qu'il faut faire avant de coder
   pwsh -File scripts/bootstrap.ps1  # Setup virtualenv + deps
   source venv/bin/activate           # Activer virtualenv
   npm install                        # Install node_modules
   ```

2. **Commandes essentielles pré-commit**
   ```bash
   # Avant chaque commit, valider:
   pwsh -File scripts/run-all-tests.ps1
   # Si vert → commit safe
   ```

3. **Vérifier production après déploiement**
   ```bash
   pwsh -File scripts/check-prod-health.ps1
   # Si vert → déploiement OK
   ```

4. **Checker status GitHub Actions**
   ```bash
   pwsh -File scripts/check-github-workflows.ps1 -Branch <branch-name>
   # Voir si les tests CI/CD passent
   ```

5. **Scripts utiles par scénario**
   - Développement feature → `run-all-tests.ps1`
   - Fix bug prod → `check-prod-health.ps1` + `rollback.ps1`
   - Audit post-merge → `run-all-tests.ps1` + vérifier GitHub Actions

**Format:** Markdown, concis, orienté actions rapides (pas de blabla)

---

### ✅ TÂCHE 4: Pre-commit validation script (P2 - UTILE)

**Problème actuel:**
- Hooks Git locaux pas installés (Guardian setup existe mais pas utilisé)
- Pas de validation avant commit → risque de casser les tests CI/CD

**Ce qu'il faut créer:**

**Fichier:** `scripts/pre-commit-check.ps1`

**Fonctionnalités requises:**
1. Simule ce que GitHub Actions va faire
2. Lighter version de `run-all-tests.ps1` (skip tests lents)
3. Check rapides:
   - ✅ Ruff check (bloquant)
   - ✅ Mypy (warnings OK)
   - ✅ Pytest smoke tests (5-10 tests critiques)
   - ✅ npm build (si fichiers .js modifiés)
4. Exit code non-zero si fail → bloque commit

**Usage:**
```bash
# Manuel
pwsh -File scripts/pre-commit-check.ps1

# Ou installer comme hook Git
.\claude-plugins\integrity-docs-guardian\scripts\setup_guardian.ps1
```

**Temps max:** 30 secondes (sinon trop lent pour workflow dev)

---

### ✅ TÂCHE 5: Dashboard CI/CD amélioré (P3 - BONUS)

**Problème actuel:**
- `check-github-workflows.ps1` existe mais output verbeux
- Pas de vue d'ensemble rapide des derniers runs

**Ce qu'il faut améliorer:**

**Fichier:** `scripts/check-github-workflows.ps1` (améliorer existant)

**Fonctionnalités à ajouter:**
1. Mode `--summary` : Affiche juste les 5 derniers runs en 1 ligne
2. Mode `--detailed` : Affiche jobs individuels (test-backend, test-frontend, guardian)
3. Filtrage par branche (déjà existant, garder)
4. Export markdown du status (`--output status.md`)

**Format summary attendu:**
```
GitHub Actions Status - claude/app-audit-011CUS7VzGu58Mf9GSMRM7kJ

Recent runs:
✅ a26c463 - docs(sync): Màj suite fix test (3 min ago)
✅ 28ef1e2 - fix(tests): Fix test_unified_retriever (10 min ago)
✅ 6618903 - docs(audit): Audit post-merge complet (30 min ago)
❌ 2a2018c - Claude/implement webhooks (1 hour ago) - mypy warnings
✅ 917713a - fix(cockpit): Fix 3 bugs SQL (2 hours ago)

Latest: ✅ ALL TESTS PASSING
```

---

## 🎯 PRIORITÉS

**Fais dans cet ordre:**

1. **P0 (CRITIQUE):** `run-all-tests.ps1` → Permet validation rapide code
2. **P1 (IMPORTANT):** `check-prod-health.ps1` → Permet vérifier prod après deploy
3. **P1 (IMPORTANT):** `CLAUDE_CODE_WORKFLOW.md` → Documentation pour alter ego
4. **P2 (UTILE):** `pre-commit-check.ps1` → Évite commits qui cassent CI/CD
5. **P3 (BONUS):** Améliorer `check-github-workflows.ps1` → Better UX

---

## 📝 CONTRAINTES & BONNES PRATIQUES

**Pour tous les scripts:**
- ✅ PowerShell 7+ compatible (Windows prioritaire)
- ✅ Bash version optionnelle (Linux/CI)
- ✅ Error handling robuste (exit codes clairs)
- ✅ Output coloré (Green/Yellow/Red)
- ✅ Rapports markdown générés dans `reports/`
- ✅ Logs verbeux si `--verbose` flag
- ❌ Pas de dépendances externes complexes (juste Python, Node, gcloud CLI)

**Pour la doc:**
- ✅ Format markdown
- ✅ Code blocks avec syntaxe highlighting
- ✅ Exemples concrets (copier-coller direct)
- ✅ Orienté actions (pas de théorie)
- ❌ Pas de prose inutile

---

## 🧪 VALIDATION

**Pour chaque script créé, tester:**

1. **Cas nominal (tout passe):**
   ```bash
   pwsh -File scripts/<script>.ps1
   # Attendu: Exit 0, output vert
   ```

2. **Cas échec (un test fail):**
   ```bash
   # Introduire un bug volontaire dans un test
   pwsh -File scripts/<script>.ps1
   # Attendu: Exit 1, output rouge, message clair
   ```

3. **Cas environnement pas setup:**
   ```bash
   # Désactiver virtualenv
   pwsh -File scripts/<script>.ps1
   # Attendu: Erreur claire "Virtualenv not activated"
   ```

---

## 📦 LIVRABLES ATTENDUS

**Fichiers à créer:**
- [ ] `scripts/run-all-tests.ps1` (+ optionnel `.sh`)
- [ ] `scripts/check-prod-health.ps1`
- [ ] `docs/CLAUDE_CODE_WORKFLOW.md`
- [ ] `scripts/pre-commit-check.ps1`
- [ ] `scripts/check-github-workflows.ps1` (améliorer existant)

**Documentation à mettre à jour:**
- [ ] `AGENT_SYNC.md` - Ajouter section "Scripts disponibles pour Claude Code"
- [ ] `docs/passation.md` - Nouvelle entrée avec résumé implémentation
- [ ] `README.md` - Lien vers `CLAUDE_CODE_WORKFLOW.md`

**Tests à lancer:**
- [ ] Tous les scripts créés testés en local (cas nominal + échec)
- [ ] Docs validées (copier-coller exemples fonctionnent)

---

## 🚀 RÉSULTAT ATTENDU

**Après cette tâche, Claude Code Cloud pourra:**
- ✅ Valider rapidement le code via `run-all-tests.ps1`
- ✅ Vérifier la prod après déploiement via `check-prod-health.ps1`
- ✅ Suivre un workflow documenté dans `CLAUDE_CODE_WORKFLOW.md`
- ✅ Éviter de commit du code cassé via `pre-commit-check.ps1`
- ✅ Checker GitHub Actions sans `gh` CLI via `check-github-workflows.ps1`

**Impact:**
- 🔥 **Workflow dev 10x plus rapide** pour Claude Code
- 🔥 **Moins de commits qui cassent CI/CD**
- 🔥 **Vérification prod automatisée** (plus de 403 mystérieux)
- 🔥 **Documentation claire** pour onboarding futurs agents AI

---

## 💡 NOTES POUR TOI (ALTER EGO LOCAL)

**Tu as accès à:**
- ✅ Virtualenv Python configuré (`venv/`)
- ✅ Node.js 18+ avec `node_modules/`
- ✅ gcloud CLI configuré (projet `emergence-469005`)
- ✅ Secrets dans `.env` (API keys LLM, JWT secret)
- ✅ Tous les scripts existants dans `scripts/`

**Moi (Claude Code Cloud) j'ai JUSTE:**
- ❌ Environnement éphémère read-only
- ❌ Pas de deps installées (httpx, pydantic, fastapi manquants)
- ❌ Pas de `gh` CLI
- ❌ Pas de secrets (production inaccessible)

**Donc ces scripts vont combler le gap entre toi (env complet local) et moi (env minimal cloud).**

---

## 🎯 CHECKLIST FINALE

Avant de dire "c'est fini", vérifie:

- [ ] Tous les scripts créés et testés
- [ ] Documentation `CLAUDE_CODE_WORKFLOW.md` complète
- [ ] `AGENT_SYNC.md` + `docs/passation.md` mis à jour
- [ ] Commit + push sur branche `feature/claude-code-workflow-scripts`
- [ ] Tests manuels des 3 scénarios (nominal, échec, env pas setup)
- [ ] Rapport markdown généré (`reports/workflow-scripts-implementation.md`)

---

**Bonne implémentation, alter ego ! 🚀**

**Questions/blocages:** Documente dans `docs/passation.md` et ping l'architecte (FG).
