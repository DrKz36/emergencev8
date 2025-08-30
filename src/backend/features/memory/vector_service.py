# src/backend/features/memory/vector_service.py
# V2.9.3 — Telemetry ultra-OFF & import-order guard :
#          - Force CHROMA_* env OFF avant tout import Chroma
#          - Monkeypatch complet de posthog (classe + fonctions module-level)
#          - API identique ; messages Chroma/PostHog supprimés des logs

import logging
import os
import shutil
import sqlite3
import sys
import types
from datetime import datetime
from typing import List, Dict, Any, Optional

# ---- Force disable telemetry as early as possible (before importing chromadb) ----
def _force_disable_telemetry_env() -> None:
    try:
        os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "0")
        os.environ.setdefault("PERSIST_TELEMETRY", "0")
        # Défensif : variantes lues par certaines builds
        os.environ.setdefault("CHROMA_TELEMETRY_ENABLED", "0")
        os.environ.setdefault("DO_NOT_TRACK", "1")
        os.environ.setdefault("POSTHOG_DISABLED", "1")
    except Exception:
        pass

def _monkeypatch_posthog_noop() -> None:
    """
    Neutralise entièrement 'posthog' quel que soit le mode d'import utilisé par Chroma :
      - Fournit une classe Posthog no-op.
      - Fournit les fonctions module-level capture/identify/flush/shutdown no-op.
    """
    def _noop(*a, **k): return None

    try:
        import posthog  # type: ignore

        class _NoopPosthog:
            def __init__(self, *a, **k): pass
            def capture(self, *a, **k): return None
            def identify(self, *a, **k): return None
            def flush(self, *a, **k): return None
            def shutdown(self, *a, **k): return None

        try:
            posthog.Posthog = _NoopPosthog          # classe no-op
            posthog.capture = _noop                 # fonctions module-level no-op
            posthog.identify = _noop
            posthog.flush = _noop
            posthog.shutdown = _noop
        except Exception:
            pass

    except Exception:
        # Module absent → on injecte un shim complet
        shim = types.ModuleType("posthog")
        class _NoopPosthog:
            def __init__(self, *a, **k): pass
            def capture(self, *a, **k): return None
            def identify(self, *a, **k): return None
            def flush(self, *a, **k): return None
            def shutdown(self, *a, **k): return None
        shim.Posthog = _NoopPosthog
        shim.capture = lambda *a, **k: None
        shim.identify = lambda *a, **k: None
        shim.flush = lambda *a, **k: None
        shim.shutdown = lambda *a, **k: None
        sys.modules.setdefault("posthog", shim)

_force_disable_telemetry_env()
_monkeypatch_posthog_noop()

# Only now import chromadb (after telemetry is hard-disabled)
import chromadb
from chromadb.config import Settings
from chromadb.types import Collection
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorService:
    """
    VectorService V2.9.3
    - API identique.
    - Auto-reset AVANT instanciation Chroma si DB corrompue (évite locks Windows).
    - Télémétrie Chroma/PostHog durcie : env forcé + module posthog neutralisé (classe + fonctions).
    - FIX existant conservé : normalisation des filtres where.
    """

    def __init__(
        self,
        persist_directory: str,
        embed_model_name: str,
        auto_reset_on_schema_error: bool = True
    ):
        """
        :param persist_directory: Répertoire de persistance Chroma (ex: 'src/backend/data/vector_store').
        :param embed_model_name: Modèle SentenceTransformer (ex: 'all-MiniLM-L6-v2').
        :param auto_reset_on_schema_error: True -> backup + reset si schéma/DB cassée.
        """
        self.persist_directory = os.path.abspath(persist_directory)
        self.embed_model_name = embed_model_name
        self.auto_reset_on_schema_error = auto_reset_on_schema_error

        os.makedirs(self.persist_directory, exist_ok=True)

        # 0) Pré-check : si DB corrompue -> backup + reset AVANT d'instancier Chroma (évite WinError 32)
        if self.auto_reset_on_schema_error and self._is_sqlite_corrupted(self.persist_directory):
            logger.warning("Pré-check: DB Chroma corrompue détectée. Auto-reset protégé AVANT initialisation…")
            backup_path = self._backup_persist_dir(self.persist_directory)
            logger.warning(f"Store existant déplacé en backup: {backup_path}")

        # 1) Charger le modèle d'embedding
        try:
            self.model = SentenceTransformer(self.embed_model_name)
            logger.info(
                f"Modèle SentenceTransformer '{self.embed_model_name}' chargé avec succès."
            )
        except Exception as e:
            logger.error(
                f"Échec du chargement du modèle '{self.embed_model_name}': {e}",
                exc_info=True
            )
            raise

        # 2) Initialiser Chroma PersistentClient (télémétrie désactivée)
        self.client = self._init_client_with_guard(
            self.persist_directory,
            self.auto_reset_on_schema_error
        )

    # ---------- Pré-check SQLite ----------
    def _is_sqlite_corrupted(self, path: str) -> bool:
        """
        Retourne True si chroma.sqlite3 est inexistant mais avec artefacts incohérents,
        ou existant mais non lisible / entête invalide / integrity_check != 'ok'.
        """
        db_path = os.path.join(path, "chroma.sqlite3")
        if not os.path.exists(db_path):
            return False
        try:
            con = sqlite3.connect(db_path)
            try:
                cur = con.execute("PRAGMA integrity_check;")
                row = cur.fetchone()
                ok = (row and isinstance(row[0], str) and row[0].lower() == "ok")
                return not ok
            finally:
                con.close()
        except sqlite3.DatabaseError:
            return True
        except Exception:
            return False

    # ---------- Initialisation protégée du client ----------
    def _init_client_with_guard(self, path: str, allow_auto_reset: bool) -> chromadb.PersistentClient:
        try:
            client = chromadb.PersistentClient(
                path=path,
                settings=Settings(anonymized_telemetry=False)  # Télémétrie désactivée
            )
            _ = client.list_collections()
            logger.info(f"Client ChromaDB connecté au répertoire: {path}")
            return client

        except Exception as e:
            msg = str(e).lower()
            schema_signatures = (
                "no such column",
                "schema mismatch",
                "wrong number of columns",
                "has no column named",
                "operationalerror",
                "file is not a database",
                "not a database",
                "database disk image is malformed",
                "could not connect to tenant",
                "default_tenant"
            )
            is_schema_issue = any(sig in msg for sig in schema_signatures)

            if is_schema_issue and allow_auto_reset:
                logger.warning(
                    "Incompatibilité/corruption du store Chroma détectée durant init. "
                    "Auto-reset protégé (post-essai) en cours…"
                )
                backup_path = self._backup_persist_dir(self.persist_directory)
                logger.warning(f"Store existant déplacé en backup: {backup_path}")
                try:
                    client = chromadb.PersistentClient(
                        path=path,
                        settings=Settings(anonymized_telemetry=False)
                    )
                    _ = client.list_collections()
                    logger.info(f"Nouveau store ChromaDB initialisé avec succès dans: {path}")
                    return client
                except Exception as e2:
                    logger.error(
                        f"Échec de la réinitialisation du store Chroma: {e2}",
                        exc_info=True
                    )
                    raise
            else:
                logger.error(
                    f"Échec de l'initialisation du client Chroma (auto-reset={allow_auto_reset}). "
                    f"Message: {e}",
                    exc_info=True
                )
                raise

    def _backup_persist_dir(self, path: str) -> str:
        """
        Déplace le dossier 'path' en 'path_backup_YYYYMMDD_HHMMSS' et recrée 'path'.
        Conçu pour être appelé AVANT toute instanciation Chroma (donc sans lock).
        """
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{path}_backup_{ts}"
        try:
            if os.path.isdir(path) and os.listdir(path):
                shutil.move(path, backup_path)
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            logger.error(
                f"Échec du backup '{path}' vers '{backup_path}': {e}",
                exc_info=True
            )
            raise
        return backup_path

    # ---------- Normalisation where (FIX) ----------
    def _normalize_where(self, where: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Règles Chroma:
          - Un seul critère: passer tel quel, ex. {'source_session_id': '...'}
          - Plusieurs critères: {'$and': [ {k1:v1}, {k2:v2}, ... ]}
          - Si déjà opérateur ($and/$or/$not):
              * si $and/$or liste de longueur 0 -> None
              * si $and/$or liste de longueur 1 -> aplatir en dict simple
              * sinon -> laisser tel quel
        """
        if not where:
            return None

        if any(str(k).startswith("$") for k in where.keys()):
            if "$and" in where and isinstance(where["$and"], list):
                lst = where["$and"]
                if len(lst) == 0:
                    return None
                if len(lst) == 1 and isinstance(lst[0], dict):
                    return lst[0]
                return where
            if "$or" in where and isinstance(where["$or"], list):
                lst = where["$or"]
                if len(lst) == 0:
                    return None
                if len(lst) == 1 and isinstance(lst[0], dict):
                    return lst[0]
                return where
            return where

        items = list(where.items())
        if len(items) <= 1:
            return where
        return {"$and": [{k: v} for k, v in items]}

    # ---------- API publique ----------
    def get_or_create_collection(self, name: str) -> Collection:
        try:
            collection = self.client.get_or_create_collection(name=name)
            logger.info(f"Collection '{name}' chargée/créée avec succès.")
            return collection
        except Exception as e:
            logger.error(
                f"Impossible de get/create la collection '{name}': {e}",
                exc_info=True
            )
            raise

    def add_items(
        self,
        collection: Collection,
        items: List[Dict[str, Any]],
        item_text_key: str = 'text'
    ) -> None:
        if not items:
            logger.warning(
                f"Tentative d'ajout d'items vides à '{collection.name}'."
            )
            return
        try:
            ids = [item['id'] for item in items]
            documents_text = [item[item_text_key] for item in items]
            metadatas = [item.get('metadata', {}) for item in items]

            from sentence_transformers import SentenceTransformer as _ST  # lazy safety
            embeddings = self.model.encode(
                documents_text,
                show_progress_bar=False
            )
            embeddings_list = (
                embeddings.tolist()
                if hasattr(embeddings, "tolist")
                else embeddings
            )

            collection.upsert(
                embeddings=embeddings_list,
                documents=documents_text,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(
                f"{len(ids)} items ajoutés/mis à jour dans '{collection.name}'."
            )
        except Exception as e:
            logger.error(
                f"Échec de l'ajout d'items à '{collection.name}': {e}",
                exc_info=True
            )
            raise

    def query(
        self,
        collection: Collection,
        query_text: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if not query_text:
            return []
        try:
            embeddings = self.model.encode(
                [query_text],
                show_progress_bar=False
            )
            embeddings_list = (
                embeddings.tolist()
                if hasattr(embeddings, "tolist")
                else embeddings
            )

            results = collection.query(
                query_embeddings=embeddings_list,
                n_results=n_results,
                where=self._normalize_where(where_filter),
                include=["documents", "metadatas", "distances"]
            )

            formatted_results: List[Dict[str, Any]] = []
            if results and results.get('ids') and results['ids'][0]:
                ids = results['ids'][0]
                docs = results.get('documents', [[]])[0]
                metas = results.get('metadatas', [[]])[0]
                dists = results.get('distances', [[]])[0]

                for i, doc_id in enumerate(ids):
                    formatted_results.append({
                        "id": doc_id,
                        "text": docs[i] if i < len(docs) else None,
                        "metadata": metas[i] if i < len(metas) else None,
                        "distance": dists[i] if i < len(dists) else None
                    })

            return formatted_results
        except Exception as e:
            safe_q = (query_text or "")[:50]
            logger.error(
                f"Échec de la recherche '{safe_q}…' dans '{collection.name}': {e}",
                exc_info=True
            )
            return []

    def delete_vectors(self, collection: Collection, where_filter: Dict[str, Any]) -> None:
        if not where_filter:
            logger.warning(
                f"Suppression annulée sur '{collection.name}' (pas de filtre)."
            )
            return
        try:
            collection.delete(where=self._normalize_where(where_filter))
            logger.info(
                f"Vecteurs supprimés de '{collection.name}' avec filtre {where_filter}."
            )
        except Exception as e:
            logger.error(
                f"Échec suppression vecteurs dans '{collection.name}': {e}",
                exc_info=True
            )
            raise
