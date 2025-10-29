"""
DatabaseManager PostgreSQL - Migration depuis SQLite
Utilise asyncpg + pgvector pour embeddings
"""
import asyncpg  # type: ignore[import-not-found]
import logging
from typing import Optional, List, Dict, Any, Tuple, AsyncIterator, cast
from contextlib import asynccontextmanager
import os

try:
    from pgvector.asyncpg import register_vector  # type: ignore[import-not-found]
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    register_vector = None  # Placeholder pour mypy
    logging.warning("pgvector not installed. Vector operations will fail.")

logger = logging.getLogger(__name__)


class PostgreSQLManager:
    """
    Gère la connexion asyncpg vers Cloud SQL PostgreSQL.
    Compatible avec pgvector pour embeddings (remplace Chroma).
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 5432,
        database: str = "emergence",
        user: str = "emergence-app",
        password: Optional[str] = None,
        min_size: int = 2,
        max_size: int = 10,
        command_timeout: float = 60.0,
        unix_socket: Optional[str] = None,  # Pour Cloud SQL Unix socket
    ):
        # Configuration connexion
        self.host = host or os.getenv("CLOUD_SQL_HOST")
        self.port = port
        self.database = database
        self.user = user
        self.password = password or os.getenv("DB_PASSWORD")
        self.unix_socket = unix_socket or os.getenv("CLOUD_SQL_UNIX_SOCKET")

        # Pool config
        self.min_size = min_size
        self.max_size = max_size
        self.command_timeout = command_timeout

        # Connection pool
        self.pool: Optional[asyncpg.Pool] = None

        logger.info(
            f"PostgreSQLManager initialized (host={self.host}, database={self.database}, "
            f"pool={self.min_size}-{self.max_size})"
        )

    async def connect(self):
        """Crée le pool de connexions asyncpg"""
        if self.pool is not None:
            logger.warning("Pool already exists, skipping connect()")
            return

        try:
            # Cloud SQL peut utiliser Unix socket ou TCP
            if self.unix_socket:
                logger.info(f"Connecting via Unix socket: {self.unix_socket}")
                self.pool = await asyncpg.create_pool(
                    host=self.unix_socket,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=self.command_timeout,
                    server_settings={
                        "application_name": "emergence-app"
                    }
                )
            else:
                logger.info(f"Connecting via TCP: {self.host}:{self.port}")
                self.pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=self.command_timeout,
                    server_settings={
                        "application_name": "emergence-app"
                    }
                )

            # Register pgvector extension
            if PGVECTOR_AVAILABLE:
                await register_vector(self.pool)
                logger.info("pgvector registered successfully")

            logger.info(f"asyncpg pool created (min={self.min_size}, max={self.max_size})")

        except Exception as e:
            logger.error(f"Failed to create asyncpg pool: {e}", exc_info=True)
            raise

    async def disconnect(self):
        """Ferme le pool de connexions"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("asyncpg pool closed")

    async def close(self):
        """Alias pour compatibility avec tests"""
        await self.disconnect()

    def is_connected(self) -> bool:
        """Vérifie si le pool est actif"""
        return self.pool is not None and not self.pool._closed

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Any]:  # asyncpg.Connection
        """
        Context manager pour acquérir une connexion depuis le pool.

        Usage:
            async with db.acquire() as conn:
                result = await conn.fetch("SELECT * FROM users")
        """
        if not self.is_connected():
            await self.connect()

        if self.pool is None:
            raise RuntimeError("Pool not initialized. Call connect() first.")

        async with self.pool.acquire() as connection:
            yield connection

    async def execute(
        self,
        query: str,
        *args: Any,
        commit: bool = True
    ) -> str:
        """
        Exécute une requête SQL (INSERT, UPDATE, DELETE).

        Args:
            query: Requête SQL avec $1, $2... placeholders
            *args: Arguments pour les placeholders
            commit: Auto-commit (toujours True pour PostgreSQL, paramètre pour compat SQLite)

        Returns:
            Status string (ex: "INSERT 0 1")
        """
        async with self.acquire() as conn:
            try:
                result = await conn.execute(query, *args, timeout=self.command_timeout)
                return cast(str, result)
            except Exception as e:
                logger.error(f"Execute failed: {e}\nQuery: {query}\nArgs: {args}", exc_info=True)
                raise

    async def fetch_one(
        self,
        query: str,
        *args: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch une seule ligne (équivalent fetchone()).

        Returns:
            Dict ou None si pas de résultat
        """
        async with self.acquire() as conn:
            try:
                row = await conn.fetchrow(query, *args, timeout=self.command_timeout)
                return dict(row) if row else None
            except Exception as e:
                logger.error(f"Fetch one failed: {e}\nQuery: {query}", exc_info=True)
                raise

    async def fetch_all(
        self,
        query: str,
        *args: Any
    ) -> List[Dict[str, Any]]:
        """
        Fetch toutes les lignes (équivalent fetchall()).

        Returns:
            Liste de dicts
        """
        async with self.acquire() as conn:
            try:
                rows = await conn.fetch(query, *args, timeout=self.command_timeout)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Fetch all failed: {e}\nQuery: {query}", exc_info=True)
                raise

    async def fetch_val(
        self,
        query: str,
        *args: Any,
        column: int = 0
    ) -> Any:
        """
        Fetch une seule valeur (équivalent fetchval()).

        Args:
            column: Index de la colonne (0 par défaut)

        Returns:
            Valeur ou None
        """
        async with self.acquire() as conn:
            try:
                return await conn.fetchval(query, *args, column=column, timeout=self.command_timeout)
            except Exception as e:
                logger.error(f"Fetch val failed: {e}\nQuery: {query}", exc_info=True)
                raise

    async def execute_many(
        self,
        query: str,
        args_list: List[Tuple[Any, ...]]
    ) -> None:
        """
        Execute batch insert/update (équivalent executemany()).

        Args:
            query: Requête SQL avec $1, $2... placeholders
            args_list: Liste de tuples d'arguments
        """
        async with self.acquire() as conn:
            try:
                await conn.executemany(query, args_list, timeout=self.command_timeout * len(args_list))
                logger.debug(f"Batch executed: {len(args_list)} rows")
            except Exception as e:
                logger.error(f"Execute many failed: {e}\nQuery: {query}", exc_info=True)
                raise

    # ==========================================
    # Vector Search Operations (pgvector)
    # ==========================================

    async def search_similar_vectors(
        self,
        table: str,
        embedding_column: str,
        query_embedding: List[float],
        user_id: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche vectorielle avec pgvector (cosine similarity).

        Args:
            table: Nom de la table (ex: "document_chunks")
            embedding_column: Nom colonne embedding (ex: "embedding")
            query_embedding: Vecteur requête (liste floats)
            user_id: Filter par user
            limit: Nb résultats max
            similarity_threshold: Seuil similarité (0-1)
            filters: Filtres additionnels (dict clé->valeur)

        Returns:
            Liste résultats avec score similarité
        """
        if not PGVECTOR_AVAILABLE:
            raise RuntimeError("pgvector extension not available")

        # Construction requête dynamique
        where_clauses = ["user_id = $2"]
        params = [query_embedding, user_id]
        param_idx = 3

        if filters:
            for key, value in filters.items():
                where_clauses.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1

        where_sql = " AND ".join(where_clauses)

        query = f"""
        SELECT
            *,
            (1 - ({embedding_column} <=> $1::vector))::DECIMAL AS similarity
        FROM {table}
        WHERE {where_sql}
            AND (1 - ({embedding_column} <=> $1::vector)) >= {similarity_threshold}
        ORDER BY {embedding_column} <=> $1::vector
        LIMIT {limit}
        """

        try:
            rows = await self.fetch_all(query, *params)
            logger.debug(f"Vector search returned {len(rows)} results (threshold={similarity_threshold})")
            return rows
        except Exception as e:
            logger.error(f"Vector search failed: {e}", exc_info=True)
            raise

    async def insert_vector(
        self,
        table: str,
        data: Dict[str, Any],
        embedding_column: str = "embedding"
    ) -> str:
        """
        Insert row avec embedding vector.

        Args:
            table: Nom table
            data: Dict colonnes->valeurs (inclut embedding)
            embedding_column: Nom colonne embedding

        Returns:
            UUID inserted row
        """
        if not PGVECTOR_AVAILABLE:
            raise RuntimeError("pgvector extension not available")

        columns = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]

        # Cast embedding as vector
        for i, col in enumerate(columns):
            if col == embedding_column:
                placeholders[i] = f"${i+1}::vector"

        query = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({', '.join(placeholders)})
        RETURNING id
        """

        values = list(data.values())

        try:
            result_id = await self.fetch_val(query, *values)
            logger.debug(f"Inserted vector into {table}: {result_id}")
            return str(result_id)
        except Exception as e:
            logger.error(f"Insert vector failed: {e}", exc_info=True)
            raise

    # ==========================================
    # Transaction Support
    # ==========================================

    @asynccontextmanager
    async def transaction(self):
        """
        Context manager pour transactions explicites.

        Usage:
            async with db.transaction() as tx:
                await tx.execute("INSERT ...")
                await tx.execute("UPDATE ...")
                # Auto-commit si pas d'exception
        """
        async with self.acquire() as conn:
            async with conn.transaction():
                yield conn

    # ==========================================
    # Health Check
    # ==========================================

    async def health_check(self) -> bool:
        """Vérifie que la DB est accessible"""
        try:
            result = await self.fetch_val("SELECT 1")
            return cast(bool, result == 1)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_version(self) -> str:
        """Retourne version PostgreSQL"""
        try:
            version = await self.fetch_val("SELECT version()")
            return cast(str, version)
        except Exception as e:
            logger.error(f"Get version failed: {e}")
            return "unknown"
