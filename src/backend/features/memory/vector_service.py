# mypy: ignore-errors
# src/backend/features/memory/vector_service.py
# V3.6.0 (V13.2 - Startup-safe RAG)
#          - Lazy-load sûr (double-checked lock) + télémétrie ultra-OFF conservée
#          - __init__ ne charge plus ni SBERT ni Chroma
#          - _ensure_inited() déclenché au 1er appel public
#          - Pré-check corruption + backup AVANT init Chroma (inchangé)
#          - API publique identique
#          - 🆕 V13.2: Mode READ-ONLY fallback si ChromaDB indisponible au démarrage
#            Écritures bloquées (upsert/update/delete) avec logs structurés
#            Nouvelles méthodes: get_vector_mode(), get_last_init_error(), is_vector_store_reachable()

import logging
import os
import shutil
import sqlite3
import sys
import types
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union, cast


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


def _env_flag(name: str, default: str = "0") -> bool:
    value = os.getenv(name, default)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


class _StubSentenceTransformer:
    """Minimal stub used when SentenceTransformer cannot be loaded (tests/offline)."""

    def __init__(self, embedding_dim: int = 384) -> None:
        self.embedding_dim = embedding_dim

    def encode(
        self,
        sentences: Union[str, Iterable[str]],
        show_progress_bar: bool = False,
        convert_to_tensor: bool = False,
        **_: Any,
    ) -> Any:
        if isinstance(sentences, str):
            normalized: List[str] = [sentences]
        else:
            normalized = list(sentences or [])

        try:
            import numpy as np

            embeddings = np.zeros(
                (len(normalized), self.embedding_dim), dtype="float32"
            )
        except Exception:
            embeddings = [[0.0] * self.embedding_dim for _ in normalized]

        if convert_to_tensor:
            try:
                import torch

                return torch.as_tensor(embeddings)
            except Exception:
                pass

        return embeddings

    __call__ = encode


class _VectorEmbeddingFunction:
    """Embedding function wrapper compatible with Chroma's interface."""

    def __init__(self, service: "VectorService") -> None:
        self._service = service

    def __call__(self, input: Sequence[str]) -> List[List[float]]:
        if not input:
            return []
        encoded = self._service.model.encode(list(input), show_progress_bar=False)  # type: ignore[union-attr]
        if hasattr(encoded, "tolist"):
            return encoded.tolist()
        return cast(List[List[float]], encoded)


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


# ---- Memory Config Loader ----
class MemoryConfig:
    """Configuration pour le système de retrieval pondéré par l'horodatage."""

    def __init__(self, config_path: Optional[str] = None):
        # Valeurs par défaut
        self.decay_lambda = 0.02
        self.reinforcement_alpha = 0.1
        self.top_k = 8
        self.score_threshold = 0.2
        self.enable_trace_logging = False
        self.gc_inactive_days = 180

        # Charger depuis fichier si disponible
        if config_path is None:
            # Chemin par défaut
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "memory_config.json")

        if os.path.exists(config_path):
            try:
                import json

                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Charger la section "default" si elle existe
                    config_data = data.get("default", data)
                    self.decay_lambda = config_data.get(
                        "decay_lambda", self.decay_lambda
                    )
                    self.reinforcement_alpha = config_data.get(
                        "reinforcement_alpha", self.reinforcement_alpha
                    )
                    self.top_k = config_data.get("top_k", self.top_k)
                    self.score_threshold = config_data.get(
                        "score_threshold", self.score_threshold
                    )
                    self.enable_trace_logging = config_data.get(
                        "enable_trace_logging", self.enable_trace_logging
                    )
                    self.gc_inactive_days = config_data.get(
                        "gc_inactive_days", self.gc_inactive_days
                    )
                logger.info(
                    f"MemoryConfig chargée depuis {config_path}: λ={self.decay_lambda}, α={self.reinforcement_alpha}, "
                    f"top_k={self.top_k}, threshold={self.score_threshold}"
                )
            except Exception as e:
                logger.warning(
                    f"Impossible de charger {config_path}, utilisation des valeurs par défaut: {e}"
                )
        else:
            logger.info(
                f"Fichier config {config_path} absent, utilisation des valeurs par défaut"
            )

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Charge la config depuis les variables d'environnement (priorité sur le fichier JSON)."""
        config = cls()
        # Override depuis env si présent
        if os.getenv("MEMORY_DECAY_LAMBDA"):
            try:
                config.decay_lambda = float(os.getenv("MEMORY_DECAY_LAMBDA"))
            except ValueError:
                pass
        if os.getenv("MEMORY_REINFORCEMENT_ALPHA"):
            try:
                config.reinforcement_alpha = float(
                    os.getenv("MEMORY_REINFORCEMENT_ALPHA")
                )
            except ValueError:
                pass
        if os.getenv("MEMORY_TOP_K"):
            try:
                config.top_k = int(os.getenv("MEMORY_TOP_K"))
            except ValueError:
                pass
        if os.getenv("MEMORY_TRACE_LOGGING"):
            config.enable_trace_logging = os.getenv(
                "MEMORY_TRACE_LOGGING", ""
            ).lower() in {"1", "true", "yes"}
        return config


# ---- P2.2 - RAG freshness & diversity helpers ----
def recency_decay(age_days: float, half_life: float = 90.0) -> float:
    """
    Calcule un facteur de décroissance temporelle exponentiel.

    Args:
        age_days: Âge du document en jours (0 = aujourd'hui)
        half_life: Nombre de jours pour que le poids soit divisé par 2 (défaut: 90j)

    Returns:
        Float entre 0 et 1 (1 = document très récent, 0 = très ancien)

    Exemples:
        - age_days=0   → 1.0   (aujourd'hui)
        - age_days=90  → 0.5   (3 mois)
        - age_days=180 → 0.25  (6 mois)
        - age_days=270 → 0.125 (9 mois)
    """
    if age_days < 0:
        age_days = 0
    return 0.5 ** (age_days / half_life)


def compute_memory_score(
    cosine_sim: float,
    delta_days: float,
    freq: int,
    lambda_: float = 0.02,
    alpha: float = 0.1,
) -> float:
    """
    Calcule un score pondéré combinant similarité sémantique, fraîcheur temporelle et fréquence d'utilisation.

    Formule : score = cosine_sim × exp(-λ × Δt) × (1 + α × freq)

    où :
    - cosine_sim : similarité cosine entre query et mémoire (0-1)
    - Δt : nombre de jours depuis last_used_at
    - freq : nombre d'utilisations récentes (use_count)
    - λ (lambda) : taux de décroissance temporelle (0.01-0.05 recommandé)
    - α (alpha) : facteur de renforcement par usage (0.05-0.2 recommandé)

    Args:
        cosine_sim: Similarité cosine (0-1, 1 = identique)
        delta_days: Jours depuis dernière utilisation (Δt)
        freq: Nombre d'utilisations (use_count)
        lambda_: Taux de décroissance exponentielle (défaut: 0.02)
                 Plus λ est grand, plus l'oubli est rapide
                 Exemples: λ=0.02 → demi-vie ~35 jours, λ=0.05 → demi-vie ~14 jours
        alpha: Facteur de renforcement par fréquence (défaut: 0.1)
               Exemples: α=0.1, freq=5 → boost +50%

    Returns:
        Score pondéré (float > 0)

    Exemples:
        >>> # Mémoire récente très utilisée
        >>> compute_memory_score(0.85, delta_days=2, freq=10, lambda_=0.02, alpha=0.1)
        1.615  # Excellent score (récent + fréquent)

        >>> # Mémoire ancienne peu utilisée
        >>> compute_memory_score(0.85, delta_days=100, freq=1, lambda_=0.02, alpha=0.1)
        0.115  # Score faible (ancien + rare)

        >>> # Mémoire ancienne mais très utilisée
        >>> compute_memory_score(0.85, delta_days=50, freq=20, lambda_=0.02, alpha=0.1)
        0.864  # Score moyen-bon (renforcement compense l'ancienneté)
    """
    import math

    # Protection contre valeurs invalides
    cosine_sim = max(0.0, min(1.0, cosine_sim))
    delta_days = max(0.0, delta_days)
    freq = max(0, freq)
    lambda_ = max(0.001, lambda_)
    alpha = max(0.0, alpha)

    # Décroissance temporelle : exp(-λ × Δt)
    freshness_weight = math.exp(-lambda_ * delta_days)

    # Renforcement par fréquence : (1 + α × freq)
    reinforcement = 1.0 + alpha * freq

    # Score final combiné
    score = cosine_sim * freshness_weight * reinforcement

    return score


def mmr(
    query_embedding: List[float],
    candidates: List[Dict[str, Any]],
    k: int = 5,
    lambda_param: float = 0.7,
) -> List[Dict[str, Any]]:
    """
    Maximal Marginal Relevance - sélectionne les k résultats les plus pertinents ET diversifiés.

    Formule: MMR = λ * sim(query, doc) - (1-λ) * max(sim(doc, selected))

    Args:
        query_embedding: Embedding de la requête
        candidates: Liste de dicts avec {id, text, metadata, distance, embedding}
        k: Nombre de résultats à retourner
        lambda_param: Balance pertinence/diversité (1.0 = full pertinence, 0.0 = full diversité)

    Returns:
        Liste de k résultats ordonnés par score MMR décroissant
    """
    import numpy as np

    if not candidates or k <= 0:
        return []

    # Prendre au max k résultats
    k = min(k, len(candidates))

    # Si un seul résultat, pas besoin de MMR
    if k == 1 or len(candidates) == 1:
        return candidates[:1]

    # Convertir query en numpy
    query_vec = np.array(query_embedding)

    # Assurer que tous les candidats ont un embedding
    # (si pas présent, utiliser l'embedding query comme fallback - pas idéal mais safe)
    for cand in candidates:
        if "embedding" not in cand or cand["embedding"] is None:
            cand["embedding"] = query_embedding

    # Extraire embeddings des candidats
    candidate_vecs = [np.array(c["embedding"]) for c in candidates]

    # Fonction de similarité cosine
    def cosine_sim(a, b):
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    # Calcul de la similarité query<->candidates
    query_sims = [cosine_sim(query_vec, vec) for vec in candidate_vecs]

    # Indices des candidats sélectionnés et restants
    selected_indices: List[int] = []
    remaining_indices = list(range(len(candidates)))

    # Premier résultat : le plus similaire à la query
    best_idx = int(np.argmax(query_sims))
    selected_indices.append(best_idx)
    remaining_indices.remove(best_idx)

    # Sélection itérative des k-1 autres résultats
    while len(selected_indices) < k and remaining_indices:
        mmr_scores = []
        for idx in remaining_indices:
            # Pertinence par rapport à la query
            relevance = query_sims[idx]

            # Similarité max avec les docs déjà sélectionnés
            max_sim_selected = max(
                cosine_sim(candidate_vecs[idx], candidate_vecs[sel_idx])
                for sel_idx in selected_indices
            )

            # Score MMR
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_selected
            mmr_scores.append((idx, mmr_score))

        # Sélectionner le meilleur score MMR
        best_idx, _ = max(mmr_scores, key=lambda x: x[1])
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)

    # Retourner les résultats sélectionnés dans l'ordre MMR
    return [candidates[idx] for idx in selected_indices]


def compute_specificity_score(text: str) -> float:
    """
    Calcule un score de spécificité basé sur la densité de contenu informatif.

    Critères:
    - Densité de tokens rares (long tokens > 6 caractères)
    - Densité de nombres/dates
    - Densité d'entités nommées (mots capitalisés)

    Args:
        text: Texte du chunk à analyser

    Returns:
        Score de spécificité entre 0 et 1 (0 = peu spécifique, 1 = très spécifique)

    Examples:
        >>> compute_specificity_score("The configuration parameter is 0.75")
        0.82  # Haute spécificité (nombres + tokens longs)

        >>> compute_specificity_score("this is a simple text")
        0.15  # Basse spécificité (mots communs courts)
    """
    if not text or not text.strip():
        return 0.0

    import re

    # Tokenize (split by whitespace and punctuation)
    tokens = re.findall(r"\b\w+\b", text)
    if not tokens:
        return 0.0

    total_tokens = len(tokens)

    # 1. Densité tokens rares (IDF approximé)
    # Heuristique: tokens longs (> 6 car) + tokens mixtes alphanumériques
    rare_tokens = [t for t in tokens if len(t) > 6 or any(c.isdigit() for c in t)]
    rare_density = len(rare_tokens) / total_tokens

    # 2. Densité nombres/dates
    # Regex: nombres décimaux, années, dates
    numbers = re.findall(r"\b\d+\.?\d*\b|\b\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b", text)
    number_density = len(numbers) / total_tokens

    # 3. Densité entités nommées (heuristique: mots capitalisés hors début de phrase)
    # Split en phrases
    sentences = re.split(r"[.!?]+", text)
    capitalized = []
    for sentence in sentences:
        words = re.findall(r"\b[A-Z][a-z]+\b", sentence)
        # Exclure le premier mot (probablement début de phrase)
        if len(words) > 1:
            capitalized.extend(words[1:])
        elif len(words) == 1:
            # Si un seul mot et pas en début de phrase, c'est probablement une entité
            if sentence.strip() and not sentence.strip().startswith(words[0]):
                capitalized.append(words[0])

    ner_density = len(capitalized) / total_tokens if capitalized else 0.0

    # Combinaison pondérée des 3 facteurs
    # Poids: rare_tokens (40%), numbers (30%), NER (30%)
    specificity_score = rare_density * 0.40 + number_density * 0.30 + ner_density * 0.30

    # Normaliser sur [0, 1] avec saturation douce (tanh)
    import math

    normalized_score = math.tanh(
        specificity_score * 2.0
    )  # tanh(x*2) → saturation à ~0.96 pour x=1

    return max(0.0, min(1.0, normalized_score))


def rerank_with_lexical_overlap(
    query: str,
    results: List[Dict[str, Any]],
    topk: int = 8,
    cosine_weight: float = 0.7,
    lexical_weight: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    Re-ranke les résultats en combinant score cosine et overlap lexical (Jaccard).

    Formule: rerank_score = cosine_weight * cosine_sim + lexical_weight * jaccard(query, text)

    Args:
        query: Requête utilisateur
        results: Liste de résultats avec {text, distance, ...}
        topk: Nombre de résultats à retourner après re-ranking
        cosine_weight: Poids du score cosine (défaut: 0.7)
        lexical_weight: Poids du score Jaccard (défaut: 0.3)

    Returns:
        Liste de résultats re-rankés (top-k)

    Examples:
        >>> results = [
        ...     {"text": "machine learning model training", "distance": 0.3},
        ...     {"text": "deep learning neural networks", "distance": 0.4},
        ... ]
        >>> reranked = rerank_with_lexical_overlap("train ML model", results, topk=2)
        >>> reranked[0]["text"]
        "machine learning model training"  # Meilleur score lexical
    """
    if not results or topk <= 0:
        return []

    import re

    # Fonction de lemmatisation simple (lowercase + strip)
    def simple_lemmatize(text: str) -> set[str]:
        """Tokenize et normalise le texte (lowercase, alphanumérique uniquement)."""
        tokens = re.findall(r"\b\w+\b", text.lower())
        return set(tokens)

    # Lemmatiser la query
    query_lemmas = simple_lemmatize(query)

    # Calculer Jaccard similarity pour chaque résultat
    scored_results = []
    for r in results:
        text = r.get("text", "")
        distance = r.get("distance", 1.0)

        # Score cosine (distance L2 squared → cosine)
        # ChromaDB L2 squared: distance = 2 * (1 - cosine_sim)
        cosine_sim = max(0.0, 1.0 - (distance / 2.0))

        # Score Jaccard
        text_lemmas = simple_lemmatize(text)
        if query_lemmas and text_lemmas:
            intersection = len(query_lemmas & text_lemmas)
            union = len(query_lemmas | text_lemmas)
            jaccard_score = intersection / union if union > 0 else 0.0
        else:
            jaccard_score = 0.0

        # Score de rerank combiné
        rerank_score = cosine_weight * cosine_sim + lexical_weight * jaccard_score

        # Enrichir résultat avec les scores
        result_copy = dict(r)
        result_copy["cosine_sim"] = round(cosine_sim, 4)
        result_copy["jaccard_score"] = round(jaccard_score, 4)
        result_copy["rerank_score"] = round(rerank_score, 4)

        scored_results.append(result_copy)

    # Trier par rerank_score décroissant
    scored_results.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)

    # Retourner top-k
    return scored_results[:topk]


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
    VectorService V3.6.0 (V13.2 - Startup-safe RAG)
    - API identique.
    - Lazy-load: modèle SBERT + backend vectoriel (Chroma ou Qdrant) instanciés au 1er usage.
    - Auto-reset AVANT instanciation Chroma si DB corrompue (évite locks Windows).
    - Télémétrie Chroma/PostHog durcie (env + shim).
    - Normalisation des filtres where conservée.
    - Backend Qdrant optionnel (via qdrant-client) avec fallback automatique sur Chroma.
    - 🆕 V13.2: Mode READ-ONLY fallback si ChromaDB indisponible au démarrage.
      Écritures bloquées avec logs structurés. Endpoint /health/ready expose status.
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

        # V13.2 - Startup-safe mode
        self._vector_mode = "readwrite"  # "readwrite" | "readonly"
        self._last_init_error: Optional[str] = None

        # 🧪 Tests/offline: autoriser un stub SBERT si configuré
        self._allow_stub_model = _env_flag("VECTOR_SERVICE_ALLOW_STUB") or _env_flag(
            "ALLOW_SENTENCE_TRANSFORMER_STUB"
        )
        stub_dim_env = os.getenv("VECTOR_SERVICE_STUB_DIM") or os.getenv(
            "SENTENCE_TRANSFORMER_STUB_DIM"
        )
        try:
            self._stub_embedding_dim = int(stub_dim_env) if stub_dim_env else 384
        except (TypeError, ValueError):
            self._stub_embedding_dim = 384
        self._using_stub_model = False

        # 🆕 Score cache pour performance
        from backend.features.memory.score_cache import ScoreCache

        cache_size = int(os.getenv("MEMORY_SCORE_CACHE_SIZE", "10000"))
        cache_ttl = int(os.getenv("MEMORY_SCORE_CACHE_TTL", "3600"))
        self.score_cache = ScoreCache(max_size=cache_size, ttl_seconds=cache_ttl)
        logger.info(
            f"[VectorService] Score cache initialisé (size={cache_size}, ttl={cache_ttl}s)"
        )

        # 🆕 Métriques Prometheus pour weighted retrieval
        from backend.features.memory.weighted_retrieval_metrics import (
            WeightedRetrievalMetrics,
        )

        self.metrics = WeightedRetrievalMetrics()
        logger.info("[VectorService] Métriques Prometheus initialisées")

        # Weighted retrieval config
        self.memory_config = MemoryConfig.from_env()
        logger.info(
            f"VectorService: Weighted retrieval activé (λ={self.memory_config.decay_lambda}, "
            f"α={self.memory_config.reinforcement_alpha}, top_k={self.memory_config.top_k})"
        )

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
                    if self._allow_stub_model:
                        logger.warning(
                            "VectorService: fallback stub activé pour '%s' (dim=%s).",
                            self.embed_model_name,
                            self._stub_embedding_dim,
                        )
                        self.model = _StubSentenceTransformer(self._stub_embedding_dim)
                        self._using_stub_model = True
                    else:
                        self._last_init_error = str(e)
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

    def _build_collection_embedding_function(self):
        return _VectorEmbeddingFunction(self)

    # ---------- V13.2 - Startup-safe READ-ONLY mode ----------
    def _check_write_allowed(self, operation: str, collection_name: str = "") -> None:
        """
        Vérifie si les écritures sont autorisées. Si mode readonly, log structuré et raise.
        """
        if self._vector_mode == "readonly":
            error_msg = (
                f"⚠️  Opération d'écriture bloquée (mode READ-ONLY): "
                f"op={operation}, collection={collection_name}, "
                f"reason=ChromaDB unavailable, last_error={self._last_init_error}"
            )
            logger.warning(error_msg)
            raise RuntimeError(
                f"VectorService en mode READ-ONLY (écritures bloquées). "
                f"Opération: {operation}"
            )

    def get_vector_mode(self) -> str:
        """Retourne le mode actuel: 'readwrite' ou 'readonly'"""
        return self._vector_mode

    def get_last_init_error(self) -> Optional[str]:
        """Retourne la dernière erreur d'initialisation (si readonly)"""
        return self._last_init_error

    def is_vector_store_reachable(self) -> bool:
        """
        Vérifie si le vector store (ChromaDB/Qdrant) est accessible.
        Retourne False si mode readonly ou si client non initialisé.
        """
        if self._vector_mode == "readonly":
            return False
        if self.backend == "chroma":
            return self.client is not None
        if self.backend == "qdrant":
            return self.qdrant_client is not None
        return False

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
    def _init_client_with_guard(self, path: str, allow_auto_reset: bool) -> Any:
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
                # V13.2 - Fallback READ-ONLY au lieu de crash
                error_msg = f"ChromaDB init failed: {e}"
                self._last_init_error = error_msg
                self._vector_mode = "readonly"
                logger.warning(
                    f"⚠️  VectorService basculé en mode READ-ONLY (ChromaDB indisponible). "
                    f"Écritures bloquées. Erreur: {e}",
                    exc_info=False,
                )
                return None  # Signal échec init sans crash

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
        self, name: str, metadata: Optional[Dict[str, Any]] = None
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

        embedding_fn = self._build_collection_embedding_function()

        try:
            collection = self.client.get_or_create_collection(  # type: ignore[union-attr]
                name=name,
                metadata=metadata,
                embedding_function=embedding_fn,
            )
            # Certaines versions de Chroma ignorent embedding_function si collection existante
            try:
                setattr(collection, "_embedding_function", embedding_fn)
            except Exception:
                pass
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
        collection_name = getattr(collection, "name", str(collection))
        self._check_write_allowed("vector_upsert", collection_name)
        if not items:
            logger.warning(f"Tentative d'ajout d'items vides à '{collection.name}'.")
            return
        try:
            ids = [item["id"] for item in items]
            documents_text = [item[item_text_key] for item in items]

            # ChromaDB only accepts str, int, float, bool in metadata - filter out invalid types
            # Filter out None, lists, dicts, and any other non-primitive types
            metadatas = [
                {
                    k: v
                    for k, v in item.get("metadata", {}).items()
                    if isinstance(v, (str, int, float, bool))
                }
                for item in items
            ]

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
        apply_recency: bool = True,  # P2.2 - Enable recency decay
        apply_mmr: bool = True,  # P2.2 - Enable MMR diversity
        recency_half_life: float = 90.0,  # P2.2 - Half-life in days
        mmr_lambda: float = 0.7,  # P2.2 - MMR balance (0.7 = 70% relevance, 30% diversity)
        apply_specificity_boost: bool = True,  # P2.1 - Enable specificity scoring
        apply_rerank: bool = True,  # P2.1 - Enable lexical rerank
    ) -> List[Dict[str, Any]]:
        """
        Recherche vectorielle avec support optionnel de recency decay, MMR, specificity boost et rerank.

        Args:
            collection: Collection Chroma/Qdrant
            query_text: Texte de la requête
            n_results: Nombre de résultats souhaités
            where_filter: Filtre de métadonnées (optionnel)
            apply_recency: Appliquer la décroissance temporelle (défaut: True)
            apply_mmr: Appliquer MMR pour diversité (défaut: True)
            recency_half_life: Demi-vie pour recency decay en jours (défaut: 90)
            mmr_lambda: Balance MMR (1.0 = full relevance, 0.0 = full diversity)
            apply_specificity_boost: Appliquer boost spécificité (densité IDF/NER/nombres) (défaut: True)
            apply_rerank: Appliquer rerank lexical avec Jaccard (défaut: True)

        Returns:
            Liste de résultats avec {id, text, metadata, distance, [age_days, recency_score, specificity_score, rerank_score]}
        """
        self._ensure_inited()
        if not query_text:
            return []
        try:
            embeddings = self.model.encode([query_text], show_progress_bar=False)  # type: ignore[union-attr]
            embeddings_list = (
                embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings
            )
            query_embedding = embeddings_list[0] if embeddings_list else []

            if self.backend == "qdrant":
                collection_name = getattr(collection, "name", str(collection))
                raw_results = self._qdrant_query(
                    collection_name,
                    query_embedding,
                    n_results * 2,
                    where_filter,  # Fetch more for MMR
                )
            else:
                results = collection.query(
                    query_embeddings=embeddings_list,
                    n_results=n_results * 2,  # Fetch more candidates for MMR filtering
                    where=self._normalize_where(where_filter),
                    include=[
                        "documents",
                        "metadatas",
                        "distances",
                        "embeddings",
                    ],  # Need embeddings for MMR
                )

                raw_results: List[Dict[str, Any]] = []
                if results and results.get("ids") and results["ids"][0]:
                    ids = results["ids"][0]
                    docs = results.get("documents", [[]])[0]
                    metas = results.get("metadatas", [[]])[0]
                    dists = results.get("distances", [[]])[0]
                    embeds = (
                        results.get("embeddings", [[]])[0]
                        if "embeddings" in results
                        else [[]] * len(ids)
                    )
                    for i, doc_id in enumerate(ids):
                        # Fix: Avoid ambiguous truth check on numpy array
                        embed_value = embeds[i] if i < len(embeds) else None
                        use_embed = embed_value is not None and (
                            not hasattr(embed_value, "__len__") or len(embed_value) > 0
                        )
                        raw_results.append(
                            {
                                "id": doc_id,
                                "text": docs[i] if i < len(docs) else None,
                                "metadata": metas[i] if i < len(metas) else None,
                                "distance": dists[i] if i < len(dists) else None,
                                "embedding": embed_value
                                if use_embed
                                else query_embedding,
                            }
                        )

            # P2.2 - Apply recency decay if enabled
            if apply_recency and raw_results:
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc)
                for result in raw_results:
                    meta = result.get("metadata") or {}
                    ts_str = meta.get("ts") or meta.get("timestamp")
                    if ts_str:
                        try:
                            # Parse timestamp (ISO format expected)
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            age_days = (now - ts).total_seconds() / 86400
                            recency_score = recency_decay(
                                age_days, half_life=recency_half_life
                            )
                            result["age_days"] = round(age_days, 1)
                            result["recency_score"] = round(recency_score, 3)
                            # Adjust distance by recency (lower distance = better match)
                            # We boost relevance by dividing distance by recency factor
                            # (capped to avoid division by zero)
                            if result.get("distance") is not None:
                                recency_factor = max(recency_score, 0.1)  # Floor at 0.1
                                result["distance"] = result["distance"] / recency_factor
                        except Exception:
                            pass  # Skip recency for malformed timestamps

            # Sort by adjusted distance (lower = better)
            raw_results.sort(key=lambda x: x.get("distance", float("inf")))

            # P2.1 - Apply specificity boost if enabled
            if apply_specificity_boost and raw_results:
                specificity_weight = float(os.getenv("RAG_SPECIFICITY_WEIGHT", "0.15"))
                collection_name = getattr(collection, "name", "unknown")

                for result in raw_results:
                    text = result.get("text", "")
                    distance = result.get("distance", 1.0)

                    # Calculer score de spécificité
                    specificity_score = compute_specificity_score(text)
                    result["specificity_score"] = round(specificity_score, 4)

                    # 📊 Enregistrer métrique Prometheus
                    try:
                        from backend.features.memory.rag_metrics import (
                            memory_rag_precision_score,
                        )

                        memory_rag_precision_score.labels(
                            collection=collection_name, metric_type="specificity"
                        ).observe(specificity_score)
                    except Exception:
                        pass  # Graceful degradation si Prometheus indisponible

                    # Combiner avec score cosine
                    # Distance ChromaDB → Score cosine : cosine = 1 - (distance / 2)
                    cosine_score = max(0.0, 1.0 - (distance / 2.0))

                    # Score final combiné : weighted average
                    # final_score = (1 - weight) * cosine + weight * specificity
                    combined_score = (
                        1 - specificity_weight
                    ) * cosine_score + specificity_weight * specificity_score

                    # 📊 Enregistrer score combiné
                    try:
                        memory_rag_precision_score.labels(
                            collection=collection_name, metric_type="combined"
                        ).observe(combined_score)
                    except Exception:
                        pass

                    # Convertir score en distance (pour tri) : distance = 2 * (1 - score)
                    result["distance"] = 2.0 * (1.0 - combined_score)
                    result["combined_score"] = round(combined_score, 4)

                # Re-trier par distance ajustée
                raw_results.sort(key=lambda x: x.get("distance", float("inf")))

            # P2.1 - Apply lexical rerank if enabled
            if apply_rerank and len(raw_results) > 1:
                rerank_topk = int(os.getenv("RAG_RERANK_TOPK", "8"))
                collection_name = getattr(collection, "name", "unknown")
                # Reranker avec top-k initial (on prend plus que n_results pour avoir du choix pour MMR)
                fetch_for_rerank = max(n_results * 2, rerank_topk * 2)
                candidates_for_rerank = raw_results[:fetch_for_rerank]

                raw_results = rerank_with_lexical_overlap(
                    query=query_text,
                    results=candidates_for_rerank,
                    topk=min(
                        len(candidates_for_rerank), rerank_topk * 2
                    ),  # Garder assez pour MMR
                    cosine_weight=0.7,
                    lexical_weight=0.3,
                )

                # 📊 Enregistrer métriques jaccard pour résultats reranked
                try:
                    from backend.features.memory.rag_metrics import (
                        memory_rag_precision_score,
                    )

                    for r in raw_results[:5]:  # Top-5 pour éviter trop de métriques
                        jaccard = r.get("jaccard_score", 0.0)
                        memory_rag_precision_score.labels(
                            collection=collection_name, metric_type="jaccard"
                        ).observe(jaccard)
                except Exception:
                    pass

            # P2.2 - Apply MMR if enabled
            if apply_mmr and len(raw_results) > 1:
                # MMR needs embeddings - ensure they're present
                final_results = mmr(
                    query_embedding=query_embedding,
                    candidates=raw_results,
                    k=n_results,
                    lambda_param=mmr_lambda,
                )
            else:
                final_results = raw_results[:n_results]

            # Clean up: remove embeddings from final results (internal use only)
            for res in final_results:
                res.pop("embedding", None)

            return final_results

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
        collection_name = getattr(collection, "name", str(collection))
        self._check_write_allowed("metadata_update", collection_name)
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
                    if all(
                        self._is_filter_empty(v) if isinstance(v, dict) else False
                        for v in values
                    ):
                        return True

        # Vérifier si toutes les valeurs sont None
        non_operator_keys = [k for k in where_filter.keys() if not k.startswith("$")]
        if non_operator_keys and all(
            where_filter[k] is None for k in non_operator_keys
        ):
            return True

        return False

    def delete_vectors(
        self, collection: Collection, where_filter: Dict[str, Any]
    ) -> None:
        self._ensure_inited()
        collection_name = getattr(collection, "name", str(collection))
        self._check_write_allowed("vector_delete", collection_name)
        if self._is_filter_empty(where_filter):
            logger.error(
                f"[VectorService] Suppression refusée sur '{collection.name}': "
                f"filtre vide ou invalide (protection suppression globale)"
            )
            raise ValueError(
                "Cannot delete with empty or invalid filter (global deletion protection)"
            )
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

    # ---------- Recherche hybride BM25 + Vectorielle (P1.5) ----------
    def hybrid_query(
        self,
        collection,
        query_text: str,
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
        alpha: float = 0.5,
        score_threshold: float = 0.0,
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75,
    ) -> List[Dict[str, Any]]:
        """
        Recherche hybride combinant BM25 (lexical) et vectorielle (sémantique).

        Args:
            collection: Collection Chroma/Qdrant
            query_text: Requête utilisateur
            n_results: Nombre de résultats finaux
            where_filter: Filtres de métadonnées (optionnel)
            alpha: Poids du scoring vectoriel (0.0 = full BM25, 1.0 = full vector)
            score_threshold: Seuil minimum de score pour retourner un résultat
            bm25_k1: Paramètre k1 de BM25 (saturation TF)
            bm25_b: Paramètre b de BM25 (normalisation longueur)

        Returns:
            Liste de résultats avec scores hybrides détaillés
        """
        try:
            from backend.features.memory.hybrid_retriever import (
                hybrid_query as _hybrid_query,
            )

            return _hybrid_query(
                vector_service=self,
                collection=collection,
                query_text=query_text,
                n_results=n_results,
                where_filter=where_filter,
                alpha=alpha,
                score_threshold=score_threshold,
                bm25_k1=bm25_k1,
                bm25_b=bm25_b,
            )
        except ImportError:
            logger.warning(
                "HybridRetriever non disponible, fallback sur query() classique"
            )
            return self.query(collection, query_text, n_results, where_filter)
        except Exception as e:
            logger.error(f"Erreur hybrid_query: {e}", exc_info=True)
            # Fallback sur query vectorielle standard
            return self.query(collection, query_text, n_results, where_filter)

    # ---------- Weighted Retrieval avec décroissance temporelle (P2.3) ----------
    def query_weighted(
        self,
        collection,
        query_text: str,
        n_results: Optional[int] = None,
        where_filter: Optional[Dict[str, Any]] = None,
        lambda_: Optional[float] = None,
        alpha: Optional[float] = None,
        score_threshold: Optional[float] = None,
        enable_trace: Optional[bool] = None,
        update_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Recherche vectorielle avec scoring pondéré combinant similarité, fraîcheur et fréquence d'utilisation.

        Formule : score = cosine_sim × exp(-λ × Δt) × (1 + α × freq)

        où :
        - cosine_sim : similarité entre query et mémoire
        - Δt : jours depuis last_used_at
        - freq : use_count (nombre de récupérations)
        - λ : taux de décroissance temporelle
        - α : facteur de renforcement par fréquence

        Args:
            collection: Collection Chroma/Qdrant
            query_text: Texte de requête
            n_results: Nombre de résultats (défaut: memory_config.top_k)
            where_filter: Filtre de métadonnées
            lambda_: Taux décroissance (défaut: memory_config.decay_lambda)
            alpha: Facteur renforcement (défaut: memory_config.reinforcement_alpha)
            score_threshold: Seuil minimum de score (défaut: memory_config.score_threshold)
            enable_trace: Active logs de trace (défaut: memory_config.enable_trace_logging)
            update_metadata: Met à jour last_used_at et use_count (défaut: True)

        Returns:
            Liste de résultats avec {id, text, metadata, distance, weighted_score, [trace_info]}

        Example:
            >>> results = vector_service.query_weighted(
            ...     collection=knowledge_collection,
            ...     query_text="CI/CD pipeline",
            ...     n_results=5
            ... )
            >>> for r in results:
            ...     print(f"{r['text']}: score={r['weighted_score']:.3f}")
        """
        self._ensure_inited()

        # Charger paramètres depuis config si non spécifiés
        lambda_ = lambda_ if lambda_ is not None else self.memory_config.decay_lambda
        alpha = alpha if alpha is not None else self.memory_config.reinforcement_alpha
        n_results = n_results if n_results is not None else self.memory_config.top_k
        score_threshold = (
            score_threshold
            if score_threshold is not None
            else self.memory_config.score_threshold
        )
        enable_trace = (
            enable_trace
            if enable_trace is not None
            else self.memory_config.enable_trace_logging
        )

        if not query_text:
            return []

        import time

        query_start = time.time()

        try:
            # 1. Récupérer candidats avec query standard (fetch plus pour re-ranking)
            fetch_size = max(n_results * 3, 20)
            raw_results = self.query(
                collection=collection,
                query_text=query_text,
                n_results=fetch_size,
                where_filter=where_filter,
                apply_recency=False,  # Désactiver recency decay standard (on utilise notre propre scoring)
                apply_mmr=False,  # Désactiver MMR (on trie par weighted_score)
            )

            if not raw_results:
                return []

            # 2. Calculer weighted scores pour chaque résultat
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            weighted_results = []
            collection_name = getattr(collection, "name", "unknown")

            for res in raw_results:
                meta = res.get("metadata", {})
                entry_id = res.get("id", "unknown")

                # Extraire métadonnées de retrieval
                last_used_str = meta.get("last_used_at") or ""
                use_count = int(meta.get("use_count", 0))

                # 🆕 Vérifier cache d'abord
                cached_score = self.score_cache.get(query_text, entry_id, last_used_str)
                if cached_score is not None:
                    # Cache hit → utiliser score caché
                    weighted_score = cached_score
                    cosine_sim = 0.0  # Pas recalculé (pas besoin)
                    delta_days = 0.0
                else:
                    # Cache miss → calculer score
                    score_start = time.time()

                    # Calculer Δt (jours depuis last_used_at)
                    if last_used_str:
                        try:
                            last_used = datetime.fromisoformat(
                                last_used_str.replace("Z", "+00:00")
                            )
                            delta_days = (now - last_used).total_seconds() / 86400
                        except Exception:
                            # Si parsing échoue, considérer comme jamais utilisé (très ancien)
                            delta_days = 999.0
                    else:
                        # Jamais utilisé → très ancien
                        delta_days = 999.0

                    # Calculer similarité cosine depuis distance
                    # ChromaDB L2 squared distance for normalized vectors: distance = 2 * (1 - cosine_sim)
                    distance = res.get("distance", 2.0)
                    cosine_sim = 1.0 - (distance / 2.0)

                    # Calculer score pondéré
                    weighted_score = compute_memory_score(
                        cosine_sim=cosine_sim,
                        delta_days=delta_days,
                        freq=use_count,
                        lambda_=lambda_,
                        alpha=alpha,
                    )

                    # 🆕 Stocker dans cache
                    self.score_cache.set(
                        query_text, entry_id, last_used_str, weighted_score
                    )

                    # 🆕 Métriques scoring
                    score_duration = time.time() - score_start
                    self.metrics.record_score(
                        collection_name, weighted_score, score_duration
                    )
                    self.metrics.record_entry_age(collection_name, delta_days)
                    self.metrics.record_use_count(collection_name, use_count)

                # Appliquer seuil
                if weighted_score < score_threshold:
                    continue

                # Enrichir résultat avec score et trace
                res["weighted_score"] = round(weighted_score, 4)
                res["cosine_sim"] = round(cosine_sim, 4)

                if enable_trace:
                    res["trace_info"] = {
                        "cosine_sim": round(cosine_sim, 4),
                        "delta_days": round(delta_days, 1),
                        "use_count": use_count,
                        "lambda": lambda_,
                        "alpha": alpha,
                        "weighted_score": round(weighted_score, 4),
                    }
                    logger.debug(
                        f"[Memory] Entry {res.get('id', 'unknown')[:8]}: "
                        f"sim={cosine_sim:.3f} | Δt={delta_days:.1f}j | freq={use_count} | score={weighted_score:.3f}"
                    )

                weighted_results.append(res)

            # 3. Trier par weighted_score décroissant
            weighted_results.sort(
                key=lambda x: x.get("weighted_score", 0.0), reverse=True
            )

            # 4. Conserver top_k
            final_results = weighted_results[:n_results]

            # 5. Mettre à jour métadonnées de retrieval (last_used_at, use_count)
            if update_metadata and final_results:
                self._update_retrieval_metadata(
                    collection=collection,
                    results=final_results,
                )

            score_info = (
                f", score_min={final_results[-1]['weighted_score']:.3f}"
                if final_results
                else ""
            )
            logger.info(
                f"[VectorService] Weighted query '{query_text[:30]}...': "
                f"{len(final_results)} résultats{score_info}"
            )

            # 🆕 Métriques requête
            query_duration = time.time() - query_start
            self.metrics.record_query(
                collection=collection_name,
                status="success",
                results_count=len(final_results),
                duration_seconds=query_duration,
            )

            return final_results

        except Exception as e:
            safe_q = (query_text or "")[:50]
            logger.error(
                f"Échec de la recherche pondérée '{safe_q}…' dans '{collection.name}': {e}",
                exc_info=True,
            )

            # 🆕 Métriques erreur
            collection_name = (
                getattr(collection, "name", "unknown") if collection else "unknown"
            )
            self.metrics.record_query(
                collection=collection_name,
                status="error",
                results_count=0,
                duration_seconds=time.time() - query_start,
            )

            return []

    def _update_retrieval_metadata(
        self,
        collection,
        results: List[Dict[str, Any]],
    ) -> None:
        """
        Met à jour les métadonnées de retrieval (last_used_at, use_count) pour les entrées récupérées.

        Args:
            collection: Collection Chroma/Qdrant
            results: Liste de résultats avec {id, metadata, ...}

        Returns:
            None
        """
        if not results:
            return

        import time

        update_start = time.time()

        try:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).isoformat()
            collection_name = getattr(collection, "name", "unknown")

            ids = []
            updated_metadatas = []

            for res in results:
                entry_id = res.get("id")
                if not entry_id:
                    continue

                meta = res.get("metadata", {})
                current_use_count = int(meta.get("use_count", 0))

                # Mise à jour
                new_meta = dict(meta)
                new_meta["last_used_at"] = now
                new_meta["use_count"] = current_use_count + 1

                # Filter out invalid types for ChromaDB (only str, int, float, bool)
                new_meta = {
                    k: v
                    for k, v in new_meta.items()
                    if isinstance(v, (str, int, float, bool))
                }

                ids.append(entry_id)
                updated_metadatas.append(new_meta)

                # 🆕 Invalider cache pour cette entrée (métadonnées changées)
                self.score_cache.invalidate(entry_id)

            if ids:
                self.update_metadatas(
                    collection=collection,
                    ids=ids,
                    metadatas=updated_metadatas,
                )
                logger.debug(
                    f"[VectorService] Metadatas de retrieval mis à jour pour {len(ids)} entrées"
                )

                # 🆕 Métriques metadata update
                update_duration = time.time() - update_start
                self.metrics.record_metadata_update(collection_name, update_duration)

        except Exception as e:
            logger.warning(
                f"Échec mise à jour retrieval metadata dans '{collection.name}': {e}",
                exc_info=True,
            )
