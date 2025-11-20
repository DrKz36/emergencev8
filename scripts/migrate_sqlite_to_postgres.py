"""
Script de migration SQLite → PostgreSQL
Migre toutes les données de l'app ÉMERGENCE vers Cloud SQL
"""

import asyncio
import aiosqlite
import logging
from pathlib import Path
import sys
from typing import List, Dict, Any
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from backend.core.database.manager_postgres import PostgreSQLManager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Tables à migrer (ordre important pour FK)
TABLES_ORDER = [
    "auth_allowlist",
    "auth_sessions",
    "auth_audit_log",
    "sessions",
    "messages",
    "documents",
    "document_chunks",  # NOUVEAU: chunks avec embeddings
    "memory_facts",  # NOUVEAU: mémoire avec embeddings
    "costs",
    "debates",
    "api_usage",
    "benchmark_runs",
]


class SQLiteToPostgresMigrator:
    """Migre données SQLite vers PostgreSQL"""

    def __init__(
        self,
        sqlite_path: str,
        postgres_manager: PostgreSQLManager,
        batch_size: int = 1000,
    ):
        self.sqlite_path = sqlite_path
        self.pg = postgres_manager
        self.batch_size = batch_size
        self.stats = {table: 0 for table in TABLES_ORDER}

    async def connect_all(self):
        """Connecte SQLite et PostgreSQL"""
        logger.info(f"Connecting to SQLite: {self.sqlite_path}")
        self.sqlite_conn = await aiosqlite.connect(self.sqlite_path)
        self.sqlite_conn.row_factory = aiosqlite.Row

        logger.info("Connecting to PostgreSQL...")
        await self.pg.connect()

        # Vérifier connexion
        pg_version = await self.pg.get_version()
        logger.info(f"PostgreSQL version: {pg_version}")

    async def close_all(self):
        """Ferme connexions"""
        if self.sqlite_conn:
            await self.sqlite_conn.close()
        await self.pg.disconnect()

    async def migrate_table(self, table_name: str):
        """
        Migre une table SQLite → PostgreSQL.

        Gère les conversions:
        - INTEGER id → UUID (génération automatique côté PG)
        - DATETIME strings → TIMESTAMP WITH TIME ZONE
        - JSON strings → JSONB
        """
        logger.info(f"Migrating table: {table_name}")

        # Récupérer toutes les rows SQLite
        cursor = await self.sqlite_conn.execute(f"SELECT * FROM {table_name}")
        rows = await cursor.fetchall()

        if not rows:
            logger.info(f"  ✓ {table_name}: 0 rows (table vide)")
            return

        # Récupérer noms colonnes
        column_names = [desc[0] for desc in cursor.description]

        # Conversion rows
        pg_rows = []
        for row in rows:
            row_dict = dict(zip(column_names, row))
            pg_row = self._convert_row(table_name, row_dict)
            pg_rows.append(pg_row)

        # Insert batch dans PostgreSQL
        await self._insert_batch(table_name, pg_rows, column_names)

        self.stats[table_name] = len(pg_rows)
        logger.info(f"  ✓ {table_name}: {len(pg_rows)} rows migrated")

    def _convert_row(self, table_name: str, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit row SQLite → PostgreSQL.

        Conversions:
        - Supprime colonne 'id' (UUID auto-généré côté PG)
        - Convertit datetime strings → datetime objects
        - Parse JSON strings → dicts
        """
        converted = {}

        for key, value in row.items():
            # Skip 'id' column (UUID auto-generated in PostgreSQL)
            if key == "id":
                continue

            # Convert datetime strings
            if value and isinstance(value, str):
                # Try parsing ISO datetime
                if "T" in value or (":" in value and "-" in value):
                    try:
                        converted[key] = datetime.fromisoformat(
                            value.replace("Z", "+00:00")
                        )
                        continue
                    except ValueError:
                        pass

                # Try parsing JSON
                if value.startswith("{") or value.startswith("["):
                    try:
                        converted[key] = json.loads(value)
                        continue
                    except json.JSONDecodeError:
                        pass

            # Default: keep as-is
            converted[key] = value

        return converted

    async def _insert_batch(
        self, table_name: str, rows: List[Dict], column_names: List[str]
    ):
        """Insert batch de rows dans PostgreSQL"""
        if not rows:
            return

        # Filter out 'id' column (auto-generated)
        insert_columns = [col for col in column_names if col != "id"]

        # Build INSERT query
        placeholders = ", ".join([f"${i + 1}" for i in range(len(insert_columns))])
        query = f"""
        INSERT INTO {table_name} ({", ".join(insert_columns)})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
        """

        # Prepare values
        values_list = [tuple(row.get(col) for col in insert_columns) for row in rows]

        # Execute batch
        try:
            await self.pg.execute_many(query, values_list)
        except Exception as e:
            logger.error(f"Batch insert failed for {table_name}: {e}")
            # Fallback: insert row by row pour identifier problème
            logger.warning(f"Falling back to row-by-row insert for {table_name}...")
            for i, values in enumerate(values_list):
                try:
                    await self.pg.execute(query, *values)
                except Exception as row_error:
                    logger.error(
                        f"Failed to insert row {i} in {table_name}: {row_error}"
                    )
                    logger.error(f"Row data: {rows[i]}")

    async def migrate_all(self):
        """Migre toutes les tables dans l'ordre"""
        logger.info("=" * 60)
        logger.info("Starting SQLite → PostgreSQL migration")
        logger.info("=" * 60)

        await self.connect_all()

        try:
            for table_name in TABLES_ORDER:
                await self.migrate_table(table_name)

        finally:
            await self.close_all()

        # Print stats
        logger.info("=" * 60)
        logger.info("Migration complete!")
        logger.info("=" * 60)
        total_rows = 0
        for table_name, count in self.stats.items():
            logger.info(f"  {table_name:30} {count:>8} rows")
            total_rows += count
        logger.info(f"  {'TOTAL':30} {total_rows:>8} rows")

    async def verify_migration(self):
        """Vérifie que la migration est correcte (compare counts)"""
        logger.info("=" * 60)
        logger.info("Verifying migration...")
        logger.info("=" * 60)

        await self.connect_all()

        try:
            discrepancies = []

            for table_name in TABLES_ORDER:
                # Count SQLite
                cursor = await self.sqlite_conn.execute(
                    f"SELECT COUNT(*) FROM {table_name}"
                )
                sqlite_count = (await cursor.fetchone())[0]

                # Count PostgreSQL
                pg_count = await self.pg.fetch_val(f"SELECT COUNT(*) FROM {table_name}")

                match = "✓" if sqlite_count == pg_count else "✗"
                logger.info(
                    f"  {match} {table_name:30} SQLite: {sqlite_count:>6}  PostgreSQL: {pg_count:>6}"
                )

                if sqlite_count != pg_count:
                    discrepancies.append((table_name, sqlite_count, pg_count))

            if discrepancies:
                logger.warning("=" * 60)
                logger.warning("DISCREPANCIES FOUND:")
                for table_name, sqlite_count, pg_count in discrepancies:
                    logger.warning(
                        f"  {table_name}: SQLite={sqlite_count} PostgreSQL={pg_count} (diff={sqlite_count - pg_count})"
                    )
            else:
                logger.info("=" * 60)
                logger.info("✓ All tables verified successfully!")

        finally:
            await self.close_all()


async def main():
    """Point d'entrée migration"""
    import os
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate ÉMERGENCE SQLite → PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        default="src/backend/data/db/emergence_v7.db",
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify migration (don't migrate)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for inserts (default: 1000)",
    )

    args = parser.parse_args()

    # PostgreSQL connection from env vars
    pg_manager = PostgreSQLManager(
        host=os.getenv("CLOUD_SQL_HOST"),
        port=int(os.getenv("CLOUD_SQL_PORT", "5432")),
        database=os.getenv("CLOUD_SQL_DATABASE", "emergence"),
        user=os.getenv("CLOUD_SQL_USER", "emergence-app"),
        password=os.getenv("DB_PASSWORD"),
        unix_socket=os.getenv("CLOUD_SQL_UNIX_SOCKET"),  # For Cloud SQL Proxy
    )

    migrator = SQLiteToPostgresMigrator(
        sqlite_path=args.sqlite_path,
        postgres_manager=pg_manager,
        batch_size=args.batch_size,
    )

    if args.verify_only:
        await migrator.verify_migration()
    else:
        await migrator.migrate_all()
        logger.info("\nRunning verification...")
        await migrator.verify_migration()


if __name__ == "__main__":
    asyncio.run(main())
