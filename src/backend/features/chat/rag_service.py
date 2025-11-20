# src/backend/features/chat/rag_service.py
"""
RAGService - Document Retrieval & Semantic Ranking

Extracted from ChatService to handle all RAG-related operations:
- Document querying from VectorService
- User intent parsing
- Semantic scoring & re-ranking
- Adjacent chunk merging
- Context formatting

✅ Phase 1 of ChatService decomposition
"""

import os
import re
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from backend.features.memory.vector_service import VectorService
from backend.features.chat.rag_metrics import RAGMetrics

logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Result of a RAG query with formatted context and metadata."""
    
    formatted_context: str
    sources: List[Dict[str, Any]]
    score: float
    hit_count: int
    cache_hit: bool = False


class RAGService:
    """
    Handles document retrieval, semantic scoring, and context formatting for RAG.
    
    🎯 Responsibilities:
    - Parse user intent from queries
    - Query vector database with filters
    - Compute semantic scores for ranking
    - Merge adjacent document chunks
    - Format context for LIM consumption
    """
    
    def __init__(
        self,
        vector_service: VectorService,
        document_service: Optional[Any] = None,
        metrics: Optional[RAGMetrics] = None
    ):
        """
        Initialize RAGService.
        
        Args:
            vector_service: VectorService for embeddings & search
            document_service: Optional DocumentService for document metadata
            metrics: Optional RAGMetrics for telemetry
        """
        self.vector_service = vector_service
        self.document_service = document_service
        self.metrics = metrics or RAGMetrics()
        
        # Collections
        self._knowledge_collection = None
        
        logger.info("RAGService initialized")
    
    async def query_documents(
        self,
        query: str,
        doc_ids: Optional[List[int]] = None,
        top_k: int = 5,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> RAGResult:
        """
        Query documents with semantic search and return formatted context.
        
        ✅ Phase 3 RAG: Multi-criteria semantic scoring + formatting
        
        Args:
            query: User query text
            doc_ids: Optional list of document IDs to filter
            top_k: Number of results to return
            user_id: Optional user ID for filtering
            agent_id: Optional agent ID for filtering
            session_id: Optional session ID for filtering
            
        Returns:
            RAGResult with formatted context and metadata
        """
        # Parse user intent
        user_intent = self.parse_intent(query)
        
        # Build where filter
        where_filter = self._build_where_filter(
            doc_ids=doc_ids,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id
        )
        
        # Query vector database
        collection = self._get_knowledge_collection()
        if not collection:
            logger.warning("[RAG] Knowledge collection not available")
            return RAGResult(
                formatted_context="",
                sources=[],
                score=0.0,
                hit_count=0
            )
        
        try:
            results = self.vector_service.query(
                collection=collection,
                query_text=user_intent["expanded_query"],
                n_results=top_k,
                where_filter=where_filter
            )
            
            if not results:
                return RAGResult(
                    formatted_context="",
                    sources=[],
                    score=0.0,
                    hit_count=0
                )
            
            # Convert to standardized format
            doc_hits = self._convert_results_to_hits(results)
            
            # Merge adjacent chunks
            merged_hits = self.merge_chunks(
                doc_hits=doc_hits,
                max_blocks=10,
                user_intent=user_intent
            )
            
            # Format context
            formatted_context = self.format_context(merged_hits)
            
            # Compute overall score (average distance)
            avg_score = sum(h.get("distance", 1.0) for h in merged_hits) / len(merged_hits) if merged_hits else 1.0
            
            return RAGResult(
                formatted_context=formatted_context,
                sources=merged_hits,
                score=avg_score,
                hit_count=len(merged_hits)
            )
            
        except Exception as e:
            logger.error(f"[RAG] Query failed: {e}", exc_info=True)
            return RAGResult(
                formatted_context="",
                sources=[],
                score=0.0,
                hit_count=0
            )
    
    def parse_intent(self, query: str) -> Dict[str, Any]:
        """
        Détecte l'intention de l'utilisateur pour adapter la recherche RAG.

        ✅ Phase 2 RAG Milestone 4 : Parsing d'intention pour filtrage sémantique

        Args:
            query: Requête utilisateur

        Returns:
            Dictionnaire avec :
            - wants_integral_citation: bool (si l'utilisateur veut une citation complète)
            - content_type: str | None ('poem', 'section', 'conversation')
            - keywords: List[str] (mots-clés extraits)
            - expanded_query: str (requête enrichie pour la recherche)
        """
        if not query:
            return {
                "wants_integral_citation": False,
                "content_type": None,
                "keywords": [],
                "expanded_query": query,
            }

        query_lower = query.lower()
        intents: dict[str, Any] = {}

        # Détection citation intégrale / exacte
        integral_patterns = [
            r"(cit|retrouv|donn|montr).*(intégral|complet|entier|exact)",
            r"\b(intégral|exactement|exact|textuel|tel quel)\b",
            r"de manière (intégrale|complète|exacte)",
            r"en entier",
            r"cite-moi.*passages",  # "Cite-moi 3 passages"
            r"cite.*ce qui est écrit",  # "Cite ce qui est écrit sur..."
        ]
        intents["wants_integral_citation"] = any(
            re.search(pattern, query_lower, re.I) for pattern in integral_patterns
        )

        # Détection type de contenu
        if re.search(r"\b(poème|poem|vers|strophe)\b", query_lower, re.I):
            intents["content_type"] = "poem"
        elif re.search(r"\b(section|chapitre|partie)\b", query_lower, re.I):
            intents["content_type"] = "section"
        elif re.search(r"\b(conversation|dialogue|échange)\b", query_lower, re.I):
            intents["content_type"] = "conversation"
        else:
            intents["content_type"] = None

        # Extraction keywords (filtrer stopwords)
        stopwords = {
            "le",
            "la",
            "les",
            "un",
            "une",
            "des",
            "de",
            "du",
            "et",
            "ou",
            "peux",
            "tu",
            "me",
            "mon",
            "ma",
            "ce",
            "que",
            "qui",
            "appelé",
            "citer",
            "manière",
            "ai",
        }
        words = re.findall(r"\b[a-zàâäéèêëïîôùûüÿæœç]{3,}\b", query_lower)
        keywords = [w for w in words if w not in stopwords]
        intents["keywords"] = keywords

        # Expansion de requête pour "poème fondateur"
        expanded = query
        if "fondateur" in keywords and intents["content_type"] == "poem":
            # Ajouter des termes associés pour améliorer le matching
            expanded += " origine premier initial création commencement"

        intents["expanded_query"] = expanded

        return intents
    
    def compute_score(
        self,
        hit: Dict[str, Any],
        user_intent: Dict[str, Any],
        doc_occurrence_count: Dict[Any, int],
        index_in_results: int,
    ) -> float:
        """
        Calcul de score sémantique multi-critères pour le re-ranking RAG.

        ✅ Phase 3 RAG : Système de scoring avancé avec signaux pondérés

        Signaux pris en compte (pondération):
        - 40% : Similarité vectorielle (distance ChromaDB)
        - 20% : Complétude (chunks fusionnés, longueur, is_complete)
        - 15% : Pertinence mots-clés (match user_intent keywords)
        - 10% : Fraîcheur (documents récents)
        - 10% : Diversité (pénalité si surreprésentation d'un doc)
        - 05% : Alignement type de contenu

        Args:
            hit: Chunk avec metadata et distance
            user_intent: Intention utilisateur (de parse_intent)
            doc_occurrence_count: Compteur d'occurrences par document_id
            index_in_results: Position dans la liste (0-based)

        Returns:
            Score final (plus bas = plus pertinent, compatible avec distance ChromaDB)
        """
        md = hit.get("metadata", {})
        base_distance = hit.get("distance", 1.0)

        # ==========================================
        # 1. SIMILARITÉ VECTORIELLE (40%)
        # ==========================================
        # Distance ChromaDB: 0 = parfait match, >1 = dissimilaire
        # On normalise à [0, 1] en supposant distance max ~2.0
        vector_score = min(base_distance / 2.0, 1.0)

        # ==========================================
        # 2. COMPLÉTUDE (20%)
        # ==========================================
        completeness_score = 0.0

        # 2.1 Bonus fusion de chunks
        merged_count = md.get("merged_chunks", 0)
        if merged_count > 1:
            # Plus de chunks fusionnés = contenu plus complet
            completeness_score -= min(merged_count * 0.05, 0.15)  # Max -0.15

        # 2.2 Bonus longueur (contenus longs plus informatifs)
        line_start = md.get("line_start", 0)
        line_end = md.get("line_end", 0)
        line_count = max(0, line_end - line_start)

        if line_count >= 40:
            completeness_score -= 0.10
        elif line_count >= 25:
            completeness_score -= 0.05

        # 2.3 Bonus is_complete flag
        if md.get("is_complete"):
            completeness_score -= 0.05

        # Normaliser à [0, 1]
        completeness_score = max(completeness_score, -0.3)  # Cap à -0.3
        completeness_normalized = (completeness_score + 0.3) / 0.3  # → [0, 1]

        # ==========================================
        # 3. PERTINENCE MOTS-CLÉS (15%)
        # ==========================================
        keyword_score = 1.0  # Par défaut neutre

        chunk_keywords = md.get("keywords", "").lower()
        user_keywords = user_intent.get("keywords", [])

        if chunk_keywords and user_keywords:
            matches = sum(1 for kw in user_keywords if  kw in chunk_keywords)
            if matches > 0:
                # Plus de matches = meilleur score
                match_ratio = min(matches / len(user_keywords), 1.0)
                keyword_score = 1.0 - (match_ratio * 0.5)  # Max -50%

        # Boost supplémentaire pour keywords critiques
        if "fondateur" in chunk_keywords and "fondateur" in user_keywords:
            keyword_score *= 0.7  # Boost additionnel

        # ==========================================
        # 4. FRAÎCHEUR / RECENCY (10%)
        # ==========================================
        recency_score = 0.5  # Par défaut neutre

        created_at = md.get("created_at")
        if created_at:
            try:
                if isinstance(created_at, str):
                    doc_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    doc_date = created_at

                age_days = (datetime.now(timezone.utc) - doc_date).days

                # Documents récents favorisés
                if age_days < 7:
                    recency_score = 0.2  # Très récent
                elif age_days < 30:
                    recency_score = 0.4  # Récent
                elif age_days < 180:
                    recency_score = 0.6  # Moyen
                else:
                    # Dépréciation progressive après 6 mois
                    recency_score = min(0.8 + (age_days - 180) / 365 * 0.2, 1.0)

            except Exception:
                pass  # Garder valeur par défaut

        # ==========================================
        # 5. DIVERSITÉ (10%)
        # ==========================================
        diversity_score = 0.5  # Par défaut neutre

        doc_id = md.get("document_id")
        if doc_id is not None:
            occurrences = doc_occurrence_count.get(doc_id, 1)

            if occurrences > 3:
                # Pénalité pour surreprésentation (éviter 10 chunks du même doc)
                diversity_score = min(0.5 + (occurrences - 3) * 0.15, 1.0)
            elif occurrences == 1:
                # Bonus pour documents uniques (favorise diversité)
                diversity_score = 0.3

        # ==========================================
        # 6. ALIGNEMENT TYPE DE CONTENU (5%)
        # ==========================================
        content_type_score = 0.5  # Par défaut neutre

        chunk_type = md.get("chunk_type", "prose")
        user_content_type = user_intent.get("content_type")

        if user_content_type and chunk_type == user_content_type:
            content_type_score = 0.2  # Bonus fort pour match exact
        elif user_content_type and chunk_type != user_content_type:
            content_type_score = 0.8  # Pénalité si type différent

        # ==========================================
        # SCORE FINAL: Moyenne pondérée
        # ==========================================
        final_score = (
            vector_score * 0.40
            + completeness_normalized * 0.20
            + keyword_score * 0.15
            + recency_score * 0.10
            + diversity_score * 0.10
            + content_type_score * 0.05
        )

        return final_score
    
    def merge_chunks(
        self,
        doc_hits: List[Dict[str, Any]],
        max_blocks: int = 10,
        user_intent: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Regroupe les chunks adjacents du même document pour reconstituer les contenus fragmentés.

        ✅ Phase 2 RAG Optimisation : Reconstruit les contenus longs (poèmes, sections)
        ✅ Phase 3 RAG Optimisation : Re-ranking sémantique multi-critères

        Args:
            doc_hits: Liste de chunks retournés par le RAG
            max_blocks: Nombre maximum de blocs à retourner
            user_intent: Intention utilisateur parsée

        Returns:
            Liste de chunks fusionnés, triés par pertinence
        """
        if not doc_hits:
            return []

        # Grouper par document_id
        by_document: Dict[Any, List[Dict[str, Any]]] = {}
        for hit in doc_hits:
            md = hit.get("metadata", {})
            doc_id = md.get("document_id")
            if doc_id is not None:
                if doc_id not in by_document:
                    by_document[doc_id] = []
                by_document[doc_id].append(hit)

        merged_hits = []

        for doc_id, chunks in by_document.items():
            # Trier par line_start pour détecter l'adjacence
            chunks_sorted = sorted(
                chunks, key=lambda x: x.get("metadata", {}).get("line_start", 0)
            )

            i = 0
            while i < len(chunks_sorted):
                current = chunks_sorted[i]
                current_md = current.get("metadata", {})
                current_end = current_md.get("line_end", 0)

                # Collecter les chunks adjacents
                adjacent_group = [current]
                j = i + 1

                while j < len(chunks_sorted):
                    next_chunk = chunks_sorted[j]
                    next_md = next_chunk.get("metadata", {})
                    next_start = next_md.get("line_start", 0)

                    # Vérifier si consécutif (tolérance de 30 lignes)
                    if next_start <= current_end + 30:
                        adjacent_group.append(next_chunk)
                        current_end = max(current_end, next_md.get("line_end", 0))
                        j += 1
                    else:
                        break

                # Fusionner si plusieurs chunks adjacents
                if len(adjacent_group) > 1:
                    # Fusionner les textes
                    merged_text = "\n".join(
                        [chunk.get("text", "") for chunk in adjacent_group]
                    )

                    # Créer métadonnées fusionnées
                    first_md = adjacent_group[0].get("metadata", {})
                    last_md = adjacent_group[-1].get("metadata", {})

                    merged_md = dict(first_md)
                    merged_md["line_start"] = first_md.get("line_start", 0)
                    merged_md["line_end"] = last_md.get("line_end", 0)
                    merged_md["line_range"] = (
                        f"{merged_md['line_start']}-{merged_md['line_end']}"
                    )
                    merged_md["is_complete"] = all(
                        c.get("metadata", {}).get("is_complete", False)
                        for c in adjacent_group
                    )
                    merged_md["merged_chunks"] = len(adjacent_group)

                    # Calculer score moyen
                    avg_score = sum(c.get("distance", 0) for c in adjacent_group) / len(
                        adjacent_group
                    )

                    merged_hit = {
                        "text": merged_text.strip(),
                        "metadata": merged_md,
                        "distance": avg_score,
                        "id": f"{doc_id}_merged_{i}",
                    }

                    merged_hits.append(merged_hit)
                    logger.info(
                        f"[RAG Merge] Fusionné {len(adjacent_group)} chunks "
                        f"(doc {doc_id}, lignes {merged_md['line_start']}-{merged_md['line_end']})"
                    )
                else:
                    # Chunk isolé, garder tel quel
                    merged_hits.append(current)

                i = j if j > i + 1 else i + 1

        # ✅ Phase 3 : Re-ranking multi-critères
        if user_intent is not None:
            # Compter occurrences par document_id
            doc_occurrence_count: Dict[Any, int] = {}
            for hit in merged_hits:
                doc_id = hit.get("metadata", {}).get("document_id")
                if doc_id is not None:
                    doc_occurrence_count[doc_id] = doc_occurrence_count.get(doc_id, 0) + 1

            # Calculer score sémantique pour chaque hit
            for idx, hit in enumerate(merged_hits):
                semantic_score = self.compute_score(
                    hit=hit,
                    user_intent=user_intent,
                    doc_occurrence_count=doc_occurrence_count,
                    index_in_results=idx,
                )
                hit["semantic_score"] = semantic_score

            # Trier par score sémantique (plus bas = meilleur)
            merged_hits.sort(key=lambda x: x.get("semantic_score", 1.0))

        # Limiter au top max_blocks
        return merged_hits[:max_blocks]
    
    def format_context(
        self, doc_hits: List[Dict[str, Any]], max_tokens: int = 50000
    ) -> str:
        """
        Formate le contexte RAG en exploitant les métadonnées sémantiques.

        ✅ Phase 2 RAG : Headers explicites par type de contenu
        ✅ Phase 3.1 : Instructions RENFORCÉES pour citations exactes
        ✅ Phase 3.2 : Limite intelligente pour éviter context_length_exceeded

        Args:
            doc_hits: Liste de dictionnaires avec 'text' et 'metadata'
            max_tokens: Limite approximative en tokens

        Returns:
            Contexte formaté avec headers explicites par type
        """
        if not doc_hits:
            return ""

        blocks = []
        has_poem = False
        has_complete_content = False
        total_chars = 0
        max_chars = max_tokens * 4  # Approximation: 1 token ≈ 4 caractères

        for hit in doc_hits:
            text = (hit.get("text") or "").strip()
            if not text:
                continue

            # ✅ Phase 3.2: Stop si dépasse la limite
            if total_chars + len(text) > max_chars:
                logger.warning(
                    f"[RAG Context] Limite atteinte ({total_chars}/{max_chars} chars), truncating remaining docs"
                )
                break

            total_chars += len(text)

            md = hit.get("metadata", {})
            chunk_type = md.get("chunk_type", "prose")
            section_title = md.get("section_title", "")
            line_range = md.get("line_range", "")
            merged_count = md.get("merged_chunks", 0)

            # Tracker contenus complets
            if merged_count > 1:
                has_complete_content = True

            # Construire le header selon le type
            if chunk_type == "poem":
                has_poem = True
                header = "[POÈME"
                if merged_count > 1:
                    header += " - CONTENU COMPLET"
                header += "]"
                if section_title:
                    header += f" {section_title}"
                if line_range:
                    header += f" (lignes {line_range})"
            elif chunk_type == "section":
                header = "[SECTION"
                if merged_count > 1:
                    header += " - CONTENU COMPLET"
                header += "]"
                if section_title:
                    header += f" {section_title}"
                if line_range:
                    header += f" (lignes {line_range})"
            elif chunk_type == "conversation":
                header = "[CONVERSATION"
                if merged_count > 1:
                    header += " - CONTENU COMPLET"
                header += "]"
                if line_range:
                    header += f" (lignes {line_range})"
            else:
                # prose
                header = ""
                if section_title:
                    header = f"[{section_title}]"
                if line_range and header:
                    header += f" (lignes {line_range})"
                if merged_count > 1 and header:
                    header = header.rstrip("]") + " - CONTENU COMPLET]"

            if header:
                blocks.append(f"{header}\n{text}")
            else:
                blocks.append(text)

        # ✅ Phase 3.1 : Instructions FORTES pour citations exactes
        instruction_parts = []

        if has_complete_content or has_poem:
            instruction_parts.append(
                "╔══════════════════════════════════════════════════════════╗\n"
                "║  INSTRUCTION PRIORITAIRE : CITATIONS TEXTUELLES          ║\n"
                "╚══════════════════════════════════════════════════════════╝"
            )

        if has_poem:
            instruction_parts.append(
                "\n🔴 RÈGLE ABSOLUE pour les POÈMES :\n"
                "   • Si l'utilisateur demande de citer un poème (intégralement, complet, etc.),\n"
                "     tu DOIS copier-coller le texte EXACT ligne par ligne.\n"
                "   • JAMAIS de paraphrase, JAMAIS de résumé.\n"
                "   • Préserve TOUS les retours à la ligne, la ponctuation, les majuscules.\n"
                "   • Format : introduis brièvement PUIS cite entre guillemets ou en bloc.\n"
            )

        if has_complete_content:
            instruction_parts.append(
                "\n🟠 RÈGLE pour les CONTENUS COMPLETS :\n"
                '   • Les blocs marqués "CONTENU COMPLET" contiennent la version intégrale.\n'
                "   • Pour toute demande de citation (section, conversation, passage),\n"
                "     copie le texte TEL QUEL depuis le bloc correspondant.\n"
                "   • Ne recompose pas, ne synthétise pas : CITE TEXTUELLEMENT.\n"
            )

        if instruction_parts:
            instruction_header = "".join(instruction_parts)
            blocks_text = "\n\n".join(blocks)
            return f"{instruction_header}\n\n{blocks_text}"
        else:
            return "\n\n".join(blocks)
    
    # ======================
    # Helper Methods
    # ======================
    
    def _get_knowledge_collection(self):
        """Get or create the knowledge collection."""
        if self._knowledge_collection is None:
            knowledge_name = os.getenv(
                "EMERGENCE_KNOWLEDGE_COLLECTION", "emergence_knowledge"
            )
            self._knowledge_collection = self.vector_service.get_or_create_collection(
                knowledge_name
            )
        return self._knowledge_collection
    
    def _build_where_filter(
        self,
        doc_ids: Optional[List[int]] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Build a where filter for vector search."""
        clauses = []
        
        if doc_ids:
            # Convert to integers
            int_doc_ids = []
            for doc_id in doc_ids:
                try:
                    int_doc_ids.append(int(doc_id))
                except (ValueError, TypeError):
                    pass
            if int_doc_ids:
                clauses.append({"document_id": {"$in": int_doc_ids}})
        
        if user_id:
            clauses.append({"user_id": user_id})
        
        if agent_id:
            clauses.append({"agent": agent_id.lower()})
        
        if session_id:
            clauses.append({"session_id": session_id})
        
        if clauses:
            return {"$and": clauses} if len(clauses) > 1 else clauses[0]
        
        return None
    
    def _convert_results_to_hits(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert VectorService results to standardized hit format."""
        ids = results.get("ids", [[]])[0] or []
        distances = results.get("distances", [[]])[0] or []
        documents = results.get("documents", [[]])[0] or []
        metadatas = results.get("metadatas", [[]])[0] or []
        
        hits = []
        for i, doc_id in enumerate(ids):
            hit = {
                "id": doc_id,
                "text": documents[i] if i < len(documents) else "",
                "distance": distances[i] if i < len(distances) else 1.0,
                "metadata": metadatas[i] if i < len(metadatas) else {},
            }
            hits.append(hit)
        
        return hits
