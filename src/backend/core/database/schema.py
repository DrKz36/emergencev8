# src/backend/core/database/schema.py
# V6.1 - Backcompat robuste: ajout conditionnel de colonnes legacy + (re)création d'index.
import logging
import os
from datetime import datetime, timezone
from .manager import DatabaseManager

logger = logging.getLogger(__name__)

TABLE_DEFINITIONS = [
    # -- coûts --
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
    # -- documents --
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
    # -- sessions (existant) --
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
    # -- threads/messages/thread_docs (NOUVEAU V6) --
    """
    CREATE TABLE IF NOT EXISTS threads (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('chat','debate')),
        title TEXT,
        agent_id TEXT,
        meta TEXT,
        archived INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_threads_user_type_updated
    ON threads(user_id, type, updated_at DESC);
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        thread_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('user','assistant','system','note')),
        agent_id TEXT,
        content TEXT NOT NULL,
        tokens INTEGER,
        meta TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_thread_created
    ON messages(thread_id, created_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS thread_docs (
        thread_id TEXT NOT NULL,
        doc_id INTEGER NOT NULL,
        weight REAL DEFAULT 1.0,
        last_used_at TEXT,
        PRIMARY KEY (thread_id, doc_id),
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    """,
    # -- migrations & monitoring (existant) --
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

# ---------------------- Helpers rétro-compatibilité ---------------------- #
async def _get_columns(db: DatabaseManager, table: str):
    try:
        rows = await db.fetch_all(f"PRAGMA table_info({table})")
        return {r["name"] for r in rows} if rows else set()
    except Exception:
        return set()

async def _add_column_if_missing(db: DatabaseManager, table: str, col_name: str, col_def: str):
    cols = await _get_columns(db, table)
    if col_name not in cols:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
        logger.info(f"[DDL] Colonne ajoutée: {table}.{col_name} {col_def}")

async def _ensure_messages_backward_compat(db: DatabaseManager):
    """
    Pour les bases locales créées avant V6 (messages sans thread_id/created_at).
    On ajoute les colonnes manquantes (nullable), puis on (re)crée l'index.
    """
    cols = await _get_columns(db, "messages")
    if not cols:
        return  # table inexistante → le DDL V6 la créera

    # Colonnes requises par V6
    await _add_column_if_missing(db, "messages", "thread_id", "TEXT")
    await _add_column_if_missing(db, "messages", "role", "TEXT")
    await _add_column_if_missing(db, "messages", "agent_id", "TEXT")
    await _add_column_if_missing(db, "messages", "content", "TEXT")
    await _add_column_if_missing(db, "messages", "tokens", "INTEGER")
    await _add_column_if_missing(db, "messages", "meta", "TEXT")
    await _add_column_if_missing(db, "messages", "created_at", "TEXT")

    # Index après rattrapage
    try:
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_thread_created
            ON messages(thread_id, created_at)
        """)
    except Exception as e:
        logger.warning(f"[DDL] Index idx_messages_thread_created non créé: {e}")

# ------------------------------------------------------------------------ #

async def create_tables(db_manager: DatabaseManager):
    logger.info("Vérification et création des tables de la base de données...")
    errors = []
    for table_sql in TABLE_DEFINITIONS:
        stmt = table_sql.strip()
        if not stmt:
            continue
        try:
            await db_manager.execute(stmt)
        except Exception as e:
            # On loggue mais on continue → backcompat appliquée ensuite.
            preview = " ".join(stmt.split())[:90]
            logger.warning(f"[DDL] Instruction ignorée (à rattraper): {preview} — {e}")
            errors.append((preview, str(e)))

    # Backcompat ciblée messages (legacy sans thread_id/created_at)
    try:
        await _ensure_messages_backward_compat(db_manager)
    except Exception as e:
        logger.error(f"[DDL] Échec backcompat 'messages': {e}", exc_info=True)
        raise

    logger.info("Toutes les tables/index requis sont en place (avec backcompat au besoin).")

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
