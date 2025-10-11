# Fix Timestamps Réels pour Consolidation Threads Archivés

> **Date:** 2025-10-11
> **Version:** V2.10.0
> **Statut:** ✅ Implémenté, en attente de tests
> **Impact:** Critique - Permet aux agents d'accéder aux dates réelles des conversations archivées

---

## 🐛 Problème Identifié

### Symptôme
Les agents ne parvenaient pas à donner les **dates et heures précises** des sujets abordés dans les conversations archivées. Lorsqu'un utilisateur demandait "Quand ai-je parlé de Docker ?", l'agent ne pouvait pas répondre avec la date réelle de la conversation.

### Cause Racine

Dans [gardener.py:763](../../src/backend/features/memory/gardener.py#L763) (ancienne version), lors de la consolidation d'un thread via `_tend_single_thread`, les métadonnées vectorielles utilisaient :

```python
# ❌ AVANT (V2.9.0)
concept_stub: Dict[str, Any] = {
    "id": tid,
    "user_id": uid,
    "thread_id": tid,
    "themes": []
}

# Dans _vectorize_concepts (ligne 1564)
"first_mentioned_at": now_iso,  # ❌ Date de CONSOLIDATION
"last_mentioned_at": now_iso,   # ❌ Date de CONSOLIDATION
```

**Problème** : `now_iso` correspondait à la **date d'exécution du gardener**, pas à la date réelle des messages historiques.

**Exemple concret** :
- Message utilisateur : "Je veux apprendre Docker" envoyé le **2025-09-15 à 14h30**
- Thread consolidé le **2025-10-11 à 08h00**
- Métadonnée stockée : `first_mentioned_at: "2025-10-11T08:00:00+00:00"` ❌

→ L'agent pensait que le sujet "Docker" avait été abordé le 11 octobre, alors que c'était le 15 septembre !

---

## ✅ Solution Implémentée

### Changements Code

#### 1. Extraction des timestamps réels des messages ([gardener.py:709-722](../../src/backend/features/memory/gardener.py#L709-L722))

```python
# ✅ APRÈS (V2.10.0)
msgs = await queries.get_messages(...)
history = []
first_msg_ts = None
last_msg_ts = None

for m in msgs or []:
    # Extraire timestamps pour métadonnées LTM
    created_at = m.get("created_at")
    if created_at:
        ts = _parse_iso_ts(created_at)
        if ts:
            if first_msg_ts is None or ts < first_msg_ts:
                first_msg_ts = ts
            if last_msg_ts is None or ts > last_msg_ts:
                last_msg_ts = ts

    history.append(...)
```

**Résultat** : `first_msg_ts` = date du **premier message**, `last_msg_ts` = date du **dernier message**.

#### 2. Enrichissement du `concept_stub` ([gardener.py:783-790](../../src/backend/features/memory/gardener.py#L783-L790))

```python
concept_stub: Dict[str, Any] = {
    "id": tid,
    "user_id": uid,
    "thread_id": tid,
    "themes": [],
    "first_message_at": first_msg_ts.isoformat() if first_msg_ts else _now_iso(),  # ✅
    "last_message_at": last_msg_ts.isoformat() if last_msg_ts else _now_iso(),     # ✅
}
```

#### 3. Utilisation des timestamps réels dans `_vectorize_concepts` ([gardener.py:1580-1582](../../src/backend/features/memory/gardener.py#L1580-L1582))

```python
# Utiliser les timestamps réels des messages si disponibles
first_mentioned = session.get("first_message_at") or now_iso  # ✅
last_mentioned = session.get("last_message_at") or now_iso    # ✅

# Métadonnées vectorielles
"first_mentioned_at": first_mentioned,  # ✅ Date RÉELLE
"last_mentioned_at": last_mentioned,    # ✅ Date RÉELLE
```

---

## 📊 Impact

### Avant (V2.9.0)

```json
{
  "concept_text": "Docker containerisation",
  "first_mentioned_at": "2025-10-11T08:00:00+00:00",  // ❌ Date de consolidation
  "last_mentioned_at": "2025-10-11T08:00:00+00:00",   // ❌ Idem
  "thread_ids": ["thread_xyz"],
  "mention_count": 1
}
```

**Requête utilisateur** : "Quand ai-je parlé de Docker ?"
**Réponse agent** : "Tu as parlé de Docker le 11 octobre 2025" ❌ (faux, c'était le 15 septembre)

### Après (V2.10.0)

```json
{
  "concept_text": "Docker containerisation",
  "first_mentioned_at": "2025-09-15T14:30:15+00:00",  // ✅ Date du message original
  "last_mentioned_at": "2025-09-28T16:20:00+00:00",   // ✅ Date du dernier message
  "thread_ids": ["thread_xyz"],
  "mention_count": 3
}
```

**Requête utilisateur** : "Quand ai-je parlé de Docker ?"
**Réponse agent** : "Tu as mentionné Docker pour la première fois le 15 septembre 2025 à 14h30, et la dernière fois le 28 septembre à 16h20." ✅

---

## 🧪 Tests

### Tests Unitaires

Fichier : [tests/memory/test_thread_consolidation_timestamps.py](../../tests/memory/test_thread_consolidation_timestamps.py)

**Couverture** :
1. ✅ `test_thread_consolidation_preserves_real_timestamps`
   - Vérifie que `first_mentioned_at` = date du premier message (±60s)
   - Vérifie que `last_mentioned_at` = date du dernier message (±60s)
   - Vérifie que `thread_ids_json` contient le bon `thread_id`

2. ✅ `test_concept_query_returns_historical_dates`
   - Simule une requête agent via `ConceptRecallTracker`
   - Vérifie qu'un concept vieux de 45 jours est correctement récupéré
   - Vérifie que `thread_ids` est accessible

3. ✅ `test_empty_thread_handles_gracefully`
   - Vérifie qu'un thread sans messages ne plante pas
   - Résultat attendu : `new_concepts = 0`, pas d'erreur

### Exécution Locale

```bash
# Lancer les tests
pytest tests/memory/test_thread_consolidation_timestamps.py -v

# Test avec logs détaillés
pytest tests/memory/test_thread_consolidation_timestamps.py -v -s
```

---

## 🚀 Déploiement

### Étape 1 : Tester Localement

```bash
# 1. Démarrer le backend en mode dev
npm run dev:backend

# 2. Dans un autre terminal, créer un thread de test
curl -X POST http://localhost:8000/api/threads/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "chat", "title": "Test Docker"}'

# 3. Envoyer quelques messages
# (via interface UI ou API /api/threads/{id}/messages)

# 4. Archiver le thread
curl -X PUT http://localhost:8000/api/threads/{thread_id}/archive \
  -H "Authorization: Bearer $TOKEN"

# 5. Consolider le thread
curl -X POST http://localhost:8000/api/memory/tend-garden \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "{thread_id}"}'

# 6. Interroger les concepts
curl -X GET "http://localhost:8000/api/memory/concepts/search?q=docker" \
  -H "Authorization: Bearer $TOKEN"
```

**Vérification attendue** :
- Le champ `first_mentioned_at` doit correspondre à la date du **premier message** du thread
- Le champ `last_mentioned_at` doit correspondre à la date du **dernier message**

### Étape 2 : Reconsolidation Production (si nécessaire)

Si vous avez déjà des threads archivés en production avec les **mauvaises dates**, vous devrez les reconsolider :

```bash
# Appeler l'endpoint de reconsolidation
curl -X POST https://emergence-app.ch/api/memory/consolidate-archived \
  -H "Authorization: Bearer $PROD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": true, "limit": 50}'
```

**Paramètres** :
- `force: true` → Reconsolide les threads déjà traités
- `limit: 50` → Traite 50 threads par batch (ajuster selon la charge)

**⚠️ Attention** : Cette opération peut être coûteuse en tokens LLM (analyse sémantique). Commencez avec `limit: 10` pour tester.

---

## 📈 Métriques de Succès

### KPIs à Surveiller

1. **Précision Temporelle**
   - Métrique : `concept_recall_temporal_accuracy`
   - Objectif : >95% des concepts ont un `first_mentioned_at` < date de consolidation
   - Mesure : Comparer `first_mentioned_at` vs `created_at` (date de vectorisation)

2. **Taux de Rappel**
   - Métrique : `concept_recall_hit_rate`
   - Objectif : Les agents trouvent 100% des concepts archivés lors de requêtes
   - Mesure : Requêtes de test sur concepts connus

3. **Latence Reconsolidation**
   - Métrique : `memory_consolidation_duration_seconds`
   - Objectif : <5s par thread archivé
   - Mesure : Logs `knowledge_consolidation` dans `monitoring` table

### Dashboard Grafana (à créer)

```promql
# Précision temporelle : % de concepts avec dates antérieures à la consolidation
sum(
  rate(concept_recall_detections_total{temporal_accuracy="correct"}[5m])
) / sum(rate(concept_recall_detections_total[5m])) * 100

# Latence moyenne consolidation threads
histogram_quantile(0.5,
  rate(memory_consolidation_duration_seconds_bucket[5m])
)
```

---

## 🔄 Compatibilité Roadmap

### Position dans la Roadmap

D'après [docs/memory-roadmap.md](../memory-roadmap.md#L35-L56) :

- ✅ **Phase P0** : Alignement persistance & cross-device (complété)
- ✅ **Phase P1** : Hors boucle WS & enrichissement conceptuel (complété 2025-10-09)
- ✅ **Phase P2** : Performance & Réactivité proactive (complété 2025-10-10)
- 🔧 **Phase P2 bis** : **FIX Timestamps archivés** (en cours - 2025-10-11)
- ⏳ **Phase P3** : Gouvernance & Observabilité (prochaine étape)

### Gap Résolu

**Gap #1 (P0)** : "L'analyse et la vectorisation sont déclenchées dans la boucle WS"
→ ✅ Résolu en P1 via `MemoryTaskQueue`

**Gap #2 (P2)** : "Métadonnées temporelles manquantes sur concepts archivés"
→ ✅ **Résolu ici (V2.10.0)** : Timestamps réels préservés

**Gap #3 (P3)** : "Décision architecture hybride Sessions/Threads"
→ ⏳ À traiter après ce fix

---

## 📚 Références

- [docs/memory-roadmap.md](../memory-roadmap.md) - Roadmap complète mémoire
- [docs/MEMORY_CAPABILITIES.md](../MEMORY_CAPABILITIES.md) - Capacités agents mémoire
- [src/backend/features/memory/gardener.py](../../src/backend/features/memory/gardener.py) - Code modifié
- [src/backend/features/memory/concept_recall.py](../../src/backend/features/memory/concept_recall.py) - API interrogation concepts

---

## ✅ Checklist Déploiement

- [x] Code modifié (gardener.py V2.10.0)
- [x] Tests unitaires créés
- [ ] Tests unitaires passent localement
- [ ] Test manuel local (thread archivé → consolidation → requête)
- [ ] Vérification métadonnées ChromaDB (dates correctes)
- [ ] Déploiement staging
- [ ] Test E2E staging (agent répond avec bonnes dates)
- [ ] Reconsolidation threads archivés production (si nécessaire)
- [ ] Validation production (requête agent sur ancien thread)
- [ ] Métriques Prometheus opérationnelles

---

**Auteur** : Assistant IA
**Reviewer** : À assigner
**Prochaine étape** : Tests locaux par l'utilisateur
