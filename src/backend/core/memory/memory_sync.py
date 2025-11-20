# src/backend/core/memory/memory_sync.py
"""
Memory Synchronization Module - Agent-specific context isolation

Gère l'isolation des contextes mémoire par agent pour éviter les confusions.
Chaque agent (Anima, Neo, Nexus) a son propre espace mémoire isolé.

Fonctionnalités:
- Context revision tracking (détection de désynchronisation)
- Agent-specific memory filtering
- Handshake protocol support (HELLO/ACK/SYNC)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Contexte mémoire d'un agent spécifique"""

    agent_id: str
    user_id: str
    context_id: str  # Format: "conv:{session_id}"
    context_rev: str  # Format: "rev:{hash}"
    last_seen_at: str  # ISO timestamp
    capabilities: List[str]  # Ex: ["rag:on", "tools:web", "memory:stm+ltm"]
    stm_count: int = 0  # Nombre d'items en mémoire court-terme
    ltm_count: int = 0  # Nombre d'items en mémoire long-terme


class MemorySyncManager:
    """
    Gestionnaire de synchronisation mémoire agent-spécifique.

    Assure que chaque agent ne voit que ses propres souvenirs et évite
    les confusions entre agents lors des résumés/chronologies.
    """

    def __init__(self, vector_service):
        self.vector_service = vector_service
        # Cache des contextes actifs par (user_id, agent_id)
        self._active_contexts: Dict[str, AgentContext] = {}

    def build_context_id(self, session_id: str) -> str:
        """Génère un context_id à partir de la session"""
        return f"conv:{session_id[:12]}"

    def build_context_rev(self, agent_id: str, user_id: str, timestamp: str) -> str:
        """
        Génère une révision de contexte basée sur l'état actuel.

        La révision change quand:
        - Un nouveau souvenir est ajouté
        - Un souvenir est modifié
        - Le contexte RAG change
        """
        # Hash simple basé sur agent+user+time (peut être amélioré avec content hash)
        content = f"{agent_id}:{user_id}:{timestamp}"
        hash_val = hashlib.sha256(content.encode()).hexdigest()[:8]
        return f"rev:{hash_val}"

    def create_agent_context(
        self,
        agent_id: str,
        user_id: str,
        session_id: str,
        capabilities: Optional[List[str]] = None,
    ) -> AgentContext:
        """
        Crée ou récupère le contexte pour un agent donné.

        Args:
            agent_id: Identifiant de l'agent (anima, neo, nexus)
            user_id: Identifiant utilisateur
            session_id: ID de session WebSocket
            capabilities: Capacités de l'agent

        Returns:
            AgentContext configuré
        """
        now = datetime.now(timezone.utc).isoformat()
        context_id = self.build_context_id(session_id)
        context_rev = self.build_context_rev(agent_id, user_id, now)

        # Compter les souvenirs existants pour cet agent
        stm_count, ltm_count = self._count_agent_memories(agent_id, user_id)

        context = AgentContext(
            agent_id=agent_id.lower(),
            user_id=user_id,
            context_id=context_id,
            context_rev=context_rev,
            last_seen_at=now,
            capabilities=capabilities or self._default_capabilities(agent_id),
            stm_count=stm_count,
            ltm_count=ltm_count,
        )

        # Cache le contexte
        cache_key = f"{user_id}:{agent_id.lower()}"
        self._active_contexts[cache_key] = context

        logger.info(
            f"[MemorySync] Context created for {agent_id} → "
            f"{context_id} (STM:{stm_count}, LTM:{ltm_count})"
        )

        return context

    def get_agent_context(self, agent_id: str, user_id: str) -> Optional[AgentContext]:
        """Récupère le contexte actif d'un agent"""
        cache_key = f"{user_id}:{agent_id.lower()}"
        return self._active_contexts.get(cache_key)

    def update_context_revision(
        self, agent_id: str, user_id: str, reason: str = "memory_update"
    ) -> str:
        """
        Met à jour la révision de contexte après modification.

        Args:
            agent_id: ID agent
            user_id: ID utilisateur
            reason: Raison de la mise à jour

        Returns:
            Nouvelle révision
        """
        cache_key = f"{user_id}:{agent_id.lower()}"
        context = self._active_contexts.get(cache_key)

        if not context:
            logger.warning(f"[MemorySync] No active context for {cache_key}")
            return ""

        now = datetime.now(timezone.utc).isoformat()
        new_rev = self.build_context_rev(agent_id, user_id, now)

        context.context_rev = new_rev
        context.last_seen_at = now

        # Recompter les mémoires
        stm_count, ltm_count = self._count_agent_memories(agent_id, user_id)
        context.stm_count = stm_count
        context.ltm_count = ltm_count

        logger.debug(
            f"[MemorySync] Context revision updated: {agent_id} → {new_rev} "
            f"(reason: {reason}, STM:{stm_count}, LTM:{ltm_count})"
        )

        return new_rev

    def build_hello_payload(
        self, context: AgentContext, model: str, provider: str
    ) -> Dict[str, Any]:
        """
        Construit le payload HELLO pour le protocole de handshake.

        Returns:
            Dict formaté pour envoi WebSocket
        """
        return {
            "type": "HELLO",
            "agent_id": context.agent_id,
            "model": model,
            "provider": provider,
            "context_id": context.context_id,
            "context_rev": context.context_rev,
            "last_seen_at": context.last_seen_at,
            "capabilities": context.capabilities,
            "memory_stats": {"stm": context.stm_count, "ltm": context.ltm_count},
        }

    def build_ack_payload(
        self, context: AgentContext, sync_status: str = "ok"
    ) -> Dict[str, Any]:
        """
        Construit le payload ACK en réponse au HELLO.

        Args:
            context: Contexte agent
            sync_status: "ok" | "desync" | "stale"
        """
        return {
            "type": "ACK",
            "agent_id": context.agent_id,
            "context_id": context.context_id,
            "context_rev": context.context_rev,
            "sync_status": sync_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def build_sync_payload(
        self,
        context: AgentContext,
        stm_items: List[Dict[str, Any]],
        ltm_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Construit le payload SYNC pour resynchroniser le contexte.

        Args:
            context: Contexte agent
            stm_items: Items mémoire court-terme
            ltm_items: Items mémoire long-terme
        """
        return {
            "type": "SYNC",
            "agent_id": context.agent_id,
            "context_id": context.context_id,
            "context_rev": context.context_rev,
            "stm": stm_items,
            "ltm": ltm_items,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _count_agent_memories(self, agent_id: str, user_id: str) -> tuple[int, int]:
        """
        Compte les souvenirs stockés pour un agent spécifique.

        Returns:
            (stm_count, ltm_count)
        """
        try:
            import os

            knowledge_name = os.getenv(
                "EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge"
            )
            col = self.vector_service.get_or_create_collection(knowledge_name)

            # Compter STM (conversations récentes)
            stm_where = {
                "$and": [
                    {"user_id": user_id},
                    {"agent_id": agent_id.lower()},
                    {"type": "conversation"},
                ]
            }
            stm_results = col.get(where=stm_where, limit=1)
            stm_count = len(stm_results.get("ids", []) or [])

            # Compter LTM (facts, preferences, concepts)
            ltm_where = {
                "$and": [
                    {"user_id": user_id},
                    {"agent_id": agent_id.lower()},
                    {"type": {"$in": ["fact", "preference", "concept"]}},
                ]
            }
            ltm_results = col.get(where=ltm_where, limit=1000)
            ltm_count = len(ltm_results.get("ids", []) or [])

            return stm_count, ltm_count

        except Exception as e:
            logger.warning(f"[MemorySync] Error counting memories: {e}")
            return 0, 0

    def _default_capabilities(self, agent_id: str) -> List[str]:
        """Capacités par défaut selon l'agent"""
        base = ["memory:stm+ltm"]

        # Anima: RAG + outils basiques
        if agent_id.lower() == "anima":
            return base + ["rag:on", "tools:basic"]

        # Neo: RAG + outils web
        elif agent_id.lower() == "neo":
            return base + ["rag:on", "tools:web", "tools:search"]

        # Nexus: RAG + outils avancés
        elif agent_id.lower() == "nexus":
            return base + ["rag:on", "tools:advanced", "tools:analysis"]

        return base

    def filter_memories_by_agent(
        self, memories: List[Dict[str, Any]], agent_id: str
    ) -> List[Dict[str, Any]]:
        """
        Filtre les souvenirs pour ne garder que ceux de l'agent spécifié.

        Args:
            memories: Liste de souvenirs (format ChromaDB)
            agent_id: ID de l'agent

        Returns:
            Liste filtrée
        """
        filtered = []
        agent_lower = agent_id.lower()

        for mem in memories:
            metadata = mem.get("metadata", {}) or {}
            mem_agent = (metadata.get("agent_id") or "").lower()

            # Garder seulement les souvenirs de cet agent
            if mem_agent == agent_lower:
                filtered.append(mem)

        return filtered

    def add_agent_tag_to_memory(
        self, memory_item: Dict[str, Any], agent_id: str
    ) -> Dict[str, Any]:
        """
        Ajoute le tag agent_id à un item mémoire avant stockage.

        Args:
            memory_item: Item à stocker (format ChromaDB)
            agent_id: ID de l'agent

        Returns:
            Item enrichi avec agent_id
        """
        if "metadata" not in memory_item:
            memory_item["metadata"] = {}

        memory_item["metadata"]["agent_id"] = agent_id.lower()

        return memory_item
