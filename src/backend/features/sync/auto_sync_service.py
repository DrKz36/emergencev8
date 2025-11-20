"""
Service de synchronisation automatique inter-agents.

Option A - Synchronisation automatique complète :
- Détection automatique des changements (file watchers)
- Consolidation intelligente (triggers basés sur seuils)
- Scheduler en arrière-plan (tâches périodiques)
- Monitoring du statut de sync (métriques + logs)
"""

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)


# ============================================================================
# MÉTRIQUES PROMETHEUS
# ============================================================================

sync_changes_detected = Counter(
    "sync_changes_detected_total",
    "Nombre de changements détectés dans les fichiers surveillés",
    ["file_type", "agent"],
)

sync_consolidations_triggered = Counter(
    "sync_consolidations_triggered_total",
    "Nombre de consolidations déclenchées",
    ["trigger_type"],
)

sync_status = Gauge(
    "sync_status",
    "Statut de synchronisation (1=synced, 0=out_of_sync, -1=error)",
    ["file_path"],
)

sync_check_duration = Histogram(
    "sync_check_duration_seconds",
    "Durée des vérifications de synchronisation",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

sync_consolidation_duration = Histogram(
    "sync_consolidation_duration_seconds",
    "Durée des consolidations",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class FileChecksum:
    """Checksum d'un fichier surveillé."""

    path: str
    checksum: str
    last_modified: datetime
    agent_owner: str | None = None


@dataclass
class SyncEvent:
    """Événement de changement détecté."""

    file_path: str
    event_type: str  # "modified", "created", "deleted"
    timestamp: datetime
    old_checksum: str | None = None
    new_checksum: str | None = None
    agent_owner: str | None = None


@dataclass
class ConsolidationTrigger:
    """Déclencheur de consolidation."""

    trigger_type: str  # "threshold", "time_based", "manual"
    conditions_met: dict[str, Any]
    timestamp: datetime


# ============================================================================
# AUTO SYNC SERVICE
# ============================================================================


class AutoSyncService:
    """Service de synchronisation automatique inter-agents."""

    def __init__(
        self,
        repo_root: Path,
        check_interval_seconds: int = 30,
        consolidation_threshold: int = 5,
        consolidation_interval_minutes: int = 60,
    ):
        """
        Initialize AutoSyncService.

        Args:
            repo_root: Racine du dépôt Git
            check_interval_seconds: Intervalle de vérification des changements (défaut: 30s)
            consolidation_threshold: Nombre de changements avant consolidation (défaut: 5)
            consolidation_interval_minutes: Intervalle min entre consolidations (défaut: 60min)
        """
        self.repo_root = repo_root
        self.check_interval = check_interval_seconds
        self.consolidation_threshold = consolidation_threshold
        self.consolidation_interval = timedelta(minutes=consolidation_interval_minutes)

        # Fichiers critiques à surveiller (relatifs à repo_root)
        self.watched_files = [
            "AGENT_SYNC.md",
            "docs/passation.md",
            "AGENTS.md",
            "CODEV_PROTOCOL.md",
            "docs/architecture/00-Overview.md",
            "docs/architecture/10-Memoire.md",
            "docs/architecture/30-Contracts.md",
            "ROADMAP.md",
        ]

        # État interne
        self.checksums: dict[str, FileChecksum] = {}
        self.pending_changes: list[SyncEvent] = []
        self.last_consolidation: datetime | None = None
        self.consolidation_callbacks: list[Callable[[ConsolidationTrigger], None]] = []

        # Tâches asyncio
        self._running = False
        self._check_task: asyncio.Task[None] | None = None
        self._consolidation_task: asyncio.Task[None] | None = None

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    async def start(self) -> None:
        """Démarre le service de synchronisation automatique."""
        if self._running:
            logger.warning("AutoSyncService already running")
            return

        logger.info(
            "Starting AutoSyncService (check_interval=%ds, threshold=%d, consolidation_interval=%dmin)",
            self.check_interval,
            self.consolidation_threshold,
            self.consolidation_interval.total_seconds() / 60,
        )

        # Initialiser les checksums
        await self._initialize_checksums()

        # Démarrer les tâches en arrière-plan
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        self._consolidation_task = asyncio.create_task(self._consolidation_loop())

        logger.info("AutoSyncService started successfully")

    async def stop(self) -> None:
        """Arrête le service de synchronisation."""
        if not self._running:
            return

        logger.info("Stopping AutoSyncService...")
        self._running = False

        # Annuler les tâches
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

        if self._consolidation_task:
            self._consolidation_task.cancel()
            try:
                await self._consolidation_task
            except asyncio.CancelledError:
                pass

        logger.info("AutoSyncService stopped")

    # ========================================================================
    # FILE WATCHING
    # ========================================================================

    async def _initialize_checksums(self) -> None:
        """Initialise les checksums de tous les fichiers surveillés."""
        logger.info(
            "Initializing checksums for %d watched files", len(self.watched_files)
        )

        for rel_path in self.watched_files:
            file_path = self.repo_root / rel_path
            if file_path.exists():
                checksum = await self._compute_checksum(file_path)
                agent_owner = self._detect_agent_owner(rel_path)

                self.checksums[rel_path] = FileChecksum(
                    path=rel_path,
                    checksum=checksum,
                    last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                    agent_owner=agent_owner,
                )

                sync_status.labels(file_path=rel_path).set(1)  # synced
            else:
                logger.warning("Watched file not found: %s", rel_path)
                sync_status.labels(file_path=rel_path).set(-1)  # error

    async def _compute_checksum(self, file_path: Path) -> str:
        """Calcule le checksum MD5 d'un fichier."""
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def _detect_agent_owner(self, rel_path: str) -> str | None:
        """Détecte l'agent propriétaire d'un fichier (basé sur le dernier commit)."""
        # Simplification : on pourrait parser git blame ou git log
        # Pour l'instant, on retourne None
        return None

    async def _check_loop(self) -> None:
        """Boucle de vérification périodique des changements."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)

                with sync_check_duration.time():
                    await self._check_for_changes()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in check loop: %s", e, exc_info=True)

    async def _check_for_changes(self) -> None:
        """Vérifie les changements dans les fichiers surveillés."""
        for rel_path in self.watched_files:
            file_path = self.repo_root / rel_path

            if not file_path.exists():
                # Fichier supprimé
                if rel_path in self.checksums:
                    event = SyncEvent(
                        file_path=rel_path,
                        event_type="deleted",
                        timestamp=datetime.now(),
                        old_checksum=self.checksums[rel_path].checksum,
                        new_checksum=None,
                        agent_owner=self.checksums[rel_path].agent_owner,
                    )
                    self.pending_changes.append(event)
                    del self.checksums[rel_path]

                    sync_status.labels(file_path=rel_path).set(0)  # out_of_sync
                    sync_changes_detected.labels(
                        file_type=self._get_file_type(rel_path), agent="unknown"
                    ).inc()

                    logger.warning("File deleted: %s", rel_path)
                continue

            # Calculer nouveau checksum
            new_checksum = await self._compute_checksum(file_path)

            if rel_path not in self.checksums:
                # Fichier créé
                event = SyncEvent(
                    file_path=rel_path,
                    event_type="created",
                    timestamp=datetime.now(),
                    old_checksum=None,
                    new_checksum=new_checksum,
                    agent_owner=self._detect_agent_owner(rel_path),
                )
                self.pending_changes.append(event)

                self.checksums[rel_path] = FileChecksum(
                    path=rel_path,
                    checksum=new_checksum,
                    last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                    agent_owner=event.agent_owner,
                )

                sync_status.labels(file_path=rel_path).set(0)  # out_of_sync
                sync_changes_detected.labels(
                    file_type=self._get_file_type(rel_path), agent="unknown"
                ).inc()

                logger.info("File created: %s", rel_path)

            elif new_checksum != self.checksums[rel_path].checksum:
                # Fichier modifié
                event = SyncEvent(
                    file_path=rel_path,
                    event_type="modified",
                    timestamp=datetime.now(),
                    old_checksum=self.checksums[rel_path].checksum,
                    new_checksum=new_checksum,
                    agent_owner=self._detect_agent_owner(rel_path),
                )
                self.pending_changes.append(event)

                self.checksums[rel_path] = FileChecksum(
                    path=rel_path,
                    checksum=new_checksum,
                    last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                    agent_owner=event.agent_owner,
                )

                sync_status.labels(file_path=rel_path).set(0)  # out_of_sync
                sync_changes_detected.labels(
                    file_type=self._get_file_type(rel_path),
                    agent=event.agent_owner or "unknown",
                ).inc()

                old_chk_display = (
                    event.old_checksum[:8] if event.old_checksum else "None"
                )
                logger.info(
                    "File modified: %s (checksum: %s -> %s)",
                    rel_path,
                    old_chk_display,
                    new_checksum[:8],
                )

    def _get_file_type(self, rel_path: str) -> str:
        """Retourne le type de fichier pour les métriques."""
        if rel_path.endswith(".md"):
            if "architecture" in rel_path:
                return "architecture"
            if "passation" in rel_path:
                return "passation"
            if rel_path == "AGENT_SYNC.md":
                return "sync"
            return "docs"
        return "other"

    # ========================================================================
    # CONSOLIDATION
    # ========================================================================

    async def _consolidation_loop(self) -> None:
        """Boucle de vérification des triggers de consolidation."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Vérifier toutes les minutes

                await self._check_consolidation_triggers()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in consolidation loop: %s", e, exc_info=True)

    async def _check_consolidation_triggers(self) -> None:
        """Vérifie si une consolidation doit être déclenchée."""
        # Trigger 1 : Seuil de changements atteint
        if len(self.pending_changes) >= self.consolidation_threshold:
            trigger = ConsolidationTrigger(
                trigger_type="threshold",
                conditions_met={
                    "pending_changes": len(self.pending_changes),
                    "threshold": self.consolidation_threshold,
                },
                timestamp=datetime.now(),
            )
            await self._trigger_consolidation(trigger)
            return

        # Trigger 2 : Intervalle de temps écoulé
        if self.last_consolidation:
            time_since_last = datetime.now() - self.last_consolidation
            if (
                time_since_last >= self.consolidation_interval
                and len(self.pending_changes) > 0
            ):
                trigger = ConsolidationTrigger(
                    trigger_type="time_based",
                    conditions_met={
                        "pending_changes": len(self.pending_changes),
                        "time_since_last_minutes": time_since_last.total_seconds() / 60,
                    },
                    timestamp=datetime.now(),
                )
                await self._trigger_consolidation(trigger)

    async def _trigger_consolidation(self, trigger: ConsolidationTrigger) -> None:
        """Déclenche une consolidation."""
        logger.info(
            "Triggering consolidation (type=%s, conditions=%s, pending_changes=%d)",
            trigger.trigger_type,
            trigger.conditions_met,
            len(self.pending_changes),
        )

        with sync_consolidation_duration.time():
            # Appeler les callbacks enregistrés
            for callback in self.consolidation_callbacks:
                try:
                    callback(trigger)
                except Exception as e:
                    logger.error(
                        "Error in consolidation callback: %s", e, exc_info=True
                    )

            # Générer rapport de consolidation
            report = await self._generate_consolidation_report(trigger)

            # Écrire le rapport dans AGENT_SYNC.md (section automatique)
            await self._write_consolidation_report(report)

            # Réinitialiser l'état
            self.pending_changes.clear()
            self.last_consolidation = datetime.now()

            # Mettre à jour les statuts (tous les fichiers sont maintenant "synced")
            for rel_path in self.checksums:
                sync_status.labels(file_path=rel_path).set(1)

        sync_consolidations_triggered.labels(trigger_type=trigger.trigger_type).inc()

        logger.info("Consolidation completed successfully")

    async def _generate_consolidation_report(
        self, trigger: ConsolidationTrigger
    ) -> dict[str, Any]:
        """Génère un rapport de consolidation."""
        # Grouper les événements par fichier
        events_by_file: dict[str, list[SyncEvent]] = {}
        for event in self.pending_changes:
            if event.file_path not in events_by_file:
                events_by_file[event.file_path] = []
            events_by_file[event.file_path].append(event)

        return {
            "timestamp": trigger.timestamp.isoformat(),
            "trigger_type": trigger.trigger_type,
            "conditions_met": trigger.conditions_met,
            "total_changes": len(self.pending_changes),
            "files_changed": len(events_by_file),
            "events_by_file": {
                file_path: [
                    {
                        "event_type": e.event_type,
                        "timestamp": e.timestamp.isoformat(),
                        "agent_owner": e.agent_owner,
                    }
                    for e in events
                ]
                for file_path, events in events_by_file.items()
            },
        }

    async def _write_consolidation_report(self, report: dict[str, Any]) -> None:
        """Écrit le rapport de consolidation dans AGENT_SYNC.md."""
        agent_sync_path = self.repo_root / "AGENT_SYNC.md"

        if not agent_sync_path.exists():
            logger.warning("AGENT_SYNC.md not found, skipping report write")
            return

        # Lire le contenu actuel
        content = agent_sync_path.read_text(encoding="utf-8")

        # Chercher la section "## 🤖 Synchronisation automatique"
        section_marker = "## 🤖 Synchronisation automatique"

        if section_marker not in content:
            # Créer la section à la fin
            content += f"\n\n---\n\n{section_marker}\n\n"

        # Insérer le rapport après le marqueur
        report_text = f"""
### Consolidation - {report["timestamp"]}

**Type de déclenchement** : `{report["trigger_type"]}`
**Conditions** : {json.dumps(report["conditions_met"], indent=2)}
**Changements consolidés** : {report["total_changes"]} événements sur {report["files_changed"]} fichiers

**Fichiers modifiés** :
{self._format_events_for_markdown(report["events_by_file"])}

---
"""

        # Insérer après le marqueur de section
        parts = content.split(section_marker, 1)
        if len(parts) == 2:
            # Insérer après le marqueur, avant le contenu existant
            new_content = parts[0] + section_marker + report_text + parts[1]
        else:
            # Ajouter à la fin
            new_content = content + report_text

        # Écrire le nouveau contenu
        agent_sync_path.write_text(new_content, encoding="utf-8")

        logger.info("Consolidation report written to AGENT_SYNC.md")

    def _format_events_for_markdown(
        self, events_by_file: dict[str, list[dict[str, Any]]]
    ) -> str:
        """Formate les événements pour Markdown."""
        lines = []
        for file_path, events in events_by_file.items():
            lines.append(f"- **{file_path}** : {len(events)} événement(s)")
            for event in events:
                lines.append(
                    f"  - `{event['event_type']}` à {event['timestamp']} (agent: {event['agent_owner'] or 'unknown'})"
                )
        return "\n".join(lines)

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def register_consolidation_callback(
        self, callback: Callable[[ConsolidationTrigger], None]
    ) -> None:
        """Enregistre un callback appelé lors de chaque consolidation."""
        self.consolidation_callbacks.append(callback)

    async def trigger_manual_consolidation(self) -> dict[str, Any]:
        """Déclenche manuellement une consolidation."""
        # Capturer le nombre de changements AVANT la consolidation
        changes_count = len(self.pending_changes)

        trigger = ConsolidationTrigger(
            trigger_type="manual",
            conditions_met={"pending_changes": changes_count},
            timestamp=datetime.now(),
        )

        await self._trigger_consolidation(trigger)

        return {
            "status": "success",
            "trigger": asdict(trigger),
            "changes_consolidated": changes_count,
        }

    def get_status(self) -> dict[str, Any]:
        """Retourne le statut actuel de la synchronisation."""
        return {
            "running": self._running,
            "pending_changes": len(self.pending_changes),
            "last_consolidation": self.last_consolidation.isoformat()
            if self.last_consolidation
            else None,
            "watched_files": len(self.watched_files),
            "checksums_tracked": len(self.checksums),
            "consolidation_threshold": self.consolidation_threshold,
            "check_interval_seconds": self.check_interval,
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_auto_sync_service: AutoSyncService | None = None


def get_auto_sync_service(
    repo_root: Path | None = None,
    **kwargs: Any,
) -> AutoSyncService:
    """Retourne l'instance singleton du service."""
    global _auto_sync_service

    if _auto_sync_service is None:
        if repo_root is None:
            # Détecter la racine du repo (remonter depuis ce fichier)
            current_file = Path(__file__)
            repo_root = current_file.parent.parent.parent.parent.parent

        _auto_sync_service = AutoSyncService(repo_root=repo_root, **kwargs)

    return _auto_sync_service
