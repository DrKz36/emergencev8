# src/backend/core/database/schema.py
# V6.1 - Backcompat robuste: ajout conditionnel de colonnes legacy + (re)création d'index.
import logging
import os
from datetime import datetime, timezone
from typing import Iterable

from .manager import DatabaseManager
from .backfill import run_user_scope_backfill

logger = logging.getLogger(__name__)

TABLE_DEFINITIONS = [
    # -- coûts --
    """
    CREATE TABLE IF NOT EXISTS costs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        session_id TEXT,
        user_id TEXT,
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
        uploaded_at TEXT NOT NULL,
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_documents_session_uploaded
    ON documents(session_id, uploaded_at DESC);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_documents_user_uploaded
    ON documents(user_id, uploaded_at DESC);
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_document_chunks_session
    ON document_chunks(session_id, document_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_document_chunks_user
    ON document_chunks(user_id, document_id);
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
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('chat','debate')),
        title TEXT,
        agent_id TEXT,
        meta TEXT,
        archived INTEGER NOT NULL DEFAULT 0,
        archival_reason TEXT,
        archived_at TEXT,
        last_message_at TEXT,
        message_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_threads_user_type_updated
    ON threads(user_id, type, updated_at DESC);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_threads_session_updated
    ON threads(session_id, updated_at DESC);
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
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_thread_created
    ON messages(thread_id, created_at);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_session_created
    ON messages(session_id, created_at);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_user_created
    ON messages(user_id, created_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS thread_docs (
        thread_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        doc_id INTEGER NOT NULL,
        weight REAL DEFAULT 1.0,
        last_used_at TEXT,
        PRIMARY KEY (thread_id, doc_id),
        FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE,
        FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_thread_docs_session
    ON thread_docs(session_id, thread_id, doc_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_thread_docs_user
    ON thread_docs(user_id, thread_id, doc_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_allowlist (
        email TEXT PRIMARY KEY,
        role TEXT NOT NULL CHECK(role IN ('member','admin')) DEFAULT 'member',
        note TEXT,
        created_at TEXT NOT NULL,
        created_by TEXT,
        revoked_at TEXT,
        revoked_by TEXT,
        password_hash TEXT,
        password_updated_at TEXT,
        password_must_reset INTEGER DEFAULT 1
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_auth_allowlist_active
    ON auth_allowlist(revoked_at);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_auth_allowlist_password_updated
    ON auth_allowlist(password_updated_at DESC);
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_sessions (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        ip_address TEXT,
        user_id TEXT,
        user_agent TEXT,
        issued_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        revoked_at TEXT,
        revoked_by TEXT,
        metadata TEXT
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_auth_sessions_email
    ON auth_sessions(email);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_auth_sessions_active
    ON auth_sessions(email, expires_at)
    WHERE revoked_at IS NULL;
    """,
    """
    CREATE TABLE IF NOT EXISTS auth_audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        email TEXT,
        actor TEXT,
        metadata TEXT,
        created_at TEXT NOT NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_auth_audit_created
    ON auth_audit_log(created_at DESC);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_auth_audit_event
    ON auth_audit_log(event_type);
    """,
    # -- password reset tokens --
    """
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        token TEXT PRIMARY KEY,
        email TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        used_at TEXT,
        FOREIGN KEY (email) REFERENCES auth_allowlist(email) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_email
    ON password_reset_tokens(email);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at
    ON password_reset_tokens(expires_at);
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

INDEX_DEFINITIONS = {
    "threads": [
        (
            "idx_threads_session_updated",
            """
            CREATE INDEX IF NOT EXISTS idx_threads_session_updated
            ON threads(session_id, updated_at DESC)
            """,
        ),
        (
            "idx_threads_user_type_updated",
            """
            CREATE INDEX IF NOT EXISTS idx_threads_user_type_updated
            ON threads(user_id, type, updated_at DESC)
            """,
        ),
    ],
    "messages": [
        (
            "idx_messages_session_created",
            """
            CREATE INDEX IF NOT EXISTS idx_messages_session_created
            ON messages(session_id, created_at)
            """,
        ),
        (
            "idx_messages_user_created",
            """
            CREATE INDEX IF NOT EXISTS idx_messages_user_created
            ON messages(user_id, created_at)
            """,
        ),
    ],
    "thread_docs": [
        (
            "idx_thread_docs_session",
            """
            CREATE INDEX IF NOT EXISTS idx_thread_docs_session
            ON thread_docs(session_id, thread_id, doc_id)
            """,
        ),
        (
            "idx_thread_docs_user",
            """
            CREATE INDEX IF NOT EXISTS idx_thread_docs_user
            ON thread_docs(user_id, thread_id, doc_id)
            """,
        ),
    ],
    "documents": [
        (
            "idx_documents_session_uploaded",
            """
            CREATE INDEX IF NOT EXISTS idx_documents_session_uploaded
            ON documents(session_id, uploaded_at DESC)
            """,
        ),
        (
            "idx_documents_user_uploaded",
            """
            CREATE INDEX IF NOT EXISTS idx_documents_user_uploaded
            ON documents(user_id, uploaded_at DESC)
            """,
        ),
    ],
    "document_chunks": [
        (
            "idx_document_chunks_session",
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_session
            ON document_chunks(session_id, document_id)
            """,
        ),
        (
            "idx_document_chunks_user",
            """
            CREATE INDEX IF NOT EXISTS idx_document_chunks_user
            ON document_chunks(user_id, document_id)
            """,
        ),
    ],
}


async def _log_index_dump(db: DatabaseManager, tables: Iterable[str]) -> None:
    for table in tables:
        try:
            rows = await db.fetch_all(f"PRAGMA index_list('{table}')")
        except Exception as exc:  # pragma: no cover - logging aid
            logger.debug(f"[DDL] Unable to dump index_list for {table}: {exc}")
            continue

        payload = []
        for row in rows:
            row_dict = dict(row)
            payload.append(
                {
                    "seq": row_dict.get("seq"),
                    "name": row_dict.get("name"),
                    "unique": row_dict.get("unique"),
                    "origin": row_dict.get("origin"),
                    "partial": row_dict.get("partial"),
                }
            )
        logger.info("[DDL] index_list(%s) -> %s", table, payload)




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
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}", commit=True)
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
    await _add_column_if_missing(db, "messages", "session_id", "TEXT")

    # Index après rattrapage
    try:
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_thread_created
            ON messages(thread_id, created_at)
        """, commit=True)
    except Exception as e:
        logger.warning(f"[DDL] Index idx_messages_thread_created non créé: {e}")


async def _ensure_allowlist_password_columns(db: DatabaseManager):
    """Ensure legacy allowlist tables get password columns and index."""
    cols = await _get_columns(db, "auth_allowlist")
    if not cols:
        return

    await _add_column_if_missing(db, "auth_allowlist", "password_hash", "TEXT")
    await _add_column_if_missing(db, "auth_allowlist", "password_updated_at", "TEXT")
    await _add_column_if_missing(db, "auth_allowlist", "password_must_reset", "INTEGER DEFAULT 1")

    try:
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_auth_allowlist_password_updated
            ON auth_allowlist(password_updated_at DESC)
        """, commit=True)
    except Exception as e:
        logger.warning(f"[DDL] Index idx_auth_allowlist_password_updated non cree: {e}")

    # Set password_must_reset to 0 for existing users who already have a password
    try:
        await db.execute("""
            UPDATE auth_allowlist
            SET password_must_reset = 0
            WHERE password_hash IS NOT NULL AND password_hash != '' AND password_must_reset IS NULL
        """, commit=True)
    except Exception as e:
        logger.warning(f"[DDL] Could not update password_must_reset for existing users: {e}")

async def _ensure_session_isolation_columns(db: DatabaseManager):
    await _add_column_if_missing(db, "threads", "session_id", "TEXT")
    await _add_column_if_missing(db, "threads", "user_id", "TEXT")
    await _add_column_if_missing(db, "messages", "session_id", "TEXT")
    await _add_column_if_missing(db, "messages", "user_id", "TEXT")
    await _add_column_if_missing(db, "thread_docs", "session_id", "TEXT")
    await _add_column_if_missing(db, "thread_docs", "user_id", "TEXT")
    await _add_column_if_missing(db, "documents", "session_id", "TEXT")
    await _add_column_if_missing(db, "documents", "user_id", "TEXT")
    await _add_column_if_missing(db, "document_chunks", "session_id", "TEXT")
    await _add_column_if_missing(db, "document_chunks", "user_id", "TEXT")
    await _add_column_if_missing(db, "auth_sessions", "user_id", "TEXT")
    index_errors = []
    for table_name, definitions in INDEX_DEFINITIONS.items():
        for index_name, ddl in definitions:
            try:
                await db.execute(ddl, commit=True)
            except Exception as exc:
                logger.warning(f"[DDL] Index {index_name} non cree: {exc}")
                index_errors.append((index_name, str(exc)))
    if index_errors:
        logger.debug("[DDL] Index creation issues: %s", index_errors)
    await _log_index_dump(db, INDEX_DEFINITIONS.keys())
# ------------------------------------------------------------------------ #

async def _ensure_costs_enriched_columns(db: DatabaseManager):
    """Garantit la présence des colonnes session_id / user_id pour la table des coûts."""
    try:
        await _add_column_if_missing(db, "costs", "session_id", "TEXT")
        await _add_column_if_missing(db, "costs", "user_id", "TEXT")
    except Exception as e:
        logger.error(f"[DDL] Impossible d'ajouter les colonnes session_id/user_id sur costs: {e}", exc_info=True)
        raise

# ------------------------------------------------------------------------ #

async def _ensure_threads_enriched_columns(db: DatabaseManager):
    """Ajoute les colonnes d'enrichissement threads (last_message_at, message_count, archival_reason)."""
    cols = await _get_columns(db, "threads")
    if not cols:
        return
    added_message_count = False
    if "archival_reason" not in cols:
        await db.execute("ALTER TABLE threads ADD COLUMN archival_reason TEXT", commit=True)
        logger.info("[DDL] Colonne ajoutée: threads.archival_reason TEXT")
    if "archived_at" not in cols:
        await db.execute("ALTER TABLE threads ADD COLUMN archived_at TEXT", commit=True)
        logger.info("[DDL] Colonne ajoutée: threads.archived_at TEXT")
    if "last_message_at" not in cols:
        await db.execute("ALTER TABLE threads ADD COLUMN last_message_at TEXT", commit=True)
        logger.info("[DDL] Colonne ajoutée: threads.last_message_at TEXT")
    if "message_count" not in cols:
        await db.execute("ALTER TABLE threads ADD COLUMN message_count INTEGER DEFAULT 0", commit=True)
        logger.info("[DDL] Colonne ajoutée: threads.message_count INTEGER DEFAULT 0")
        added_message_count = True
    if added_message_count:
        try:
            await db.execute("UPDATE threads SET message_count = 0 WHERE message_count IS NULL", commit=True)
        except Exception as exc:
            logger.warning(f"[DDL] Impossible d'initialiser threads.message_count: {exc}")

# ------------------------------------------------------------------------ #

async def create_tables(db_manager: DatabaseManager):
    logger.info("Vérification et création des tables de la base de données...")
    if not db_manager.is_connected():
        await db_manager.connect()
    errors = []
    for table_sql in TABLE_DEFINITIONS:
        stmt = table_sql.strip()
        if not stmt:
            continue
        try:
            await db_manager.execute(stmt, commit=True)
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

    try:
        await _ensure_allowlist_password_columns(db_manager)
    except Exception as e:
        logger.error(f"[DDL] echec backcompat 'auth_allowlist': {e}", exc_info=True)
        raise

    try:
        await _ensure_session_isolation_columns(db_manager)
    except Exception as e:
        logger.error(f"[DDL] echec backcompat 'session isolation': {e}", exc_info=True)
        raise

    try:
        await _ensure_costs_enriched_columns(db_manager)
    except Exception as e:
        logger.error(f"[DDL] echec backcompat 'costs': {e}", exc_info=True)
        raise

    try:
        await _ensure_threads_enriched_columns(db_manager)
    except Exception as e:
        logger.error(f"[DDL] echec backcompat 'threads enriched columns': {e}", exc_info=True)
        raise

    logger.info("Toutes les tables/index requis sont en place (avec backcompat au besoin).")

async def run_migrations(db_manager: DatabaseManager, migrations_dir: str):
    logger.info("Démarrage du processus de migration de la base de données...")
    if not db_manager.is_connected():
        await db_manager.connect()
    await db_manager.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            applied_at TEXT NOT NULL
        );
    """, commit=True)
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
                    # Utiliser executescript pour supporter les triggers SQLite (BEGIN...END)
                    conn = await db_manager._ensure_connection()
                    try:
                        await conn.executescript(sql_script)
                        await conn.commit()
                    except Exception as script_err:
                        # Pour compatibilité: essayer statement par statement si executescript échoue
                        if "duplicate column" in str(script_err).lower():
                            logger.debug(f"[Migration] Colonnes déjà existantes, ignorées: {script_err}")
                        else:
                            # Fallback: exécuter statement par statement (anciennes migrations)
                            for statement in sql_script.split(';'):
                                stmt = statement.strip()
                                if stmt:
                                    try:
                                        await db_manager.execute(stmt, commit=True)
                                    except Exception as stmt_err:
                                        if "duplicate column" in str(stmt_err).lower() and "alter table" in stmt.lower():
                                            logger.debug(f"[Migration] Colonne déjà existante, ignorée: {stmt_err}")
                                        else:
                                            raise
                await db_manager.execute(
                    "INSERT INTO migrations (filename, applied_at) VALUES (?, ?)",
                    (filename, datetime.now(timezone.utc).isoformat()),
                    commit=True,
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
    await run_user_scope_backfill(db_manager)
    logger.info("Initialisation de la base de données terminée.")
