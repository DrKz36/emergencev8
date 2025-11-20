# src/backend/features/memory/hybrid_retriever.py
# V1.0 - Hybrid retrieval (BM25 + Vector) pour RAG avancé (P1.5 - Émergence V8)
"""
HybridRetriever : Combine BM25 (lexical) + recherche vectorielle (semantic)
pour améliorer la pertinence du RAG.

Paramètres configurables :
- alpha : poids du scoring vectoriel (0.0 = full BM25, 1.0 = full vector)
- score_threshold : seuil minimum pour retourner un résultat
- top_k : nombre de résultats finaux à retourner

Architecture :
- BM25 : scoring lexical basé sur les tokens (rank-bm25)
- Vector : scoring sémantique via embedding similarity
- Fusion : Reciprocal Rank Fusion (RRF) ou weighted average
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, cast
from collections import Counter
import math

from .rag_metrics import RAGMetricsTracker

logger = logging.getLogger(__name__)


class BM25Scorer:
    """
    BM25 (Okapi BM25) : algorithme de ranking lexical basé sur TF-IDF amélioré.
    Référence : https://en.wikipedia.org/wiki/Okapi_BM25

    Paramètres :
    - k1 : contrôle la saturation du term frequency (défaut 1.5)
    - b : contrôle l'importance de la longueur du document (défaut 0.75)
    """

    def __init__(
        self,
        corpus: List[str],
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.doc_freqs: List[Counter[str]] = []
        self.idf: Dict[str, float] = {}
        self.doc_len: List[int] = []
        self.avgdl: float = 0.0
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        """Tokenisation simple : lowercase + split sur non-alphanumériques"""
        tokens = re.findall(r"\b\w+\b", text.lower())
        return tokens

    def _build_index(self) -> None:
        """Construit l'index BM25 : doc_freqs, IDF, longueurs moyennes"""
        num_docs = len(self.corpus)
        if num_docs == 0:
            return

        # Calculer term frequencies par document
        for doc in self.corpus:
            tokens = self._tokenize(doc)
            self.doc_len.append(len(tokens))
            self.doc_freqs.append(Counter(tokens))

        self.avgdl = sum(self.doc_len) / num_docs if num_docs > 0 else 0

        # Calculer IDF : log((N - n(t) + 0.5) / (n(t) + 0.5))
        df: Dict[str, int] = {}  # document frequency par terme
        for freq in self.doc_freqs:
            for term in freq.keys():
                df[term] = df.get(term, 0) + 1

        for term, count in df.items():
            idf_val = math.log((num_docs - count + 0.5) / (count + 0.5) + 1.0)
            self.idf[term] = idf_val

    def get_scores(self, query: str) -> List[float]:
        """
        Calcule les scores BM25 pour chaque document du corpus.

        Formule BM25 :
        score(D, Q) = Σ IDF(qi) · (f(qi, D) · (k1 + 1)) / (f(qi, D) + k1 · (1 - b + b · |D| / avgdl))
        """
        query_tokens = self._tokenize(query)
        scores = [0.0] * len(self.corpus)

        for idx, freq_dict in enumerate(self.doc_freqs):
            doc_len = self.doc_len[idx]
            for term in query_tokens:
                if term not in freq_dict:
                    continue
                tf = freq_dict[term]
                idf = self.idf.get(term, 0.0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * doc_len / self.avgdl
                )
                scores[idx] += idf * (numerator / denominator)

        return scores


class HybridRetriever:
    """
    Retriever hybride combinant BM25 et recherche vectorielle.

    Workflow :
    1. Recherche BM25 sur le corpus textuel
    2. Recherche vectorielle via VectorService
    3. Fusion des scores (weighted average ou RRF)
    4. Filtrage par score_threshold
    5. Retour des top_k meilleurs résultats
    """

    def __init__(
        self,
        alpha: float = 0.5,
        score_threshold: float = 0.0,
        top_k: int = 5,
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75,
    ):
        """
        Args:
            alpha: Poids du scoring vectoriel (0.0 = full BM25, 1.0 = full vector)
            score_threshold: Seuil minimum de score pour retourner un résultat
            top_k: Nombre de résultats à retourner
            bm25_k1: Paramètre k1 de BM25 (saturation TF)
            bm25_b: Paramètre b de BM25 (normalisation longueur)
        """
        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"alpha doit être entre 0.0 et 1.0, reçu {alpha}")

        self.alpha = alpha
        self.score_threshold = score_threshold
        self.top_k = top_k
        self.bm25_k1 = bm25_k1
        self.bm25_b = bm25_b
        self.bm25_scorer: Optional[BM25Scorer] = None

    def _normalize_scores(self, scores: List[float]) -> List[float]:
        """Normalise les scores dans [0, 1]"""
        if not scores:
            return []
        max_score = max(scores)
        if max_score == 0:
            return [0.0] * len(scores)
        return [s / max_score for s in scores]

    def _merge_results(
        self,
        bm25_results: List[Tuple[int, float]],
        vector_results: List[Dict[str, Any]],
        all_texts: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Fusionne les résultats BM25 et vectoriels.

        Args:
            bm25_results: Liste de (index, score_bm25)
            vector_results: Liste de dicts avec 'id', 'text', 'metadata', 'distance'
            all_texts: Corpus complet (pour retrouver les textes par index)

        Returns:
            Liste de résultats hybrides triés par score décroissant
        """
        # Créer un mapping index → score BM25 normalisé
        bm25_scores_raw = [0.0] * len(all_texts)
        for idx, score in bm25_results:
            if 0 <= idx < len(all_texts):
                bm25_scores_raw[idx] = score

        bm25_scores_normalized = self._normalize_scores(bm25_scores_raw)

        # Créer un mapping text → score vectoriel (distance → similarity)
        vector_map: Dict[str, float] = {}
        for vr in vector_results:
            text = (vr.get("text") or "").strip()
            distance = vr.get("distance", 1.0)
            # Convertir distance en similarité (0 = loin, 1 = proche)
            similarity = 1.0 / (1.0 + distance) if distance > 0 else 1.0
            vector_map[text] = similarity

        # Normaliser les scores vectoriels
        if vector_map:
            max_vec_score = max(vector_map.values())
            if max_vec_score > 0:
                vector_map = {k: v / max_vec_score for k, v in vector_map.items()}

        # Combiner les scores : hybrid_score = (1 - alpha) * bm25 + alpha * vector
        hybrid_results: List[Dict[str, Any]] = []
        for idx, text in enumerate(all_texts):
            bm25_score = (
                bm25_scores_normalized[idx]
                if idx < len(bm25_scores_normalized)
                else 0.0
            )
            vector_score = vector_map.get(text, 0.0)

            hybrid_score = (1 - self.alpha) * bm25_score + self.alpha * vector_score

            if hybrid_score < self.score_threshold:
                continue

            # Retrouver les métadonnées depuis vector_results si disponible
            metadata = {}
            for vr in vector_results:
                if (vr.get("text") or "").strip() == text:
                    metadata = vr.get("metadata", {})
                    break

            hybrid_results.append(
                {
                    "text": text,
                    "score": hybrid_score,
                    "bm25_score": bm25_score,
                    "vector_score": vector_score,
                    "metadata": metadata,
                }
            )

        # Trier par score décroissant
        hybrid_results.sort(key=lambda x: x["score"], reverse=True)

        return hybrid_results[: self.top_k]

    def retrieve(
        self,
        query: str,
        corpus: List[str],
        vector_results: Optional[List[Dict[str, Any]]] = None,
        collection_name: str = "default",
    ) -> List[Dict[str, Any]]:
        """
        Récupère les meilleurs passages via scoring hybride.

        Args:
            query: Requête utilisateur
            corpus: Liste de tous les textes du corpus (pour BM25)
            vector_results: Résultats pré-calculés de la recherche vectorielle
                            (doit contenir 'text', 'metadata', 'distance')
            collection_name: Nom de la collection (pour métriques)

        Returns:
            Liste de résultats hybrides avec scores, triés par pertinence
        """
        if not query or not corpus:
            return []

        # Track metrics
        with RAGMetricsTracker(collection_name, "hybrid") as tracker:
            # 1. Scoring BM25
            self.bm25_scorer = BM25Scorer(corpus, k1=self.bm25_k1, b=self.bm25_b)
            bm25_scores = self.bm25_scorer.get_scores(query)
            bm25_results = [(idx, score) for idx, score in enumerate(bm25_scores)]
            bm25_results.sort(key=lambda x: x[1], reverse=True)

            # 2. Utiliser les résultats vectoriels (déjà calculés par VectorService)
            if vector_results is None:
                vector_results = []

            # 3. Fusion des scores
            hybrid_results = self._merge_results(bm25_results, vector_results, corpus)

            # 4. Calculer le nombre de résultats filtrés
            total_candidates = len(corpus)
            filtered_count = total_candidates - len(hybrid_results)
            if filtered_count > 0:
                tracker.record_filtered(filtered_count, "below_threshold")

            # 5. Enregistrer les résultats
            tracker.record_results(hybrid_results)

            logger.info(
                f"HybridRetriever: query='{query[:50]}...', "
                f"corpus_size={len(corpus)}, "
                f"bm25_top={bm25_results[0][1] if bm25_results else 0:.3f}, "
                f"hybrid_top={hybrid_results[0]['score'] if hybrid_results else 0:.3f}, "
                f"filtered={filtered_count}"
            )

        return hybrid_results


# ============================================================
# Helpers pour intégration avec VectorService
# ============================================================


def hybrid_query(
    vector_service: Any,
    collection: Any,
    query_text: str,
    n_results: int = 5,
    where_filter: Optional[Dict[str, Any]] = None,
    alpha: float = 0.5,
    score_threshold: float = 0.0,
    bm25_k1: float = 1.5,
    bm25_b: float = 0.75,
    collection_name: str = "default",
) -> List[Dict[str, Any]]:
    """
    Effectue une recherche hybride BM25 + vectorielle sur une collection.

    Args:
        vector_service: Instance de VectorService
        collection: Collection Chroma/Qdrant
        query_text: Requête utilisateur
        n_results: Nombre de résultats à retourner
        where_filter: Filtres de métadonnées (optionnel)
        alpha: Poids du scoring vectoriel (0.0 = full BM25, 1.0 = full vector)
        score_threshold: Seuil minimum de score
        bm25_k1: Paramètre k1 de BM25
        bm25_b: Paramètre b de BM25
        collection_name: Nom de la collection (pour métriques)

    Returns:
        Liste de résultats hybrides avec scores détaillés
    """
    # 1. Recherche vectorielle classique
    vector_results = vector_service.query(
        collection=collection,
        query_text=query_text,
        n_results=n_results * 2,  # Récupérer plus de résultats pour le reranking
        where_filter=where_filter,
    )

    if not vector_results:
        return []

    # 2. Construire le corpus pour BM25
    corpus = [r.get("text", "") for r in vector_results if r.get("text")]

    if not corpus:
        return cast(list[dict[str, Any]], vector_results[:n_results])

    # 3. Appliquer le retriever hybride
    retriever = HybridRetriever(
        alpha=alpha,
        score_threshold=score_threshold,
        top_k=n_results,
        bm25_k1=bm25_k1,
        bm25_b=bm25_b,
    )

    hybrid_results = retriever.retrieve(
        query=query_text,
        corpus=corpus,
        vector_results=vector_results,
        collection_name=collection_name,
    )

    return hybrid_results
