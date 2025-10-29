"""
Redis Cache Manager - Memorystore Redis
Gère cache sessions, RAG results, agent contexts
"""
import redis.asyncio as aioredis
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import timedelta
import os

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Gère connexion Redis (Memorystore) pour cache applicatif.

    Use cases:
    - Cache résultats RAG (TTL 5 min)
    - Sessions utilisateurs (TTL 30 min)
    - Contexte agents (TTL 15 min)
    - Pub/Sub pour notifications real-time
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 10,
        decode_responses: bool = True
    ):
        # Connection config
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port
        self.db = db
        self.password = password or os.getenv("REDIS_PASSWORD")
        self.max_connections = max_connections
        self.decode_responses = decode_responses

        # Redis client
        self.client: Optional[aioredis.Redis] = None

        logger.info(f"RedisManager initialized (host={self.host}:{self.port}, db={self.db})")

    async def connect(self):
        """Crée connexion Redis avec pool"""
        if self.client is not None:
            logger.warning("Redis client already exists, skipping connect()")
            return

        try:
            # URL format: redis://[[username]:[password]]@host:port/db
            if self.password:
                url = f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
            else:
                url = f"redis://{self.host}:{self.port}/{self.db}"

            self.client = await aioredis.from_url(
                url,
                decode_responses=self.decode_responses,
                max_connections=self.max_connections,
                encoding="utf-8"
            )

            # Test connexion
            await self.client.ping()
            logger.info(f"Connected to Redis: {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            raise

    async def disconnect(self):
        """Ferme connexion Redis"""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Redis connection closed")

    async def close(self):
        """Alias pour compatibility"""
        await self.disconnect()

    def is_connected(self) -> bool:
        """Vérifie si connecté"""
        return self.client is not None

    async def health_check(self) -> bool:
        """Health check Redis"""
        try:
            response = await self.client.ping()
            return response is True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    # ==========================================
    # Basic Operations
    # ==========================================

    async def get(self, key: str) -> Optional[str]:
        """Get string value"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed for key={key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set string value with optional TTL.

        Args:
            key: Redis key
            value: String value
            ex: Expiration en secondes
            px: Expiration en millisecondes
            nx: Set only if key doesn't exist
            xx: Set only if key exists

        Returns:
            True si succès
        """
        try:
            result = await self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
            return result is True or result == "OK"
        except Exception as e:
            logger.error(f"Redis SET failed for key={key}: {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """Delete keys"""
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE failed for keys={keys}: {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            return await self.client.exists(*keys)
        except Exception as e:
            logger.error(f"Redis EXISTS failed for keys={keys}: {e}")
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key={key}: {e}")
            return False

    async def ttl(self, key: str) -> int:
        """Get TTL of key (seconds)"""
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis TTL failed for key={key}: {e}")
            return -2  # Key doesn't exist

    # ==========================================
    # JSON Operations (helper)
    # ==========================================

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON object"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON for key={key}: {e}")
        return None

    async def set_json(
        self,
        key: str,
        value: Dict[str, Any],
        ex: Optional[int] = None
    ) -> bool:
        """Set JSON object"""
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, ex=ex)
        except Exception as e:
            logger.error(f"Failed to encode JSON for key={key}: {e}")
            return False

    # ==========================================
    # Hash Operations
    # ==========================================

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value"""
        try:
            return await self.client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET failed for name={name} key={key}: {e}")
            return None

    async def hset(
        self,
        name: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        mapping: Optional[Dict] = None
    ) -> int:
        """Set hash field(s)"""
        try:
            return await self.client.hset(name, key, value, mapping=mapping)
        except Exception as e:
            logger.error(f"Redis HSET failed for name={name}: {e}")
            return 0

    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields"""
        try:
            return await self.client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL failed for name={name}: {e}")
            return {}

    # ==========================================
    # List Operations
    # ==========================================

    async def lpush(self, key: str, *values: str) -> int:
        """Push to list (left)"""
        try:
            return await self.client.lpush(key, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH failed for key={key}: {e}")
            return 0

    async def rpush(self, key: str, *values: str) -> int:
        """Push to list (right)"""
        try:
            return await self.client.rpush(key, *values)
        except Exception as e:
            logger.error(f"Redis RPUSH failed for key={key}: {e}")
            return 0

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        """Get list range"""
        try:
            return await self.client.lrange(key, start, stop)
        except Exception as e:
            logger.error(f"Redis LRANGE failed for key={key}: {e}")
            return []

    async def ltrim(self, key: str, start: int, stop: int) -> bool:
        """Trim list to range"""
        try:
            result = await self.client.ltrim(key, start, stop)
            return result is True or result == "OK"
        except Exception as e:
            logger.error(f"Redis LTRIM failed for key={key}: {e}")
            return False

    # ==========================================
    # Application-specific helpers
    # ==========================================

    async def cache_rag_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
        ttl: int = 300  # 5 minutes
    ) -> bool:
        """
        Cache résultats RAG pour requête.

        Args:
            query: Query text
            results: Liste documents/chunks
            ttl: TTL en secondes (default: 5 min)
        """
        key = f"rag:query:{hash(query)}"
        return await self.set_json(key, {"query": query, "results": results}, ex=ttl)

    async def get_rag_cache(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Récupère résultats RAG cachés"""
        key = f"rag:query:{hash(query)}"
        cached = await self.get_json(key)
        return cached.get("results") if cached else None

    async def store_session_context(
        self,
        session_id: str,
        context: Dict[str, Any],
        ttl: int = 1800  # 30 minutes
    ) -> bool:
        """
        Stocke contexte session (messages récents, état conversation).

        Args:
            session_id: Session UUID
            context: Contexte dict
            ttl: TTL en secondes (default: 30 min)
        """
        key = f"session:{session_id}:context"
        return await self.set_json(key, context, ex=ttl)

    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Récupère contexte session"""
        key = f"session:{session_id}:context"
        return await self.get_json(key)

    async def delete_session_context(self, session_id: str) -> bool:
        """Supprime contexte session (logout)"""
        key = f"session:{session_id}:context"
        deleted = await self.delete(key)
        return deleted > 0

    async def store_agent_state(
        self,
        session_id: str,
        agent_id: str,
        state: Dict[str, Any],
        ttl: int = 900  # 15 minutes
    ) -> bool:
        """
        Stocke état agent (mémoire courte, thinking, etc.).

        Args:
            session_id: Session UUID
            agent_id: Agent (anima, neo, nexus)
            state: État dict
            ttl: TTL en secondes (default: 15 min)
        """
        key = f"agent:{session_id}:{agent_id}:state"
        return await self.set_json(key, state, ex=ttl)

    async def get_agent_state(
        self,
        session_id: str,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Récupère état agent"""
        key = f"agent:{session_id}:{agent_id}:state"
        return await self.get_json(key)

    async def increment_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int = 60
    ) -> int:
        """
        Increment rate limit counter.

        Args:
            identifier: IP, user_id, etc.
            limit: Max requests
            window: Window en secondes

        Returns:
            Current count (after increment)
        """
        key = f"ratelimit:{identifier}"

        try:
            # Increment
            count = await self.client.incr(key)

            # Set expiration on first increment
            if count == 1:
                await self.client.expire(key, window)

            return count
        except Exception as e:
            logger.error(f"Rate limit increment failed for {identifier}: {e}")
            return 0

    async def check_rate_limit(self, identifier: str, limit: int) -> bool:
        """
        Check si rate limit atteint.

        Returns:
            True si autorisé, False si limite atteinte
        """
        key = f"ratelimit:{identifier}"
        count = await self.get(key)
        current = int(count) if count else 0
        return current < limit

    # ==========================================
    # Pub/Sub (notifications real-time)
    # ==========================================

    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel"""
        try:
            return await self.client.publish(channel, message)
        except Exception as e:
            logger.error(f"Redis PUBLISH failed for channel={channel}: {e}")
            return 0

    async def subscribe(self, *channels: str):
        """
        Subscribe to channels (returns async generator).

        Usage:
            async for message in redis.subscribe("notifications"):
                print(message)
        """
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
