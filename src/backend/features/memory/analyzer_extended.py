# analyzer_extended.py - Topic shift detection extension
import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


async def detect_topic_shift(
    analyzer_instance: Any,
    session_id: str,
    recent_messages: List[Dict[str, Any]],
    stm_summary: Optional[str] = None,
    threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Detect topic shift by comparing recent messages with STM summary.

    Args:
        analyzer_instance: MemoryAnalyzer instance
        session_id: Session identifier
        recent_messages: Last 3-5 messages from conversation
        stm_summary: Current STM summary (if available)
        threshold: Similarity threshold below which we consider a topic shift (default: 0.5)

    Returns:
        Dict with 'topic_shifted' (bool), 'similarity' (float), 'suggestion' (str)
    """
    if not recent_messages or len(recent_messages) < 2:
        return {"topic_shifted": False, "similarity": 1.0, "suggestion": None}

    # If no STM summary available, no shift detected
    if not stm_summary or not stm_summary.strip():
        return {"topic_shifted": False, "similarity": 1.0, "suggestion": None}

    # Extract text from recent messages
    recent_text = "\n".join(
        f"{m.get('role')}: {m.get('content') or m.get('message', '')}"
        for m in recent_messages[-3:]  # Last 3 messages
    )

    if not recent_text.strip():
        return {"topic_shifted": False, "similarity": 1.0, "suggestion": None}

    try:
        # Use vector service to compute similarity
        chat_service = analyzer_instance.chat_service
        if not chat_service:
            return {"topic_shifted": False, "similarity": 1.0, "suggestion": None}

        vector_service = getattr(chat_service, "vector_service", None)
        if not vector_service or not hasattr(vector_service, "embedding_function"):
            return {"topic_shifted": False, "similarity": 1.0, "suggestion": None}

        # Get embeddings
        embedding_fn = vector_service.embedding_function
        stm_embedding = embedding_fn([stm_summary])[0]
        recent_embedding = embedding_fn([recent_text])[0]

        # Calculate cosine similarity
        similarity = _cosine_similarity(stm_embedding, recent_embedding)

        # Detect shift
        topic_shifted = similarity < threshold

        suggestion_text: Optional[str] = None
        if topic_shifted:
            suggestion_text = (
                f"Changement de sujet détecté (similarité: {similarity:.2f}). "
                "Voulez-vous créer un nouveau thread pour cette conversation ?"
            )

        result: Dict[str, Any] = {
            "topic_shifted": topic_shifted,
            "similarity": float(similarity),
            "suggestion": suggestion_text,
        }

        if topic_shifted:
            # Notify via WebSocket
            await analyzer_instance._notify(
                session_id,
                {
                    "type": "topic_shift",
                    "similarity": float(similarity),
                    "threshold": threshold,
                    "suggestion": suggestion_text,
                },
            )

            logger.info(
                f"Topic shift détecté pour session {session_id}: "
                f"similarity={similarity:.3f} < threshold={threshold}"
            )

        return result

    except Exception as e:
        logger.warning(f"Erreur détection topic shift pour {session_id}: {e}")
        return {"topic_shifted": False, "similarity": 1.0, "suggestion": None}


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))
    except Exception:
        return 0.0
