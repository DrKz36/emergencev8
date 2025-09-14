# src/backend/features/memory/vector_service.py
# V3.0.0 — Lazy-load sûr (double-checked lock) + télémétrie ultra-OFF conservée
#          - __init__ ne charge plus ni SBERT ni Chroma
#          - _ensure_inited() déclenché au 1er appel public
#          - Pré-check corruption + backup AVANT init Chroma (inchangé)
#          - API publique identique

import logging
import os
import shutil
import sqlite3
import sys
import types
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional

# ---- Force disable telemetry as early as possible (before importing chromadb) ----
def _force_disable_telemetry_env() -> None:
    try:
        os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "0")
        os.environ.setdefault("PERSIST_TELEMETRY", "0")
        os.environ.setdefault("CHROMA_TELEMETRY_ENABLED", "0")
        os.environ.setdefault("DO_NOT_TRACK", "1")
        os.environ.setdefault("POSTHOG_DISABLED", "1")
    except Exception:
        pass

def _monkeypatch_posthog_noop() -> None:
    """Neutralise totalement le module posthog (classe + fonctions module-level)."""
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
            posthog.Posthog = _NoopPosthog
            posthog.capture = _noop
            posthog.identify = _noop
            posthog.flush = _noop
            posthog.shutdown = _noop
        except Exception:
            pass
    except Exception:
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

# Imports de libs (on garde les imports module-level, l'instanciation sera lazy)
import chromadb
from chromadb.config import Settings
from chromadb.types import Collection
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class VectorService:
    """
    VectorService V3.0.0
    - API identique.
    - Lazy-load: modèle SBERT + client Chroma instanciés au 1er usage (_ensure_inited()).
    - Auto-reset AVANT instanciation Chroma si DB corrompue (évite locks Windows).
    - Télémétrie Chroma/PostHog durcie (env + shim).
    - Normalisation des filtres where conservée.
    """

    def __init__(
        self,
        persist_directory: str,
        embed_model_name: str,
        auto_reset_on_schema_error: bool = True
    ):
        self.persist_directory = os.path.abspath(persist_directory)
        self.embed_model_name = embed_model_name
        self.auto_reset_on_schema_error = auto_reset_on_schema_error

        os.makedirs(self.persist_directory, exist_ok=True)

        # Lazy members (instanciés à la demande)
        self.model: Optional[SentenceTransformer] = None
        self.client: Optional[chromadb.PersistentClient] = None

        # Guard thread-safe (double-checked lock)
        self._init_lock = threading.Lock()
        self._inited = False

    # ---------- Lazy init ----------
    def _ensure_inited(self) -> None:
        if self._inited and self.model is not None and self.client is not None:
            return
        with self._init_lock:
            if self._inited and self.model is not None and self.client is not None:
                return

            # 0) Pré-check : corruption SQLite → backup + reset AVANT Chroma
            if self.auto_reset_on_schema_error and self._is_sqlite_corrupted(self.persist_directory):
                logger.warning("Pré-check: DB Chroma corrompue détectée. Auto-reset protégé AVANT initialisation…")
                backup_path = self._backup_persist_dir(self.persist_directory)
                logger.warning(f"Store existant déplacé en backup: {backup_path}")

            # 1) Charger le modèle d'embedding
            try:
                self.model = SentenceTransformer(self.embed_model_name)
                logger.info(f"Modèle SentenceTransformer '{self.embed_model_name}' chargé (lazy).")
            except Exception as e:
                logger.error(f"Échec du chargement du modèle '{self.embed_model_name}': {e}", exc_info=True)
                raise

            # 2) Initialiser Chroma PersistentClient (télémétrie désactivée)
            self.client = self._init_client_with_guard(
                self.persist_directory,
                self.auto_reset_on_schema_error
            )
            self._inited = True
            logger.info("VectorService initialisé (lazy) : SBERT + Chroma prêts.")

    # ---------- Pré-check SQLite ----------
    def _is_sqlite_corrupted(self, path: str) -> bool:
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
                settings=Settings(anonymized_telemetry=False)
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
                logger.warning("Incompatibilité/corruption du store Chroma détectée durant init. Auto-reset protégé (post-essai)…")
                backup_path = self._backup_persist_dir(self.persist_directory)
                logger.warning(f"Store existant déplacé en backup: {backup_path}")
                client = chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))
                _ = client.list_collections()
                logger.info(f"Nouveau store ChromaDB initialisé avec succès dans: {path}")
                return client
            else:
                logger.error(f"Échec de l'initialisation du client Chroma (auto-reset={allow_auto_reset}). Message: {e}", exc_info=True)
                raise

    def _backup_persist_dir(self, path: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{path}_backup_{ts}"
        try:
            if os.path.isdir(path) and os.listdir(path):
                shutil.move(path, backup_path)
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            logger.error(f"Échec du backup '{path}' vers '{backup_path}': {e}", exc_info=True)
            raise
        return backup_path

    # ---------- Normalisation where (FIX) ----------
    def _normalize_where(self, where: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not where:
            return None
        if any(str(k).startswith("$") for k in where.keys()):
            if "$and" in where and isinstance(where["$and"], list):
                lst = where["$and"]
                if len(lst) == 0: return None
                if len(lst) == 1 and isinstance(lst[0], dict): return lst[0]
                return where
            if "$or" in where and isinstance(where["$or"], list):
                lst = where["$or"]
                if len(lst) == 0: return None
                if len(lst) == 1 and isinstance(lst[0], dict): return lst[0]
                return where
            return where
        items = list(where.items())
        if len(items) <= 1:
            return where
        return {"$and": [{k: v} for k, v in items]}

    # ---------- API publique ----------
    def get_or_create_collection(self, name: str) -> Collection:
        self._ensure_inited()
        try:
            collection = self.client.get_or_create_collection(name=name)  # type: ignore[union-attr]
            logger.info(f"Collection '{name}' chargée/créée avec succès.")
            return collection
        except Exception as e:
            logger.error(f"Impossible de get/create la collection '{name}': {e}", exc_info=True)
            raise

    def add_items(self, collection: Collection, items: List[Dict[str, Any]], item_text_key: str = 'text') -> None:
        self._ensure_inited()
        if not items:
            logger.warning(f"Tentative d'ajout d'items vides à '{collection.name}'.")
            return
        try:
            ids = [item['id'] for item in items]
            documents_text = [item[item_text_key] for item in items]
            metadatas = [item.get('metadata', {}) for item in items]

            embeddings = self.model.encode(documents_text, show_progress_bar=False)  # type: ignore[union-attr]
            embeddings_list = embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

            collection.upsert(embeddings=embeddings_list, documents=documents_text, metadatas=metadatas, ids=ids)
            logger.info(f"{len(ids)} items ajoutés/mis à jour dans '{collection.name}'.")
        except Exception as e:
            logger.error(f"Échec de l'ajout d'items à '{collection.name}': {e}", exc_info=True)
            raise

    def query(self, collection: Collection, query_text: str, n_results: int = 5, where_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._ensure_inited()
        if not query_text:
            return []
        try:
            embeddings = self.model.encode([query_text], show_progress_bar=False)  # type: ignore[union-attr]
            embeddings_list = embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

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
            logger.error(f"Échec de la recherche '{safe_q}…' dans '{collection.name}': {e}", exc_info=True)
            return []

    def delete_vectors(self, collection: Collection, where_filter: Dict[str, Any]) -> None:
        self._ensure_inited()
        if not where_filter:
            logger.warning(f"Suppression annulée sur '{collection.name}' (pas de filtre).")
            return
        try:
            collection.delete(where=self._normalize_where(where_filter))
            logger.info(f"Vecteurs supprimés de '{collection.name}' avec filtre {where_filter}.")
        except Exception as e:
            logger.error(f"Échec suppression vecteurs dans '{collection.name}': {e}", exc_info=True)
            raise
