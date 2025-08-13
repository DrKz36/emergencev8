# src/backend/core/database/manager.py
# V23.0 - FIX: Alignement de save_session avec le schéma BDD V5.0.
import aiosqlite
import logging
import json
from typing import Optional, List, TYPE_CHECKING
from pathlib import Path
from datetime import datetime, timezone

# Pour l'annotation de type sans import circulaire
if TYPE_CHECKING:
    from backend.shared.models import Session

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Gère le cycle de vie de la connexion à la base de données aiosqlite.
    Version 23.0 - Correction de la sauvegarde de session.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
        self.db_dir = Path(self.db_path).parent
        self.db_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"DatabaseManager (Async) V23.0 initialisé pour : {self.db_path}")

    async def connect(self):
        """Établit la connexion à la base de données."""
        if self.connection is None or self.connection._conn is None:
            try:
                self.connection = await aiosqlite.connect(self.db_path)
                self.connection.row_factory = aiosqlite.Row
                await self.connection.execute("PRAGMA journal_mode=WAL;")
                await self.connection.execute("PRAGMA foreign_keys = ON;")
                logger.info("Nouvelle connexion aiosqlite établie en mode WAL.")
            except Exception as e:
                logger.error(f"Erreur critique lors de la connexion à la DB: {e}", exc_info=True)
                raise

    async def disconnect(self):
        """Ferme la connexion à la base de données."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            logger.info("Connexion aiosqlite fermée.")

    async def execute(self, query: str, params: tuple = None):
        """Exécute une requête qui ne retourne pas de résultat (INSERT, UPDATE, DELETE)."""
        if not self.connection:
            await self.connect()
        await self.connection.execute(query, params or ())
        await self.connection.commit()

    async def executemany(self, query: str, params: List[tuple]):
        """Exécute une requête plusieurs fois."""
        if not self.connection:
            await self.connect()
        await self.connection.executemany(query, params)
        await self.connection.commit()

    async def fetch_one(self, query: str, params: tuple = None) -> Optional[aiosqlite.Row]:
        """Récupère une seule ligne."""
        if not self.connection:
            await self.connect()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params or ())
            return await cursor.fetchone()

    async def fetch_all(self, query: str, params: tuple = None) -> List[aiosqlite.Row]:
        """Récupère toutes les lignes correspondantes."""
        if not self.connection:
            await self.connect()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, params or ())
            return await cursor.fetchall()

    async def save_session(self, session_data: 'Session'):
        """
        Sauvegarde une session complète dans la base de données (UPSERT).
        Cette version est alignée avec le schéma de la table 'sessions' V5.0.
        """
        # --- CORRECTION V23.0 ---
        # La requête est maintenant synchronisée avec les colonnes de schema.py
        # (created_at, updated_at, etc.)
        history_json = json.dumps(getattr(session_data, 'history', []))
        metadata = getattr(session_data, 'metadata', {})
        summary = metadata.get('summary')
        concepts = metadata.get('concepts')
        entities = metadata.get('entities')
        concepts_json = json.dumps(concepts) if concepts is not None else None
        entities_json = json.dumps(entities) if entities is not None else None

        query = """
            INSERT INTO sessions (id, user_id, created_at, updated_at, session_data, summary, extracted_concepts, extracted_entities)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at = excluded.updated_at,
                session_data = excluded.session_data,
                summary = excluded.summary,
                extracted_concepts = excluded.extracted_concepts,
                extracted_entities = excluded.extracted_entities;
        """
        
        # Mapping des attributs de l'objet Session vers les colonnes de la BDD
        params = (
            session_data.id,
            session_data.user_id,
            session_data.start_time.isoformat(),  # Mappe start_time -> created_at
            session_data.end_time.isoformat() if session_data.end_time else datetime.now(timezone.utc).isoformat(), # Mappe end_time -> updated_at
            history_json, # Mappe history -> session_data
            summary,
            concepts_json,
            entities_json
        )
        
        try:
            await self.execute(query, params)
            logger.info(f"Session {session_data.id} sauvegardée avec succès via DatabaseManager.")
        except Exception as e:
            logger.error(f"Échec de la sauvegarde de la session {session_data.id}: {e}", exc_info=True)
            # On ne 'raise' plus pour éviter de faire planter l'application à la fermeture.
            # L'erreur est loggée, c'est suffisant.
