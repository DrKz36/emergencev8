# Prompt Session Suivante - Emergence V8

## 📊 État Production Actuel

### Déploiements validés ✅
- **Révision Cloud Run** : `emergence-app-phase3b`
- **Image** : `cockpit-phase3-20251009-073931` (digest `sha256:4c0a51...`)
- **URL** : https://emergence-app-486095406755.europe-west1.run.app
- **Métriques Prometheus** : ✅ Actives (13 métriques concept_recall + memory_analysis)
- **Métriques cache** : ✅ Instrumentées (`cache_hits_total`, `cache_misses_total`)
- **Timeline SQL** : ✅ Stabilisée (LEFT JOIN corrigés)
- **Tests** : ✅ 152 tests pytest, ruff, mypy, npm build passent

### Travaux Codex complétés (session parallèle)
- ✅ `qa_metrics_validation.py` - QA cockpit unifiée
- ✅ `scripts/qa/run_cockpit_qa.ps1` - Routine orchestrée
- ✅ `scripts/qa/purge_test_documents.py` - Nettoyage artefacts
- ✅ TimelineService corrigé (erreur SQL résolue)
- ✅ types-psutil ajouté (mypy clean)
- ✅ Documentation complète Phase 3 cockpit

### Commits récents
```
6c032b1 qa: unify cockpit QA workflow and cleanup timelines
2546c25 docs: prompt P1 enrichissement mémoire - déportation async + préférences
78e0643 docs: validation complète cockpit Phase 3 + prompt deploy Codex
625b295 feat: métriques coûts enrichies + timeline dashboard (Phase 3)
```

---

## 🎯 PROCHAINE PRIORITÉ : PHASE P1 MÉMOIRE

### Contexte stratégique

**Cockpit Phase 3** : ✅ **COMPLÉTÉ ET DÉPLOYÉ**
- Métriques Prometheus opérationnelles
- Timeline + coûts fonctionnels
- QA automatisée prête

**Mémoire sémantique** : 🔄 **PHASE P1 À IMPLÉMENTER**
- P0 validée ✅ (persistance, restauration, cache BDD)
- Phase 2 validée ✅ (neo_analysis, cache in-memory)
- Phase 3 validée ✅ (métriques Prometheus)
- **P1 restante** : Enrichissement conceptuel (préférences, intentions, contraintes)

### Document de référence

📄 **[PROMPT_P1_MEMORY_ENRICHMENT.md](PROMPT_P1_MEMORY_ENRICHMENT.md)** (987 lignes)
- Guide complet Phase P1 décomposée en 3 volets
- Code complet fourni (task_queue.py, preference_extractor.py)
- Tests unitaires inclus
- Durée estimée : 10-14h

---

## 📋 TÂCHES PRIORITAIRES

### Option A : Implémenter P1 Mémoire (RECOMMANDÉ)

**Priorité** : HAUTE - Feature critique pour enrichissement mémoire

**P1.1 - Déportation Asynchrone** (3-4h) - 🔴 PRIORITÉ HAUTE
- [ ] Créer `src/backend/features/memory/task_queue.py`
- [ ] Implémenter `MemoryTaskQueue` (asyncio.Queue + workers)
- [ ] Ajouter `analyze_session_async()` dans `analyzer.py`
- [ ] Modifier lifecycle `main.py` (startup/shutdown)
- [ ] Tests unitaires queue
- [ ] Validation latence WebSocket <100ms

**P1.2 - Extension Extraction** (6-8h) - 🟡 PRIORITÉ MOYENNE
- [ ] Créer `src/backend/features/memory/preference_extractor.py`
- [ ] Pipeline hybride (filtrage lexical → LLM → normalisation)
- [ ] Intégrer dans `MemoryGardener.garden_thread()`
- [ ] Vectorisation collection `memory_preferences_{user_sub}`
- [ ] Tests unitaires extraction
- [ ] Validation corpus (précision >0.85, rappel >0.75)

**P1.3 - Instrumentation Métriques** (1-2h) - 🟢 PRIORITÉ BASSE
- [ ] Instrumenter 3 métriques cache restantes (déjà fait par Codex ✅)
- [ ] Ajouter 5 métriques préférences
- [ ] Tests métriques
- [ ] Dashboard Grafana update

**Fichiers fournis dans le prompt** :
- Code complet `MemoryTaskQueue` (200+ lignes)
- Code complet `PreferenceExtractor` (400+ lignes)
- Tests unitaires
- Critères de succès détaillés

---

### Option B : Routine QA & Planification (MAINTENANCE)

**Priorité** : BASSE - Automatisation déjà en place

1. **Routine QA distante**
   - Exécuter `scripts/qa/run_cockpit_qa.ps1` avec credentials prod
   - Archiver rapports dans `docs/monitoring/snapshots/`

2. **Planification automatique**
   - Task Scheduler Windows (ou cron)
   - Quotidien 07:30 CEST
   - Documenter dans `docs/qa/cockpit-qa-playbook.md`

3. **Bundle final FG**
   - Relire git diff
   - Aligner `build_tag.txt` avec révision Cloud Run
   - Préparer commit/push/tag si requis

---

## 💡 RECOMMANDATION

**Attaquer P1 Mémoire (Option A)** car :

1. **Impact métier** : Feature critique pour enrichissement mémoire LTM
2. **Fondation P2** : P1 prépare la réactivité proactive (rappels conceptuels)
3. **Code prêt** : 987 lignes de guide + code complet fourni
4. **Momentum** : P0-Phase2-Phase3 validées, logique d'enchainer P1
5. **QA cockpit** : Automatisation déjà complète (Option B = maintenance)

---

## 📝 Prompt de Reprise (Copier-Coller)

```markdown
Bonjour Claude,

Je reprends le développement d'Emergence V8 après validation complète Phase 3 Cockpit (métriques Prometheus + timeline).

**État actuel** :
- ✅ Production : révision `emergence-app-phase3b` déployée et stable
- ✅ Métriques Prometheus : 13 métriques actives + cache instrumenté
- ✅ QA cockpit : automatisée via `qa_metrics_validation.py`
- ✅ Tests : 152 pytest, ruff, mypy, npm build passent
- ✅ Mémoire : P0 validée, Phase 2-3 déployées

**Mission : Implémenter Phase P1 - Enrichissement Mémoire**

Guide complet disponible : **[PROMPT_P1_MEMORY_ENRICHMENT.md](PROMPT_P1_MEMORY_ENRICHMENT.md)** (987 lignes)

**Tâches hiérarchisées** :

1. **P1.1 - Déportation Asynchrone** (3-4h) - 🔴 HAUTE
   - Créer `MemoryTaskQueue` (asyncio) pour éviter blocage event loop
   - Implémenter `analyze_session_async()`
   - Tests unitaires + validation latence WebSocket <100ms

2. **P1.2 - Extension Extraction** (6-8h) - 🟡 MOYENNE
   - Pipeline hybride préférences/intentions/contraintes
   - `PreferenceExtractor` avec filtrage lexical + LLM (gpt-4o-mini)
   - Collection vectorielle `memory_preferences_{user_sub}`
   - Validation corpus (précision >0.85)

3. **P1.3 - Métriques** (1-2h) - 🟢 BASSE
   - 5 métriques préférences Prometheus
   - Dashboard Grafana update

**Code complet fourni** dans PROMPT_P1 :
- `task_queue.py` (200+ lignes)
- `preference_extractor.py` (400+ lignes)
- Tests unitaires
- Critères de succès

**Ordre d'exécution** : P1.1 → P1.2 → P1.3 (total 10-14h)

**Fichiers clés** :
- [docs/memory-roadmap.md](docs/memory-roadmap.md) - Roadmap complète
- [PROMPT_P1_MEMORY_ENRICHMENT.md](PROMPT_P1_MEMORY_ENRICHMENT.md) - Guide détaillé

Commence par **lire PROMPT_P1_MEMORY_ENRICHMENT.md** puis implémenter P1.1 (déportation asynchrone).

Objectif : Event loop non bloqué + extraction préférences automatique + 8 nouvelles métriques.

Bonne session ! 🚀
```

---

## 📚 Ressources

### Documentation Phase P1
- **[PROMPT_P1_MEMORY_ENRICHMENT.md](PROMPT_P1_MEMORY_ENRICHMENT.md)** - Guide complet (987 lignes)
- **[docs/memory-roadmap.md](docs/memory-roadmap.md)** - Roadmap mémoire
- **[docs/deployments/PHASES_RECAP.md](docs/deployments/PHASES_RECAP.md)** - État Phases 2-3

### État Production
- **[docs/deployments/2025-10-09-deploy-cockpit-phase3.md](docs/deployments/2025-10-09-deploy-cockpit-phase3.md)** - Déploiement Codex
- **[docs/monitoring/prometheus-phase3-setup.md](docs/monitoring/prometheus-phase3-setup.md)** - Setup monitoring

### QA Cockpit (si besoin)
- `qa_metrics_validation.py` - Script unifié
- `scripts/qa/run_cockpit_qa.ps1` - Routine orchestrée
- **[docs/qa/cockpit-qa-playbook.md](docs/qa/cockpit-qa-playbook.md)** - Playbook

---

## 🎯 Objectif Session

**Implémenter Phase P1 Mémoire** pour :
1. ✅ Event loop WebSocket non bloqué (<100ms)
2. ✅ Extraction automatique préférences/intentions/contraintes
3. ✅ Collection vectorielle enrichie `memory_preferences_*`
4. ✅ 8 nouvelles métriques Prometheus
5. ✅ Tests validés (précision >0.85, rappel >0.75)

**Phase P1 prépare P2** (réactivité proactive) où les préférences capturées seront utilisées pour suggérer actions contextuelles.

---

**Dernière mise à jour** : 2025-10-09 après déploiement Codex Phase 3 Cockpit
