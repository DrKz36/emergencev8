# src/backend/core/database/schema.py
# V6.0 - Mémoire persistante : ajoute 'is_consolidated' à sessions + table 'knowledge_concepts'.
import logging
import os
from datetime import datetime, timezone
from typing import List
from .manager import DatabaseManager

logger = logging.getLogger(__name__)

TABLE_DEFINITIONS: List[str] = [
    # --- Costs ---
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

    # --- Documents ---
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

    # --- Document chunks ---
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    """,

    # --- Sessions (mémoire brut de session) ---
    # Ajout de 'is_consolidated' (DEFAULT 0) pour le suivi de consolidation par le MemoryGardener.
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        session_data TEXT,
        summary TEXT,
        extracted_concepts TEXT,
        extracted_entities TEXT,
        is_consolidated INTEGER NOT NULL DEFAULT 0
    );
    """,

    # --- Migrations bookkeeping ---
    """
    CREATE TABLE IF NOT EXISTS migrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE NOT NULL,
        applied_at TEXT NOT NULL
    );
    """,

    # --- Monitoring ---
    """
    CREATE TABLE IF NOT EXISTS monitoring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        event_details TEXT,
        timestamp TEXT NOT NULL
    );
    """,

    # --- Knowledge base (concepts consolidés) ---
    # NOTE: les vecteurs sont gérés par ChromaDB ; on conserve ici un index sémantique minimal.
    """
    CREATE TABLE IF NOT EXISTS knowledge_concepts (
        id TEXT PRIMARY KEY,
        concept TEXT NOT NULL,
        description TEXT,
        categories TEXT,          -- JSON array (TEXT)
        vector_id TEXT,           -- id correspondant dans le store vectoriel (Chroma)
        created_at TEXT NOT NULL
    );
    """
]

async def create_tables(db_manager: DatabaseManager):
    logger.info("Vérification et création des tables de la base de données.")
    for table_sql in TABLE_DEFINITIONS:
        if table_sql.strip():
            await db_manager.execute(table_sql)
    logger.info("Toutes les tables ont été créées ou existent déjà.")

async def _ensure_schema_upgrades(db_manager: DatabaseManager):
    """Applique les petites migrations idempotentes nécessaires sans fichiers .sql.
    - Ajoute la colonne sessions.is_consolidated si absente.
    - Crée knowledge_concepts si absent (déjà couvert par CREATE IF NOT EXISTS).
    """
    # 1) Ajouter 'is_consolidated' à sessions si manquant
    try:
        cols = await db_manager.fetch_all("PRAGMA table_info(sessions);")
        colnames = {row[1] if isinstance(row, tuple) else row["name"] for row in cols}
        if "is_consolidated" not in colnames:
            logger.warning("Colonne 'is_consolidated' absente de 'sessions' -> ALTER TABLE en cours…")
            await db_manager.execute("ALTER TABLE sessions ADD COLUMN is_consolidated INTEGER NOT NULL DEFAULT 0;")
            logger.info("Colonne 'is_consolidated' ajoutée avec succès.")
    except Exception as e:
        logger.error(f"Échec lors de l'assurance du schéma 'sessions.is_consolidated': {e}", exc_info=True)
        raise

async def run_migrations(db_manager: DatabaseManager, migrations_dir: str):
    """Conserve le mécanisme existant si des fichiers .sql sont présents."""
    logger.info("Démarrage du processus de migration de la base de données…")
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
    # Assure les petites mises à niveau sans fichiers de migration.
    await _ensure_schema_upgrades(db_manager)
    # Puis exécute d'éventuels scripts .sql existants
    await run_migrations(db_manager, migrations_dir)
    logger.info("Initialisation de la base de données terminée.")
