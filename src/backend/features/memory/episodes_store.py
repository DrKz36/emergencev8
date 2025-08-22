# src/backend/features/memory/episodes_store.py
# UTF-8 (CRLF recommandé)
# Firestore Episodes (LTM) — stockage par utilisateur -> sous-collection "episodes".
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from google.cloud import firestore  # type: ignore
except Exception as _e:  # pragma: no cover
    firestore = None  # la présence est vérifiée à l'init


class EpisodesStore:
    """
    Store LTM basé Firestore.
    Arbo: users/{user_id}/episodes/{episode_id}
    """
    def __init__(self, project: Optional[str] = None) -> None:
        if firestore is None:
            raise RuntimeError("Le package 'google-cloud-firestore' est requis.")
        # ADC / Workload Identity sur Cloud Run, sinon FIRESTORE_EMULATOR_HOST en dev
        self._client = firestore.Client(project=project)

    def _col(self, user_id: str):
        if not user_id:
            raise ValueError("user_id manquant")
        return self._client.collection("users").document(user_id).collection("episodes")

    def upsert_episode(
        self,
        *,
        user_id: str,
        episode_id: Optional[str],
        thread_id: str,
        title: Optional[str],
        summary: str,
        keywords: List[str],
        quality_score: Optional[float] = None,
        created_at: Optional[str] = None,
    ) -> str:
        eid = episode_id or str(uuid.uuid4())
        now_iso = created_at or datetime.now(timezone.utc).isoformat()
        payload: Dict[str, Any] = {
            "episode_id": eid,
            "thread_id": thread_id,
            "title": title or "",
            "summary": summary or "",
            "keywords": keywords or [],
            "quality_score": quality_score,
            "created_at": now_iso,
        }
        self._col(user_id).document(eid).set(payload, merge=True)
        return eid

    def list_for_thread(self, *, user_id: str, thread_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = self._col(user_id).where("thread_id", "==", thread_id).order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        docs = q.stream()
        out: List[Dict[str, Any]] = []
        for d in docs:
            item = d.to_dict() or {}
            item["episode_id"] = item.get("episode_id") or d.id
            out.append(item)
        return out

    def delete_for_thread(self, *, user_id: str, thread_id: str) -> int:
        # suppression simple (petit volume)
        docs = self._col(user_id).where("thread_id", "==", thread_id).stream()
        c = 0
        for d in docs:
            d.reference.delete()
            c += 1
        return c
