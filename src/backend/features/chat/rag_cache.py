# src/backend/features/chat/rag_cache.py
# Phase 3 RAG: Service de cache pour résultats RAG fréquents
#
# Architecture:
# - Support Redis (optionnel) avec fallback vers cache mémoire local
# - Clé basée sur fingerprint (hash query + filters)
# - TTL configurable via env
# - Invalidation sélective par document_id

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union
from collections import OrderedDict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("[RAG Cache] redis package not available, using in-memory cache")

logger = logging.getLogger(__name__)


class RAGCache:
    """
    Service de cache pour résultats RAG avec support Redis optionnel.

    Features:
    - Cache distribué (Redis) ou local (OrderedDict LRU)
    - TTL configurable
    - Invalidation par document_id
    - Fingerprinting intelligent de requêtes
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl_seconds: int = 3600,
        max_memory_items: int = 500
    ):
        """
        Initialize RAG cache.

        Args:
            redis_url: Redis connection URL (ex: redis://localhost:6379/0)
            ttl_seconds: Time-to-live pour les entrées cache
            max_memory_items: Taille max du cache mémoire (si Redis indisponible)
        """
        self.ttl_seconds = ttl_seconds
        self.max_memory_items = max_memory_items
        self.redis_client: Optional['redis.Redis'] = None
        self.memory_cache: OrderedDict[str, Tuple[datetime, Any]] = OrderedDict()
        self.enabled = True

        # Tentative de connexion Redis
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test de connexion
                self.redis_client.ping()
                logger.info(f"[RAG Cache] Connected to Redis: {redis_url}")
            except Exception as e:
                logger.warning(f"[RAG Cache] Redis connection failed: {e}, using memory cache")
                self.redis_client = None
        else:
            logger.info("[RAG Cache] Using in-memory cache (Redis not configured)")

    @staticmethod
    def _generate_fingerprint(
        query_text: str,
        where_filter: Optional[Dict[str, Any]],
        agent_id: str,
        selected_doc_ids: Optional[List[int]] = None
    ) -> str:
        """
        Génère un fingerprint unique pour une requête RAG.

        Args:
            query_text: Texte de la requête
            where_filter: Filtres ChromaDB
            agent_id: ID de l'agent
            selected_doc_ids: IDs de documents sélectionnés

        Returns:
            Hash SHA256 tronqué (16 premiers caractères)
        """
        # Normaliser la requête (lowercase, strip)
        normalized_query = query_text.lower().strip()

        # Sérialiser les filtres de façon déterministe
        filter_str = json.dumps(where_filter, sort_keys=True) if where_filter else ""

        # Sérialiser les doc_ids
        doc_ids_str = json.dumps(sorted(selected_doc_ids)) if selected_doc_ids else ""

        # Composer la clé complète
        composite_key = f"{normalized_query}|{filter_str}|{agent_id}|{doc_ids_str}"

        # Hash
        hash_obj = hashlib.sha256(composite_key.encode('utf-8'))
        fingerprint = hash_obj.hexdigest()[:16]  # 16 premiers caractères suffisent

        return fingerprint

    def get(
        self,
        query_text: str,
        where_filter: Optional[Dict[str, Any]],
        agent_id: str,
        selected_doc_ids: Optional[List[int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Récupère un résultat depuis le cache.

        Returns:
            Dict avec 'doc_hits' et 'rag_sources' si trouvé, None sinon
        """
        if not self.enabled:
            return None

        fingerprint = self._generate_fingerprint(
            query_text, where_filter, agent_id, selected_doc_ids
        )

        try:
            if self.redis_client:
                return self._get_from_redis(fingerprint)
            else:
                return self._get_from_memory(fingerprint)
        except Exception as e:
            logger.error(f"[RAG Cache] Error retrieving cache: {e}")
            return None

    def set(
        self,
        query_text: str,
        where_filter: Optional[Dict[str, Any]],
        agent_id: str,
        doc_hits: List[Dict[str, Any]],
        rag_sources: List[Dict[str, Any]],
        selected_doc_ids: Optional[List[int]] = None
    ) -> None:
        """
        Stocke un résultat dans le cache.
        """
        if not self.enabled:
            return

        fingerprint = self._generate_fingerprint(
            query_text, where_filter, agent_id, selected_doc_ids
        )

        cache_entry = {
            'doc_hits': doc_hits,
            'rag_sources': rag_sources,
            'timestamp': datetime.utcnow().isoformat(),
            'query_text': query_text[:100],  # Pour debug
        }

        try:
            if self.redis_client:
                self._set_in_redis(fingerprint, cache_entry)
            else:
                self._set_in_memory(fingerprint, cache_entry)
        except Exception as e:
            logger.error(f"[RAG Cache] Error storing cache: {e}")

    def invalidate_by_document(self, document_id: int) -> None:
        """
        Invalide toutes les entrées cache contenant un document_id donné.

        Note: En mode Redis, on invalide tout le cache (pattern scan trop coûteux).
        En mode mémoire, on scanne les entrées.
        """
        if not self.enabled:
            return

        try:
            if self.redis_client:
                # En production Redis, on préfère un flush complet (pattern scan = coûteux)
                # Alternative: utiliser Redis Sets pour tracker documents <-> fingerprints
                logger.info(f"[RAG Cache] Document {document_id} updated, flushing Redis cache")
                self._flush_redis()
            else:
                # En mémoire locale, on peut scanner
                logger.info(f"[RAG Cache] Document {document_id} updated, scanning memory cache")
                self._invalidate_memory_by_doc(document_id)
        except Exception as e:
            logger.error(f"[RAG Cache] Error invalidating cache: {e}")

    def invalidate_all(self):
        """Invalide tout le cache."""
        try:
            if self.redis_client:
                self._flush_redis()
            else:
                self.memory_cache.clear()
            logger.info("[RAG Cache] Cache fully invalidated")
        except Exception as e:
            logger.error(f"[RAG Cache] Error flushing cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne des statistiques sur le cache."""
        if self.redis_client:
            try:
                from typing import cast

                info = cast(Mapping[str, Any], self.redis_client.info('stats'))
                return {
                    'backend': 'redis',
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'connected': True,
                }
            except Exception:
                return {'backend': 'redis', 'connected': False}
        else:
            return {
                'backend': 'memory',
                'size': len(self.memory_cache),
                'max_size': self.max_memory_items,
            }

    # ==========================================
    # Redis implementation
    # ==========================================

    def _get_from_redis(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Récupère depuis Redis."""
        if self.redis_client is None:
            return None
        key = f"rag:query:{fingerprint}"
        cached_raw = self.redis_client.get(key)
        if cached_raw:
            logger.debug(f"[RAG Cache] Redis HIT: {fingerprint}")
            from typing import cast

            payload = cast(Union[str, bytes, bytearray], cached_raw)
            return cast(dict[str, Any], json.loads(payload))
        logger.debug(f"[RAG Cache] Redis MISS: {fingerprint}")
        return None

    def _set_in_redis(self, fingerprint: str, entry: Dict[str, Any]) -> None:
        """Stocke dans Redis avec TTL."""
        if self.redis_client is None:
            return
        key = f"rag:query:{fingerprint}"
        self.redis_client.setex(
            key,
            self.ttl_seconds,
            json.dumps(entry)
        )
        logger.debug(f"[RAG Cache] Redis SET: {fingerprint} (TTL={self.ttl_seconds}s)")

    def _flush_redis(self) -> None:
        """Flush toutes les clés rag:* dans Redis."""
        # Attention: SCAN peut être coûteux en prod, on flush tout le namespace
        if self.redis_client is None:
            return
        cursor = 0
        deleted = 0
        while True:
            from typing import cast

            cursor, keys = cast(
                Tuple[int, Sequence[Any]],
                self.redis_client.scan(cursor, match='rag:query:*', count=100),
            )
            if keys:
                deleted += cast(int, self.redis_client.delete(*keys))
            if cursor == 0:
                break
        logger.info(f"[RAG Cache] Flushed {deleted} Redis keys")

    # ==========================================
    # Memory implementation (LRU)
    # ==========================================

    def _get_from_memory(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Récupère depuis cache mémoire avec vérification TTL."""
        if fingerprint in self.memory_cache:
            timestamp, entry = self.memory_cache[fingerprint]
            age = (datetime.utcnow() - timestamp).total_seconds()

            if age < self.ttl_seconds:
                # Move to end (LRU)
                self.memory_cache.move_to_end(fingerprint)
                logger.debug(f"[RAG Cache] Memory HIT: {fingerprint} (age={age:.1f}s)")
                from typing import cast
                return cast(dict[str, Any], entry)
            else:
                # Expiré
                del self.memory_cache[fingerprint]
                logger.debug(f"[RAG Cache] Memory EXPIRED: {fingerprint}")

        logger.debug(f"[RAG Cache] Memory MISS: {fingerprint}")
        return None

    def _set_in_memory(self, fingerprint: str, entry: Dict[str, Any]) -> None:
        """Stocke dans cache mémoire avec LRU eviction."""
        # Supprimer le plus ancien si plein
        if len(self.memory_cache) >= self.max_memory_items:
            oldest_key = next(iter(self.memory_cache))
            del self.memory_cache[oldest_key]
            logger.debug(f"[RAG Cache] Memory evicted: {oldest_key}")

        self.memory_cache[fingerprint] = (datetime.utcnow(), entry)
        logger.debug(f"[RAG Cache] Memory SET: {fingerprint}")

    def _invalidate_memory_by_doc(self, document_id: int) -> None:
        """Invalide les entrées mémoire contenant un document_id."""
        to_delete = []
        for fingerprint, (timestamp, entry) in self.memory_cache.items():
            doc_hits = entry.get('doc_hits', [])
            for hit in doc_hits:
                md = hit.get('metadata', {})
                if md.get('document_id') == document_id:
                    to_delete.append(fingerprint)
                    break

        for fp in to_delete:
            del self.memory_cache[fp]

        if to_delete:
            logger.info(f"[RAG Cache] Invalidated {len(to_delete)} memory entries for doc {document_id}")


# ==========================================
# Factory function
# ==========================================

def create_rag_cache(
    redis_url: Optional[str] = None,
    ttl_seconds: Optional[int] = None
) -> RAGCache:
    """
    Factory pour créer une instance RAGCache avec config depuis env.

    Env variables:
    - RAG_CACHE_REDIS_URL: URL de connexion Redis
    - RAG_CACHE_TTL_SECONDS: TTL du cache (défaut: 3600)
    - RAG_CACHE_ENABLED: Activer/désactiver le cache (défaut: true)
    - RAG_CACHE_MAX_MEMORY_ITEMS: Taille max cache mémoire (défaut: 500)
    """
    # Lire config depuis env
    redis_url = redis_url or os.getenv('RAG_CACHE_REDIS_URL')
    ttl_seconds = ttl_seconds or int(os.getenv('RAG_CACHE_TTL_SECONDS', '3600'))
    max_memory_items = int(os.getenv('RAG_CACHE_MAX_MEMORY_ITEMS', '500'))
    enabled = os.getenv('RAG_CACHE_ENABLED', 'true').lower() in ('true', '1', 'yes')

    cache = RAGCache(
        redis_url=redis_url,
        ttl_seconds=ttl_seconds,
        max_memory_items=max_memory_items
    )

    cache.enabled = enabled

    if not enabled:
        logger.warning("[RAG Cache] Cache is DISABLED via RAG_CACHE_ENABLED")

    return cache


logger.info("[RAG Cache] Module initialized")
