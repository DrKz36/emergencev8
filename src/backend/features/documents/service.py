# src/backend/features/documents/service.py
# V8.3 - Ajout de get_all_documents/delete_document + purge vecteurs par document_id
import logging
import uuid
import asyncio
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import UploadFile, HTTPException
from pathlib import Path

from backend.core.database.manager import DatabaseManager
from backend.core.database import queries as db_queries
from backend.features.documents.parser import ParserFactory
from backend.features.memory.vector_service import VectorService
from backend.core import config

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(
        self,
        db_manager: DatabaseManager,
        parser_factory: ParserFactory,
        vector_service: VectorService,
        uploads_dir: str,
    ):
        self.db_manager = db_manager
        self.parser_factory = parser_factory
        self.vector_service = vector_service
        self.document_collection = self.vector_service.get_or_create_collection(
            config.DOCUMENT_COLLECTION_NAME
        )
        self.uploads_dir = Path(uploads_dir)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"DocumentService (V8.3) initialisé. Collection: '{config.DOCUMENT_COLLECTION_NAME}'"
        )

    def _chunk_text(self, text: str) -> List[str]:
        # Simple chunking pour l'instant (aligné avec core/config.py si besoin)
        return [
            text[i : i + config.CHUNK_SIZE]
            for i in range(0, len(text), config.CHUNK_SIZE)
        ]

    def _detect_content_type(self, text: str, lines: List[str]) -> str:
        """
        Détecte automatiquement le type de contenu d'un chunk.

        Returns:
            "poem", "section", "conversation", ou "prose"
        """
        if not text or not text.strip():
            return "prose"

        # Heuristique 1 : Détection de conversation (timestamps)
        if any(re.match(r'\[\d{2}\.\d{2}\.\d{2}', line) for line in lines[:5]):
            return "conversation"

        # Heuristique 2 : Détection de section (headers)
        if any(re.match(r'^#{1,6}\s+', line) or re.match(r'^[IVX]+\.\s+[A-Z]', line) for line in lines[:3]):
            return "section"

        # Heuristique 3 : Détection de poème (ASSOUPLISSEMENT Phase 2)
        # Critères : lignes courtes + structure versifiée
        non_empty_lines = [l for l in lines if l.strip()]
        if len(non_empty_lines) >= 4:
            avg_line_length = sum(len(l) for l in non_empty_lines) / len(non_empty_lines)

            # Poème : lignes courtes (< 70 caractères en moyenne)
            if avg_line_length < 70:
                # Vérifier densité de lignes courtes (>60% lignes < 80 car)
                short_lines = [l for l in non_empty_lines if len(l) < 80]
                short_ratio = len(short_lines) / len(non_empty_lines)

                # Si beaucoup de lignes courtes, c'est probablement un poème
                if short_ratio > 0.6:
                    return "poem"

                # OU vérifier structure en strophes (paragraphes séparés par \n\n)
                if '\n\n' in text:
                    paragraphs = [p for p in text.split('\n\n') if p.strip()]
                    # Accepter 1+ strophe (au lieu de 2+)
                    if len(paragraphs) >= 1 and short_ratio > 0.5:
                        return "poem"

        return "prose"

    def _extract_section_title(self, lines: List[str]) -> Optional[str]:
        """
        Extrait le titre de section si présent dans les premières lignes.

        Returns:
            Titre de la section ou None
        """
        for line in lines[:5]:
            # Markdown headers (# Titre)
            match = re.match(r'^#{1,6}\s+(.+)$', line.strip())
            if match:
                return match.group(1).strip()

            # Numérotation romaine/décimale (I. Titre, 1. Titre)
            match = re.match(r'^[IVX]+\.\s+([A-Z].+)$', line.strip())
            if match:
                return match.group(1).strip()

        return None

    def _extract_keywords(self, text: str, max_keywords: int = 7) -> List[str]:
        """
        Extrait les mots-clés significatifs d'un texte.

        Returns:
            Liste de mots-clés (max_keywords au maximum)
        """
        # Stopwords français courants
        stopwords = {
            'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou',
            'mais', 'dans', 'pour', 'sur', 'avec', 'sans', 'mon', 'ma', 'mes',
            'ce', 'cette', 'ces', 'que', 'qui', 'quoi', 'dont', 'où', 'je',
            'tu', 'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'à', 'au',
            'aux', 'est', 'sont', 'était', 'été', 'être', 'avoir', 'ai', 'as',
            'a', 'avons', 'avez', 'ont', 'par', 'ne', 'pas', 'plus', 'très',
            'bien', 'tout', 'tous', 'toute', 'toutes', 'en', 'y', 'se', 'si'
        }

        # Mots-clés prioritaires (score boosté)
        priority_keywords = {
            'fondateur', 'origine', 'premier', 'initial', 'commencement',
            'passerelle', 'hirondelle', 'espoir', 'quête', 'renaissance'
        }

        # Extraire les mots (lettres uniquement, min 3 caractères)
        words = re.findall(r'\b[a-zàâäéèêëïîôùûüÿæœç]{3,}\b', text.lower())

        # Filtrer stopwords et compter occurrences
        word_counts: Dict[str, int] = {}
        for word in words:
            if word not in stopwords:
                # Boost x5 pour mots prioritaires
                boost = 5 if word in priority_keywords else 1
                word_counts[word] = word_counts.get(word, 0) + boost

        # Trier par fréquence et prendre top N
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]

    def _chunk_text_semantic(
        self,
        text: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Découpe le texte en chunks sémantiques en respectant l'intégrité des structures.

        Stratégie :
        1. Détecter les sections (headers markdown, numérotation romaine)
        2. Détecter les poèmes (lignes courtes + espacement régulier)
        3. Découper en respectant les paragraphes (\n\n)
        4. Ajouter overlap de 100 caractères entre chunks

        Returns:
            Liste de dictionnaires avec :
            - text: contenu du chunk
            - chunk_type: "poem", "section", "conversation", "prose"
            - section_title: titre de la section (si détecté)
            - keywords: liste de mots-clés
            - line_start: ligne de début
            - line_end: ligne de fin
            - is_complete: True si le chunk contient un élément complet
        """
        if not text or not text.strip():
            return []

        chunks = []
        lines = text.split('\n')
        total_lines = len(lines)

        # Étape 1 : Découper par paragraphes (séparés par \n\n)
        paragraphs = []
        current_paragraph = []
        paragraph_line_start = 0

        for i, line in enumerate(lines):
            if not line.strip() and current_paragraph:
                # Fin de paragraphe
                paragraphs.append({
                    'lines': current_paragraph,
                    'line_start': paragraph_line_start,
                    'line_end': i
                })
                current_paragraph = []
                paragraph_line_start = i + 1
            else:
                current_paragraph.append(line)

        # Dernier paragraphe
        if current_paragraph:
            paragraphs.append({
                'lines': current_paragraph,
                'line_start': paragraph_line_start,
                'line_end': len(lines)
            })

        # Étape 2 : Regrouper les paragraphes en chunks sémantiques
        current_chunk_paragraphs = []
        current_chunk_size = 0

        for para_dict in paragraphs:
            para_text = '\n'.join(para_dict['lines'])
            para_size = len(para_text)

            # Si le paragraphe seul dépasse CHUNK_SIZE, le forcer en chunk unique
            if para_size > config.CHUNK_SIZE:
                # Flush chunk courant
                if current_chunk_paragraphs:
                    chunks.append(self._finalize_chunk(
                        current_chunk_paragraphs,
                        filename,
                        len(chunks)
                    ))
                    current_chunk_paragraphs = []
                    current_chunk_size = 0

                # Créer chunk unique pour ce paragraphe long
                chunks.append(self._finalize_chunk(
                    [para_dict],
                    filename,
                    len(chunks)
                ))
                continue

            # Si ajouter ce paragraphe dépasse CHUNK_SIZE, flush chunk courant
            if current_chunk_size + para_size > config.CHUNK_SIZE and current_chunk_paragraphs:
                chunks.append(self._finalize_chunk(
                    current_chunk_paragraphs,
                    filename,
                    len(chunks)
                ))
                current_chunk_paragraphs = []
                current_chunk_size = 0

            # Ajouter paragraphe au chunk courant
            current_chunk_paragraphs.append(para_dict)
            current_chunk_size += para_size + 2  # +2 pour \n\n entre paragraphes

        # Flush dernier chunk
        if current_chunk_paragraphs:
            chunks.append(self._finalize_chunk(
                current_chunk_paragraphs,
                filename,
                len(chunks)
            ))

        # Étape 3 : Ajouter overlap entre chunks adjacents
        for i in range(len(chunks) - 1):
            current_text = chunks[i]['text']
            next_text = chunks[i + 1]['text']

            # Prendre les 100 derniers caractères du chunk courant
            if len(current_text) > config.CHUNK_OVERLAP:
                overlap_text = current_text[-config.CHUNK_OVERLAP:]
                # Ajouter au début du chunk suivant (si pas déjà présent)
                if not next_text.startswith(overlap_text):
                    chunks[i + 1]['text'] = f"{overlap_text}\n\n{next_text}"
                    chunks[i + 1]['has_overlap'] = True

        logger.info(
            f"Chunking sémantique terminé : {len(chunks)} chunks pour '{filename}' "
            f"({total_lines} lignes)"
        )

        return chunks

    def _finalize_chunk(
        self,
        paragraphs: List[Dict[str, Any]],
        filename: str,
        chunk_index: int
    ) -> Dict[str, Any]:
        """
        Finalise un chunk en extrayant ses métadonnées.

        Args:
            paragraphs: Liste de dictionnaires {lines, line_start, line_end}
            filename: Nom du fichier source
            chunk_index: Index du chunk

        Returns:
            Dictionnaire avec métadonnées complètes
        """
        # Reconstruire le texte
        all_lines = []
        line_start = paragraphs[0]['line_start']
        line_end = paragraphs[-1]['line_end']

        for para in paragraphs:
            all_lines.extend(para['lines'])

        text = '\n'.join(all_lines)

        # Détection du type
        chunk_type = self._detect_content_type(text, all_lines)

        # Extraction du titre de section
        section_title = self._extract_section_title(all_lines)

        # Extraction des mots-clés
        keywords = self._extract_keywords(text)

        # Déterminer si le chunk est complet
        # Heuristique : un chunk est complet s'il contient < CHUNK_SIZE caractères
        # (pas tronqué) et qu'il forme une unité cohérente
        is_complete = len(text) < config.CHUNK_SIZE

        return {
            'text': text,
            'chunk_type': chunk_type,
            'section_title': section_title,
            'keywords': keywords,
            'line_start': line_start,
            'line_end': line_end,
            'line_range': f"{line_start}-{line_end}",
            'is_complete': is_complete,
            'has_overlap': False,
            'chunk_index': chunk_index,
        }

    async def process_uploaded_file(
        self,
        file: UploadFile,
        *,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> int:
        filename = file.filename
        if not filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant.")
        filepath = self.uploads_dir / f"{uuid.uuid4()}_{filename}"

        try:
            with open(filepath, "wb") as buffer:
                buffer.write(await file.read())

            doc_id = await db_queries.insert_document(
                self.db_manager,
                filename=filename,
                filepath=str(filepath),
                status="pending",
                uploaded_at=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
                user_id=user_id,
            )

            parser = self.parser_factory.get_parser(filepath.suffix)
            text_content = await asyncio.to_thread(parser.parse, str(filepath))

            # ✅ Phase 2 RAG : Chunking sémantique avec métadonnées enrichies
            semantic_chunks = self._chunk_text_semantic(text_content, filename)

            await db_queries.update_document_processing_info(
                self.db_manager,
                doc_id=doc_id,
                session_id=session_id,
                user_id=user_id,
                char_count=len(text_content),
                chunk_count=len(semantic_chunks),
                status="ready",
            )

            # Préparer les chunks pour la DB (compatibilité avec schéma existant)
            chunk_rows = []
            if semantic_chunks:
                chunk_rows = [
                    {
                        "id": f"{doc_id}_{chunk['chunk_index']}",
                        "document_id": doc_id,
                        "chunk_index": chunk['chunk_index'],
                        "content": chunk['text'],
                    }
                    for chunk in semantic_chunks
                ]
                await db_queries.insert_document_chunks(
                    self.db_manager,
                    session_id=session_id,
                    chunks=chunk_rows,
                    user_id=user_id,
                )

            # ✅ Phase 2 RAG : Enrichir les métadonnées des vecteurs ChromaDB
            chunk_vectors = [
                {
                    "id": f"{doc_id}_{chunk['chunk_index']}",
                    "text": chunk['text'],
                    "metadata": {
                        "document_id": doc_id,
                        "filename": filename,
                        "session_id": session_id,
                        "user_id": user_id,
                        "owner_id": user_id,
                        # Métadonnées sémantiques
                        "chunk_type": chunk.get('chunk_type', 'prose'),
                        "section_title": chunk.get('section_title') or '',
                        "keywords": ','.join(chunk.get('keywords', [])),  # Convertir liste en string
                        "line_range": chunk.get('line_range', ''),
                        "line_start": chunk.get('line_start', 0),
                        "line_end": chunk.get('line_end', 0),
                        "is_complete": chunk.get('is_complete', False),
                    },
                }
                for chunk in semantic_chunks
            ]
            if chunk_vectors:
                self.vector_service.add_items(
                    collection=self.document_collection, items=chunk_vectors
                )

            logger.info(
                f"Document '{filename}' (ID: {doc_id}) traité et vectorisé avec succès."
            )
            return doc_id

        except Exception as e:
            logger.error(
                f"Erreur lors du traitement du fichier '{filename}': {e}", exc_info=True
            )
            raise HTTPException(
                status_code=500, detail="Erreur lors du traitement du fichier."
            )
        finally:
            pass

    # --- ✅ NOUVELLES MÉTHODES EXPOSÉES AU ROUTEUR ---

    async def get_all_documents(self, session_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retourne la liste des documents enregistrés pour la session donnée.
        """
        return await db_queries.get_all_documents(
            self.db_manager, session_id=session_id, user_id=user_id
        )

    async def delete_document(self, doc_id: int, session_id: str, user_id: Optional[str] = None) -> bool:
        """
        Supprime un document de la session :
         1) purge des vecteurs associés
         2) suppression en base (document + chunks + liaisons)
        """
        doc = await db_queries.get_document_by_id(
            self.db_manager, doc_id, session_id=session_id, user_id=user_id
        )
        if not doc:
            return False

        try:
            where_filter = {"document_id": int(doc_id), "session_id": session_id}
            if user_id:
                where_filter["user_id"] = user_id
            self.vector_service.delete_vectors(
                collection=self.document_collection,
                where_filter=where_filter,
            )
        except Exception as e:
            logger.warning(f"Echec purge vecteurs pour document {doc_id}: {e}")

        deleted = await db_queries.delete_document(
            self.db_manager, int(doc_id), session_id, user_id=user_id
        )
        return bool(deleted)

    # ✅ Phase 3 RAG : Méthode de recherche avec scoring multi-critères
    def search_documents(
        self,
        query: str,
        session_id: str,
        user_id: Optional[str] = None,
        top_k: int = 5,
        intent: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Recherche dans les documents avec scoring multi-critères Phase 3.

        Args:
            query: Requête utilisateur
            session_id: ID de session
            user_id: ID utilisateur (optionnel)
            top_k: Nombre de résultats à retourner
            intent: Intention parsée (wants_integral_citation, content_type, keywords)

        Returns:
            Liste de dictionnaires avec :
            - text: Contenu du chunk
            - score: Score final (0-1)
            - metadata: Métadonnées enrichies
            - distance: Distance vectorielle brute
        """
        if not query or not query.strip():
            return []

        try:
            # Construire le filtre pour la session/user
            where_filter: Dict[str, Any] = {"session_id": session_id}
            if user_id:
                where_filter["user_id"] = user_id

            # Étape 1 : Recherche vectorielle (récupère plus que nécessaire pour re-ranking)
            results = self.vector_service.query(
                collection=self.document_collection,
                query_text=query,
                n_results=top_k * 3,  # Sur-échantillonner pour re-ranking
                where_filter=where_filter,
            )

            if not results:
                return []

            # Étape 2 : Appliquer scoring multi-critères
            scored_results = []
            for r in results:
                text = r.get("text", "")
                metadata = r.get("metadata", {})
                distance = r.get("distance", 1.0)

                # Score vectoriel (0-1, plus bas = meilleur)
                vector_score = max(0.0, 1.0 - distance)

                # Score de complétude (chunks complets privilégiés)
                completeness_score = 1.0 if metadata.get("is_complete") else 0.5

                # Score de keywords (match avec requête)
                keyword_score = self._compute_keyword_score(
                    text, query, metadata.get("keywords", "")
                )

                # Score de recency (pas implémenté ici, mettre 0.5 par défaut)
                recency_score = 0.5

                # Score de diversité (calculé après)
                diversity_score = 0.5

                # Score de type (bonus si match content_type)
                type_score = self._compute_type_score(metadata, intent)

                # ✅ Phase 3 : Pondération multi-critères
                # vector: 40%, completeness: 20%, keywords: 15%, recency: 10%, diversity: 10%, type: 5%
                final_score = (
                    vector_score * 0.40 +
                    completeness_score * 0.20 +
                    keyword_score * 0.15 +
                    recency_score * 0.10 +
                    diversity_score * 0.10 +
                    type_score * 0.05
                )

                scored_results.append({
                    "text": text,
                    "score": final_score,
                    "metadata": metadata,
                    "distance": distance,
                    "id": r.get("id", ""),
                })

            # Étape 3 : Calculer diversité (pénaliser documents identiques)
            scored_results = self._apply_diversity_penalty(scored_results)

            # Étape 4 : Trier par score final et prendre top_k
            scored_results.sort(key=lambda x: x["score"], reverse=True)
            return scored_results[:top_k]

        except Exception as e:
            logger.error(f"Erreur lors de la recherche de documents: {e}", exc_info=True)
            return []

    def _compute_keyword_score(self, text: str, query: str, chunk_keywords: str) -> float:
        """
        Calcule le score de correspondance de mots-clés entre la requête et le chunk.

        Args:
            text: Texte du chunk
            query: Requête utilisateur
            chunk_keywords: Mots-clés du chunk (string séparé par virgules)

        Returns:
            Score entre 0 et 1
        """
        if not text or not query:
            return 0.0

        # Normaliser
        text_lower = text.lower()
        query_lower = query.lower()

        # Extraire les mots de la requête (min 3 caractères)
        query_words = set(re.findall(r'\b[a-zàâäéèêëïîôùûüÿæœç]{3,}\b', query_lower))

        # Extraire les mots-clés du chunk
        chunk_kw = set(kw.strip().lower() for kw in chunk_keywords.split(',') if kw.strip())

        if not query_words:
            return 0.0

        # Compter les matches exacts
        match_count = sum(1 for word in query_words if word in text_lower)

        # Bonus si match avec keywords du chunk
        keyword_match_count = len(query_words & chunk_kw)

        # Score = (matches exacts + bonus keywords) / nombre de mots requête
        score = (match_count + keyword_match_count * 2) / (len(query_words) * 3)

        return min(1.0, score)

    def _compute_type_score(self, metadata: Dict[str, Any], intent: Optional[Dict[str, Any]]) -> float:
        """
        Calcule le score de correspondance de type de contenu.

        Args:
            metadata: Métadonnées du chunk
            intent: Intention parsée (content_type)

        Returns:
            Score entre 0 et 1
        """
        if not intent or not intent.get("content_type"):
            return 0.5  # Neutre si pas d'intention

        chunk_type = metadata.get("chunk_type", "prose")
        expected_type = intent.get("content_type")

        if chunk_type == expected_type:
            return 1.0  # Match parfait
        elif expected_type == "poem" and chunk_type in ("poem", "prose"):
            return 0.7  # Accepter prose si recherche de poème
        else:
            return 0.3  # Pénalité si mismatch

    def _apply_diversity_penalty(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Applique une pénalité de diversité pour éviter trop de chunks du même document.

        Args:
            results: Liste de résultats scorés

        Returns:
            Résultats avec score diversity_score mis à jour
        """
        doc_counts: Dict[int, int] = {}

        for r in results:
            doc_id = r["metadata"].get("document_id", 0)
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

        # Appliquer pénalité exponentielle
        doc_occurrences: Dict[int, int] = {}
        for r in results:
            doc_id = r["metadata"].get("document_id", 0)
            occurrence_count = doc_occurrences.get(doc_id, 0)
            doc_occurrences[doc_id] = occurrence_count + 1

            # Diversité = 1 / (1 + occurrences) => 1, 0.5, 0.33, 0.25...
            diversity_score = 1.0 / (1 + occurrence_count)

            # Recalculer le score final avec la vraie diversité
            # On extrait les composantes (estimation inverse)
            current_score = r["score"]
            # Soustraire l'ancienne contribution de diversité (0.5 * 0.10 = 0.05)
            base_score = current_score - 0.05
            # Ajouter la nouvelle contribution
            r["score"] = base_score + diversity_score * 0.10

        return results

