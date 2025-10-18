# 🧠 ROADMAP - REFONTE ARCHITECTURE MÉMOIRE AGENTS

**Date création**: 2025-10-18
**Objectif**: Refonte complète du système de mémoire pour garantir fiabilité, proactivité et cohérence
**Statut**: PLANIFIÉ - Prêt pour exécution

---

## 📋 TABLE DES MATIÈRES

1. [Contexte & Diagnostic](#contexte--diagnostic)
2. [Architecture Actuelle](#architecture-actuelle)
3. [Problèmes Identifiés](#problèmes-identifiés)
4. [Plan d'Exécution](#plan-dexécution)
   - [Sprint 1: Clarification Session vs Conversation](#sprint-1-clarification-session-vs-conversation)
   - [Sprint 2: Consolidation Auto Threads Archivés](#sprint-2-consolidation-auto-threads-archivés)
   - [Sprint 3: Rappel Proactif Unifié](#sprint-3-rappel-proactif-unifié)
   - [Sprint 4: Isolation Agent Stricte](#sprint-4-isolation-agent-stricte)
   - [Sprint 5: Interface Utilisateur](#sprint-5-interface-utilisateur)
5. [Validation & Tests](#validation--tests)
6. [Références Fichiers](#références-fichiers)

---

## 🔍 CONTEXTE & DIAGNOSTIC

### Situation Actuelle
- ✅ STM (Short-Term Memory) fonctionne pour sessions actives
- ✅ LTM (Long-Term Memory) vectorielle ChromaDB opérationnelle
- ❌ **Threads archivés NON consolidés automatiquement**
- ❌ **Agent ne "se souvient" pas spontanément de conversations passées**
- ❌ **Confusion conceptuelle entre Session (WS) et Conversation (persistante)**

### Demande Utilisateur
> "Je veux qu'ils puissent à la demande se souvenir des conversations passées, y.c celles archivées"

### Problème Principal
Architecture fragmentée où:
- **Session** = Connexion WebSocket éphémère (durée session)
- **Thread** = Conversation persistante (permanent)
- **Confusion**: `threads.session_id` lie conversation à session WS éphémère

---

## 🏗️ ARCHITECTURE ACTUELLE

### Composants Clés

#### 1. STM - Mémoire Court Terme
```
SessionManager (RAM)
  └─ active_sessions: Dict[str, Session]
       └─ Session:
            ├─ history: List[Dict]  (messages)
            ├─ metadata: {summary, concepts, entities}
            └─ finalize_session() → DB sessions table
```

**Fichiers**:
- [`src/backend/core/session_manager.py`](src/backend/core/session_manager.py) (lignes 51-943)
- [`src/backend/shared/models.py`](src/backend/shared/models.py) (lignes 29-43)

#### 2. LTM - Mémoire Long Terme
```
ChromaDB: "emergence_knowledge"
  ├─ type: "concept"      (consolidés via MemoryGardener)
  ├─ type: "preference"   (confidence >= 0.6)
  ├─ type: "intent"
  ├─ type: "constraint"
  └─ type: "fact"
```

**Fichiers**:
- [`src/backend/features/memory/gardener.py`](src/backend/features/memory/gardener.py) (lignes 1-300+)
- [`src/backend/features/memory/analyzer.py`](src/backend/features/memory/analyzer.py) (lignes 1-300+)
- [`src/backend/features/memory/vector_service.py`](src/backend/features/memory/vector_service.py)

#### 3. Conversations Persistantes
```sql
-- Table threads (conversations)
threads (
    id TEXT PRIMARY KEY,
    session_id TEXT,        -- ⚠️ Lien vers WS éphémère!
    user_id TEXT,
    type TEXT,              -- 'chat' | 'debate'
    archived INTEGER,       -- 0 | 1
    archived_at TEXT,
    last_message_at TEXT,
    message_count INTEGER
)

-- Table messages
messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT,
    role TEXT,
    content TEXT,
    created_at TEXT,
    user_id TEXT
)
```

**Fichiers**:
- [`src/backend/core/database/schema.py`](src/backend/core/database/schema.py) (lignes 85-149)
- [`src/backend/core/database/queries.py`](src/backend/core/database/queries.py) (lignes 814-859)

#### 4. Rappel Mémoire
```python
# STM: Hydratation session depuis thread
SessionManager._hydrate_session_from_thread()  # ligne 470

# LTM: Construction contexte RAG
MemoryContextBuilder.build_memory_context()    # ligne 91

# Archives: Recherche temporelle (PAS UTILISÉ PROACTIVEMENT)
MemoryQueryTool.get_conversation_timeline()    # memory_query_tool.py
```

**Fichiers**:
- [`src/backend/features/chat/memory_ctx.py`](src/backend/features/chat/memory_ctx.py) (lignes 40-675)
- [`src/backend/features/memory/memory_query_tool.py`](src/backend/features/memory/memory_query_tool.py)

---

## 🚨 PROBLÈMES IDENTIFIÉS

### P1 - CRITIQUE: Confusion Session vs Conversation
**Symptôme**: `threads.session_id` pointe vers session WS éphémère
**Impact**: Impossible de retrouver facilement conversations d'un utilisateur
**Fichiers**:
- `src/backend/core/database/schema.py:88` (définition threads)
- `src/backend/core/database/queries.py:798` (create_thread)

### P2 - HAUTE: Threads Archivés Non Consolidés
**Symptôme**: Archivage thread ne déclenche pas consolidation LTM
**Impact**: Souvenirs perdus après archivage
**Fichiers**:
- `src/backend/core/database/queries.py:900-925` (update_thread)
- `src/backend/features/memory/router.py:2026-2122` (consolidate_archived endpoint existe mais pas utilisé)

### P3 - HAUTE: Pas de Rappel Proactif Archives
**Symptôme**: Agent ne "se souvient" pas spontanément
**Impact**: Contexte appauvri, utilisateur doit demander explicitement
**Fichiers**:
- `src/backend/features/chat/memory_ctx.py:91-194` (build_memory_context)
- `src/backend/features/memory/memory_query_tool.py` (outil existe mais pas intégré)

### P4 - MOYENNE: Isolation Agent Incohérente
**Symptôme**: Concepts legacy sans `agent_id` visibles par tous agents
**Impact**: Risque confusion/hallucinations
**Fichiers**:
- `src/backend/features/chat/memory_ctx.py:642-674` (_result_matches_agent - filtrage permissif)
- `src/backend/core/memory/memory_sync.py:289-315` (filter_memories_by_agent)

### P5 - BASSE: Architecture Fragmentée
**Symptôme**: Pas de couche unifiée STM+LTM+Archives
**Impact**: Code complexe, maintenance difficile
**Solution**: Créer `UnifiedMemoryRetriever`

---

## 🎯 PLAN D'EXÉCUTION

---

## SPRINT 1: Clarification Session vs Conversation
**Durée**: 2-3 jours
**Priorité**: 🔴 CRITIQUE
**Objectif**: Séparer clairement Session (WS) et Conversation (persistante)

### Étape 1.1: Ajouter `conversation_id` Canonique

**Fichiers à modifier**:
1. `src/backend/core/database/schema.py`
2. `migrations/` (nouvelle migration)

**Actions**:

```python
# 1. Créer migration: migrations/20251018_add_conversation_id.sql
"""
-- Ajouter colonne conversation_id
ALTER TABLE threads ADD COLUMN conversation_id TEXT;

-- Initialiser avec id existant (rétrocompatibilité)
UPDATE threads SET conversation_id = id WHERE conversation_id IS NULL;

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_threads_user_conversation
ON threads(user_id, conversation_id);

-- Index composite pour requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_threads_user_type_conversation
ON threads(user_id, type, conversation_id);
"""

# 2. Mettre à jour schema.py (ligne ~85)
# Ajouter conversation_id dans TABLE_DEFINITIONS pour threads:
"""
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,  -- ✅ NOUVEAU: identifiant canonique
    session_id TEXT NOT NULL,       -- Gardé pour rétrocompat (lien WS source)
    user_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('chat','debate')),
    ...
)
"""
```

**Validation**:
```bash
# Test migration
pytest tests/test_migrations.py::test_conversation_id_migration

# Vérifier données
python -c "
from src.backend.core.database.manager import DatabaseManager
db = DatabaseManager('emergence.db')
await db.connect()
result = await db.fetch_all('SELECT id, conversation_id FROM threads LIMIT 5')
print(result)
"
```

### Étape 1.2: Mettre à Jour Code Utilisant threads

**Fichiers à modifier**:
1. `src/backend/core/database/queries.py`
2. `src/backend/core/session_manager.py`
3. `src/backend/features/threads/router.py`

**Actions**:

```python
# 1. queries.py - Modifier create_thread (ligne ~798)
async def create_thread(
    db: DatabaseManager,
    thread_id: str,
    session_id: str,
    user_id: str,
    type_: str,
    *,
    title: Optional[str] = None,
    agent_id: Optional[str] = None,
    meta: Optional[Dict] = None,
    conversation_id: Optional[str] = None,  # ✅ NOUVEAU
) -> str:
    # Générer conversation_id si pas fourni
    if not conversation_id:
        conversation_id = thread_id  # Par défaut = thread_id

    await db.execute(
        """
        INSERT INTO threads (
            id, conversation_id, session_id, user_id, type,
            title, agent_id, meta, archived, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            thread_id,
            conversation_id,  # ✅ NOUVEAU
            session_id,
            user_id,
            type_,
            title,
            agent_id,
            json.dumps(meta or {}),
            now_iso,
            now_iso
        ),
        commit=True
    )
    return conversation_id

# 2. Ajouter helper pour récupérer threads par conversation_id
async def get_threads_by_conversation(
    db: DatabaseManager,
    conversation_id: str,
    user_id: str,
    *,
    include_archived: bool = False
) -> List[Dict[str, Any]]:
    """Récupère tous threads d'une conversation (même conversation, sessions différentes)"""
    clauses = ["conversation_id = ?", "user_id = ?"]
    params = [conversation_id, user_id]

    if not include_archived:
        clauses.append("archived = 0")

    query = f"""
        SELECT * FROM threads
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC
    """
    rows = await db.fetch_all(query, tuple(params))
    return [dict(r) for r in rows]
```

**Validation**:
```bash
# Test unitaire
pytest tests/core/database/test_queries.py::test_conversation_id_creation
pytest tests/core/database/test_queries.py::test_get_threads_by_conversation

# Test intégration
pytest tests/integration/test_conversation_continuity.py
```

### Étape 1.3: Renommer Concepts dans Code (Optionnel mais Recommandé)

**Fichiers à modifier**:
1. `src/backend/shared/models.py` (renommer Session → WebSocketSession)
2. Mise à jour imports dans tous fichiers

**Actions**:
```python
# models.py (ligne 29)
class WebSocketSession(BaseModel):  # ✅ Renommé depuis Session
    """
    Représente une session WebSocket active (éphémère).
    Distinction claire avec Conversation (persistante).
    """
    id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    last_activity: datetime
    history: List[Dict[str, Any]]
    metadata: Dict[str, Any]

# Alias rétrocompatibilité
Session = WebSocketSession  # Pour migration en douceur
```

**Note**: Cette étape peut être reportée au Sprint 4 si besoin de livrer rapidement.

### ✅ Critères de Succès Sprint 1
- [ ] Migration `conversation_id` appliquée sans erreur
- [ ] Toutes conversations existantes ont `conversation_id = id`
- [ ] Nouveaux threads créés avec `conversation_id`
- [ ] Requêtes `get_threads_by_conversation()` fonctionnelles
- [ ] Tests unitaires passent (100% coverage nouvelles fonctions)
- [ ] Rétrocompatibilité préservée (`session_id` toujours utilisable)

---

## SPRINT 2: Consolidation Auto Threads Archivés
**Durée**: 3-4 jours
**Priorité**: 🟠 HAUTE
**Objectif**: Garantir que TOUTE conversation archivée soit consolidée en LTM

### Étape 2.1: Hook Automatique lors Archivage

**Fichiers à modifier**:
1. `src/backend/core/database/queries.py` (update_thread)
2. `src/backend/features/memory/gardener.py`

**Actions**:

```python
# 1. queries.py - Modifier update_thread (ligne ~900)
async def update_thread(
    db: DatabaseManager,
    thread_id: str,
    session_id: Optional[str],
    *,
    user_id: Optional[str] = None,
    title: Optional[str] = None,
    agent_id: Optional[str] = None,
    archived: Optional[bool] = None,
    meta: Optional[Dict[str, Any]] = None,
    gardener = None,  # ✅ NOUVEAU: injection MemoryGardener
) -> None:
    fields: list[str] = []
    params: list[Any] = []

    # ... code existant ...

    if archived is not None:
        fields.append("archived = ?")
        params.append(1 if archived else 0)

        # ✅ NOUVEAU: Si archivage, ajouter timestamp + raison
        if archived:
            fields.append("archived_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())

            # Raison par défaut si pas dans meta
            archival_reason = (meta or {}).get('archival_reason', 'manual_archive')
            fields.append("archival_reason = ?")
            params.append(archival_reason)

    # ... code existant de mise à jour ...

    # ✅ NOUVEAU: Déclencher consolidation si archivage
    if archived and gardener:
        try:
            logger.info(f"Thread {thread_id} archivé, déclenchement consolidation LTM...")
            await gardener._tend_single_thread(
                thread_id=thread_id,
                session_id=session_id,
                user_id=user_id or _get_user_from_thread(db, thread_id)
            )

            # Marquer comme consolidé
            await db.execute(
                "UPDATE threads SET consolidated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), thread_id),
                commit=True
            )
            logger.info(f"Thread {thread_id} consolidé en LTM avec succès")
        except Exception as e:
            logger.error(f"Échec consolidation thread {thread_id}: {e}", exc_info=True)
            # Ne pas bloquer l'archivage si consolidation échoue
```

**Injection MemoryGardener**:
```python
# 2. Dans router threads ou container
from backend.features.memory.gardener import MemoryGardener

@router.patch("/threads/{thread_id}/archive")
async def archive_thread(
    thread_id: str,
    request: Request,
    reason: Optional[str] = None
):
    container = request.app.state.service_container
    gardener = MemoryGardener(
        db_manager=container.db_manager(),
        vector_service=container.vector_service(),
        memory_analyzer=container.memory_analyzer()
    )

    await queries.update_thread(
        db=container.db_manager(),
        thread_id=thread_id,
        session_id=None,
        archived=True,
        meta={"archival_reason": reason or "manual"},
        gardener=gardener  # ✅ Injection
    )
```

**Validation**:
```python
# Test unitaire
async def test_archive_thread_triggers_consolidation():
    """Vérifier que archivage déclenche consolidation LTM"""
    # Setup
    db = DatabaseManager(':memory:')
    gardener = MemoryGardener(db, vector_service, analyzer)

    # Créer thread avec messages
    thread_id = await create_thread(db, ...)
    await add_message(db, thread_id, "Message test", ...)

    # Archiver (doit déclencher consolidation)
    await update_thread(db, thread_id, archived=True, gardener=gardener)

    # Vérifier consolidation
    thread = await get_thread(db, thread_id)
    assert thread['consolidated_at'] is not None

    # Vérifier concepts en ChromaDB
    concepts = vector_service.get(where={"thread_id": thread_id})
    assert len(concepts['ids']) > 0
```

### Étape 2.2: Job Batch Rattrapage Archives Existants

**Fichier à créer**:
`src/backend/cli/consolidate_all_archives.py`

**Actions**:

```python
# consolidate_all_archives.py
#!/usr/bin/env python3
"""
Script de migration ponctuel: Consolide tous threads archivés non traités.

Usage:
    python src/backend/cli/consolidate_all_archives.py --user-id <user_id>
    python src/backend/cli/consolidate_all_archives.py --all  # Admin only
"""
import asyncio
import argparse
import logging
from datetime import datetime, timezone

from backend.core.database.manager import DatabaseManager
from backend.features.memory.gardener import MemoryGardener
from backend.features.memory.vector_service import VectorService
from backend.features.memory.analyzer import MemoryAnalyzer
from backend.core.database import queries

logger = logging.getLogger(__name__)

async def is_already_consolidated(vector_service, thread_id: str) -> bool:
    """Vérifie si thread déjà consolidé en cherchant concepts dans ChromaDB"""
    try:
        collection = vector_service.get_or_create_collection("emergence_knowledge")
        result = collection.get(
            where={"thread_id": thread_id},
            limit=1
        )
        ids = result.get("ids") or []
        if isinstance(ids, list) and len(ids) > 0:
            if isinstance(ids[0], list):
                return len(ids[0]) > 0
            return True
        return False
    except Exception as e:
        logger.warning(f"Check consolidation failed for {thread_id}: {e}")
        return False

async def consolidate_all_archives(
    db: DatabaseManager,
    gardener: MemoryGardener,
    vector_service: VectorService,
    *,
    user_id: Optional[str] = None,
    limit: int = 1000,
    force: bool = False
):
    """Consolide tous threads archivés non traités"""

    # Récupérer threads archivés
    logger.info(f"Récupération threads archivés (user_id={user_id}, limit={limit})...")
    threads = await queries.get_threads(
        db,
        session_id=None,
        user_id=user_id,
        archived_only=True,
        limit=limit
    )

    logger.info(f"Trouvé {len(threads)} thread(s) archivé(s)")

    consolidated = 0
    skipped = 0
    errors = []

    for i, thread in enumerate(threads, 1):
        thread_id = thread.get('id')
        if not thread_id:
            continue

        logger.info(f"[{i}/{len(threads)}] Processing thread {thread_id[:8]}...")

        try:
            # Vérifier si déjà consolidé
            if not force and await is_already_consolidated(vector_service, thread_id):
                logger.info(f"  → Déjà consolidé, skip")
                skipped += 1
                continue

            # Consolider
            result = await gardener._tend_single_thread(
                thread_id=thread_id,
                session_id=thread.get('session_id'),
                user_id=thread.get('user_id')
            )

            new_concepts = result.get('new_concepts', 0)
            if new_concepts > 0:
                logger.info(f"  → Consolidé: {new_concepts} concepts")
                consolidated += 1

                # Marquer comme consolidé
                await db.execute(
                    "UPDATE threads SET consolidated_at = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), thread_id),
                    commit=True
                )
            else:
                logger.info(f"  → Aucun concept extrait")
                skipped += 1

        except Exception as e:
            logger.error(f"  → ERREUR: {e}", exc_info=True)
            errors.append({
                'thread_id': thread_id,
                'error': str(e)
            })

    # Rapport final
    logger.info(f"""
    ╔═══════════════════════════════════════╗
    ║  CONSOLIDATION BATCH TERMINÉE         ║
    ╠═══════════════════════════════════════╣
    ║  Total threads: {len(threads):4d}               ║
    ║  Consolidés:    {consolidated:4d}               ║
    ║  Skipped:       {skipped:4d}               ║
    ║  Erreurs:       {len(errors):4d}               ║
    ╚═══════════════════════════════════════╝
    """)

    if errors:
        logger.error(f"Erreurs détaillées:\n{errors}")

    return {
        'total': len(threads),
        'consolidated': consolidated,
        'skipped': skipped,
        'errors': errors
    }

async def main():
    parser = argparse.ArgumentParser(description="Consolide threads archivés")
    parser.add_argument('--user-id', help="User ID à traiter")
    parser.add_argument('--all', action='store_true', help="Tous utilisateurs (admin)")
    parser.add_argument('--limit', type=int, default=1000, help="Limite threads")
    parser.add_argument('--force', action='store_true', help="Forcer reconsolidation")
    parser.add_argument('--db', default='emergence.db', help="Chemin DB")
    args = parser.parse_args()

    # Setup
    logging.basicConfig(level=logging.INFO)
    db = DatabaseManager(args.db)
    await db.connect()

    vector_service = VectorService()
    analyzer = MemoryAnalyzer(db, enable_offline_mode=True)
    gardener = MemoryGardener(db, vector_service, analyzer)

    # Exécution
    user_id = None if args.all else args.user_id
    if not user_id and not args.all:
        logger.error("--user-id ou --all requis")
        return 1

    await consolidate_all_archives(
        db, gardener, vector_service,
        user_id=user_id,
        limit=args.limit,
        force=args.force
    )

    await db.close()
    return 0

if __name__ == '__main__':
    exit(asyncio.run(main()))
```

**Exécution**:
```bash
# Consolider archives d'un utilisateur spécifique
python src/backend/cli/consolidate_all_archives.py --user-id user_123

# Consolider TOUS archives (admin)
python src/backend/cli/consolidate_all_archives.py --all --limit 5000

# Forcer reconsolidation (migration)
python src/backend/cli/consolidate_all_archives.py --all --force
```

**Validation**:
```bash
# Vérifier consolidation
python -c "
from src.backend.core.database.manager import DatabaseManager
db = DatabaseManager('emergence.db')
await db.connect()

# Threads archivés
total = await db.fetch_one('SELECT COUNT(*) as c FROM threads WHERE archived=1')
print(f'Total archived: {total[\"c\"]}')

# Threads consolidés
consolidated = await db.fetch_one('SELECT COUNT(*) as c FROM threads WHERE archived=1 AND consolidated_at IS NOT NULL')
print(f'Consolidated: {consolidated[\"c\"]}')
"
```

### Étape 2.3: Ajouter Colonne `consolidated_at`

**Fichier migration**: `migrations/20251018_add_consolidated_at.sql`

```sql
-- Ajouter colonne pour tracker consolidation
ALTER TABLE threads ADD COLUMN consolidated_at TEXT;

-- Index pour requêtes de threads non consolidés
CREATE INDEX IF NOT EXISTS idx_threads_archived_not_consolidated
ON threads(archived, consolidated_at)
WHERE archived = 1 AND consolidated_at IS NULL;
```

### ✅ Critères de Succès Sprint 2
- [ ] Hook consolidation automatique lors archivage fonctionne
- [ ] Script batch `consolidate_all_archives.py` exécuté avec succès
- [ ] 100% threads archivés ont `consolidated_at` non NULL
- [ ] Concepts visibles dans ChromaDB pour chaque thread archivé
- [ ] Tests unitaires passent (consolidation automatique)
- [ ] Monitoring: métrique `threads_consolidated_total` ajoutée

---

## SPRINT 3: Rappel Proactif Unifié
**Durée**: 4-5 jours
**Priorité**: 🟠 HAUTE
**Objectif**: Agent "se souvient" spontanément de conversations passées pertinentes

### Étape 3.1: Créer `UnifiedMemoryRetriever`

**Fichier à créer**: `src/backend/features/memory/unified_retriever.py`

**Actions**:

```python
# unified_retriever.py
"""
UnifiedMemoryRetriever - Couche unifiée de rappel mémoire.

Récupère contexte depuis:
1. STM (session active)
2. LTM (concepts/préférences vectoriels)
3. Archives (conversations passées pertinentes)
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MemoryContext:
    """Contexte mémoire unifié pour injection dans prompt"""

    def __init__(self):
        self.stm_history: List[Dict] = []
        self.ltm_concepts: List[Dict] = []
        self.ltm_preferences: List[Dict] = []
        self.archived_conversations: List[Dict] = []

    def to_prompt_sections(self) -> List[tuple[str, str]]:
        """Formatte pour injection dans prompt système"""
        sections = []

        # Préférences actives (prioritaire)
        if self.ltm_preferences:
            prefs_text = "\n".join([
                f"- {p['text']}" for p in self.ltm_preferences[:5]
            ])
            sections.append(("Préférences actives", prefs_text))

        # Conversations passées pertinentes
        if self.archived_conversations:
            conv_text = "\n".join([
                f"- {c['date']}: {c['summary']}"
                for c in self.archived_conversations[:3]
            ])
            sections.append(("Conversations passées pertinentes", conv_text))

        # Concepts pertinents
        if self.ltm_concepts:
            concepts_text = "\n".join([
                f"- {c['text']}" for c in self.ltm_concepts[:5]
            ])
            sections.append(("Connaissances pertinentes", concepts_text))

        return sections

    def to_markdown(self) -> str:
        """Formate en markdown pour injection prompt"""
        sections = self.to_prompt_sections()
        parts = []
        for title, body in sections:
            if body.strip():
                parts.append(f"### {title}\n{body.strip()}")
        return "\n\n".join(parts)


class UnifiedMemoryRetriever:
    """
    Récupérateur unifié de mémoire agent.
    Centralise accès STM + LTM + Archives.
    """

    def __init__(
        self,
        session_manager,
        vector_service,
        db_manager,
        memory_query_tool
    ):
        self.session_manager = session_manager
        self.vector_service = vector_service
        self.db = db_manager
        self.memory_query_tool = memory_query_tool

    async def retrieve_context(
        self,
        user_id: str,
        agent_id: str,
        session_id: str,
        current_query: str,
        *,
        include_stm: bool = True,
        include_ltm: bool = True,
        include_archives: bool = True,
        top_k_concepts: int = 5,
        top_k_archives: int = 3
    ) -> MemoryContext:
        """
        Récupère contexte unifié pour agent.

        Args:
            user_id: Identifiant utilisateur
            agent_id: Identifiant agent (anima/neo/nexus)
            session_id: Session WebSocket active
            current_query: Requête utilisateur actuelle
            include_stm: Inclure STM (défaut: True)
            include_ltm: Inclure LTM concepts (défaut: True)
            include_archives: Inclure archives (défaut: True)
            top_k_concepts: Nombre concepts LTM (défaut: 5)
            top_k_archives: Nombre conversations archivées (défaut: 3)

        Returns:
            MemoryContext avec sections remplies
        """
        context = MemoryContext()

        # 1. STM: Historique session active
        if include_stm:
            context.stm_history = await self._get_stm_context(session_id)

        # 2. LTM: Préférences + concepts pertinents
        if include_ltm:
            ltm_results = await self._get_ltm_context(
                user_id, agent_id, current_query, top_k=top_k_concepts
            )
            context.ltm_preferences = ltm_results['preferences']
            context.ltm_concepts = ltm_results['concepts']

        # 3. 🆕 Archives: Conversations passées pertinentes
        if include_archives:
            context.archived_conversations = await self._get_archived_context(
                user_id, agent_id, current_query, limit=top_k_archives
            )

        logger.info(
            f"[UnifiedRetriever] Context récupéré: "
            f"STM={len(context.stm_history)} msgs, "
            f"LTM={len(context.ltm_concepts)} concepts, "
            f"Prefs={len(context.ltm_preferences)}, "
            f"Archives={len(context.archived_conversations)} convs"
        )

        return context

    async def _get_stm_context(self, session_id: str) -> List[Dict]:
        """Récupère historique session active"""
        try:
            return self.session_manager.get_full_history(session_id)
        except Exception as e:
            logger.warning(f"STM retrieval failed: {e}")
            return []

    async def _get_ltm_context(
        self, user_id: str, agent_id: str, query: str, top_k: int
    ) -> Dict[str, List[Dict]]:
        """Récupère préférences + concepts depuis ChromaDB"""
        try:
            collection = self.vector_service.get_or_create_collection(
                "emergence_knowledge"
            )

            # Préférences actives (confidence >= 0.6)
            prefs = collection.get(
                where={
                    "$and": [
                        {"user_id": user_id},
                        {"agent_id": agent_id},
                        {"type": "preference"},
                        {"confidence": {"$gte": 0.6}}
                    ]
                },
                include=["documents", "metadatas"]
            )

            preferences = [
                {
                    'text': doc,
                    'confidence': meta.get('confidence', 0.5),
                    'topic': meta.get('topic', 'general')
                }
                for doc, meta in zip(
                    prefs.get('documents', []),
                    prefs.get('metadatas', [])
                )
            ]

            # Concepts pertinents (requête vectorielle)
            concepts_results = self.vector_service.query(
                collection=collection,
                query_text=query,
                n_results=top_k,
                where_filter={
                    "$and": [
                        {"user_id": user_id},
                        {"agent_id": agent_id},
                        {"type": "concept"}
                    ]
                }
            )

            concepts = [
                {
                    'text': r.get('text', ''),
                    'score': r.get('score', 0),
                    'metadata': r.get('metadata', {})
                }
                for r in (concepts_results or [])
            ]

            return {
                'preferences': preferences,
                'concepts': concepts
            }

        except Exception as e:
            logger.error(f"LTM retrieval failed: {e}", exc_info=True)
            return {'preferences': [], 'concepts': []}

    async def _get_archived_context(
        self, user_id: str, agent_id: str, query: str, limit: int
    ) -> List[Dict]:
        """
        🆕 Récupère conversations archivées pertinentes.

        Stratégie:
        1. Si threads archivés consolidés en LTM → déjà dans concepts
        2. Sinon, recherche fulltext dans messages archivés
        """
        try:
            # Recherche temporelle dans messages archivés
            from backend.core.temporal_search import TemporalSearch

            temporal = TemporalSearch(db_manager=self.db)
            messages = await temporal.search_messages(
                query=query,
                limit=limit * 5,  # Fetch more pour filtrer
                user_id=user_id
            )

            # Filtrer messages de threads archivés seulement
            from backend.core.database import queries

            archived_messages = []
            seen_threads = set()

            for msg in messages:
                thread_id = msg.get('thread_id')
                if not thread_id or thread_id in seen_threads:
                    continue

                # Vérifier si thread archivé
                thread = await queries.get_thread_any(
                    self.db, thread_id, session_id=None, user_id=user_id
                )

                if thread and thread.get('archived'):
                    seen_threads.add(thread_id)
                    archived_messages.append({
                        'thread_id': thread_id,
                        'title': thread.get('title', 'Sans titre'),
                        'date': self._format_date(thread.get('archived_at')),
                        'summary': msg.get('content', '')[:200],
                        'relevance': msg.get('score', 0)
                    })

                if len(archived_messages) >= limit:
                    break

            # Trier par pertinence
            archived_messages.sort(
                key=lambda x: x['relevance'],
                reverse=True
            )

            return archived_messages[:limit]

        except Exception as e:
            logger.error(f"Archive retrieval failed: {e}", exc_info=True)
            return []

    @staticmethod
    def _format_date(iso_date: Optional[str]) -> str:
        """Formatte date ISO en français naturel"""
        if not iso_date:
            return ""
        try:
            dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
            months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                     "juil", "août", "sept", "oct", "nov", "déc"]
            month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
            return f"{dt.day} {month}"
        except:
            return iso_date[:10]
```

**Validation**:
```python
# Test unitaire
async def test_unified_retriever_full_context():
    """Test récupération contexte complet"""
    retriever = UnifiedMemoryRetriever(session_mgr, vector, db, query_tool)

    context = await retriever.retrieve_context(
        user_id="user_123",
        agent_id="anima",
        session_id="sess_456",
        current_query="Comment déployer avec Docker?"
    )

    # Vérifications
    assert isinstance(context, MemoryContext)
    assert len(context.ltm_preferences) > 0  # Préférences présentes
    assert len(context.ltm_concepts) > 0     # Concepts pertinents
    assert len(context.archived_conversations) > 0  # Archives trouvées

    # Format markdown
    markdown = context.to_markdown()
    assert "### Préférences actives" in markdown
    assert "### Conversations passées pertinentes" in markdown
```

### Étape 3.2: Intégrer dans `MemoryContextBuilder`

**Fichier à modifier**: `src/backend/features/chat/memory_ctx.py`

**Actions**:

```python
# memory_ctx.py (ligne ~40)
class MemoryContextBuilder:
    def __init__(self, session_manager, vector_service):
        self.session_manager = session_manager
        self.vector_service = vector_service

        # 🆕 Ajouter UnifiedMemoryRetriever
        from backend.features.memory.unified_retriever import UnifiedMemoryRetriever
        from backend.features.memory.memory_query_tool import MemoryQueryTool

        # Obtenir db_manager depuis session_manager
        db_manager = getattr(session_manager, 'db_manager', None)

        if db_manager:
            memory_query_tool = MemoryQueryTool(vector_service)
            self.unified_retriever = UnifiedMemoryRetriever(
                session_manager=session_manager,
                vector_service=vector_service,
                db_manager=db_manager,
                memory_query_tool=memory_query_tool
            )
        else:
            logger.warning("db_manager non disponible, UnifiedRetriever désactivé")
            self.unified_retriever = None

        # Cache préférences (existant)
        self._prefs_cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)

        logger.info(
            "[MemoryContextBuilder] Initialized with UnifiedRetriever "
            f"(enabled={self.unified_retriever is not None})"
        )

    async def build_memory_context(
        self,
        session_id: str,
        last_user_message: str,
        top_k: int = 5,
        agent_id: Optional[str] = None,
        use_unified_retriever: bool = True  # ✅ NOUVEAU: flag activation
    ) -> str:
        """
        Construit contexte mémoire pour injection prompt.

        🆕 Si use_unified_retriever=True, utilise UnifiedRetriever pour:
        - Préférences (cache 5min)
        - Concepts vectoriels pertinents
        - Conversations archivées pertinentes
        """
        try:
            if not last_user_message:
                return ""

            uid = self.try_get_user_id(session_id)

            # 🆕 NOUVEAU: Utiliser UnifiedRetriever si disponible
            if use_unified_retriever and self.unified_retriever and uid and agent_id:
                logger.info("[MemoryContext] Using UnifiedRetriever for context")

                context = await self.unified_retriever.retrieve_context(
                    user_id=uid,
                    agent_id=agent_id,
                    session_id=session_id,
                    current_query=last_user_message,
                    top_k_concepts=top_k,
                    top_k_archives=3  # Top 3 conversations archivées
                )

                return context.to_markdown()

            # FALLBACK: Comportement existant (si unified_retriever désactivé)
            logger.info("[MemoryContext] Using legacy retrieval (no UnifiedRetriever)")

            knowledge_name = os.getenv(
                "EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge"
            )
            knowledge_col = self.vector_service.get_or_create_collection(knowledge_name)

            sections = []

            # Préférences (cache existant)
            if uid:
                prefs = self._fetch_active_preferences_cached(knowledge_col, uid)
                if prefs:
                    sections.append(("Préférences actives", prefs))

            # Meta query detection (existant)
            if uid and self._is_meta_query(last_user_message):
                chronological = await self._build_chronological_context(
                    uid, last_user_message, agent_id=agent_id
                )
                if chronological:
                    sections.append(("Historique des sujets abordés", chronological))
                return self.merge_blocks(sections)

            # Vector search (existant)
            where_filter = {"user_id": uid} if uid else None
            results = self.vector_service.query(
                collection=knowledge_col,
                query_text=last_user_message,
                n_results=top_k * 2,
                where_filter=where_filter,
            )

            if results and agent_id:
                results = [
                    r for r in results
                    if self._result_matches_agent(r, agent_id.lower())
                ][:top_k]

            if results:
                weighted = self._apply_temporal_weighting(results)
                lines = [
                    f"- {r.get('text', '').strip()}{self._format_temporal_hint(r.get('metadata', {}))}"
                    for r in weighted[:top_k]
                    if r.get('text', '').strip()
                ]
                if lines:
                    sections.append(("Connaissances pertinentes", "\n".join(lines)))

            return self.merge_blocks(sections)

        except Exception as e:
            logger.warning(f"build_memory_context: {e}")
            return ""
```

**Flag d'activation**:
```python
# Utilisation dans chat service
memory_context = await memory_ctx_builder.build_memory_context(
    session_id=session_id,
    last_user_message=user_message,
    agent_id=agent_id,
    use_unified_retriever=True  # ✅ Activer nouveau système
)
```

**Validation**:
```python
# Test end-to-end
async def test_memory_context_includes_archives():
    """Vérifier que contexte inclut conversations archivées"""
    # Setup: Créer conversation archivée avec contenu pertinent
    thread_id = await create_archived_thread_with_content(
        db, user_id="user_123",
        content="Nous avons discuté de Docker et Kubernetes"
    )

    # Consolider en LTM
    await gardener._tend_single_thread(thread_id, ...)

    # Nouvelle requête similaire
    context = await memory_ctx.build_memory_context(
        session_id="new_session",
        last_user_message="Comment déployer avec Docker?",
        agent_id="anima",
        use_unified_retriever=True
    )

    # Vérifier mention conversation passée
    assert "Conversations passées pertinentes" in context
    assert "Docker" in context or "Kubernetes" in context
```

### Étape 3.3: Ajouter Feature Flag & Monitoring

**Fichier**: `.env` et code monitoring

```bash
# .env - Feature flag
ENABLE_UNIFIED_MEMORY_RETRIEVER=true  # Activation progressive
UNIFIED_RETRIEVER_INCLUDE_ARCHIVES=true
UNIFIED_RETRIEVER_TOP_K_ARCHIVES=3
```

**Monitoring Prometheus**:
```python
# unified_retriever.py - Ajouter métriques
from prometheus_client import Counter, Histogram

UNIFIED_RETRIEVER_CALLS = Counter(
    'unified_retriever_calls_total',
    'Nombre appels UnifiedRetriever',
    ['agent_id', 'source']  # source: stm, ltm, archives
)

UNIFIED_RETRIEVER_DURATION = Histogram(
    'unified_retriever_duration_seconds',
    'Durée récupération contexte',
    ['source']
)

# Dans retrieve_context()
with UNIFIED_RETRIEVER_DURATION.labels(source='total').time():
    # ... code ...

    if include_archives:
        with UNIFIED_RETRIEVER_DURATION.labels(source='archives').time():
            context.archived_conversations = await self._get_archived_context(...)
        UNIFIED_RETRIEVER_CALLS.labels(
            agent_id=agent_id,
            source='archives'
        ).inc()
```

### ✅ Critères de Succès Sprint 3
- [ ] `UnifiedMemoryRetriever` créé et testé unitairement
- [ ] Intégration dans `MemoryContextBuilder` fonctionnelle
- [ ] Conversations archivées apparaissent dans contexte agent
- [ ] Feature flag permet activation/désactivation
- [ ] Métriques Prometheus opérationnelles
- [ ] Tests end-to-end passent (rappel proactif)
- [ ] Performance: Latence contexte < 200ms (P95)

---

## SPRINT 4: Isolation Agent Stricte
**Durée**: 2-3 jours
**Priorité**: 🟡 MOYENNE
**Objectif**: Garantir séparation stricte mémoire entre agents (Anima/Neo/Nexus)

### Étape 4.1: Backfill `agent_id` Concepts Legacy

**Fichier à créer**: `src/backend/cli/backfill_agent_ids.py`

**Actions**:

```python
# backfill_agent_ids.py
"""
Backfill agent_id pour concepts legacy (sans agent_id).
Inférence basée sur thread_ids source.
"""
import asyncio
import logging
from typing import Optional

from backend.features.memory.vector_service import VectorService
from backend.core.database.manager import DatabaseManager
from backend.core.database import queries

logger = logging.getLogger(__name__)

async def infer_agent_from_thread(db: DatabaseManager, thread_id: str) -> Optional[str]:
    """Infère agent_id depuis thread source"""
    try:
        thread = await queries.get_thread_any(db, thread_id)
        if thread:
            agent_id = thread.get('agent_id')
            if agent_id:
                return agent_id.lower()
        return 'anima'  # Défaut
    except Exception as e:
        logger.warning(f"Failed to infer agent from thread {thread_id}: {e}")
        return 'anima'

async def backfill_missing_agent_ids(
    vector_service: VectorService,
    db: DatabaseManager,
    *,
    user_id: Optional[str] = None,
    dry_run: bool = False
):
    """Backfill agent_id pour concepts sans agent_id"""

    collection = vector_service.get_or_create_collection("emergence_knowledge")

    # Récupérer concepts sans agent_id
    where = {"type": "concept"}
    if user_id:
        where = {"$and": [where, {"user_id": user_id}]}

    results = collection.get(
        where=where,
        include=["metadatas"]
    )

    concept_ids = results.get('ids', [])
    metadatas = results.get('metadatas', [])

    logger.info(f"Trouvé {len(concept_ids)} concepts à analyser")

    updated = 0
    skipped = 0

    for concept_id, meta in zip(concept_ids, metadatas):
        # Skip si agent_id déjà présent
        if meta.get('agent_id'):
            skipped += 1
            continue

        # Inférer depuis thread_ids
        thread_ids = meta.get('thread_ids', [])
        if not thread_ids:
            logger.debug(f"Concept {concept_id[:8]}... sans thread_ids, skip")
            skipped += 1
            continue

        # Prendre premier thread_id
        inferred_agent = await infer_agent_from_thread(db, thread_ids[0])

        logger.info(
            f"Concept {concept_id[:8]}... → agent_id inféré: {inferred_agent}"
        )

        if not dry_run:
            # Mettre à jour
            updated_meta = {**meta, 'agent_id': inferred_agent}
            collection.update(
                ids=[concept_id],
                metadatas=[updated_meta]
            )
            updated += 1
        else:
            logger.info(f"  [DRY-RUN] Aurait mis à jour avec agent_id={inferred_agent}")
            updated += 1

    logger.info(f"""
    ╔═══════════════════════════════════════╗
    ║  BACKFILL AGENT_ID TERMINÉ            ║
    ╠═══════════════════════════════════════╣
    ║  Total concepts: {len(concept_ids):4d}              ║
    ║  Updated:        {updated:4d}              ║
    ║  Skipped:        {skipped:4d}              ║
    ║  Dry-run:        {str(dry_run):5s}             ║
    ╚═══════════════════════════════════════╝
    """)

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--user-id', help="User ID à traiter")
    parser.add_argument('--dry-run', action='store_true', help="Simulation")
    parser.add_argument('--db', default='emergence.db')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    db = DatabaseManager(args.db)
    await db.connect()

    vector_service = VectorService()

    await backfill_missing_agent_ids(
        vector_service, db,
        user_id=args.user_id,
        dry_run=args.dry_run
    )

    await db.close()

if __name__ == '__main__':
    asyncio.run(main())
```

**Exécution**:
```bash
# Dry-run (simulation)
python src/backend/cli/backfill_agent_ids.py --dry-run

# Exécution réelle
python src/backend/cli/backfill_agent_ids.py

# Pour un utilisateur spécifique
python src/backend/cli/backfill_agent_ids.py --user-id user_123
```

### Étape 4.2: Modifier Filtrage pour Mode Strict

**Fichier à modifier**: `src/backend/features/chat/memory_ctx.py`

**Actions**:

```python
# memory_ctx.py (ligne ~642)
@staticmethod
def _result_matches_agent(
    result: Dict[str, Any],
    agent_id: str,
    strict_mode: bool = None  # ✅ NOUVEAU paramètre
) -> bool:
    """
    Vérifie si résultat correspond à agent demandé.

    Args:
        result: Résultat vectoriel
        agent_id: Agent ID normalisé (lowercase)
        strict_mode:
            - True: Filtrage strict (ignore concepts sans agent_id)
            - False: Filtrage permissif (inclut concepts sans agent_id)
            - None: Auto (lire depuis env STRICT_AGENT_ISOLATION)
    """
    # Auto-détection mode depuis env
    if strict_mode is None:
        import os
        strict_mode = os.getenv('STRICT_AGENT_ISOLATION', 'false').lower() == 'true'

    metadata = result.get("metadata", {})
    if not isinstance(metadata, dict):
        return not strict_mode  # Mode permissif = inclure, strict = exclure

    result_agent_id = metadata.get("agent_id")

    # Cas 1: Pas d'agent_id
    if not result_agent_id:
        # Mode strict: EXCLURE concepts sans agent_id
        # Mode permissif: INCLURE (comportement legacy)
        return not strict_mode

    # Cas 2: Agent ID correspond
    if isinstance(result_agent_id, str) and result_agent_id.lower() == agent_id:
        return True

    # Cas 3: Ne correspond pas
    return False
```

**Configuration**:
```bash
# .env - Activer mode strict progressivement
STRICT_AGENT_ISOLATION=false  # Phase transition (défaut)
# STRICT_AGENT_ISOLATION=true  # Phase finale (après backfill)
```

**Tests**:
```python
# Test isolation stricte
async def test_strict_agent_isolation():
    """Vérifier filtrage strict agent_id"""
    # Setup: Concepts avec/sans agent_id
    collection.add(
        ids=['c1', 'c2', 'c3'],
        documents=['Doc Anima', 'Doc Neo', 'Doc Legacy'],
        metadatas=[
            {'agent_id': 'anima', 'user_id': 'u1'},
            {'agent_id': 'neo', 'user_id': 'u1'},
            {'user_id': 'u1'}  # Pas d'agent_id
        ]
    )

    # Mode strict = True
    results = vector_service.query(
        query_text="test",
        where_filter={'user_id': 'u1'}
    )
    filtered_strict = [
        r for r in results
        if _result_matches_agent(r, 'anima', strict_mode=True)
    ]
    assert len(filtered_strict) == 1  # Seulement c1
    assert filtered_strict[0]['id'] == 'c1'

    # Mode permissif = False
    filtered_permissive = [
        r for r in results
        if _result_matches_agent(r, 'anima', strict_mode=False)
    ]
    assert len(filtered_permissive) == 2  # c1 + c3 (legacy)
```

### Étape 4.3: Plan Migration Strict Mode

**Roadmap activation**:

```
Phase 1 (Semaine 1-2): PRÉPARATION
├─ Backfill agent_id concepts legacy
├─ Tests isolation stricte
└─ STRICT_AGENT_ISOLATION=false (permissif)

Phase 2 (Semaine 3): ACTIVATION BETA
├─ STRICT_AGENT_ISOLATION=true pour 10% utilisateurs
├─ Monitoring métriques isolation
└─ Tests utilisateurs beta

Phase 3 (Semaine 4): ROLLOUT COMPLET
├─ STRICT_AGENT_ISOLATION=true pour 100%
├─ Déprécier mode permissif
└─ Cleanup code legacy
```

**Monitoring**:
```python
# Métriques isolation agent
from prometheus_client import Counter

AGENT_ISOLATION_VIOLATIONS = Counter(
    'agent_isolation_violations_total',
    'Concepts cross-agent détectés',
    ['agent_requesting', 'agent_concept']
)

# Dans _result_matches_agent()
if strict_mode and result_agent_id and result_agent_id != agent_id:
    AGENT_ISOLATION_VIOLATIONS.labels(
        agent_requesting=agent_id,
        agent_concept=result_agent_id
    ).inc()
```

### ✅ Critères de Succès Sprint 4
- [ ] Script backfill exécuté: 100% concepts ont agent_id
- [ ] Mode strict implémenté et testé
- [ ] Feature flag `STRICT_AGENT_ISOLATION` opérationnel
- [ ] Monitoring violations isolation actif
- [ ] Tests unitaires passent (mode strict/permissif)
- [ ] Documentation mise à jour (migration guide)

---

## SPRINT 5: Interface Utilisateur (BONUS)
**Durée**: 5-7 jours
**Priorité**: 🟢 BASSE (BONUS)
**Objectif**: Dashboard utilisateur pour visualiser/gérer sa mémoire

### Fonctionnalités Proposées

#### 1. Dashboard Mémoire
```
/api/memory/user/dashboard

Response:
{
  "stats": {
    "conversations_total": 47,
    "conversations_active": 5,
    "conversations_archived": 42,
    "concepts_total": 156,
    "preferences_active": 12,
    "memory_size_mb": 4.2
  },
  "timeline": [
    {
      "period": "Cette semaine",
      "topics": ["Docker", "CI/CD", "Kubernetes"],
      "conversation_count": 3
    }
  ],
  "top_concepts": [
    {
      "concept": "Docker containerization",
      "mentions": 8,
      "last_mentioned": "2025-10-15"
    }
  ]
}
```

#### 2. Gestion Conversations
```
GET /api/threads?archived=true&search=docker
PATCH /api/threads/{id}/unarchive
DELETE /api/threads/{id}?permanent=true
```

#### 3. Gestion Concepts
```
GET /api/memory/concepts?sort=frequent&limit=50
PATCH /api/memory/concepts/{id}  # Modifier description/tags
POST /api/memory/concepts/merge  # Fusionner concepts similaires
DELETE /api/memory/concepts/{id}
```

#### 4. Export/Import Mémoire
```
GET /api/memory/export  # Export JSON complet
POST /api/memory/import  # Import depuis backup
```

**Note**: Routes déjà implémentées dans `src/backend/features/memory/router.py` (lignes 936-2122)

### Composants Frontend (React)

**Fichiers à créer**:
```
src/frontend/components/memory/
├── MemoryDashboard.tsx        # Dashboard principal
├── ConversationsList.tsx      # Liste conversations archivées
├── ConceptsGraph.tsx          # Graph visualisation concepts
├── PreferencesManager.tsx     # Gestion préférences
└── MemoryExport.tsx           # Export/Import
```

### ✅ Critères de Succès Sprint 5
- [ ] Dashboard mémoire accessible et responsive
- [ ] Recherche fulltext conversations fonctionnelle
- [ ] Visualisation graph concepts opérationnelle
- [ ] Export/import mémoire testé
- [ ] Documentation utilisateur rédigée

---

## 🧪 VALIDATION & TESTS

### Tests Unitaires Requis

```python
# tests/features/memory/test_unified_retriever.py
async def test_unified_retriever_stm():
    """Test récupération STM"""

async def test_unified_retriever_ltm():
    """Test récupération LTM (prefs + concepts)"""

async def test_unified_retriever_archives():
    """Test récupération conversations archivées"""

async def test_unified_retriever_full_context():
    """Test contexte complet (STM + LTM + Archives)"""

# tests/features/memory/test_consolidation.py
async def test_auto_consolidation_on_archive():
    """Test consolidation auto lors archivage"""

async def test_batch_consolidation_archives():
    """Test script batch consolidation"""

# tests/core/database/test_conversation_id.py
async def test_conversation_id_creation():
    """Test création conversation avec conversation_id"""

async def test_get_threads_by_conversation():
    """Test récupération par conversation_id"""

# tests/features/memory/test_agent_isolation.py
async def test_strict_agent_filtering():
    """Test filtrage strict agent_id"""

async def test_agent_id_backfill():
    """Test backfill agent_id legacy"""
```

### Tests d'Intégration

```python
# tests/integration/test_memory_e2e.py
async def test_full_memory_lifecycle():
    """
    Test cycle complet:
    1. Créer conversation
    2. Ajouter messages
    3. Archiver (déclenche consolidation)
    4. Nouvelle session
    5. Requête → Vérifier rappel archives
    """

async def test_cross_session_memory_recall():
    """
    Test rappel mémoire entre sessions:
    1. Session A: Parler de Docker
    2. Archiver conversation
    3. Session B (nouveau WS): Demander "Docker?"
    4. Vérifier contexte inclut conversation A
    """

async def test_agent_memory_isolation():
    """
    Test isolation entre agents:
    1. Anima: Créer concept "Docker"
    2. Neo: Requête "Docker"
    3. Vérifier Neo ne voit pas concept Anima (mode strict)
    """
```

### Métriques de Succès

```
Performance:
├─ Latence rappel contexte: < 200ms (P95)
├─ Latence consolidation: < 2s par thread
└─ Latence batch consolidation: < 5s pour 100 threads

Fiabilité:
├─ 100% threads archivés consolidés
├─ 0 violation isolation agent (mode strict)
└─ 99.9% uptime endpoints mémoire

Qualité:
├─ Coverage tests: > 85%
├─ 0 régression fonctionnelle
└─ Documentation complète (100% endpoints)
```

---

## 📚 RÉFÉRENCES FICHIERS

### Fichiers Critiques à Modifier

```
src/backend/core/
├── database/
│   ├── schema.py (L85-149)          # Ajout conversation_id, consolidated_at
│   └── queries.py (L798-925)         # Modifications create/update/get_threads
├── session_manager.py (L51-943)      # Intégration conversation_id
└── memory/
    └── memory_sync.py (L289-315)     # Isolation agent

src/backend/features/
├── chat/
│   └── memory_ctx.py (L40-675)       # Intégration UnifiedRetriever
└── memory/
    ├── router.py (L2026-2122)        # Endpoints consolidation
    ├── gardener.py (L1-300+)         # Consolidation auto
    ├── analyzer.py (L1-300+)         # Extraction concepts
    └── unified_retriever.py (NEW)    # ✅ À créer

migrations/
├── 20251018_add_conversation_id.sql  # ✅ À créer
└── 20251018_add_consolidated_at.sql  # ✅ À créer

src/backend/cli/
├── consolidate_all_archives.py (NEW) # ✅ À créer
└── backfill_agent_ids.py (NEW)       # ✅ À créer
```

### Fichiers de Configuration

```
.env
├── ENABLE_UNIFIED_MEMORY_RETRIEVER=true
├── UNIFIED_RETRIEVER_INCLUDE_ARCHIVES=true
├── UNIFIED_RETRIEVER_TOP_K_ARCHIVES=3
└── STRICT_AGENT_ISOLATION=false  # → true après backfill
```

---

## 🚀 QUICKSTART - PROCHAINE INSTANCE

### Commandes Rapides

```bash
# 1. Vérifier état actuel
python -c "
from src.backend.core.database.manager import DatabaseManager
db = DatabaseManager('emergence.db')
await db.connect()
rows = await db.fetch_all('PRAGMA table_info(threads)')
print('Colonnes threads:', [r['name'] for r in rows])
"

# 2. Appliquer migrations Sprint 1
python src/backend/core/database/manager.py run_migrations migrations/

# 3. Lancer consolidation batch (Sprint 2)
python src/backend/cli/consolidate_all_archives.py --user-id <USER_ID>

# 4. Backfill agent_id (Sprint 4)
python src/backend/cli/backfill_agent_ids.py --dry-run  # Test
python src/backend/cli/backfill_agent_ids.py             # Réel

# 5. Tests validation
pytest tests/features/memory/test_unified_retriever.py -v
pytest tests/integration/test_memory_e2e.py -v
```

### Ordre d'Exécution Recommandé

```
1. Sprint 1 (CRITIQUE) - 2-3 jours
   └─> Clarification Session vs Conversation
       → Permet accès facile conversations utilisateur

2. Sprint 2 (HAUTE) - 3-4 jours
   └─> Consolidation Auto Archives
       → Garantit aucun souvenir perdu

3. Sprint 3 (HAUTE) - 4-5 jours
   └─> Rappel Proactif Unifié
       → Agent "se souvient" spontanément

4. Sprint 4 (MOYENNE) - 2-3 jours
   └─> Isolation Agent Stricte
       → Prévient confusion entre agents

5. Sprint 5 (BONUS) - 5-7 jours
   └─> Interface Utilisateur
       → Contrôle utilisateur sur mémoire
```

---

## 📞 SUPPORT & QUESTIONS

### Décisions Architecture à Valider

- [ ] Approbation ajout `conversation_id` (breaking change schema)
- [ ] Validation stratégie consolidation automatique
- [ ] Choix mode isolation agent (strict vs permissif)
- [ ] Priorisation Sprint 5 (UI) vs autres features

### Points d'Attention

⚠️ **Migration DB**: Backups avant modifications schema
⚠️ **Performance**: Consolidation batch peut être lente (>1000 threads)
⚠️ **Rétrocompat**: Garder `session_id` fonctionnel pendant transition
⚠️ **Tests**: Valider sur environnement staging avant prod

---

**Fin de Roadmap** - Prêt pour exécution Sprint 1 🚀
