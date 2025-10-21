# src/backend/core/ws_outbox.py
"""
WsOutbox - WebSocket outbound message coalescing + backpressure

Problème résolu:
- Rafales de messages WS saturent la bande passante
- Pas de régulation de débit sortant
- Latence frontend due aux bursts réseau

Solution:
- Queue avec backpressure (maxsize=512)
- Coalescence sur 25ms pour grouper les messages
- Envoi par batch (newline-delimited JSON)
- Gestion propre du shutdown (stop event)

Usage:
    outbox = WsOutbox(websocket)
    await outbox.start()

    await outbox.send({"type": "chat.message", "payload": {...}})

    await outbox.stop()
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket

try:
    from prometheus_client import Gauge, Counter, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Config
COALESCE_MS = 25  # Fenêtre de coalescence (25ms)
OUTBOX_MAX = 512  # Taille max queue (backpressure)

# Métriques Prometheus
if PROMETHEUS_AVAILABLE:
    ws_outbox_queue_size = Gauge(
        "ws_outbox_queue_size",
        "Current size of WsOutbox message queue"
    )
    ws_outbox_batch_size = Histogram(
        "ws_outbox_batch_size",
        "Size of message batches sent via WsOutbox",
        buckets=[1, 2, 5, 10, 20, 50, 100]
    )
    ws_outbox_send_latency = Histogram(
        "ws_outbox_send_latency_seconds",
        "Latency of WsOutbox batch sends",
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25]
    )
    ws_outbox_dropped_total = Counter(
        "ws_outbox_dropped_messages_total",
        "Total number of messages dropped due to full queue"
    )
    ws_outbox_send_errors_total = Counter(
        "ws_outbox_send_errors_total",
        "Total number of send errors"
    )
else:
    ws_outbox_queue_size: Optional[Gauge] = None  # type: ignore[assignment,no-redef]
    ws_outbox_batch_size: Optional[Histogram] = None  # type: ignore[assignment,no-redef]
    ws_outbox_send_latency: Optional[Histogram] = None  # type: ignore[assignment,no-redef]
    ws_outbox_dropped_total: Optional[Counter] = None  # type: ignore[assignment,no-redef]
    ws_outbox_send_errors_total: Optional[Counter] = None  # type: ignore[assignment,no-redef]


class WsOutbox:
    """
    Buffer sortant WebSocket avec coalescence et backpressure.

    Principe:
    - Messages ajoutés à la queue
    - Drain loop groupe les messages sur 25ms
    - Envoi groupé (newline-delimited JSON)
    - Drop si queue pleine (backpressure)
    """

    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.q: asyncio.Queue = asyncio.Queue(maxsize=OUTBOX_MAX)
        self._task: Optional[asyncio.Task] = None
        self._closed = asyncio.Event()
        self._stats = {
            "sent_batches": 0,
            "sent_messages": 0,
            "dropped_messages": 0,
            "send_errors": 0,
        }

    async def start(self) -> None:
        """Démarre la drain loop."""
        if self._task is not None:
            logger.warning("[WsOutbox] Already started")
            return

        self._task = asyncio.create_task(self._drain())
        logger.debug("[WsOutbox] Started drain loop")

    async def stop(self) -> None:
        """Arrête la drain loop proprement."""
        self._closed.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("[WsOutbox] Drain task did not finish in time")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        logger.info(
            f"[WsOutbox] Stopped - Stats: sent_batches={self._stats['sent_batches']}, "
            f"sent_messages={self._stats['sent_messages']}, "
            f"dropped={self._stats['dropped_messages']}, "
            f"errors={self._stats['send_errors']}"
        )

    async def send(self, payload: Dict[str, Any]) -> None:
        """
        Envoie un message (ajout à la queue).

        Si la queue est pleine, drop le message (backpressure).
        """
        try:
            self.q.put_nowait(payload)
            # Mise à jour métrique queue size
            if ws_outbox_queue_size:
                ws_outbox_queue_size.set(self.q.qsize())
        except asyncio.QueueFull:
            self._stats["dropped_messages"] += 1
            if ws_outbox_dropped_total:
                ws_outbox_dropped_total.inc()
            logger.warning(
                f"[WsOutbox] Dropped message due to full queue "
                f"(queue_size={self.q.qsize()}, max={OUTBOX_MAX})"
            )

    def get_stats(self) -> Dict[str, int]:
        """Retourne les stats actuelles."""
        return {
            **self._stats,
            "queue_size": self.q.qsize(),
        }

    async def _drain(self) -> None:
        """
        Drain loop: récupère messages et les groupe par batch de 25ms.
        """
        while not self._closed.is_set():
            try:
                # Attend le premier message (timeout 100ms pour vérifier _closed)
                try:
                    first = await asyncio.wait_for(self.q.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                # Groupe les messages sur 25ms
                batch = [first]
                deadline = time.perf_counter() + (COALESCE_MS / 1000)

                while time.perf_counter() < deadline:
                    try:
                        batch.append(self.q.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                # Envoi du batch
                await self._send_batch(batch)

            except asyncio.CancelledError:
                logger.debug("[WsOutbox] Drain loop cancelled")
                break
            except Exception as e:
                logger.error(f"[WsOutbox] Unexpected error in drain loop: {e}", exc_info=True)
                # Continue la loop malgré l'erreur

    async def _send_batch(self, batch: list) -> None:
        """
        Envoie un batch de messages (newline-delimited JSON).
        """
        if not batch:
            return

        start_time = time.perf_counter()

        try:
            # Sérialisation newline-delimited JSON
            msg = "\n".join(json.dumps(x) for x in batch)

            # Envoi WebSocket
            await self.ws.send_text(msg)

            # Stats
            self._stats["sent_batches"] += 1
            self._stats["sent_messages"] += len(batch)

            # Métriques Prometheus
            if ws_outbox_batch_size:
                ws_outbox_batch_size.observe(len(batch))
            if ws_outbox_send_latency:
                latency = time.perf_counter() - start_time
                ws_outbox_send_latency.observe(latency)
            if ws_outbox_queue_size:
                ws_outbox_queue_size.set(self.q.qsize())

            logger.debug(f"[WsOutbox] Sent batch of {len(batch)} messages")

        except Exception as e:
            self._stats["send_errors"] += 1
            if ws_outbox_send_errors_total:
                ws_outbox_send_errors_total.inc()
            logger.error(
                f"[WsOutbox] Error sending batch (size={len(batch)}): {e}",
                exc_info=True
            )
