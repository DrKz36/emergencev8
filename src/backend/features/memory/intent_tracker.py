# intent_tracker.py - Suivi et expiration des intentions
import logging
import asyncio
from typing import Dict, Any, List, Optional, cast
from datetime import datetime, timezone, timedelta
import re

logger = logging.getLogger(__name__)


class IntentTracker:
    """
    Gestion des intentions utilisateur avec expiration et rappels.

    Fonctionnalités:
    - Parser timeframes (demain, cette semaine, dans 3 jours)
    - Suivre intentions avec échéances
    - Envoyer rappels proactifs via WebSocket
    - Purger intentions ignorées (3+ rappels)
    """

    # Timeframe parsing patterns
    TIMEFRAME_PATTERNS = [
        (r"aujourd['']?hui", lambda: datetime.now(timezone.utc)),
        (r"demain", lambda: datetime.now(timezone.utc) + timedelta(days=1)),
        (
            r"apr[eè]s[- ]demain",
            lambda: datetime.now(timezone.utc) + timedelta(days=2),
        ),
        (
            r"cette semaine",
            lambda: datetime.now(timezone.utc) + timedelta(days=7),
        ),
        (
            r"la semaine prochaine",
            lambda: datetime.now(timezone.utc) + timedelta(days=14),
        ),
        (
            r"ce mois[- ]ci",
            lambda: datetime.now(timezone.utc) + timedelta(days=30),
        ),
        (
            r"le mois prochain",
            lambda: datetime.now(timezone.utc) + timedelta(days=60),
        ),
        (
            r"dans (\d+) jours?",
            lambda m: datetime.now(timezone.utc)
            + timedelta(days=int(m.group(1))),
        ),
        (
            r"dans (\d+) semaines?",
            lambda m: datetime.now(timezone.utc)
            + timedelta(weeks=int(m.group(1))),
        ),
        (
            r"dans (\d+) mois",
            lambda m: datetime.now(timezone.utc)
            + timedelta(days=30 * int(m.group(1))),
        ),
    ]

    def __init__(self, vector_service, connection_manager=None):
        self.vector_service = vector_service
        self.connection_manager = connection_manager
        self.reminder_counts: Dict[str, int] = {}  # Track reminder count per intent
        # 🔒 Lock pour accès concurrent aux compteurs (Bug #3 fix)
        self._reminder_lock = asyncio.Lock()

    def parse_timeframe(self, text: str) -> Optional[datetime]:
        """
        Parse natural language timeframe to datetime.

        Args:
            text: Timeframe text (e.g., "demain", "dans 3 jours")

        Returns:
            Datetime if parsed successfully, None otherwise
        """
        text_lower = text.lower().strip()

        for pattern, resolver in self.TIMEFRAME_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    if callable(resolver):
                        # Check if resolver takes match object as parameter
                        import inspect

                        sig = inspect.signature(resolver)
                        if len(sig.parameters) == 1:
                            return cast(datetime | None, resolver(match))
                        else:
                            return cast(datetime | None, resolver())
                except Exception as e:
                    logger.debug(
                        f"Erreur résolution timeframe pour '{pattern}': {e}"
                    )
                    continue

        return None

    async def increment_reminder(self, intent_id: str) -> int:
        """Incrémente compteur de rappel de manière thread-safe"""
        async with self._reminder_lock:
            self.reminder_counts[intent_id] = self.reminder_counts.get(intent_id, 0) + 1
            return self.reminder_counts[intent_id]

    async def get_reminder_count(self, intent_id: str) -> int:
        """Récupère compteur de rappel de manière thread-safe"""
        async with self._reminder_lock:
            return self.reminder_counts.get(intent_id, 0)

    async def delete_reminder(self, intent_id: str) -> None:
        """Supprime compteur de rappel de manière thread-safe"""
        async with self._reminder_lock:
            self.reminder_counts.pop(intent_id, None)

    async def check_expiring_intents(
        self, user_id: str, lookahead_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Check for intentions approaching their deadline.

        Args:
            user_id: User identifier
            lookahead_days: Days to look ahead (default: 7)

        Returns:
            List of expiring intents with reminder info
        """
        try:
            knowledge_name = "emergence_knowledge"  # or from env
            col = self.vector_service.get_or_create_collection(knowledge_name)

            now = datetime.now(timezone.utc)
            deadline = now + timedelta(days=lookahead_days)

            # Query intents with upcoming deadlines
            where = {
                "$and": [
                    {"user_id": user_id},
                    {"type": "intent"},
                ]
            }

            got = col.get(where=where, include=["documents", "metadatas"])
            docs = got.get("documents", []) or []
            metas = got.get("metadatas", []) or []
            ids = got.get("ids", []) or []

            expiring = []

            for i, meta in enumerate(metas):
                if not meta or not isinstance(meta, dict):
                    continue

                timeframe_str = meta.get("timeframe")
                if not timeframe_str:
                    continue

                # Parse timeframe
                intent_deadline = self.parse_timeframe(timeframe_str)
                if not intent_deadline:
                    continue

                # Check if approaching deadline
                if now <= intent_deadline <= deadline:
                    intent_id = ids[i] if i < len(ids) else ""
                    reminder_count = self.reminder_counts.get(intent_id, 0) if intent_id else 0

                    expiring.append(
                        {
                            "id": intent_id,
                            "text": docs[i] if i < len(docs) else "",
                            "deadline": intent_deadline.isoformat(),
                            "days_remaining": (intent_deadline - now).days,
                            "reminder_count": reminder_count,
                            "metadata": meta,
                        }
                    )

            return expiring

        except Exception as e:
            logger.error(f"Erreur vérification intentions expirantes: {e}")
            return []

    async def send_intent_reminders(
        self, session_id: str, user_id: str, lookahead_days: int = 7
    ) -> int:
        """
        Send reminders for expiring intents via WebSocket.

        Args:
            session_id: Session identifier
            user_id: User identifier
            lookahead_days: Days to look ahead

        Returns:
            Number of reminders sent
        """
        expiring = await self.check_expiring_intents(user_id, lookahead_days)

        if not expiring:
            return 0

        sent_count = 0

        for intent in expiring:
            # Skip if already reminded 3+ times
            if intent["reminder_count"] >= 3:
                logger.info(
                    f"Intent {intent['id']} ignoré après 3 rappels, purge recommandée"
                )
                continue

            # Send reminder via WebSocket
            if self.connection_manager:
                try:
                    await self.connection_manager.send_personal_message(
                        {
                            "type": "ws:memory_reminder",
                            "payload": {
                                "intent_id": intent["id"],
                                "text": intent["text"],
                                "deadline": intent["deadline"],
                                "days_remaining": intent["days_remaining"],
                                "reminder_count": intent["reminder_count"] + 1,
                            },
                        },
                        session_id,
                    )

                    # Increment reminder count (thread-safe)
                    await self.increment_reminder(intent["id"])
                    sent_count += 1

                    logger.info(
                        f"Rappel intention envoyé: {intent['id']} "
                        f"(J-{intent['days_remaining']}, "
                        f"rappel #{intent['reminder_count'] + 1})"
                    )

                except Exception as e:
                    logger.warning(
                        f"Erreur envoi rappel intention {intent['id']}: {e}"
                    )

        return sent_count

    async def purge_ignored_intents(self, user_id: str) -> int:
        """
        Purge intents that have been reminded 3+ times without action.

        Args:
            user_id: User identifier

        Returns:
            Number of intents purged
        """
        try:
            knowledge_name = "emergence_knowledge"
            col = self.vector_service.get_or_create_collection(knowledge_name)

            purged = 0

            # Find intents to purge (thread-safe copy)
            async with self._reminder_lock:
                intents_to_purge = [
                    intent_id for intent_id, count in self.reminder_counts.items() if count >= 3
                ]

            # Purge intents (outside lock to avoid long hold)
            for intent_id in intents_to_purge:
                try:
                    col.delete(ids=[intent_id])
                    await self.delete_reminder(intent_id)  # Thread-safe delete
                    purged += 1
                    logger.info(f"Intention {intent_id} purgée (3+ rappels ignorés)")
                except Exception as e:
                    logger.warning(f"Erreur purge intention {intent_id}: {e}")

            return purged

        except Exception as e:
            logger.error(f"Erreur purge intentions ignorées: {e}")
            return 0

    async def mark_intent_completed(self, intent_id: str) -> None:
        """Mark intent as completed (remove from reminder tracking) - thread-safe."""
        await self.delete_reminder(intent_id)
        logger.info(f"Intention {intent_id} marquée comme complétée")
