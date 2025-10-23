# src/backend/features/memory/score_cache.py
# V1.0 - Cache LRU pour scores de mémoire pondérée
#
# Objectif: Améliorer performance en cachant les scores calculés
# pour éviter recalculs inutiles (notamment pour queries répétées).
#
# Stratégie:
# - Cache LRU avec TTL (Time To Live)
# - Clé = hash(query_text + entry_id + last_used_at)
# - Invalidation automatique si métadonnées changent
# - Métriques Prometheus (hit rate, evictions)
#
# Date création: 2025-10-21

import logging
import hashlib
from typing import Dict, Any, Optional, cast
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, REGISTRY

    def _get_cache_counter(name: str, doc: str) -> Counter:
        try:
            return Counter(name, doc, ['operation'], registry=REGISTRY)
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(name)
            if existing is None:
                raise
            return cast(Counter, existing)

    def _get_cache_gauge(name: str, doc: str) -> Gauge:
        try:
            return Gauge(name, doc, registry=REGISTRY)
        except ValueError:
            existing = getattr(REGISTRY, "_names_to_collectors", {}).get(name)
            if existing is None:
                raise
            return cast(Gauge, existing)

    SCORE_CACHE_OPS = _get_cache_counter(
        'score_cache_operations_total',
        'Opérations cache scores (hit/miss/set/evict)'
    )
    SCORE_CACHE_SIZE = _get_cache_gauge(
        'score_cache_size',
        'Taille actuelle cache scores'
    )
    PROMETHEUS_AVAILABLE = True

except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.debug("[ScoreCache] Prometheus client non disponible")


class ScoreCache:
    """
    Cache LRU pour scores de mémoire pondérée.

    Fonctionnalités:
    - Cache avec TTL (Time To Live)
    - Invalidation automatique
    - Métriques Prometheus
    - Thread-safe (via dict avec GIL Python)
    """

    def __init__(
        self,
        max_size: int = 10000,
        ttl_seconds: int = 3600
    ):
        """
        Initialize ScoreCache.

        Args:
            max_size: Taille max du cache (défaut: 10000)
            ttl_seconds: Durée de vie en secondes (défaut: 3600 = 1h)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        # Map entry_id -> set de clés de cache pour invalidation rapide
        self._entry_to_keys: Dict[str, set[str]] = {}
        logger.info(
            f"[ScoreCache] Initialisé (max_size={max_size}, ttl={ttl_seconds}s)"
        )

    def get(
        self,
        query_text: str,
        entry_id: str,
        last_used_at: str
    ) -> Optional[float]:
        """
        Récupère score depuis cache.

        Args:
            query_text: Texte de la requête
            entry_id: ID de l'entrée vectorielle
            last_used_at: Timestamp last_used_at de l'entrée

        Returns:
            Score pondéré ou None si cache miss
        """
        cache_key = self._compute_key(query_text, entry_id, last_used_at)

        cached = self._cache.get(cache_key)
        if not cached:
            if PROMETHEUS_AVAILABLE:
                SCORE_CACHE_OPS.labels(operation='miss').inc()
            return None

        # Vérifier TTL
        now = datetime.now(timezone.utc)
        expires_at = cached["expires_at"]
        if now > expires_at:
            # Expiré → evict
            del self._cache[cache_key]
            if PROMETHEUS_AVAILABLE:
                SCORE_CACHE_OPS.labels(operation='evict').inc()
                SCORE_CACHE_SIZE.set(len(self._cache))
            logger.debug(f"[ScoreCache] Cache expiré pour {cache_key[:16]}...")
            return None

        # Cache hit
        if PROMETHEUS_AVAILABLE:
            SCORE_CACHE_OPS.labels(operation='hit').inc()

        logger.debug(f"[ScoreCache] Cache hit pour {cache_key[:16]}...")
        return cast(float | None, cached["score"])

    def set(
        self,
        query_text: str,
        entry_id: str,
        last_used_at: str,
        score: float
    ) -> None:
        """
        Stocke score dans cache.

        Args:
            query_text: Texte de la requête
            entry_id: ID de l'entrée vectorielle
            last_used_at: Timestamp last_used_at
            score: Score pondéré à cacher
        """
        # Eviction LRU si cache plein
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        cache_key = self._compute_key(query_text, entry_id, last_used_at)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds)

        self._cache[cache_key] = {
            "score": score,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
            "entry_id": entry_id  # Stocker pour invalidation
        }

        # Associer clé à entry_id pour invalidation rapide
        if entry_id not in self._entry_to_keys:
            self._entry_to_keys[entry_id] = set()
        self._entry_to_keys[entry_id].add(cache_key)

        if PROMETHEUS_AVAILABLE:
            SCORE_CACHE_OPS.labels(operation='set').inc()
            SCORE_CACHE_SIZE.set(len(self._cache))

        logger.debug(f"[ScoreCache] Stocké {cache_key[:16]}... = {score:.4f}")

    def invalidate(self, entry_id: str) -> None:
        """
        Invalide toutes les entrées cache pour entry_id donné.

        Utilisé quand métadonnées changent (last_used_at, use_count).

        Args:
            entry_id: ID de l'entrée à invalider
        """
        # Récupérer toutes les clés associées à cet entry_id
        keys_to_delete = self._entry_to_keys.get(entry_id, set())

        for key in list(keys_to_delete):
            if key in self._cache:
                del self._cache[key]

        # Nettoyer la map entry_to_keys
        if entry_id in self._entry_to_keys:
            del self._entry_to_keys[entry_id]

        if PROMETHEUS_AVAILABLE:
            SCORE_CACHE_OPS.labels(operation='evict').inc(len(keys_to_delete))
            SCORE_CACHE_SIZE.set(len(self._cache))

        logger.debug(
            f"[ScoreCache] Invalidé {len(keys_to_delete)} entrées pour {entry_id}"
        )

    def clear(self) -> None:
        """Vide complètement le cache."""
        count = len(self._cache)
        self._cache.clear()
        self._entry_to_keys.clear()

        if PROMETHEUS_AVAILABLE:
            SCORE_CACHE_OPS.labels(operation='evict').inc(count)
            SCORE_CACHE_SIZE.set(0)

        logger.info(f"[ScoreCache] Cache vidé ({count} entrées)")

    def _compute_key(
        self,
        query_text: str,
        entry_id: str,
        last_used_at: str
    ) -> str:
        """
        Calcule clé de cache.

        Args:
            query_text: Texte de la requête
            entry_id: ID de l'entrée
            last_used_at: Timestamp last_used_at

        Returns:
            Clé de cache (hash SHA256)
        """
        # Clé = hash(query_text + entry_id + last_used_at)
        # Si last_used_at change, le cache est invalidé automatiquement
        raw_key = f"{query_text}|{entry_id}|{last_used_at}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def _evict_oldest(self) -> None:
        """
        Evict l'entrée la plus ancienne (LRU).

        Stratégie simple: supprimer entrée avec created_at le plus vieux.
        """
        if not self._cache:
            return

        # Trouver clé la plus ancienne
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k]["created_at"]
        )

        # Nettoyer la map entry_to_keys
        entry_id = self._cache[oldest_key].get("entry_id")
        if entry_id and entry_id in self._entry_to_keys:
            self._entry_to_keys[entry_id].discard(oldest_key)
            if not self._entry_to_keys[entry_id]:
                del self._entry_to_keys[entry_id]

        del self._cache[oldest_key]

        if PROMETHEUS_AVAILABLE:
            SCORE_CACHE_OPS.labels(operation='evict').inc()
            SCORE_CACHE_SIZE.set(len(self._cache))

        logger.debug(f"[ScoreCache] Evicted {oldest_key[:16]}... (LRU)")

    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne statistiques du cache.

        Returns:
            {
                "size": 1234,
                "max_size": 10000,
                "usage_percent": 12.34,
                "ttl_seconds": 3600
            }
        """
        size = len(self._cache)
        return {
            "size": size,
            "max_size": self.max_size,
            "usage_percent": round((size / self.max_size) * 100, 2) if self.max_size > 0 else 0,
            "ttl_seconds": self.ttl_seconds
        }
