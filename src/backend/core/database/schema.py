# src/backend/core/database/schema.py
# V5.0 - FIX: Schéma de la table 'sessions' entièrement resynchronisé.
import logging
import os
from datetime import datetime, timezone
from .manager import DatabaseManager

logger = logging.getLogger(__name__)

TABLE_DEFINITIONS = [
    """
    CREATE TABLE IF NOT EXISTS costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        agent TEXT NOT NULL,
        model TEXT NOT NULL,
        input_tokens INTEGER,
        output_tokens INTEGER,
        total_cost REAL NOT NULL,
        feature TEXT NOT NULL CHECK(feature IN ('chat', 'document_processing', 'debate'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        status TEXT NOT NULL,
        char_count INTEGER,
        chunk_count INTEGER,
        error_message TEXT,
        uploaded_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    """,
    # --- CORRECTION V5.0 - SCHÉMA 'SESSIONS' FINAL ---
    # Ce schéma est maintenant aligné avec les requêtes (queries.py)
    # et inclut toutes les colonnes nécessaires.
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        session_data TEXT,
        summary TEXT,
        extracted_concepts TEXT,
        extracted_entities TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE NOT NULL,
        applied_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS monitoring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        event_details TEXT,
        timestamp TEXT NOT NULL
    );
    """
]

async def create_tables(db_manager: DatabaseManager):
    logger.info("Vérification et création des tables de la base de données...")
    for table_sql in TABLE_DEFINITIONS:
        if table_sql.strip():
            await db_manager.execute(table_sql)
    logger.info("Toutes les tables ont été créées ou existent déjà.")

async def run_migrations(db_manager: DatabaseManager, migrations_dir: str):
    logger.info("Démarrage du processus de migration de la base de données...")
    await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            applied_at TEXT NOT NULL
        );
    """)
    res = await db_manager.fetch_all("SELECT filename FROM migrations")
    applied_migrations = {row['filename'] for row in res}
    if not os.path.exists(migrations_dir):
        logger.warning(f"Le répertoire des migrations '{migrations_dir}' n'existe pas. Aucune migration à appliquer.")
        return
    migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])
    for filename in migration_files:
        if filename not in applied_migrations:
            logger.info(f"Application de la migration: {filename}")
            try:
                filepath = os.path.join(migrations_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                if sql_script.strip():
                    for statement in sql_script.split(';'):
                        if statement.strip():
                            await db_manager.execute(statement)
                await db_manager.execute(
                    "INSERT INTO migrations (filename, applied_at) VALUES (?, ?)",
                    (filename, datetime.now(timezone.utc).isoformat())
                )
                logger.info(f"Migration {filename} appliquée avec succès.")
            except Exception as e:
                logger.error(f"Échec de l'application de la migration {filename}: {e}", exc_info=True)
                raise
        else:
            logger.debug(f"Migration {filename} déjà appliquée, ignorée.")
    logger.info("Processus de migration terminé.")

async def initialize_database(db_manager: DatabaseManager, migrations_dir: str):
    await db_manager.connect()
    await create_tables(db_manager)
    await run_migrations(db_manager, migrations_dir)
    logger.info("Initialisation de la base de données terminée.")
