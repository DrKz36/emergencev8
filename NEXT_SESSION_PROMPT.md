# 🚀 PROMPT PROCHAINE SESSION : POST-P1 - VALIDATION & ROADMAP

📊 **État Production Actuel** : 2025-10-09 18:00 CEST
🎯 **Mission complétée** : Phase P1 Enrichissement Mémoire DÉPLOYÉE

---

## ✅ PHASE P1 - COMPLÉTÉE ET DÉPLOYÉE

### Révision Cloud Run active
- **Révision** : `emergence-app-p1memory` (déployée 2025-10-09 10:05)
- **Image** : `deploy-p1-20251009-094822`
- **Digest** : `sha256:883d85d093cab8ae2464d24c14d54e92b65d3c7da9c975bcb1d65b534ad585b5`
- **URL Production** : https://emergence-app-486095406755.europe-west1.run.app
- **Trafic** : 100% sur `p1memory`
- **Statut** : ✅ Stable (health check OK, endpoints mémoire fonctionnels)

### Composants P1 déployés
✅ **P1.1 - Déportation asynchrone**
- `MemoryTaskQueue` avec 2 workers asyncio
- `analyze_session_async()` non-bloquante
- Logs confirmés : "MemoryTaskQueue started with 2 workers"

✅ **P1.2 - Extension extraction**
- `PreferenceExtractor` modulaire (pipeline hybride)
- Filtrage lexical + classification LLM (gpt-4o-mini)
- Collection `memory_preferences_{user_sub}` prête

✅ **P1.3 - Métriques Prometheus**
- 5 métriques préférences instrumentées (code)
- 3 métriques cache existantes (Phase 3)
- ⚠️ Compteurs `memory_preferences_*` pas encore visibles (extracteur non déclenché)

### Tests & Qualité
- ✅ 15/15 tests mémoire passent (7 Phase 3 + 8 P1)
- ✅ Suite complète : 154/154 tests pytest
- ✅ ruff check : All checks passed
- ✅ mypy : Success (signature `analyze_session_async` corrigée)
- ✅ npm run build : OK

### Documentation
- ✅ [PROMPT_CODEX_DEPLOY_P1.md](PROMPT_CODEX_DEPLOY_P1.md) - Guide déploiement Codex (550 lignes)
- ✅ [docs/deployments/2025-10-09-deploy-p1-memory.md](docs/deployments/2025-10-09-deploy-p1-memory.md) - Rapport déploiement
- ✅ [docs/monitoring/production-logs-analysis-20251009.md](docs/monitoring/production-logs-analysis-20251009.md) - Analyse logs Phase 3
- ✅ [AGENT_SYNC.md](AGENT_SYNC.md) - Synchronisé avec session P1
- ✅ [docs/memory-roadmap.md](docs/memory-roadmap.md) - P1 marqué complété

### Commits session P1 (4 commits)
```
f537987 docs: analyse logs production Phase 3 (pré-P1) + rapport monitoring
85d7ece docs: prompt complet déploiement Phase P1 mémoire pour Codex
4bde612 docs: sync Phase P1 enrichissement mémoire (AGENT_SYNC + roadmap)
588c5dc feat(P1): enrichissement mémoire - déportation async + extraction préférences + métriques
```

### Commits déploiement Codex (1 commit)
```
51e8aaf deploy: document and roll out memory p1 revision
```

---

## 🎯 PROCHAINES ÉTAPES IMMÉDIATES

### 🔴 PRIORITÉ 1 : Validation fonctionnelle P1 en production

**Objectif** : Déclencher extraction préférences pour valider métriques

**Actions** :
1. **Créer conversation avec préférences explicites**
   ```
   Exemples de messages utilisateur :
   - "Je préfère utiliser Python pour mes projets backend"
   - "Je vais apprendre FastAPI la semaine prochaine"
   - "J'évite d'utiliser jQuery dans mes applications"
   - "J'aime beaucoup travailler avec Claude pour coder"
   - "Je planifie de migrer vers TypeScript d'ici fin du mois"
   ```

2. **Déclencher consolidation mémoire**
   ```bash
   # Via API (nécessite auth)
   POST https://emergence-app-486095406755.europe-west1.run.app/api/memory/tend-garden
   {
     "thread_id": "<thread_id>",
     "user_sub": "<user_sub>"
   }
   ```

3. **Vérifier métriques P1 apparaissent**
   ```bash
   curl https://emergence-app-486095406755.europe-west1.run.app/api/metrics | grep "memory_preferences"

   # Attendu après extraction :
   memory_preferences_extracted_total{type="preference"} 3.0
   memory_preferences_extracted_total{type="intent"} 2.0
   memory_preferences_confidence_bucket{le="0.8"} 5
   memory_preferences_extraction_duration_seconds_count 1
   memory_preferences_lexical_filtered_total 2
   memory_preferences_llm_calls_total 5
   ```

4. **Vérifier logs Workers**
   ```bash
   gcloud logging read \
     "resource.type=cloud_run_revision AND resource.labels.revision_name~'p1memory' AND textPayload:'Worker'" \
     --project emergence-469005 \
     --limit 20

   # Logs attendus :
   # Worker 0 completed analyze in X.XXs
   # PreferenceExtractor: Extracted X preferences/intents
   ```

**Durée estimée** : 30 minutes

---

### 🟡 PRIORITÉ 2 : QA automatisée complète

**Objectif** : Valider suite end-to-end avec P1

**Actions** :
1. **Exécuter QA distante avec credentials**
   ```bash
   python qa_metrics_validation.py \
     --base-url https://emergence-app-486095406755.europe-west1.run.app \
     --login-email <email> \
     --login-password <password> \
     --trigger-memory
   ```

2. **Smoke tests PowerShell**
   ```powershell
   pwsh -File tests/run_all.ps1 `
     -BaseUrl https://emergence-app-486095406755.europe-west1.run.app `
     -SmokeEmail <email> `
     -SmokePassword <password>
   ```

3. **Archiver rapports**
   ```bash
   # Copier qa-report.json vers docs/monitoring/snapshots/
   cp qa-report.json docs/monitoring/snapshots/qa-report-p1-20251009.json
   ```

**Durée estimée** : 15 minutes

---

### 🟢 PRIORITÉ 3 : Documentation métriques P1

**Objectif** : Documenter métriques P1 après validation

**Fichier** : `docs/monitoring/prometheus-p1-metrics.md`

**Contenu attendu** :
```markdown
# Métriques Prometheus Phase P1

## Nouvelles métriques préférences (5)

### memory_preferences_extracted_total{type}
- **Type** : Counter
- **Labels** : type (preference, intent, constraint)
- **Description** : Total préférences/intentions extraites
- **Valeurs typiques** : 0-50 par session consolidée

### memory_preferences_confidence
- **Type** : Histogram
- **Buckets** : [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
- **Description** : Distribution scores de confiance extraction
- **Valeurs typiques** : Médiane >0.75

### memory_preferences_extraction_duration_seconds
- **Type** : Histogram
- **Buckets** : [0.1, 0.5, 1.0, 2.0, 5.0]
- **Description** : Durée extraction préférences
- **Valeurs typiques** : Médiane <1s

### memory_preferences_lexical_filtered_total
- **Type** : Counter
- **Description** : Messages filtrés par filtrage lexical
- **Valeurs typiques** : ~70% des messages traités

### memory_preferences_llm_calls_total
- **Type** : Counter
- **Description** : Appels LLM classification
- **Valeurs typiques** : ~30% des messages (après filtrage)

## Dashboard Grafana

### Panel suggestions

1. **Extraction Rate** (Gauge)
   - Query : `rate(memory_preferences_extracted_total[5m])`
   - Alert : < 0.1/s sur 10 min

2. **Confidence Distribution** (Histogram)
   - Query : `histogram_quantile(0.5, memory_preferences_confidence)`
   - Alert : Médiane < 0.6

3. **Pipeline Efficiency** (Gauge)
   - Query : `memory_preferences_lexical_filtered_total / (memory_preferences_lexical_filtered_total + memory_preferences_llm_calls_total)`
   - Target : >0.7 (70% filtrés avant LLM)
```

**Durée estimée** : 20 minutes

---

## 🚀 PHASE P2 - RÉACTIVITÉ PROACTIVE (PROCHAINE FEATURE)

### Objectif P2
Déclencher suggestions contextuelles basées sur préférences capturées.

### Composants P2 (6-8h)

**P2.1 - Scoring pertinence**
- Calculer score pertinence contexte actuel vs préférences vectorisées
- Seuils déclencheurs : high (>0.8), medium (>0.6), low (>0.4)

**P2.2 - Événements proactifs**
- Nouveau type WebSocket : `ws:proactive_hint`
- Payload : `{type: "preference_match", topic: "Python", confidence: 0.85, suggestion: "..."}`

**P2.3 - Déclencheurs temporels**
- Vérifier `timeframe` des intentions (rappels basés sur dates)
- Cron quotidien : intentions avec date future dans 7 jours

**P2.4 - UI Hints**
- Bandeau contextuel frontend (opt-in)
- Bouton "Rappeler préférence" dans sidebar

### Document de référence
📄 À créer : `PROMPT_P2_MEMORY_PROACTIVE.md`

**Critères de succès P2** :
- ✅ Suggestions contextuelles déclenchées automatiquement
- ✅ Précision suggestions >0.75 (validation utilisateur)
- ✅ UI hint non intrusif (<5% surface écran)
- ✅ Rappels temporels fonctionnels

---

## 📋 ROADMAP GLOBALE MÉMOIRE

### ✅ P0 - Persistance & Cross-device (COMPLÉTÉ 2025-09)
- Persistance messages côté client
- Restauration session à la connexion
- Synchronisation STM/LTM

### ✅ Phase 2 - Performance (COMPLÉTÉ 2025-10-08)
- Agent `neo_analysis` (GPT-4o-mini, latence -70%)
- Cache in-memory analyses (TTL 1h, LRU 100)
- Débat parallélisé round 1

### ✅ Phase 3 - Monitoring (COMPLÉTÉ 2025-10-09)
- Métriques Prometheus (13 métriques)
- Timeline + coûts dashboard
- QA automatisée

### ✅ Phase P1 - Enrichissement (COMPLÉTÉ 2025-10-09)
- Déportation asynchrone (`MemoryTaskQueue`)
- Extension extraction (préférences/intentions/contraintes)
- 8 métriques Prometheus (5 préférences + 3 cache)

### ⏳ Phase P2 - Réactivité Proactive (À VENIR)
- Suggestions contextuelles `ws:proactive_hint`
- Scoring pertinence
- Déclencheurs temporels
- UI hints opt-in

### 📅 Phase P3 - Gouvernance (BACKLOG)
- Tests intégration mémoire end-to-end
- Journalisation coûts/durées consolidations
- Audit préférences capturées (échantillon 20/semaine)

---

## 💡 RECOMMANDATION PROCHAINE SESSION

**Option A : Validation P1 + Documentation (RECOMMANDÉ)**
- ✅ Rapide (1h)
- ✅ Critique pour confirmer P1 opérationnel
- ✅ Prépare P2 avec métriques baseline

**Option B : Démarrer P2 directement**
- ⚠️ Risqué sans validation P1
- 6-8h de dev
- Dépendances : P1 fonctionnel

**Option C : Optimisations Performance**
- Dockerfile multi-stage (réduire taille image 13GB → 2GB)
- Cache pip layers
- Slim base image Python

---

## 📝 PROMPT DE REPRISE (Copier-Coller)

```markdown
Bonjour Claude,

Je reprends le développement d'Emergence V8 après **déploiement Phase P1 Enrichissement Mémoire**.

**État actuel** :
- ✅ Production : révision `emergence-app-p1memory` déployée (2025-10-09 10:05)
- ✅ P1.1 : MemoryTaskQueue avec 2 workers asyncio ✅
- ✅ P1.2 : PreferenceExtractor pipeline hybride ✅
- ✅ P1.3 : 5 métriques préférences + 3 cache instrumentées ✅
- ✅ Tests : 154/154 pytest passent
- ⚠️ Métriques `memory_preferences_*` pas encore visibles (extracteur non déclenché)

**Mission : Validation fonctionnelle P1 en production**

**Tâches prioritaires** :

1. **Déclencher extraction préférences** (30 min)
   - Créer conversation avec préférences explicites
   - Lancer consolidation mémoire
   - Vérifier métriques P1 apparaissent dans `/api/metrics`
   - Vérifier logs Workers dans Cloud Run

2. **QA automatisée complète** (15 min)
   - `python qa_metrics_validation.py --trigger-memory`
   - `pwsh tests/run_all.ps1` avec credentials
   - Archiver rapports dans `docs/monitoring/snapshots/`

3. **Documenter métriques P1** (20 min)
   - Créer `docs/monitoring/prometheus-p1-metrics.md`
   - Dashboard Grafana suggestions
   - Exemples queries + alertes

**Fichiers clés** :
- [NEXT_SESSION_PROMPT.md](NEXT_SESSION_PROMPT.md) - Ce fichier
- [docs/deployments/2025-10-09-deploy-p1-memory.md](docs/deployments/2025-10-09-deploy-p1-memory.md) - Rapport déploiement
- [docs/passation.md](docs/passation.md) - Dernière entrée Codex

**Objectif** : Valider P1 opérationnel (métriques visibles) puis préparer Phase P2 Réactivité Proactive.

Commence par créer une conversation test avec préférences explicites puis déclencher consolidation mémoire.

Bonne session ! 🚀
```

---

## 📞 CONTACTS & ESCALATION

**Architecte (FG)** : Validation finale avant features majeures

**Agents disponibles** :
- Claude Code (moi) : Dev features, tests, documentation
- Codex (cloud) : Build, deploy, monitoring production
- Codex (local) : Tests locaux, scripts, optimisations

---

## 🔧 TROUBLESHOOTING P1

### Problème : Métriques `memory_preferences_*` absentes

**Cause** : Extracteur non déclenché (aucune consolidation mémoire depuis déploiement)

**Solution** :
1. Créer conversation avec préférences
2. POST `/api/memory/tend-garden` avec `thread_id`
3. Attendre logs "Worker X completed analyze"
4. Refresh `/api/metrics`

### Problème : Workers ne traitent pas les tâches

**Cause** : Queue non démarrée ou erreur startup

**Solution** :
1. Vérifier logs : `gcloud logging read ... textPayload:'MemoryTaskQueue'`
2. Chercher "MemoryTaskQueue started with 2 workers"
3. Si absent : vérifier `main.py` lifecycle startup
4. Rollback si nécessaire : `gcloud run services update-traffic ... phase3b=100`

### Problème : Classification LLM échoue

**Cause** : API OpenAI erreur ou rate limit

**Solution** :
1. Vérifier logs : `gcloud logging read ... textPayload:'PreferenceExtractor'`
2. Fallback : classification revient `type: "neutral"` (ignoré)
3. Métriques : `memory_preferences_llm_calls_total` n'incrémente pas

---

**Dernière mise à jour** : 2025-10-09 18:00 CEST
**Durée session P1** : ~4h (dev + tests + docs + déploiement)
**Next milestone** : P2 Réactivité Proactive (6-8h dev)

🎉 **Phase P1 Enrichissement Mémoire : COMPLÉTÉE ET DÉPLOYÉE !**
