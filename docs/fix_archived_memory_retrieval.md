# Fix: Récupération des souvenirs archivés

**Date**: 2025-10-18
**Problème**: Les agents (Anima, Neo, Nexus) ne récupèrent pas les souvenirs des conversations archivées
**Statut**: ✅ Corrigé

## Contexte du problème

Quand un utilisateur demandait à Anima de résumer tous les sujets et conversations abordés ensemble, elle:
- ❌ N'avait accès qu'aux souvenirs de la session courante
- ❌ Hallucinait des informations (ex: mentionnant Kierkegaard et Simone Weil sans raison)
- ❌ Ne récupérait pas les concepts des threads archivés consolidés

### Exemple du problème

```
User: Peux-tu me résumer tous les sujets qu'on a abordé ensemble le nombre de fois qu'ils ont été abordés et le jour et la date

Anima: Cette semaine, on a surtout tourné autour de la construction d'une mémoire temporelle...
- Philosophie et littérature : Tu as mentionné Kierkegard, Simone Weil... [HALLUCINATION]
Je n'ai pas accès aux dates et heures précises... [FAUX - elle devrait avoir accès]
```

## Cause racine

Le problème était dans le **filtrage trop strict par `agent_id`** dans deux modules critiques:

### 1. `memory_query_tool.py` - Filtre ChromaDB trop restrictif

**Avant** (bugué):
```python
# Filtrait strictement par agent_id
if agent_id:
    base_conditions.append({"agent_id": agent_id.lower()})
```

**Problème**: Les anciens concepts consolidés avant l'implémentation du tag `agent_id` n'avaient PAS ce champ, donc étaient systématiquement exclus.

### 2. `memory_ctx.py` - Même problème dans le contexte vectoriel

**Avant** (bugué):
```python
# Filtre combiné: user_id ET agent_id
where_filter = {
    "$and": [
        {"user_id": uid},
        {"agent_id": agent_id.lower()}
    ]
}
```

**Problème**: Excluait tous les concepts legacy sans `agent_id`.

## Solution implémentée

### Stratégie: Filtrage PERMISSIF

Au lieu de filtrer strictement dans ChromaDB (qui exclut les concepts legacy), on:

1. **Récupère TOUS les concepts de l'utilisateur** depuis ChromaDB
2. **Filtre côté Python** avec une logique PERMISSIVE:
   - ✅ Inclut les concepts avec l'`agent_id` demandé
   - ✅ Inclut AUSSI les concepts SANS `agent_id` (legacy/rétrocompatibilité)
   - ❌ Exclut seulement les concepts d'un AUTRE agent

### Changements dans `memory_query_tool.py`

```python
def _build_timeframe_filter(...):
    # ✅ On ne filtre PLUS par agent_id dans ChromaDB
    base_conditions = [
        {"user_id": user_id},
        {"type": "concept"}
    ]
    # agent_id sera filtré côté Python dans list_discussed_topics

def list_discussed_topics(...):
    # ✅ Filtrage PERMISSIF côté Python
    if agent_id:
        normalized_agent_id = agent_id.lower()
        topics = [
            topic for topic in topics
            if self._topic_matches_agent(topic, normalized_agent_id)
        ]

@staticmethod
def _topic_matches_agent(topic: TopicSummary, agent_id: str) -> bool:
    topic_agent_id = topic.agent_id

    # Cas 1: Pas d'agent_id → concept legacy, on l'inclut ✅
    if not topic_agent_id:
        return True

    # Cas 2: Agent ID correspond ✅
    if topic_agent_id.lower() == agent_id:
        return True

    # Cas 3: Autre agent ❌
    return False
```

### Changements dans `memory_ctx.py`

```python
# ✅ Récupère TOUS les concepts de l'utilisateur
where_filter = {"user_id": uid} if uid else None

results = self.vector_service.query(
    collection=knowledge_col,
    query_text=last_user_message,
    n_results=top_k * 2,  # Récupérer plus pour filtrer après
    where_filter=where_filter,
)

# ✅ Filtrage PERMISSIF côté Python
if results and agent_id:
    normalized_agent_id = agent_id.lower()
    results = [
        r for r in results
        if self._result_matches_agent(r, normalized_agent_id)
    ]
    results = results[:top_k]
```

## Consolidation automatique des threads archivés

### Déjà implémenté ✅

Le système consolide automatiquement les threads lors de l'archivage via:
- Hook dans `threads/router.py` (ligne 192-212)
- Task queue asynchrone `memory/task_queue.py`
- Worker qui appelle `gardener._tend_single_thread()`

### Pour les threads archivés AVANT ce fix

**Script de migration fourni**: `consolidate_all_archives.py`

```bash
# Consolider tous les threads archivés non consolidés
python consolidate_all_archives.py

# Ou utiliser le CLI complet
python -m backend.cli.consolidate_archived_threads --verbose
```

## Résultat attendu

Après ce fix et la consolidation des archives:

✅ Anima peut résumer TOUS les sujets abordés (session courante + archives)
✅ Les dates et heures sont précises (tirées des métadonnées ChromaDB)
✅ Plus d'hallucinations sur des sujets non discutés
✅ Rétrocompatibilité avec les anciens concepts (sans agent_id)
✅ Isolation future entre agents (Neo, Nexus, Anima) tout en gardant accès aux concepts legacy

## Tests de validation

### Test 1: Vérifier que les concepts legacy sont récupérés

```python
from backend.features.memory.memory_query_tool import MemoryQueryTool

tool = MemoryQueryTool(vector_service)
topics = await tool.list_discussed_topics(
    user_id="test_user",
    timeframe="all",
    agent_id="anima"  # Doit inclure concepts sans agent_id
)

# Vérifier qu'on a des topics avec agent_id=None (legacy)
legacy_topics = [t for t in topics if t.agent_id is None]
print(f"Found {len(legacy_topics)} legacy topics")
```

### Test 2: Demander à Anima de résumer l'historique

```
User: Peux-tu me résumer tous les sujets qu'on a abordé ensemble avec les dates précises?

Anima: [Devrait lister TOUS les sujets avec dates exactes, incluant les archives]
```

## Fichiers modifiés

- `src/backend/features/memory/memory_query_tool.py` - Filtre PERMISSIF ChromaDB + Python
- `src/backend/features/chat/memory_ctx.py` - Filtre PERMISSIF contexte vectoriel
- `consolidate_all_archives.py` - Script helper de migration
- `docs/fix_archived_memory_retrieval.md` - Cette doc

## Notes pour l'avenir

### Si isolation stricte entre agents souhaitée plus tard

Pour activer une isolation STRICTE (concepts d'Anima invisibles pour Neo):

```python
# Dans _topic_matches_agent() et _result_matches_agent()
# Changer:
if not topic_agent_id:
    return True  # ← PERMISSIF (actuel)

# En:
if not topic_agent_id:
    return False  # ← STRICT (concepts legacy exclus)
```

**⚠️ Attention**: Cette modification casserait la rétrocompatibilité avec les anciens concepts.

### Migration recommandée

Si isolation stricte nécessaire:
1. Lancer un script de backfill pour taguer TOUS les concepts legacy avec leur agent_id
2. Attendre que tous les concepts soient tagués
3. Basculer vers le mode STRICT

---

**Auteur**: Claude Code (Sonnet 4.5)
**Validé par**: FG (Architecte)
