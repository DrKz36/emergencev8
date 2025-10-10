# 🧪 Guide de Validation Phase P1 — Production

📅 **Date** : 2025-10-09
🎯 **Révision** : `emergence-app-p1memory`
🌐 **URL** : https://emergence-app-486095406755.europe-west1.run.app

---

## ✅ État des Métriques P1 (Baseline)

### Vérification effectuée : 2025-10-09

**Résultat** : ✅ Toutes les métriques P1 sont instrumentées et visibles

```bash
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/metrics | grep "memory_preferences"
```

**Métriques observées** :

| Métrique | Type | Valeur actuelle | Statut |
|----------|------|-----------------|--------|
| `memory_preferences_extracted_total` | counter | 0.0 | ✅ Instrumentée |
| `memory_preferences_confidence` | histogram | 0.0 (count) | ✅ Instrumentée |
| `memory_preferences_extraction_duration_seconds` | histogram | 0.0 (count) | ✅ Instrumentée |
| `memory_preferences_lexical_filtered_total` | counter | 0.0 | ✅ Instrumentée |
| `memory_preferences_llm_calls_total` | counter | 0.0 | ✅ Instrumentée |

**Interprétation** :
- 🟢 Toutes les métriques sont initialisées avec `_created` timestamps
- 🟢 Compteurs à zéro attendu (extracteur non déclenché)
- 🟢 MemoryTaskQueue démarré (logs confirmés dans déploiement Codex)

---

## 🧪 Protocole de Validation Fonctionnelle

### Étape 1 : Créer conversation avec préférences explicites

**Via UI Production** : https://emergence-app-486095406755.europe-west1.run.app

**Messages utilisateur à envoyer** (copier-coller dans le chat) :

```
Bonjour, je voudrais te parler de mes préférences de développement.

Je préfère utiliser Python pour mes projets backend, surtout avec FastAPI.

J'évite d'utiliser jQuery dans mes nouvelles applications web.

Je vais apprendre TypeScript la semaine prochaine pour améliorer mon code frontend.

J'aime beaucoup travailler avec Claude Code pour automatiser mes tâches.

Je planifie de migrer mon projet vers Docker d'ici la fin du mois.
```

**Préférences attendues** :
- 3 préférences (`préfère`, `évite`, `aime`)
- 2 intentions (`vais apprendre`, `planifie de migrer`)

---

### Étape 2 : Déclencher consolidation mémoire

**Option A : Via UI** (recommandé pour premier test)

Attendre **5 minutes** après la conversation, la consolidation se déclenche automatiquement lors de la persistence de session.

**Option B : Via API** (nécessite authentification)

```bash
# Récupérer le thread_id depuis l'UI (inspecter Network > WebSocket handshake)
THREAD_ID="<thread_id>"
USER_SUB="<user_sub>"

# POST avec authentication token
curl -X POST https://emergence-app-486095406755.europe-west1.run.app/api/memory/tend-garden \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "{\"thread_id\": \"$THREAD_ID\", \"user_sub\": \"$USER_SUB\"}"
```

---

### Étape 3 : Vérifier métriques P1 incrémentées

**Attendre 2-3 minutes** après consolidation, puis :

```bash
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/metrics | grep "memory_preferences_extracted_total"
```

**Résultat attendu** :

```prometheus
memory_preferences_extracted_total{type="preference"} 3.0
memory_preferences_extracted_total{type="intent"} 2.0
memory_preferences_extracted_total{type="constraint"} 0.0
```

**Vérifier histogrammes** :

```bash
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/metrics | grep "memory_preferences_confidence"
```

**Attendu** : `memory_preferences_confidence_count` > 0, buckets >0.7 incrémentés

---

### Étape 4 : Vérifier logs Workers

**Via gcloud CLI** :

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.revision_name~'p1memory' AND textPayload:'Worker'" \
  --project emergence-469005 \
  --limit 20 \
  --format "table(timestamp, textPayload)"
```

**Logs attendus** :

```
2025-10-09 XX:XX:XX  Worker 0 processing task: analyze
2025-10-09 XX:XX:XX  Worker 0 completed analyze in 1.234s
2025-10-09 XX:XX:XX  PreferenceExtractor: Extracted 5 candidates
2025-10-09 XX:XX:XX  PreferenceExtractor: Classified 5 records (3 preference, 2 intent)
```

---

### Étape 5 : Vérifier collection vectorielle

**Via Chroma/Qdrant API** (si accès configuré) :

```bash
# Exemple pour Chroma (localhost:8000)
curl http://localhost:8000/api/v1/collections/memory_preferences_${USER_SUB}/count
```

**Attendu** : `count: 5` (5 préférences/intentions vectorisées)

---

## 📊 Critères de Succès P1

| Critère | Cible | Validation |
|---------|-------|------------|
| Métriques instrumentées | 5/5 | ✅ Confirmé |
| Extraction déclenchée | ✅ | ⏳ À tester |
| Préférences capturées | ≥3 | ⏳ À tester |
| Intentions capturées | ≥2 | ⏳ À tester |
| Confiance médiane | >0.7 | ⏳ À tester |
| Durée extraction | <2s | ⏳ À tester |
| Filtrage lexical | ~70% | ⏳ À tester |
| Logs Workers | OK | ⏳ À tester |
| Collection vectorielle | Créée | ⏳ À tester |

---

## 🔧 Troubleshooting

### Problème : Métriques restent à zéro après consolidation

**Causes possibles** :
1. Consolidation pas déclenchée (vérifier logs)
2. Messages non détectés par filtrage lexical (trop courts)
3. Classification LLM retourne `neutral` (confiance faible)

**Actions** :
1. Vérifier logs : `gcloud logging read ... textPayload:'MemoryGardener'`
2. Chercher `garden_thread` ou `extract_preferences`
3. Vérifier logs `PreferenceExtractor` pour voir messages traités

### Problème : Workers ne traitent pas les tâches

**Symptôme** : Aucun log "Worker X processing task"

**Solution** :
1. Vérifier startup : `gcloud logging read ... textPayload:'MemoryTaskQueue'`
2. Chercher "MemoryTaskQueue started with 2 workers"
3. Si absent, vérifier `main.py` lifecycle startup
4. Rollback si nécessaire : `gcloud run services update-traffic ... phase3b=100`

### Problème : Classification LLM timeout

**Symptôme** : Logs "OpenAI API error" ou "timeout"

**Solution** :
1. Vérifier quota OpenAI (dashboard)
2. Vérifier connectivity depuis Cloud Run
3. Fallback automatique : classification retourne `neutral` (ignoré)

---

## 📈 Métriques de Référence Attendues

### Après 1 consolidation (5 messages)

```prometheus
memory_preferences_extracted_total{type="preference"} 3.0
memory_preferences_extracted_total{type="intent"} 2.0
memory_preferences_confidence_count 5.0
memory_preferences_confidence_sum ~3.8  # Médiane ~0.76
memory_preferences_extraction_duration_seconds_count 1.0
memory_preferences_extraction_duration_seconds_sum ~1.2s
memory_preferences_lexical_filtered_total 0.0  # Tous les messages passent le filtre
memory_preferences_llm_calls_total 5.0  # 5 appels LLM
```

### Après 10 consolidations (50 messages variés)

```prometheus
memory_preferences_extracted_total{type="preference"} ~15.0
memory_preferences_extracted_total{type="intent"} ~10.0
memory_preferences_extracted_total{type="constraint"} ~5.0
memory_preferences_lexical_filtered_total ~35.0  # 70% filtrés
memory_preferences_llm_calls_total ~15.0  # 30% classifiés
```

---

## ✅ Checklist de Validation

- [ ] **Baseline** : Métriques P1 visibles dans `/api/metrics` ✅
- [ ] **Test conversation** : Créer conversation avec 5 préférences/intentions
- [ ] **Consolidation** : Déclencher via UI (attente 5 min) ou API
- [ ] **Métriques** : Vérifier `memory_preferences_extracted_total` > 0
- [ ] **Confiance** : Vérifier médiane `memory_preferences_confidence` > 0.7
- [ ] **Performance** : Vérifier `extraction_duration_seconds` < 2s
- [ ] **Logs Workers** : Confirmer "Worker X completed analyze"
- [ ] **Collection** : Vérifier création `memory_preferences_{user_sub}`
- [ ] **QA automatisée** : Exécuter `qa_metrics_validation.py --trigger-memory`
- [ ] **Documentation** : Archiver résultats dans `docs/monitoring/snapshots/`

---

## 📝 Rapport de Validation (Template)

```markdown
# Rapport de Validation P1 — [Date]

## Environnement
- Révision : emergence-app-p1memory
- Thread ID : <thread_id>
- User Sub : <user_sub>

## Tests effectués
1. ✅ Conversation créée avec 5 messages (3 préférences, 2 intentions)
2. ✅ Consolidation déclenchée (méthode : UI/API)
3. ✅ Métriques incrémentées dans les 3 minutes

## Résultats
- `memory_preferences_extracted_total{type="preference"}` : 3.0 ✅
- `memory_preferences_extracted_total{type="intent"}` : 2.0 ✅
- Confiance médiane : 0.78 ✅ (>0.7)
- Durée extraction : 1.23s ✅ (<2s)
- Filtrage lexical : 0% (attendu, tous les messages ciblés)
- Appels LLM : 5 ✅

## Logs Workers
- [X] Logs "Worker 0 processing task: analyze" présents
- [X] Logs "PreferenceExtractor: Extracted X candidates" présents
- [X] Aucune erreur

## Collection vectorielle
- Nom : memory_preferences_<user_sub>
- Count : 5 ✅

## Conclusion
✅ Phase P1 validée en production. Extraction préférences fonctionnelle.

**Prochaine étape** : Phase P2 Réactivité Proactive
```

---

## 🚀 Prochaines Étapes Post-Validation

### Si validation réussie ✅

1. **Documenter métriques baseline** → `docs/monitoring/prometheus-p1-metrics.md`
2. **QA automatisée complète** → `qa_metrics_validation.py`
3. **Planifier Phase P2** → Suggestions contextuelles `ws:proactive_hint`

### Si validation échouée ❌

1. **Analyser logs détaillés** → Identifier cause racine
2. **Tests locaux** → Reproduire avec `pytest tests/memory/test_preference_extractor.py -v`
3. **Hotfix si nécessaire** → Déployer révision corrective
4. **Rollback si bloquant** → Retour phase3b via `gcloud run services update-traffic`

---

**Dernière mise à jour** : 2025-10-09
**Auteur** : Claude Code
**Statut** : ✅ Métriques baseline confirmées, prêt pour test fonctionnel
