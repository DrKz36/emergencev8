# src/backend/features/memory/vector_service.py
# V2.11.1 — Lazy-imports + API parity (add_items/query/delete_vectors) + **embed_texts public**
# - Conserve exactement l’API de V2.9.3: get_or_create_collection, add_items, query, delete_vectors
# - Ajoute embed_texts(texts) attendu par MemoryGardener._vectorize_concepts
# - Déplace les imports lourds (chromadb, sentence_transformers) dans __init__
# - Télémétrie ultra-OFF (env + posthog no-op) AVANT tout import Chroma
# - Auto-reset protégé si schéma/DB Chroma cassé
# - Normalisation where conservée

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import sys
import types
from datetime import datetime
from typing import List, Dict, Any, Optional, TYPE_CHECKING

logger = logging.getLogger(__name__)

# ---- Helpers télémétrie (appelés dans __init__ AVANT import Chroma) ----------
def _force_disable_telemetry_env() -> None:
    try:
        os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "0")
        os.environ.setdefault("PERSIST_TELEMETRY", "0")
        # variantes défensives
        os.environ.setdefault("CHROMA_TELEMETRY_ENABLED", "0")
        os.environ.setdefault("DO_NOT_TRACK", "1")
        os.environ.setdefault("POSTHOG_DISABLED", "1")
    except Exception:
        pass

def _monkeypatch_posthog_noop() -> None:
    """Neutralise complètement 'posthog' (classe + fonctions module-level)."""
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

if TYPE_CHECKING:
    from chromadb.types import Collection  # hints only
else:
    Collection = Any  # runtime-friendly


class VectorService:
    """
    VectorService V2.11.1 — Lazy-import + API parity
    - API identique à V2.9.3 (add_items/query/delete_vectors)
    - Ajoute embed_texts(texts) pour consommation externe (Gardener)
    - Import Chroma/SentenceTransformer déplacé dans __init__ (cold start Cloud Run)
    - Auto-reset si schéma cassé (backup + re-init)
    """

    def __init__(
        self,
        persist_directory: str,
        embed_model_name: str,
        auto_reset_on_schema_error: bool = True
    ):
        """
        :param persist_directory: Répertoire de persistance (ex: '/app/data/vector_store').
        :param embed_model_name:  Modèle SentenceTransformer (ex: 'all-MiniLM-L6-v2').
        :param auto_reset_on_schema_error: True → backup + reset si schéma/DB cassée.
        """
        self.persist_directory = os.path.abspath(persist_directory)
        self.embed_model_name = embed_model_name
        self.auto_reset_on_schema_error = auto_reset_on_schema_error

        os.makedirs(self.persist_directory, exist_ok=True)

        # IMPORTANT: neutraliser télémétrie AVANT import Chroma
        _force_disable_telemetry_env()
        _monkeypatch_posthog_noop()

        # Imports lourds → maintenant (lazy)
        from sentence_transformers import SentenceTransformer  # type: ignore
        import chromadb  # type: ignore
        from chromadb.config import Settings  # type: ignore

        self._chromadb = chromadb
        self._ChromaSettings = Settings

        # 0) Pré-check corruption SQLite AVANT instanciation client
        if self.auto_reset_on_schema_error and self._is_sqlite_corrupted(self.persist_directory):
            logger.warning("Pré-check: DB Chroma corrompue. Auto-reset protégé AVANT initialisation…")
            backup_path = self._backup_persist_dir(self.persist_directory)
            logger.warning(f"Store existant déplacé en backup: {backup_path}")

        # 1) Charger le modèle d'embedding
        try:
            self.model = SentenceTransformer(self.embed_model_name)
            logger.info(f"Modèle SentenceTransformer '{self.embed_model_name}' chargé.")
        except Exception as e:
            logger.error(f"Échec chargement modèle '{self.embed_model_name}': {e}", exc_info=True)
            raise

        # 2) Initialiser Chroma PersistentClient (télémétrie désactivée)
        self.client = self._init_client_with_guard(
            self.persist_directory,
            self.auto_reset_on_schema_error
        )

    # ---------- Pré-check SQLite ----------
    def _is_sqlite_corrupted(self, path: str) -> bool:
        """
        True si chroma.sqlite3 est illisible / entête invalide / integrity_check != 'ok'.
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
    def _init_client_with_guard(self, path: str, allow_auto_reset: bool):
        try:
            client = self._chromadb.PersistentClient(
                path=path,
                settings=self._ChromaSettings(anonymized_telemetry=False)
            )
            _ = client.list_collections()
            logger.info(f"Client ChromaDB connecté: {path}")
            return client

        except Exception as e:
            msg = str(e).lower()
            schema_signatures = (
                "no such column", "schema mismatch", "wrong number of columns",
                "has no column named", "operationalerror", "file is not a database",
                "not a database", "database disk image is malformed",
                "could not connect to tenant", "default_tenant"
            )
            is_schema_issue = any(sig in msg for sig in schema_signatures)
            if is_schema_issue and allow_auto_reset:
                logger.warning("Incompatibilité/corruption du store Chroma détectée. Auto-reset protégé…")
                backup_path = self._backup_persist_dir(self.persist_directory)
                logger.warning(f"Store existant déplacé en backup: {backup_path}")
                try:
                    client = self._chromadb.PersistentClient(
                        path=path,
                        settings=self._ChromaSettings(anonymized_telemetry=False)
                    )
                    _ = client.list_collections()
                    logger.info(f"Nouveau store ChromaDB initialisé: {path}")
                    return client
                except Exception as e2:
                    logger.error(f"Réinitialisation store Chroma échouée: {e2}", exc_info=True)
                    raise
            else:
                logger.error(f"Init Chroma échouée (auto-reset={allow_auto_reset}). Message: {e}", exc_info=True)
                raise

    def _backup_persist_dir(self, path: str) -> str:
        """Déplace 'path' vers 'path_backup_YYYYMMDD_HHMMSS' puis recrée 'path'."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{path}_backup_{ts}"
        try:
            if os.path.isdir(path) and os.listdir(path):
                shutil.move(path, backup_path)
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            logger.error(f"Backup '{path}' → '{backup_path}' KO: {e}", exc_info=True)
            raise
        return backup_path

    # ---------- Normalisation where ----------
    def _normalize_where(self, where: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Règles Chroma:
          - 1 critère -> dict tel quel
          - >1 critère -> {'$and': [ {k1:v1}, {k2:v2}, ... ]}
          - Opérateurs $and/$or : nettoyer listes vides / singleton
        """
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

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Encode une liste de textes en embeddings (liste de listes de floats) via SentenceTransformer.
        """
        if not texts:
            return []
        try:
            emb = self.model.encode(texts, show_progress_bar=False)
            return emb.tolist() if hasattr(emb, "tolist") else emb  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Échec embed_texts sur {len(texts)} textes: {e}", exc_info=True)
            raise

    def get_or_create_collection(self, name: str) -> Collection:
        collection = self.client.get_or_create_collection(name=name)
        logger.info(f"Collection '{name}' chargée/créée.")
        return collection  # type: ignore[return-value]

    def add_items(
        self,
        collection: Collection,
        items: List[Dict[str, Any]],
        item_text_key: str = "text"
    ) -> None:
        if not items:
            logger.warning(f"Tentative d'ajout d'items vides à '{getattr(collection, 'name', '?')}'.")
            return
        try:
            ids = [item["id"] for item in items]
            documents_text = [item[item_text_key] for item in items]
            metadatas = [item.get("metadata", {}) for item in items]

            # Encodage embeddings
            embeddings = self.model.encode(documents_text, show_progress_bar=False)
            embeddings_list = embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

            collection.upsert(
                embeddings=embeddings_list,
                documents=documents_text,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"{len(ids)} items ajoutés/mis à jour dans '{getattr(collection, 'name', '?')}'.")
        except Exception as e:
            logger.error(f"Échec add_items sur '{getattr(collection, 'name', '?')}': {e}", exc_info=True)
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
            embeddings = self.model.encode([query_text], show_progress_bar=False)
            embeddings_list = embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

            results = collection.query(
                query_embeddings=embeddings_list,
                n_results=n_results,
                where=self._normalize_where(where_filter),
                include=["documents", "metadatas", "distances"]
            )

            formatted: List[Dict[str, Any]] = []
            if results and results.get("ids") and results["ids"][0]:
                ids = results["ids"][0]
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]

                for i, doc_id in enumerate(ids):
                    formatted.append({
                        "id": doc_id,
                        "text": docs[i] if i < len(docs) else None,
                        "metadata": metas[i] if i < len(metas) else None,
                        "distance": dists[i] if i < len(dists) else None
                    })
            return formatted
        except Exception as e:
            safe_q = (query_text or "")[:50]
            logger.error(f"Échec query '{safe_q}…' dans '{getattr(collection, 'name', '?')}': {e}", exc_info=True)
            return []

    def delete_vectors(self, collection: Collection, where_filter: Dict[str, Any]) -> None:
        if not where_filter:
            logger.warning(f"Suppression annulée sur '{getattr(collection, 'name', '?')}' (pas de filtre).")
            return
        try:
            collection.delete(where=self._normalize_where(where_filter))
            logger.info(f"Vecteurs supprimés de '{getattr(collection, 'name', '?')}' avec filtre {where_filter}.")
        except Exception as e:
            logger.error(f"Échec suppression vecteurs dans '{getattr(collection, 'name', '?')}': {e}", exc_info=True)
            raise
