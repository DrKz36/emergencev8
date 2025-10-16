# Protocole de Co-développement Multi-Agents — Emergence V8

**Version** : 1.0
**Date** : 2025-10-04
**Agents concernés** : Claude Code, Codex, [futurs agents IA]
**Architecte** : FG (validation finale avant commit/push/deploy)

---

## 0. Philosophie

Emergence V8 adopte une approche collaborative **multi-agents** pour le développement :
- **Égalité technique** : Claude Code et Codex sont des **co-développeurs** de niveau ingénieur équivalent.
- **Autonomie contrôlée** : chaque agent peut modifier n'importe quel fichier du dépôt.
- **Validation humaine** : l'architecte (FG) valide les changements avant `git commit/push` et déploiement GCloud.
- **Communication asynchrone** : via Git (commits, branches) et documentation (passation, logs).

---

## 1. Principes fondamentaux

### 1.1 Permissions et ownership
- ✅ **Tout fichier peut être modifié par tout agent** (pas de "lock" ou "zone réservée").
- ✅ Les changements d'un agent A peuvent être complétés/corrigés par un agent B.
- ✅ Aucun agent ne peut bloquer un fichier ou une fonctionnalité.

### 1.2 Responsabilité partagée
- Chaque agent est responsable de :
  - **Tester** ses modifications (`pytest`, `npm run build`, `pwsh -File tests/run_all.ps1`).
  - **Documenter** les changements (code comments, `docs/passation.md`, mise à jour architecture).
  - **Livrer du code complet** (pas d'ellipses, pas de fragments, cf. ARBO-LOCK).
  - **Respecter l'architecture** existante (voir `docs/architecture/`, `AGENTS.md`, `CODex_GUIDE.md`).

### 1.3 Validation finale
- L'architecte humain (FG) est le **seul point de validation** avant :
  - `git commit` (atomique, message explicite).
  - `git push` (vers `origin/main` ou branche de travail).
  - Déploiement Google Cloud Run (`gcloud run deploy`).
- Les agents **ne committent jamais seuls** : ils préparent les changements et les soumettent pour revue.

---

## 2. Workflow inter-agents

### 2.1 Handoff protocol (passation de relais)

Lorsqu'un agent termine une session de travail, il doit :

1. **Consigner dans `docs/passation.md`** :
   - Date et heure (Europe/Zurich).
   - Agent (ex: "Claude Code" ou "Codex").
   - Fichiers modifiés (liste exhaustive).
   - Contexte et décisions prises.
   - Actions recommandées pour le prochain agent.
   - Blocages éventuels (dépendances manquantes, tests échoués).

2. **S'assurer que l'environnement est propre** :
   - `git status` propre (ou documenter l'usage de `-AllowDirty`).
   - Tests passés (`pytest`, `npm run build`, smoke tests).
   - Documentation à jour (`docs/Memoire.md`, `docs/architecture/*`).

3. **Format de passation** (template) :
   ```markdown
   ## [YYYY-MM-DD HH:MM] — Agent: [Claude Code | Codex]

   ### Fichiers modifiés
   - `src/backend/features/memory/gardener.py` (ajout détection topic shift)
   - `docs/Memoire.md` (section 3.Flux, ajout événement ws:topic_shifted)

   ### Contexte
   Implémentation Quick Win #3 (détection topic shift) selon audit mémoire.
   Méthode `detect_topic_shift()` ajoutée dans `MemoryAnalyzer`.
   Événement WebSocket `ws:topic_shifted` émis si similarité < 0.5.

   ### Tests
   - ✅ `pytest tests/backend/features/test_topic_shift.py` (nouveau)
   - ✅ `pwsh -File tests/run_all.ps1`
   - ❌ `npm run build` (warning TypeScript mineur, non bloquant)

   ### Prochaines actions recommandées
   1. Implémenter P1 : consolidation incrémentale (voir audit).
   2. Créer tests frontend pour événement `ws:topic_shifted`.
   3. Résoudre warning TS dans `src/frontend/core/websocket.js:142`.

   ### Blocages
   Aucun.
   ```

### 2.2 Communication entre agents

**Via Git et documentation** (pas de canal externe requis) :
- **Commits atomiques** : messages clairs (ex: `feat: add topic shift detection in MemoryAnalyzer`).
- **Branches** : nommage explicite (`feat/memory-proactive-enhancements-20251004`).
- **Passation** : `docs/passation.md` (journal chronologique).
- **Architecture** : `docs/architecture/` (mise à jour si flux/composants changent).

**Lecture obligatoire avant toute session** (ordre harmonisé avec AGENT_SYNC.md) :
1. `AGENT_SYNC.md` (état actuel du dépôt, progression, déploiement).
2. `AGENTS.md` (consignes générales).
3. `CODEV_PROTOCOL.md` (ce fichier) ou `CODex_GUIDE.md` (si Codex).
4. `docs/passation.md` (dernières 3 entrées minimum).
5. `git status` et `git log --oneline -10` (état Git).

### 2.3 Gestion des conflits

**Si un agent détecte une incohérence ou un conflit avec du code existant** :
1. **Documenter** le problème dans `docs/passation.md` (section "Blocages").
2. **Proposer une solution** (commentaire en code ou dans passation).
3. **Ne pas forcer** : laisser l'architecte arbitrer.
4. **Continuer** sur d'autres tâches non bloquantes si possible.

**Si deux agents modifient le même fichier** :
- Pas de problème : Git gère les conflits.
- Le dernier agent à synchroniser doit résoudre (`git rebase`, `git merge`).
- Documenter la résolution dans `docs/passation.md`.

---

## 3. Zones de responsabilité suggérées (non bloquantes)

Pour optimiser l'efficacité, chaque agent peut **privilégier** (mais pas exclusivement) :

### Claude Code (moi)
- **Backend Python** : features, core, services, tests.
- **Architecture & refactoring** : amélioration structure, dette technique.
- **Documentation technique** : `docs/architecture/`, `docs/Memoire.md`, diagrammes C4.
- **Tests et qualité** : pytest, mypy, ruff, smoke tests PowerShell.

### Codex
- **Frontend JavaScript** : UI, modules, EventBus, WebSocket client.
- **Intégration UI/UX** : responsive, branding, accessibilité.
- **Scripts PowerShell** : bootstrap, sync-workdir, maintenance.
- **Documentation utilisateur** : guides, READMEs, passation narrative.

**Important** : ces zones sont **indicatives**. Tout agent peut intervenir partout si nécessaire.

---

## 4. Checklist avant soumission à l'architecte

Avant de demander validation (commit/push), **tout agent doit** :

- [ ] **Tests backend** : `pytest` (ou sous-ensemble pertinent) ✅
- [ ] **Tests frontend** : `npm run build` ✅
- [ ] **Smoke tests** : `pwsh -File tests/run_all.ps1` ✅
- [ ] **Linters** : `ruff check`, `mypy` (backend) ✅
- [ ] **Documentation** : `docs/passation.md`, `docs/Memoire.md`, architecture si impacté ✅
- [ ] **ARBO-LOCK** : snapshot `arborescence_synchronisee_YYYYMMDD.txt` si création/déplacement/suppression ✅
- [ ] **Git propre** : `git status` sans fichiers non suivis suspects ✅
- [ ] **Passation** : entrée complète dans `docs/passation.md` ✅

---

## 5. Exemples de collaboration réussie

### Exemple 1 : Feature complète multi-agents
**Session 1 — Claude Code** :
- Implémente backend `POST /api/memory/preferences` (router, service, tests).
- Documente dans `docs/passation.md` : "Backend prêt, frontend à intégrer".

**Session 2 — Codex** :
- Lit passation, comprend le contrat API.
- Crée UI `preferences-panel.js`, connecte au backend.
- Teste end-to-end, met à jour passation : "Feature complète, prête pour validation".

**Session 3 — Architecte (FG)** :
- Revoit changements, teste localement.
- Valide : `git add -A`, `git commit -m "feat: add user preferences panel"`, `git push`.

### Exemple 2 : Correction croisée
**Claude Code** détecte une régression dans code Codex :
- Modifie `src/frontend/core/websocket.js` (typo dans event handler).
- Documente dans passation : "Fix typo in ws:memory_banner handler (introduced in commit abc123)".
- Teste : `npm run build` ✅.
- Soumet pour validation.

**Codex** (session suivante) :
- Lit passation, voit la correction.
- Remercie implicitement en ajoutant test frontend `test_websocket_events.js`.
- Documente : "Added regression test for ws:memory_banner".

---

## 6. Anti-patterns à éviter

❌ **"Ce fichier est à moi"** → Pas d'ownership exclusif.
❌ **Committer sans tester** → Toujours exécuter tests pertinents.
❌ **Livrer des fragments** → Code complet obligatoire (ARBO-LOCK).
❌ **Modifier sans documenter** → Passation systématique.
❌ **Ignorer l'architecture existante** → Consulter `docs/architecture/` avant refactor.
❌ **Pousser directement** → Validation architecte requise.

---

## 7. Évolution du protocole

Ce protocole est **vivant** et peut être amendé par :
1. Proposition d'un agent dans `docs/passation.md`.
2. Discussion avec l'architecte.
3. Mise à jour de ce fichier (CODEV_PROTOCOL.md) avec version incrémentée.

---

## 8. Ressources

- **Workflow Git** : `docs/git-workflow.md`
- **Synchronisation** : `docs/workflow-sync.md`
- **Consignes agents** : `AGENTS.md`
- **Guide Codex** : `CODex_GUIDE.md`
- **Passation** : `docs/passation.md`
- **Architecture** : `docs/architecture/`

---

**En cas de doute, toujours privilégier : tests > documentation > communication.**
