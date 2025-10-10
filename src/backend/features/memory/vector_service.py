# mypy: ignore-errors
# src/backend/features/memory/vector_service.py
# V3.0.0 - Lazy-load sûr (double-checked lock) + télémétrie ultra-OFF conservée
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
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, cast




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

    def _noop(*_: Any, **__: Any) -> None:
        return None

    class _NoopPosthog:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def capture(self, *args: Any, **kwargs: Any) -> None:
            return None

        def identify(self, *args: Any, **kwargs: Any) -> None:
            return None

        def flush(self, *args: Any, **kwargs: Any) -> None:
            return None

        def shutdown(self, *args: Any, **kwargs: Any) -> None:
            return None

    try:
        import posthog  # type: ignore

        posthog_mod = cast(Any, posthog)
        try:
            setattr(posthog_mod, "Posthog", _NoopPosthog)
            setattr(posthog_mod, "capture", _noop)
            setattr(posthog_mod, "identify", _noop)
            setattr(posthog_mod, "flush", _noop)
            setattr(posthog_mod, "shutdown", _noop)
        except Exception:
            pass
    except Exception:
        shim = types.ModuleType("posthog")
        setattr(shim, "Posthog", _NoopPosthog)
        setattr(shim, "capture", _noop)
        setattr(shim, "identify", _noop)
        setattr(shim, "flush", _noop)
        setattr(shim, "shutdown", _noop)
        sys.modules.setdefault("posthog", shim)


_force_disable_telemetry_env()
_monkeypatch_posthog_noop()

# Imports de libs (on garde les imports module-level, l'instanciation sera lazy)
import chromadb  # noqa: E402
from chromadb.config import Settings  # noqa: E402
from chromadb.types import Collection  # noqa: E402
from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]  # noqa: E402

try:
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.http import models as qdrant_models  # type: ignore
except Exception:  # pragma: no cover - dépendance optionnelle
    QdrantClient = None  # type: ignore
    qdrant_models = None  # type: ignore

logger = logging.getLogger(__name__)


class QdrantCollectionAdapter:
    """Adapte l'API collection Chroma attendue par le code pour Qdrant."""

    def __init__(self, service: "VectorService", name: str):
        self._service = service
        self.name = name

    # Les signatures restent compatibles avec chroma.Collection.get/delete
    def get(self, where: Optional[Dict[str, Any]] = None, limit: Optional[int] = None):
        return self._service._qdrant_get(self.name, where_filter=where, limit=limit)

    def delete(
        self, where: Optional[Dict[str, Any]] = None, ids: Optional[List[str]] = None
    ) -> None:
        self._service._qdrant_delete_via_collection(
            self.name, where_filter=where, ids=ids
        )


class VectorService:
    """
    VectorService V3.5.0
    - API identique.
    - Lazy-load: modèle SBERT + backend vectoriel (Chroma ou Qdrant) instanciés au 1er usage.
    - Auto-reset AVANT instanciation Chroma si DB corrompue (évite locks Windows).
    - Télémétrie Chroma/PostHog durcie (env + shim).
    - Normalisation des filtres where conservée.
    - Backend Qdrant optionnel (via qdrant-client) avec fallback automatique sur Chroma.
    """

    def __init__(
        self,
        persist_directory: str,
        embed_model_name: str,
        auto_reset_on_schema_error: bool = True,
        backend_preference: str = "auto",
        qdrant_url: Optional[str] = None,
        qdrant_api_key: Optional[str] = None,
    ):
        self.persist_directory = os.path.abspath(persist_directory)
        self.embed_model_name = embed_model_name
        self.auto_reset_on_schema_error = auto_reset_on_schema_error
        self.backend_preference = (backend_preference or "auto").strip().lower()
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL") or None
        self.qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY") or None

        os.makedirs(self.persist_directory, exist_ok=True)

        # Lazy members (instanciés à la demande)
        self.model: Any = None
        self.client: Any = None
        self.qdrant_client: Optional[QdrantClient] = None  # type: ignore[assignment]

        # Backend effectif sélectionné ("chroma" ou "qdrant")
        self.backend: str = "chroma"
        self._qdrant_known_collections: Dict[str, int] = {}

        # Guard thread-safe (double-checked lock)
        self._init_lock = threading.Lock()
        self._inited = False

    # ---------- Lazy init ----------
    def _ensure_inited(self) -> None:
        if self._inited and self.model is not None:
            if self.backend == "chroma" and self.client is not None:
                return
            if self.backend == "qdrant" and self.qdrant_client is not None:
                return
        with self._init_lock:
            if self._inited and self.model is not None:
                if self.backend == "chroma" and self.client is not None:
                    return
                if self.backend == "qdrant" and self.qdrant_client is not None:
                    return

            # 0) Pré-check : corruption SQLite → backup + reset AVANT Chroma
            if self.auto_reset_on_schema_error and self._is_sqlite_corrupted(
                self.persist_directory
            ):
                logger.warning(
                    "Pré-check: DB Chroma corrompue détectée. Auto-reset protégé AVANT initialisation…"
                )
                backup_path = self._backup_persist_dir(self.persist_directory)
                logger.warning(f"Store existant déplacé en backup: {backup_path}")

            # 1) Charger le modèle d'embedding (commun aux backends)
            if self.model is None:
                try:
                    self.model = SentenceTransformer(self.embed_model_name)
                    logger.info(
                        f"Modèle SentenceTransformer '{self.embed_model_name}' chargé (lazy)."
                    )
                except Exception as e:
                    logger.error(
                        f"Échec du chargement du modèle '{self.embed_model_name}': {e}",
                        exc_info=True,
                    )
                    raise

            # 2) Sélectionner et initialiser le backend vectoriel
            backend = self._select_backend()
            if backend == "qdrant":
                if not self._init_qdrant_client():
                    logger.warning(
                        "VectorService: fallback sur Chroma (init Qdrant impossible)."
                    )
                    backend = "chroma"

            if backend == "chroma":
                self.client = self._init_client_with_guard(
                    self.persist_directory, self.auto_reset_on_schema_error
                )
            else:
                logger.info("VectorService: backend Qdrant activé.")

            self.backend = backend
            self._inited = True
            logger.info(
                "VectorService initialisé (lazy) : SBERT + backend %s prêts.",
                backend.upper(),
            )

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
                ok = row and isinstance(row[0], str) and row[0].lower() == "ok"
                return not ok
            finally:
                con.close()
        except sqlite3.DatabaseError:
            return True
        except Exception:
            return False

    # ---------- Initialisation protégée du client ----------
    def _init_client_with_guard(
        self, path: str, allow_auto_reset: bool
    ) -> Any:
        try:
            client = chromadb.PersistentClient(
                path=path, settings=Settings(anonymized_telemetry=False)
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
                "default_tenant",
            )
            is_schema_issue = any(sig in msg for sig in schema_signatures)

            if is_schema_issue and allow_auto_reset:
                logger.warning(
                    "Incompatibilité/corruption du store Chroma détectée durant init. Auto-reset protégé (post-essai)…"
                )
                backup_path = self._backup_persist_dir(self.persist_directory)
                logger.warning(f"Store existant déplacé en backup: {backup_path}")
                client = chromadb.PersistentClient(
                    path=path, settings=Settings(anonymized_telemetry=False)
                )
                _ = client.list_collections()
                logger.info(
                    f"Nouveau store ChromaDB initialisé avec succès dans: {path}"
                )
                return client
            else:
                logger.error(
                    f"Échec de l'initialisation du client Chroma (auto-reset={allow_auto_reset}). Message: {e}",
                    exc_info=True,
                )
                raise

    def _backup_persist_dir(self, path: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{path}_backup_{ts}"
        try:
            if os.path.isdir(path) and os.listdir(path):
                shutil.move(path, backup_path)
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            logger.error(
                f"Échec du backup '{path}' vers '{backup_path}': {e}", exc_info=True
            )
            raise
        return backup_path

    # ---------- Sélection backend ----------
    def _select_backend(self) -> str:
        pref = (self.backend_preference or "auto").lower()
        if pref in {"chroma", "chromadb"}:
            return "chroma"
        if pref == "qdrant":
            return "qdrant"
        if pref == "auto":
            if QdrantClient is not None and self.qdrant_url:
                return "qdrant"
        return "chroma"

    def _init_qdrant_client(self) -> bool:
        if QdrantClient is None:
            logger.warning(
                "qdrant-client non installé - impossible d'initialiser le backend Qdrant."
            )
            self.qdrant_client = None
            return False
        target = self.qdrant_url
        if not target:
            logger.warning("VectorService: URL Qdrant absente (env QDRANT_URL).")
            self.qdrant_client = None
            return False
        try:
            self.qdrant_client = QdrantClient(
                url=target, api_key=self.qdrant_api_key, timeout=5.0
            )  # type: ignore[call-arg]
            self.qdrant_client.get_collections()
            logger.info(f"Client Qdrant connecté: {target}")
            return True
        except Exception as e:
            logger.error(f"Échec connexion Qdrant ({target}): {e}", exc_info=True)
            self.qdrant_client = None
            return False

    # ---------- Normalisation where (FIX) ----------
    def _normalize_where(
        self, where: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
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

    # ---------- Backend Qdrant helpers ----------
    def _flatten_where_pairs(
        self, where_filter: Optional[Dict[str, Any]]
    ) -> List[tuple[str, Any]]:
        pairs: List[tuple[str, Any]] = []

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in {"$and", "$or"} and isinstance(value, list):
                        for child in value:
                            _walk(child)
                    elif not str(key).startswith("$"):
                        pairs.append((key, value))

        if where_filter:
            _walk(where_filter)
        return pairs

    def _build_qdrant_filter(self, where_filter: Optional[Dict[str, Any]]):
        if qdrant_models is None or not where_filter:
            return None
        pairs = self._flatten_where_pairs(where_filter)
        if not pairs:
            return None
        conditions = [
            qdrant_models.FieldCondition(
                key=key, match=qdrant_models.MatchValue(value=value)
            )
            for key, value in pairs
        ]
        if not conditions:
            return None
        return qdrant_models.Filter(must=conditions)

    def _ensure_qdrant_collection(self, name: str, vector_size: int) -> None:
        if self.qdrant_client is None or qdrant_models is None:
            raise RuntimeError("Backend Qdrant indisponible")
        if name in self._qdrant_known_collections:
            return
        try:
            info = self.qdrant_client.get_collection(name)
            if info:
                self._qdrant_known_collections[name] = vector_size or getattr(
                    getattr(info, "config", None), "vectors_count", 0
                )
                return
        except Exception:
            pass
        if vector_size <= 0:
            raise ValueError(
                "vector_size requis pour initialiser une collection Qdrant"
            )
        params = qdrant_models.VectorParams(
            size=vector_size, distance=qdrant_models.Distance.COSINE
        )
        try:
            self.qdrant_client.create_collection(
                collection_name=name, vectors_config=params
            )
            logger.info(f"Collection Qdrant '{name}' créée (dim={vector_size}).")
        except Exception as e:
            if "exists" not in str(e).lower():
                logger.warning(f"Création collection Qdrant '{name}' impossible: {e}")
            else:
                logger.info(f"Collection Qdrant '{name}' déjà existante.")
        self._qdrant_known_collections[name] = vector_size

    def _qdrant_upsert(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        if self.qdrant_client is None or qdrant_models is None:
            raise RuntimeError("Backend Qdrant non initialisé")
        if not embeddings:
            logger.warning("Tentative d'upsert Qdrant sans embeddings.")
            return
        vector_size = len(embeddings[0])
        self._ensure_qdrant_collection(collection_name, vector_size)

        points = []
        for idx, vector in enumerate(embeddings):
            payload = dict(metadatas[idx] or {}) if idx < len(metadatas) else {}
            text_value = documents[idx] if idx < len(documents) else None
            if text_value is not None:
                payload.setdefault("text", text_value)
            payload = {k: v for k, v in payload.items() if v is not None}
            point_id = ids[idx] if idx < len(ids) else uuid.uuid4().hex
            points.append(
                qdrant_models.PointStruct(id=point_id, vector=vector, payload=payload)
            )

        if not points:
            return

        self.qdrant_client.upsert(collection_name=collection_name, points=points)
        logger.info(f"{len(points)} vecteurs upsertés dans Qdrant '{collection_name}'.")

    def _qdrant_query(
        self,
        collection_name: str,
        query_vector: List[float],
        n_results: int,
        where_filter: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if self.qdrant_client is None or qdrant_models is None:
            return []
        filter_obj = self._build_qdrant_filter(where_filter)
        try:
            results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=max(1, n_results),
                with_payload=True,
                with_vectors=False,
                filter=filter_obj,
            )
        except Exception as e:
            logger.error(
                f"Échec recherche Qdrant '{collection_name}': {e}", exc_info=True
            )
            return []

        formatted: List[Dict[str, Any]] = []
        for scored in results or []:
            payload = dict(scored.payload or {})
            text_value = payload.pop("text", None)
            formatted.append(
                {
                    "id": str(scored.id),
                    "text": text_value,
                    "metadata": payload,
                    "distance": scored.score,
                }
            )
        return formatted

    def _qdrant_delete(
        self,
        collection_name: str,
        where_filter: Optional[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> None:
        if self.qdrant_client is None or qdrant_models is None:
            return
        if ids:
            selector = qdrant_models.PointIdsList(points=[str(i) for i in ids])
        else:
            filter_obj = self._build_qdrant_filter(where_filter)
            if not filter_obj:
                logger.warning(
                    f"Suppression Qdrant '{collection_name}' ignorée (aucun filtre)."
                )
                return
            selector = qdrant_models.FilterSelector(filter=filter_obj)
        try:
            self.qdrant_client.delete(
                collection_name=collection_name, points_selector=selector
            )
        except Exception as e:
            logger.error(
                f"Échec suppression Qdrant '{collection_name}': {e}", exc_info=True
            )

    def _qdrant_get(
        self,
        collection_name: str,
        where_filter: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        if self.qdrant_client is None or qdrant_models is None:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]]}
        filter_obj = self._build_qdrant_filter(where_filter)
        fetched = []
        offset = None
        remaining = limit if limit is not None else None
        while True:
            batch_size = 128
            if remaining is not None:
                if remaining <= 0:
                    break
                batch_size = min(batch_size, remaining)
            try:
                page, offset = self.qdrant_client.scroll(
                    collection_name=collection_name,
                    limit=batch_size,
                    filter=filter_obj,
                    with_payload=True,
                    with_vectors=False,
                    offset=offset,
                )
            except Exception as e:
                logger.error(
                    f"Échec scroll Qdrant '{collection_name}': {e}", exc_info=True
                )
                break
            if not page:
                break
            fetched.extend(page)
            if remaining is not None:
                remaining -= len(page)
                if remaining <= 0:
                    break
            if offset is None:
                break

        ids = [[str(r.id) for r in fetched]]
        documents = [[(r.payload or {}).get("text") for r in fetched]]
        metadatas = [
            [
                {k: v for k, v in (r.payload or {}).items() if k != "text"}
                for r in fetched
            ]
        ]
        return {"ids": ids, "documents": documents, "metadatas": metadatas}

    def _qdrant_delete_via_collection(
        self,
        collection_name: str,
        where_filter: Optional[Dict[str, Any]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        self._qdrant_delete(collection_name, where_filter, ids)

    # ---------- API publique ----------
    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Get or create a ChromaDB collection with optimized HNSW parameters.

        Args:
            name: Collection name
            metadata: Optional collection metadata (HNSW config, etc.)
                     Default: Optimized for LTM queries (M=16, space=cosine)

        Returns:
            Collection object (ChromaDB or QdrantCollectionAdapter)
        """
        self._ensure_inited()
        if self.backend == "qdrant":
            return QdrantCollectionAdapter(self, name)

        # Default optimized metadata for LTM collections (P2 performance)
        if metadata is None:
            metadata = {
                "hnsw:space": "cosine",  # Cosine similarity (standard for embeddings)
                "hnsw:M": 16,  # Connections per node (balance precision/speed)
                # Note: ChromaDB v0.4+ auto-optimizes metadata filters (user_id, type, confidence)
                # No explicit index creation needed
            }

        try:
            collection = self.client.get_or_create_collection(  # type: ignore[union-attr]
                name=name,
                metadata=metadata
            )
            logger.info(
                f"Collection '{name}' chargée/créée avec HNSW optimisé "
                f"(M={metadata.get('hnsw:M', 'default')}, space={metadata.get('hnsw:space', 'default')})"
            )
            return collection
        except Exception as e:
            logger.error(
                f"Impossible de get/create la collection '{name}': {e}", exc_info=True
            )
            raise

    def add_items(
        self, collection, items: List[Dict[str, Any]], item_text_key: str = "text"
    ) -> None:
        self._ensure_inited()
        if not items:
            logger.warning(f"Tentative d'ajout d'items vides à '{collection.name}'.")
            return
        try:
            ids = [item["id"] for item in items]
            documents_text = [item[item_text_key] for item in items]
            metadatas = [item.get("metadata", {}) for item in items]

            precomputed_embeddings: List[List[float]] = []
            use_precomputed = True
            for item in items:
                embedding = item.get("embedding")
                if embedding is None:
                    use_precomputed = False
                    break
                precomputed_embeddings.append(list(embedding))

            if use_precomputed:
                embeddings_list = precomputed_embeddings
            else:
                embeddings = self.model.encode(documents_text, show_progress_bar=False)  # type: ignore[union-attr]
                embeddings_list = (
                    embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings
                )

            if self.backend == "qdrant":
                collection_name = getattr(collection, "name", str(collection))
                self._qdrant_upsert(
                    collection_name, ids, embeddings_list, documents_text, metadatas
                )
            else:
                collection.upsert(
                    embeddings=embeddings_list,
                    documents=documents_text,
                    metadatas=metadatas,
                    ids=ids,
                )
                logger.info(
                    f"{len(ids)} items ajoutés/mis à jour dans '{collection.name}'."
                )
        except Exception as e:
            logger.error(
                f"Échec de l'ajout d'items à '{collection.name}': {e}", exc_info=True
            )
            raise

    def query(
        self,
        collection,
        query_text: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_inited()
        if not query_text:
            return []
        try:
            embeddings = self.model.encode([query_text], show_progress_bar=False)  # type: ignore[union-attr]
            embeddings_list = (
                embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings
            )
            if self.backend == "qdrant":
                collection_name = getattr(collection, "name", str(collection))
                vector = embeddings_list[0] if embeddings_list else []
                return self._qdrant_query(
                    collection_name, vector, n_results, where_filter
                )

            results = collection.query(
                query_embeddings=embeddings_list,
                n_results=n_results,
                where=self._normalize_where(where_filter),
                include=["documents", "metadatas", "distances"],
            )

            formatted_results: List[Dict[str, Any]] = []
            if results and results.get("ids") and results["ids"][0]:
                ids = results["ids"][0]
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                dists = results.get("distances", [[]])[0]
                for i, doc_id in enumerate(ids):
                    formatted_results.append(
                        {
                            "id": doc_id,
                            "text": docs[i] if i < len(docs) else None,
                            "metadata": metas[i] if i < len(metas) else None,
                            "distance": dists[i] if i < len(dists) else None,
                        }
                    )
            return formatted_results
        except Exception as e:
            safe_q = (query_text or "")[:50]
            logger.error(
                f"Échec de la recherche '{safe_q}…' dans '{collection.name}': {e}",
                exc_info=True,
            )
            return []

    def update_metadatas(
        self, collection: Collection, ids: List[str], metadatas: List[Dict[str, Any]]
    ) -> None:
        self._ensure_inited()
        if not ids:
            return
        if len(ids) != len(metadatas):
            logger.warning(
                "update_metadatas: taille ids/metadatas incoherente - abandon."
            )
            return
        try:
            collection.update(ids=ids, metadatas=metadatas)
            logger.info(
                f"Metadatas mises a jour pour {len(ids)} items dans '{collection.name}'."
            )
        except Exception as e:
            logger.warning(
                f"Echec update metadatas '{collection.name}': {e}", exc_info=True
            )

    def _is_filter_empty(self, where_filter: Dict[str, Any]) -> bool:
        """Vérifie récursivement si un filtre est vide ou sans critères valides."""
        if not where_filter:
            return True

        # Vérifier opérateurs logiques ($and, $or, $not)
        for op in ["$and", "$or"]:
            if op in where_filter:
                values = where_filter[op]
                if isinstance(values, list):
                    # Liste vide → filtre vide
                    if not values:
                        return True
                    # Si toutes les sous-conditions sont vides → filtre vide
                    if all(self._is_filter_empty(v) if isinstance(v, dict) else False for v in values):
                        return True

        # Vérifier si toutes les valeurs sont None
        non_operator_keys = [k for k in where_filter.keys() if not k.startswith("$")]
        if non_operator_keys and all(where_filter[k] is None for k in non_operator_keys):
            return True

        return False

    def delete_vectors(
        self, collection: Collection, where_filter: Dict[str, Any]
    ) -> None:
        self._ensure_inited()
        if self._is_filter_empty(where_filter):
            logger.error(
                f"[VectorService] Suppression refusée sur '{collection.name}': "
                f"filtre vide ou invalide (protection suppression globale)"
            )
            raise ValueError("Cannot delete with empty or invalid filter (global deletion protection)")
        try:
            if self.backend == "qdrant":
                collection_name = getattr(collection, "name", str(collection))
                self._qdrant_delete(collection_name, where_filter)
            else:
                collection.delete(where=self._normalize_where(where_filter))
                logger.info(
                    f"Vecteurs supprimés de '{collection.name}' avec filtre {where_filter}."
                )
        except Exception as e:
            logger.error(
                f"Échec suppression vecteurs dans '{collection.name}': {e}",
                exc_info=True,
            )
            raise
