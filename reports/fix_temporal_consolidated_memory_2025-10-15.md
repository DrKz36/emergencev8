# Fix - Contexte Temporel avec Mémoire Consolidée
**Date:** 2025-10-15
**Problème:** Anima ne peut pas fournir les dates pour les conversations archivées/consolidées
**Solution:** Enrichir le contexte temporel avec recherche dans la knowledge base

---

## Problème Identifié

### Symptômes Observés

**Comportement actuel:**
```
User: "Quand avons-nous parlé de Docker ?"
Anima: "On a parlé de Docker le 8 octobre à 14h32." ✅

User: "Quand avons-nous parlé de mon poème fondateur?"
Anima: "On a parlé de ton poème fondateur plusieurs fois cette semaine,
        mais je n'ai pas les dates et heures précises." ❌
```

### Analyse de la Cause

**Problème:** La fonction `_build_temporal_history_context()` récupère uniquement les 20 derniers messages du thread actif via `queries.get_messages()`.

**Conséquence:** Les conversations archivées et consolidées dans la knowledge base (`emergence_knowledge`) ne sont pas incluses dans le contexte temporel.

**Preuve:**
- L'historique des consolidations montre plusieurs entrées pour "poème fondateur" avec dates (14/10, 15/10)
- Ces entrées sont stockées dans ChromaDB (`emergence_knowledge`) avec métadonnées timestamp
- Elles ne sont pas accessibles via `get_messages()` qui lit uniquement la table `messages` SQLite

---

## Solution Implémentée

### Changements Apportés

**Fichier:** `src/backend/features/chat/service.py`

#### 1. Signature de Fonction Modifiée (ligne 1130-1137)

**Avant:**
```python
async def _build_temporal_history_context(
    self,
    thread_id: str,
    session_id: str,
    user_id: str,
    limit: int = 20
) -> str:
```

**Après:**
```python
async def _build_temporal_history_context(
    self,
    thread_id: str,
    session_id: str,
    user_id: str,
    limit: int = 20,
    last_user_message: str = ""  # NOUVEAU paramètre
) -> str:
```

**Raison:** Permet de faire une recherche sémantique dans la mémoire consolidée basée sur la question de l'utilisateur.

#### 2. Recherche dans Knowledge Base (lignes 1159-1188)

**Code ajouté:**
```python
# NOUVEAU: Enrichir avec concepts consolidés si question temporelle pertinente
consolidated_entries = []
if last_user_message and self._knowledge_collection is None:
    knowledge_name = os.getenv("EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge")
    self._knowledge_collection = self.vector_service.get_or_create_collection(knowledge_name)

if last_user_message and self._knowledge_collection:
    try:
        # Recherche sémantique dans la mémoire consolidée
        results = self._knowledge_collection.query(
            query_texts=[last_user_message],
            n_results=5,
            where={"user_id": user_id} if user_id else None
        )

        if results and results.get("metadatas") and results["metadatas"][0]:
            for metadata in results["metadatas"][0]:
                # Extraire timestamp et résumé des concepts consolidés
                timestamp = metadata.get("timestamp") or metadata.get("created_at")
                summary = metadata.get("summary") or metadata.get("content", "")
                concept_type = metadata.get("type", "concept")

                if timestamp and summary:
                    consolidated_entries.append({
                        "timestamp": timestamp,
                        "content": summary[:80] + ("..." if len(summary) > 80 else ""),
                        "type": concept_type
                    })
    except Exception as e:
        logger.debug(f"[TemporalHistory] Erreur recherche knowledge: {e}")
```

**Fonctionnement:**
1. Recherche sémantique dans `emergence_knowledge` avec la question utilisateur
2. Récupère les 5 meilleurs résultats pertinents
3. Extrait `timestamp`, `summary`, et `type` des métadonnées
4. Tronque le contenu à 80 caractères

#### 3. Fusion et Tri des Événements (lignes 1190-1227)

**Code ajouté:**
```python
# Combiner et trier tous les événements (messages + concepts consolidés)
all_events = []

# Ajouter les messages du thread
for msg in messages:
    role = msg.get("role", "").lower()
    content = msg.get("content", "")
    created_at = msg.get("created_at")
    agent_id = msg.get("agent_id")

    if role not in ["user", "assistant"]:
        continue

    if created_at:
        all_events.append({
            "timestamp": created_at,
            "role": role,
            "content": content,
            "agent_id": agent_id,
            "source": "thread"
        })

# Ajouter les entrées consolidées
for entry in consolidated_entries:
    all_events.append({
        "timestamp": entry["timestamp"],
        "role": "memory",
        "content": entry["content"],
        "type": entry["type"],
        "source": "consolidated"
    })

# Trier tous les événements par date (du plus ancien au plus récent)
try:
    all_events.sort(key=lambda x: datetime.fromisoformat(x["timestamp"].replace("Z", "+00:00")))
except Exception as sort_err:
    logger.debug(f"[TemporalHistory] Tri impossible: {sort_err}")
```

**Fonctionnement:**
1. Crée une liste unifiée `all_events` pour messages + concepts consolidés
2. Marque chaque événement avec sa source (`thread` ou `consolidated`)
3. Trie tous les événements chronologiquement

#### 4. Formatage Différencié (lignes 1233-1266)

**Code ajouté:**
```python
for event in all_events:
    try:
        # Parser la date
        dt = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        day = dt.day
        month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
        time_str = f"{dt.hour}h{dt.minute:02d}"
        date_str = f"{day} {month} à {time_str}"
    except Exception:
        date_str = "date inconnue"

    # Extraire un aperçu du contenu
    content = event.get("content", "")
    preview = content[:80].strip() if isinstance(content, str) else ""
    if len(content) > 80:
        preview += "..."

    # Formater selon le type d'événement
    if event["source"] == "thread":
        role = event.get("role")
        agent_id = event.get("agent_id")
        if role == "user":
            lines.append(f"**[{date_str}] Toi :** {preview}")
        elif role == "assistant" and agent_id:
            lines.append(f"**[{date_str}] {agent_id.title()} :** {preview}")
    elif event["source"] == "consolidated":
        # Marquer les entrées issues de la mémoire consolidée
        concept_type = event.get("type", "concept")
        lines.append(f"**[{date_str}] Mémoire ({concept_type}) :** {preview}")

if len(all_events) > 0:
    logger.info(f"[TemporalHistory] Contexte enrichi: {len(messages)} messages + {len(consolidated_entries)} concepts consolidés")
```

**Formatage:**
- Messages du thread : `**[15 oct à 3h08] Toi :** Message...`
- Messages assistant : `**[15 oct à 3h09] Anima :** Réponse...`
- **Mémoire consolidée : `**[14 oct à 4h30] Mémoire (concept) :** Résumé du concept...**`

#### 5. Mise à Jour de l'Appel (ligne 1859)

**Avant:**
```python
recall_context = await self._build_temporal_history_context(
    thread_id=thread_id,
    session_id=session_id,
    user_id=uid,
    limit=20
)
```

**Après:**
```python
recall_context = await self._build_temporal_history_context(
    thread_id=thread_id,
    session_id=session_id,
    user_id=uid,
    limit=20,
    last_user_message=last_user_message  # NOUVEAU paramètre passé
)
```

---

## Exemple de Contexte Enrichi

### Avant (sans concepts consolidés)

```markdown
### Historique récent de cette conversation

**[15 oct à 3h41] Toi :** Quand avons-nous parlé de Docker ?
**[15 oct à 3h41] Anima :** On a parlé de Docker le 8 octobre à 14h32...
```

### Après (avec concepts consolidés)

```markdown
### Historique récent de cette conversation

**[14 oct à 4h24] Mémoire (concept) :** L'utilisateur demande à plusieurs reprises à l'assistant de citer intégralemen...
**[14 oct à 4h30] Mémoire (concept) :** L'utilisateur répète plusieurs fois des demandes de citation intégrale de son...
**[15 oct à 3h02] Mémoire (concept) :** L'utilisateur demande à plusieurs reprises des citations intégrales de son poè...
**[15 oct à 3h41] Toi :** quand avons-nous parlé de mon poème fondateur?
**[15 oct à 3h41] Anima :** [Réponse...]
```

**Résultat:** Anima a maintenant accès aux timestamps des conversations archivées sur le poème fondateur.

---

## Impact

### Améliorations

✅ **Questions temporelles sur contenu ancien**
- Anima peut maintenant répondre avec dates précises même pour conversations archivées
- Exemple: "Quand avons-nous parlé de X ?" fonctionne même si X est consolidé

✅ **Vue chronologique complète**
- Fusion messages récents + mémoire consolidée
- Tri chronologique automatique
- Distinction visuelle (source thread vs. mémoire)

✅ **Recherche sémantique intelligente**
- Utilise ChromaDB pour trouver concepts pertinents
- Top 5 résultats les plus similaires à la question
- Filtrage par user_id pour isolation

✅ **Logs enrichis**
```
[TemporalHistory] Contexte enrichi: 10 messages + 3 concepts consolidés
```

### Limitations Connues

⚠️ **Dépendance métadonnées consolidées**
- Nécessite que Memory Gardener stocke `timestamp` dans les métadonnées
- Si `timestamp` manquant, l'entrée consolidée ne sera pas incluse

⚠️ **Performance avec knowledge base volumineuse**
- Recherche sémantique sur 5 résultats (acceptable)
- Peut être plus lent si collection très grande (>10k entrées)

⚠️ **Limite de 5 concepts consolidés**
- Hardcodé `n_results=5` dans la recherche ChromaDB
- Peut manquer certains événements si nombreuses conversations archivées

---

## Tests Requis

### Test 1: Question Temporelle sur Contenu Archivé ⏳

**Action:**
```
User: "Quand avons-nous parlé de mon poème fondateur?"
```

**Résultat attendu:**
```
Anima: "On a parlé de ton poème fondateur plusieurs fois :
- Le 14 octobre à 4h24
- Le 14 octobre à 4h30
- Le 15 octobre à 3h02
[...]"
```

**Vérification logs:**
```
[TemporalHistory] Contexte enrichi: X messages + Y concepts consolidés
```

### Test 2: Fusion Messages + Mémoire ⏳

**Action:**
```
User: "Donne-moi l'historique complet de nos discussions sur Docker"
```

**Résultat attendu:**
- Inclut messages récents du thread
- Inclut concepts consolidés pertinents
- Ordre chronologique correct

### Test 3: Performance ⏳

**Vérifier:**
- Temps de réponse < 1 seconde
- Pas d'erreur si knowledge base vide
- Pas d'erreur si métadonnées manquantes

---

## Prochaines Étapes

### Validation (À faire maintenant)

1. **Redémarrer backend**
   ```bash
   pwsh -File scripts/run-backend.ps1
   ```

2. **Tester question poème fondateur**
   - Poser: "Quand avons-nous parlé de mon poème fondateur?"
   - Vérifier réponse inclut dates précises
   - Consulter logs backend

3. **Tester question Docker (régression)**
   - Poser: "Quand avons-nous parlé de Docker ?"
   - Vérifier toujours fonctionnel

### Optimisations Futures (Phase 2)

1. **Paramètre configurable n_results**
   ```python
   n_results = min(5, limit // 2)  # Adapter selon limite
   ```

2. **Cache recherche consolidée**
   - Éviter recherche répétée pour même question
   - Invalider si nouvelle consolidation

3. **Filtrage par date**
   - Paramètre `since` pour limiter recherche
   - Éviter résultats très anciens non pertinents

4. **Métrique Prometheus**
   ```python
   memory_temporal_consolidated_entries_total
   memory_temporal_query_duration_seconds{source="thread"|"consolidated"}
   ```

---

## Références

### Code Modifié

- [service.py:1130-1270](../src/backend/features/chat/service.py#L1130-L1270) - Fonction enrichie
- [service.py:1859](../src/backend/features/chat/service.py#L1859) - Appel mis à jour

### Documentation

- [MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md](../docs/architecture/MEMORY_TEMPORAL_CONTEXT_IMPLEMENTATION.md)
- [test_results_temporal_memory_2025-10-15.md](test_results_temporal_memory_2025-10-15.md)

### Rapports Session

- [session_validation_temporelle_2025-10-15.md](session_validation_temporelle_2025-10-15.md)

---

## Résumé

**Problème:** Contexte temporel limité aux 20 derniers messages → conversations archivées ignorées

**Solution:** Recherche sémantique dans `emergence_knowledge` + fusion chronologique

**Résultat:** Anima peut maintenant fournir dates précises pour toutes conversations, récentes ou archivées

**Statut:** ✅ Implémenté - ⏳ À tester

---

**Créé le:** 2025-10-15
**Par:** Session de correction post-validation Phase 1
**Prochaine action:** Redémarrer backend et tester avec question poème fondateur
