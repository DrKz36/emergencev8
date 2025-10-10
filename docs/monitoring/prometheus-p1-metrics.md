# Métriques Prometheus Phase P1 - Enrichissement Mémoire

**Date création** : 2025-10-09
**Status** : Instrumentées, en attente de déclenchement

## État actuel en production

**Révision** : `emergence-app-p1memory`
**Image** : `deploy-p1-20251009-094822`
**Déploiement** : 2025-10-09 10:05 CEST
**Trafic** : 100%

### Composants P1 déployés

✅ **MemoryTaskQueue**
- 2 workers asyncio opérationnels
- Logs confirmés : `MemoryTaskQueue started with 2 workers` (2025-10-09 12:09:24)

✅ **PreferenceExtractor**
- Pipeline hybride (filtrage lexical + classification LLM gpt-4o-mini)
- Code déployé et instrumenté
- ⚠️ **Non déclenché** : aucune consolidation mémoire avec préférences depuis déploiement

✅ **Métriques Phase 3** (visibles)
- `memory_analysis_success_total` : 7 analyses (neo_analysis)
- `memory_analysis_cache_hits_total` : 1
- `memory_analysis_cache_misses_total` : 6
- `memory_analysis_cache_size` : 6 entrées
- `concept_recall_*` : histogrammes instrumentés

✅ **Métriques P1** (instrumentées et visibles - baseline confirmé 2025-10-09)
- `memory_preferences_extracted_total{type}` : 0.0 (counter initialisé)
- `memory_preferences_confidence` : 0.0 count, buckets créés [0.5-1.0]
- `memory_preferences_extraction_duration_seconds` : 0.0 count, buckets créés [0.1-5.0]
- `memory_preferences_lexical_filtered_total` : 0.0 (counter initialisé)
- `memory_preferences_llm_calls_total` : 0.0 (counter initialisé)

**État** : Toutes les métriques sont instrumentées avec `_created` timestamps (1.760054488e+09). Compteurs à zéro attendu (extracteur non déclenché).

---

## Nouvelles métriques P1 (5)

### 1. memory_preferences_extracted_total{type}

**Type** : Counter
**Labels** : `type` (preference, intent, constraint)
**Description** : Nombre total de préférences/intentions/contraintes extraites
**Valeurs typiques** : 0-50 par session consolidée

**Utilisation** :
```promql
# Rate d'extraction préférences
rate(memory_preferences_extracted_total{type="preference"}[5m])

# Total par type
sum by (type) (memory_preferences_extracted_total)
```

**Alertes suggérées** :
- `rate(memory_preferences_extracted_total[10m]) < 0.1` : Taux d'extraction faible
- `memory_preferences_extracted_total{type="preference"} == 0` pendant > 1h : Extracteur inactif

---

### 2. memory_preferences_confidence

**Type** : Histogram
**Buckets** : [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
**Description** : Distribution des scores de confiance d'extraction
**Valeurs typiques** : Médiane > 0.75

**Utilisation** :
```promql
# Médiane du score de confiance
histogram_quantile(0.5, memory_preferences_confidence)

# P95 (95e percentile)
histogram_quantile(0.95, memory_preferences_confidence)

# Proportion score < 0.7 (faible confiance)
sum(memory_preferences_confidence_bucket{le="0.7"}) /
sum(memory_preferences_confidence_count)
```

**Alertes suggérées** :
- `histogram_quantile(0.5, memory_preferences_confidence) < 0.6` : Médiane trop basse
- Score médian < 0.7 pendant > 30min : Qualité extraction dégradée

---

### 3. memory_preferences_extraction_duration_seconds

**Type** : Histogram
**Buckets** : [0.1, 0.5, 1.0, 2.0, 5.0]
**Description** : Durée d'extraction des préférences (pipeline complet)
**Valeurs typiques** : Médiane < 1s, P95 < 2s

**Utilisation** :
```promql
# Latence médiane
histogram_quantile(0.5, memory_preferences_extraction_duration_seconds)

# P99 (pire cas)
histogram_quantile(0.99, memory_preferences_extraction_duration_seconds)

# Rate d'extractions lentes (>2s)
sum(memory_preferences_extraction_duration_seconds_bucket{le="2.0"}) /
sum(memory_preferences_extraction_duration_seconds_count)
```

**Alertes suggérées** :
- `histogram_quantile(0.5, memory_preferences_extraction_duration_seconds) > 2.0` : Latence médiane trop haute
- P99 > 5s pendant > 10min : Ralentissements critiques

---

### 4. memory_preferences_lexical_filtered_total

**Type** : Counter
**Description** : Messages filtrés par le filtrage lexical (avant LLM)
**Valeurs typiques** : ~70% des messages traités

**Utilisation** :
```promql
# Rate de filtrage
rate(memory_preferences_lexical_filtered_total[5m])

# Ratio filtré / total
memory_preferences_lexical_filtered_total /
(memory_preferences_lexical_filtered_total + memory_preferences_llm_calls_total)
```

**Target** : > 0.7 (70% filtrés sans appel LLM)

**Alertes suggérées** :
- Ratio < 0.6 : Filtrage lexical insuffisant, coûts LLM en hausse
- Rate filtrage = 0 pendant > 1h : Extracteur inactif

---

### 5. memory_preferences_llm_calls_total

**Type** : Counter
**Description** : Appels LLM pour classification (après filtrage lexical)
**Valeurs typiques** : ~30% des messages (après filtrage)

**Utilisation** :
```promql
# Rate d'appels LLM
rate(memory_preferences_llm_calls_total[5m])

# Ratio LLM / total
memory_preferences_llm_calls_total /
(memory_preferences_lexical_filtered_total + memory_preferences_llm_calls_total)
```

**Target** : < 0.3 (30% passent au LLM)

**Alertes suggérées** :
- Ratio > 0.5 : Trop d'appels LLM, revoir filtrage lexical
- `rate(memory_preferences_llm_calls_total[5m]) > 10` : Appels LLM excessifs

---

## Dashboard Grafana - Suggestions de panels

### Panel 1 : Extraction Rate (Gauge)

**Titre** : "Préférences extraites (5 min)"
**Type** : Stat (valeur unique)
**Query** :
```promql
rate(memory_preferences_extracted_total[5m])
```

**Seuils** :
- 🟢 Vert : > 0.5/s
- 🟡 Jaune : 0.1-0.5/s
- 🔴 Rouge : < 0.1/s

**Alert** : < 0.1/s pendant 10 minutes

---

### Panel 2 : Confidence Distribution (Histogram)

**Titre** : "Distribution scores de confiance"
**Type** : Graph (Time series)
**Queries** :
```promql
# P50 (médiane)
histogram_quantile(0.5, memory_preferences_confidence)

# P95
histogram_quantile(0.95, memory_preferences_confidence)

# P99
histogram_quantile(0.99, memory_preferences_confidence)
```

**Seuils** :
- 🟢 Médiane > 0.75
- 🟡 Médiane 0.6-0.75
- 🔴 Médiane < 0.6

**Alert** : Médiane < 0.6 pendant 30 minutes

---

### Panel 3 : Pipeline Efficiency (Gauge)

**Titre** : "Efficacité filtrage lexical (%)"
**Type** : Stat (pourcentage)
**Query** :
```promql
100 * (
  memory_preferences_lexical_filtered_total /
  (memory_preferences_lexical_filtered_total + memory_preferences_llm_calls_total)
)
```

**Seuils** :
- 🟢 Vert : > 70%
- 🟡 Jaune : 50-70%
- 🔴 Rouge : < 50%

**Target** : > 70% (réduction coûts LLM)

---

### Panel 4 : Extraction Latency (Time Series)

**Titre** : "Latence extraction préférences"
**Type** : Graph (Time series)
**Queries** :
```promql
# Médiane
histogram_quantile(0.5, memory_preferences_extraction_duration_seconds)

# P95
histogram_quantile(0.95, memory_preferences_extraction_duration_seconds)

# P99 (pire cas)
histogram_quantile(0.99, memory_preferences_extraction_duration_seconds)
```

**Seuils** :
- 🟢 Médiane < 1s
- 🟡 Médiane 1-2s
- 🔴 Médiane > 2s

---

### Panel 5 : Extraction by Type (Bar chart)

**Titre** : "Préférences par type (24h)"
**Type** : Bar chart
**Query** :
```promql
sum by (type) (increase(memory_preferences_extracted_total[24h]))
```

**Types attendus** :
- `preference` : préférences utilisateur (ex: "J'aime Python")
- `intent` : intentions futures (ex: "Je vais apprendre FastAPI")
- `constraint` : contraintes/restrictions (ex: "J'évite jQuery")

---

## Validation post-déploiement

### Checklist validation P1

- [x] **Révision déployée** : `emergence-app-p1memory` active (100% trafic)
- [x] **Workers démarrés** : Logs "MemoryTaskQueue started with 2 workers"
- [x] **Métriques Phase 3 visibles** : `memory_analysis_*`, `concept_recall_*` OK
- [x] **Métriques P1 instrumentées** : `memory_preferences_*` visibles (baseline 0.0)
- [ ] **Extraction déclenchée** : Conversation test + consolidation
- [ ] **Métriques P1 incrémentées** : Vérifier compteurs >0 après extraction
- [ ] **Logs PreferenceExtractor** : Vérifier extraction dans Cloud Run logs
- [ ] **Dashboard Grafana** : Panels P1 ajoutés

### Prochaines étapes (validation)

1. **Déclencher extraction** :
   - Créer conversation avec préférences explicites
   - Exemples messages :
     - "Je préfère utiliser Python pour mes projets backend"
     - "Je vais apprendre FastAPI la semaine prochaine"
     - "J'évite d'utiliser jQuery dans mes applications"
   - POST `/api/memory/tend-garden` avec `thread_id` + `user_sub`

2. **Vérifier métriques apparaissent** :
   ```bash
   curl https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep "memory_preferences"
   ```

   **Attendu après extraction** :
   ```prometheus
   memory_preferences_extracted_total{type="preference"} 3.0
   memory_preferences_extracted_total{type="intent"} 2.0
   memory_preferences_confidence_bucket{le="0.8"} 5
   memory_preferences_extraction_duration_seconds_count 1
   memory_preferences_lexical_filtered_total 2
   memory_preferences_llm_calls_total 5
   ```

3. **Vérifier logs Workers** :
   ```bash
   gcloud logging read \
     "resource.type=cloud_run_revision AND resource.labels.revision_name:p1memory AND textPayload:PreferenceExtractor" \
     --project emergence-469005 \
     --limit 20
   ```

   **Logs attendus** :
   ```
   PreferenceExtractor: Extracted 5 preferences/intents
   Worker 0 completed analyze in 1.23s
   ```

---

## Troubleshooting P1

### Problème : Métriques `memory_preferences_*` absentes

**Cause** : Extracteur non déclenché (aucune consolidation mémoire avec préférences)

**Solution** :
1. Créer conversation avec messages contenant préférences
2. POST `/api/memory/tend-garden` avec `thread_id` valide
3. Attendre logs "Worker X completed analyze"
4. Refresh `/api/metrics`

### Problème : Extraction duration > 5s

**Cause** : Appels LLM lents ou rate limit OpenAI

**Solution** :
1. Vérifier logs : chercher timeouts LLM
2. Augmenter filtrage lexical (réduire appels LLM)
3. Optimiser prompt classification (plus concis)
4. Vérifier quota OpenAI API

### Problème : Confidence scores < 0.6

**Cause** : Classification LLM incertaine

**Solution** :
1. Vérifier prompt `PreferenceExtractor` (clarté instructions)
2. Analyser échantillon préférences extraites (faux positifs ?)
3. Ajuster seuil confiance si nécessaire
4. Enrichir filtrage lexical (éliminer messages ambigus)

---

## Coûts estimés P1

### Analyse par consolidation

- **Filtrage lexical** : 0 coût (règles locales)
- **Appels LLM** (gpt-4o-mini) :
  - ~30% messages → classification
  - ~10 tokens input/message
  - ~5 tokens output/message
  - Coût : ~$0.0001/message ($0.15/1M input, $0.60/1M output)

### Exemple : Session 50 messages

- **Filtrés lexical** : 35 messages (70%)
- **Passés au LLM** : 15 messages (30%)
- **Tokens total** : 225 (150 input + 75 output)
- **Coût** : $0.000068 (~0.07 centime)

### Estimation mensuelle

- **10 consolidations/jour**
- **500 messages/jour**
- **150 appels LLM/jour** (30%)
- **Coût** : ~$0.20/mois

**Comparaison** :
- Avant P1 : 0 extraction préférences
- Après P1 : +$0.20/mois pour enrichissement mémoire long terme

---

## Références

- **Code source** :
  - [src/backend/features/memory/preference_extractor.py](../../src/backend/features/memory/preference_extractor.py)
  - [src/backend/features/memory/task_queue.py](../../src/backend/features/memory/task_queue.py)
  - [src/backend/features/memory/analyzer.py](../../src/backend/features/memory/analyzer.py)

- **Tests** :
  - [tests/memory/test_preference_extractor.py](../../tests/memory/test_preference_extractor.py) (8/8 OK)
  - [tests/memory/test_task_queue.py](../../tests/memory/test_task_queue.py) (5/5 OK)

- **Documentation** :
  - [NEXT_SESSION_PROMPT.md](../../NEXT_SESSION_PROMPT.md) - Prompt session validation P1
  - [SESSION_SUMMARY_20251009.md](../../SESSION_SUMMARY_20251009.md) - Résumé déploiement P1
  - [docs/deployments/2025-10-09-deploy-p1-memory.md](../deployments/2025-10-09-deploy-p1-memory.md)

---

**Dernière mise à jour** : 2025-10-09 18:45 CEST
**Statut** : Métriques instrumentées, en attente de validation fonctionnelle
