"""
File de tâches asynchrone pour MemoryAnalyzer et MemoryGardener.
Évite blocage event loop WebSocket.

Usage:
    queue = get_memory_queue()
    await queue.start()
    await queue.enqueue("analyze", {"session_id": "..."})
    await queue.enqueue("consolidate_thread", {"thread_id": "...", "session_id": "...", "user_id": "..."})
"""

import asyncio
import logging
from typing import Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MemoryTask:
    """Tâche d'analyse/jardinage mémoire"""

    task_type: str  # "analyze" | "garden" | "consolidate_thread"
    payload: dict
    callback: Callable | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class MemoryTaskQueue:
    """
    File de tâches asynchrone pour opérations mémoire lourdes.

    Usage:
        queue = MemoryTaskQueue()
        await queue.start()
        await queue.enqueue("analyze", {"session_id": "..."})
    """

    def __init__(self, max_workers: int = 2):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.max_workers = max_workers
        self.workers: list[asyncio.Task] = []
        self.running = False

    async def start(self):
        """Démarre les workers de traitement"""
        if self.running:
            return

        self.running = True
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)
        logger.info(f"MemoryTaskQueue started with {self.max_workers} workers")

    async def stop(self):
        """Arrête proprement les workers"""
        self.running = False

        # Envoyer signal arrêt
        for _ in range(self.max_workers):
            await self.queue.put(None)

        # Attendre fin workers
        await asyncio.gather(*self.workers, return_exceptions=True)
        logger.info("MemoryTaskQueue stopped")

    async def enqueue(
        self, task_type: str, payload: dict, callback: Callable | None = None
    ):
        """Ajoute une tâche à la file"""
        task = MemoryTask(task_type=task_type, payload=payload, callback=callback)
        await self.queue.put(task)
        logger.debug(f"Task enqueued: {task_type} - {payload.get('session_id', 'N/A')}")

    async def _worker(self, worker_id: int):
        """Worker qui consomme la file"""
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Attendre tâche (timeout pour vérifier self.running)
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                if task is None:  # Signal arrêt
                    break

                # Traiter tâche
                await self._process_task(task, worker_id)

            except asyncio.TimeoutError:
                continue  # Pas de tâche, continuer
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)

        logger.info(f"Worker {worker_id} stopped")

    async def _process_task(self, task: MemoryTask, worker_id: int):
        """Traite une tâche mémoire"""
        start = datetime.utcnow()

        try:
            if task.task_type == "analyze":
                result = await self._run_analysis(task.payload)
            elif task.task_type == "garden":
                result = await self._run_gardening(task.payload)
            elif task.task_type == "consolidate_thread":
                # 🆕 NOUVEAU (Phase P0): Consolidation thread archivé
                result = await self._run_thread_consolidation(task.payload)
            else:
                logger.warning(f"Unknown task type: {task.task_type}")
                return

            duration = (datetime.utcnow() - start).total_seconds()
            logger.info(
                f"Worker {worker_id} completed {task.task_type} in {duration:.2f}s"
            )

            # Callback si fourni
            if task.callback:
                await task.callback(result)

        except Exception as e:
            logger.error(f"Task {task.task_type} failed: {e}", exc_info=True)

    async def _run_analysis(self, payload: dict):
        """Exécute MemoryAnalyzer.analyze_session_for_concepts"""
        from backend.containers import ServiceContainer

        container = ServiceContainer()
        analyzer = container.memory_analyzer()
        session_id = payload["session_id"]
        force = payload.get("force", False)

        # Récupérer l'historique depuis la session
        chat_service = container.chat_service()
        session_manager = getattr(chat_service, "session_manager", None)
        if not session_manager:
            logger.error(f"SessionManager not available for session {session_id}")
            return {"status": "error", "session_id": session_id}

        try:
            session = session_manager.get_session(session_id)
            history = getattr(session, "history", [])
        except Exception as e:
            logger.error(f"Failed to get history for session {session_id}: {e}")
            return {"status": "error", "session_id": session_id}

        result = await analyzer.analyze_session_for_concepts(
            session_id, history=history, force=force
        )
        return {"status": "completed", "session_id": session_id, "result": result}

    async def _run_gardening(self, payload: dict):
        """Exécute MemoryGardener.garden_thread"""
        from backend.containers import ServiceContainer

        container = ServiceContainer()
        gardener = container.memory_gardener()
        thread_id = payload["thread_id"]
        user_sub = payload.get("user_sub")

        await gardener.garden_thread(thread_id, user_sub=user_sub)
        return {"status": "gardened", "thread_id": thread_id}

    async def _run_thread_consolidation(self, payload: dict):
        """
        🆕 Phase P0: Consolide un thread archivé dans LTM.

        Payload:
            - thread_id (required): ID du thread à consolider
            - session_id (optional): Session ID associée
            - user_id (optional): User ID propriétaire
            - reason (optional): Raison de la consolidation ("archiving", "manual", etc.)
        """
        from backend.containers import ServiceContainer
        from backend.features.memory.gardener import MemoryGardener

        thread_id = payload.get("thread_id")
        session_id = payload.get("session_id")
        user_id = payload.get("user_id")
        reason = payload.get("reason", "manual")

        if not thread_id:
            logger.warning("[MemoryTaskQueue] consolidate_thread sans thread_id")
            return {"status": "error", "message": "Missing thread_id"}

        # Récupérer gardener depuis container
        container = ServiceContainer()
        gardener = MemoryGardener(
            db_manager=container.db_manager(),
            vector_service=container.vector_service(),
            memory_analyzer=container.memory_analyzer()
        )

        # Consolider thread
        logger.info(
            f"[MemoryTaskQueue] Consolidating archived thread {thread_id} "
            f"(reason: {reason})"
        )

        result = await gardener._tend_single_thread(
            thread_id=thread_id,
            session_id=session_id,
            user_id=user_id
        )

        new_concepts = result.get("new_concepts", 0)
        logger.info(
            f"[MemoryTaskQueue] Thread {thread_id} consolidated: "
            f"{new_concepts} new concepts"
        )

        return {
            "status": "consolidated",
            "thread_id": thread_id,
            "new_concepts": new_concepts,
            "result": result
        }


# Singleton global
_task_queue: MemoryTaskQueue | None = None


def get_memory_queue() -> MemoryTaskQueue:
    """Récupère l'instance globale de la file"""
    global _task_queue
    if _task_queue is None:
        _task_queue = MemoryTaskQueue(max_workers=2)
    return _task_queue
