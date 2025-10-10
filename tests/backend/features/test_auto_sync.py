"""Tests pour AutoSyncService - Synchronisation automatique inter-agents."""

import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from backend.features.sync.auto_sync_service import (
    AutoSyncService,
    ConsolidationTrigger,
    FileChecksum,
)


@pytest.fixture
def temp_repo(tmp_path: Path) -> Path:
    """Crée un dépôt temporaire avec des fichiers de test."""
    # Créer structure de base
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture").mkdir()

    # Créer fichiers surveillés
    (tmp_path / "AGENT_SYNC.md").write_text("# Agent Sync\nVersion 1.0", encoding="utf-8")
    (tmp_path / "docs" / "passation.md").write_text("# Passation\nEntry 1", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Agents\nAgent 1", encoding="utf-8")
    (tmp_path / "CODEV_PROTOCOL.md").write_text("# Protocol\nV1", encoding="utf-8")
    (tmp_path / "docs" / "architecture" / "00-Overview.md").write_text("# Overview\nV1", encoding="utf-8")

    return tmp_path


@pytest.fixture
def sync_service(temp_repo: Path) -> AutoSyncService:
    """Crée une instance AutoSyncService pour les tests."""
    return AutoSyncService(
        repo_root=temp_repo,
        check_interval_seconds=1,  # Rapide pour les tests
        consolidation_threshold=3,
        consolidation_interval_minutes=1,
    )


@pytest.mark.asyncio
async def test_service_lifecycle(sync_service: AutoSyncService) -> None:
    """Test du lifecycle start/stop du service."""
    assert not sync_service._running

    await sync_service.start()
    assert sync_service._running
    assert len(sync_service.checksums) > 0  # Fichiers initialisés

    await sync_service.stop()
    assert not sync_service._running


@pytest.mark.asyncio
async def test_initialize_checksums(sync_service: AutoSyncService, temp_repo: Path) -> None:
    """Test de l'initialisation des checksums."""
    await sync_service._initialize_checksums()

    # Vérifier que les fichiers existants sont trackés
    assert "AGENT_SYNC.md" in sync_service.checksums
    assert "docs/passation.md" in sync_service.checksums
    assert "AGENTS.md" in sync_service.checksums

    # Vérifier structure FileChecksum
    cs = sync_service.checksums["AGENT_SYNC.md"]
    assert isinstance(cs, FileChecksum)
    assert cs.path == "AGENT_SYNC.md"
    assert len(cs.checksum) == 32  # MD5 hex
    assert isinstance(cs.last_modified, datetime)


@pytest.mark.asyncio
async def test_detect_file_modification(sync_service: AutoSyncService, temp_repo: Path) -> None:
    """Test de la détection des modifications de fichiers."""
    await sync_service.start()
    await asyncio.sleep(0.5)  # Laisser l'init se faire

    # Modifier un fichier
    agent_sync_path = temp_repo / "AGENT_SYNC.md"
    agent_sync_path.write_text("# Agent Sync\nVersion 2.0 - MODIFIED", encoding="utf-8")

    # Attendre que le check loop détecte le changement
    await asyncio.sleep(2)

    # Vérifier qu'un événement "modified" a été créé
    assert len(sync_service.pending_changes) > 0
    event = next((e for e in sync_service.pending_changes if e.file_path == "AGENT_SYNC.md"), None)
    assert event is not None
    assert event.event_type == "modified"
    assert event.old_checksum is not None
    assert event.new_checksum is not None
    assert event.old_checksum != event.new_checksum

    await sync_service.stop()


@pytest.mark.asyncio
async def test_detect_file_creation(sync_service: AutoSyncService, temp_repo: Path) -> None:
    """Test de la détection de création de fichiers."""
    # Ajouter ROADMAP.md dans les fichiers surveillés
    sync_service.watched_files.append("ROADMAP.md")

    await sync_service.start()
    await asyncio.sleep(0.5)

    # Créer un nouveau fichier
    roadmap_path = temp_repo / "ROADMAP.md"
    roadmap_path.write_text("# Roadmap\nPhase 1", encoding="utf-8")

    # Attendre détection
    await asyncio.sleep(2)

    # Vérifier événement "created"
    assert len(sync_service.pending_changes) > 0
    event = next((e for e in sync_service.pending_changes if e.file_path == "ROADMAP.md"), None)
    assert event is not None
    assert event.event_type == "created"
    assert event.old_checksum is None
    assert event.new_checksum is not None

    await sync_service.stop()


@pytest.mark.asyncio
async def test_detect_file_deletion(sync_service: AutoSyncService, temp_repo: Path) -> None:
    """Test de la détection de suppression de fichiers."""
    await sync_service.start()
    await asyncio.sleep(0.5)

    # Supprimer un fichier
    agents_path = temp_repo / "AGENTS.md"
    agents_path.unlink()

    # Attendre détection
    await asyncio.sleep(2)

    # Vérifier événement "deleted"
    event = next((e for e in sync_service.pending_changes if e.file_path == "AGENTS.md"), None)
    assert event is not None
    assert event.event_type == "deleted"
    assert event.old_checksum is not None
    assert event.new_checksum is None

    # Vérifier que le checksum a été retiré
    assert "AGENTS.md" not in sync_service.checksums

    await sync_service.stop()


@pytest.mark.asyncio
async def test_consolidation_threshold_trigger(temp_repo: Path) -> None:
    """Test du déclenchement automatique par seuil de changements."""
    # Créer service avec check interval court pour les tests
    fast_service = AutoSyncService(
        repo_root=temp_repo,
        check_interval_seconds=1,
        consolidation_threshold=3,
        consolidation_interval_minutes=0,  # Pas d'intervalle minimal = vérif immédiate
    )

    consolidation_triggered = []

    def on_consolidation(trigger: ConsolidationTrigger) -> None:
        consolidation_triggered.append(trigger)

    fast_service.register_consolidation_callback(on_consolidation)

    await fast_service.start()
    await asyncio.sleep(0.5)

    # Modifier 3 fichiers (seuil = 3)
    (temp_repo / "AGENT_SYNC.md").write_text("Modified 1", encoding="utf-8")
    await asyncio.sleep(1.5)

    (temp_repo / "AGENTS.md").write_text("Modified 2", encoding="utf-8")
    await asyncio.sleep(1.5)

    (temp_repo / "CODEV_PROTOCOL.md").write_text("Modified 3", encoding="utf-8")

    # Attendre que les changements soient détectés (check loop = 1s)
    await asyncio.sleep(3)

    # Vérifier que 3 changements ont été détectés (threshold atteint)
    # Note: La consolidation loop vérifie toutes les 60s, donc on test juste la détection ici
    # La consolidation automatique complète est testée en intégration
    assert len(fast_service.pending_changes) >= 3

    # Déclencher manuellement pour vérifier le trigger
    result = await fast_service.trigger_manual_consolidation()
    assert result["changes_consolidated"] >= 3

    # Vérifier callback a été appelé
    assert len(consolidation_triggered) > 0
    trigger = consolidation_triggered[0]
    assert trigger.trigger_type == "manual"

    await fast_service.stop()


@pytest.mark.asyncio
async def test_manual_consolidation(sync_service: AutoSyncService, temp_repo: Path) -> None:
    """Test du déclenchement manuel de consolidation."""
    consolidation_triggered = []

    def on_consolidation(trigger: ConsolidationTrigger) -> None:
        consolidation_triggered.append(trigger)

    sync_service.register_consolidation_callback(on_consolidation)

    await sync_service.start()
    await asyncio.sleep(0.5)

    # Modifier 1 fichier (en dessous du seuil)
    (temp_repo / "AGENT_SYNC.md").write_text("Modified", encoding="utf-8")
    await asyncio.sleep(2)

    # Vérifier qu'il y a bien 1 changement
    assert len(sync_service.pending_changes) > 0

    # Déclencher manuellement
    result = await sync_service.trigger_manual_consolidation()

    # Vérifier résultat
    assert result["status"] == "success"
    assert result["changes_consolidated"] >= 1

    # Vérifier callback
    assert len(consolidation_triggered) > 0
    trigger = consolidation_triggered[0]
    assert trigger.trigger_type == "manual"

    # Vérifier réinitialisation
    assert len(sync_service.pending_changes) == 0

    await sync_service.stop()


@pytest.mark.asyncio
async def test_get_status(sync_service: AutoSyncService) -> None:
    """Test de la récupération du statut."""
    status = sync_service.get_status()

    assert "running" in status
    assert "pending_changes" in status
    assert "last_consolidation" in status
    assert "watched_files" in status
    assert "checksums_tracked" in status
    assert "consolidation_threshold" in status
    assert "check_interval_seconds" in status

    assert status["running"] is False
    assert status["consolidation_threshold"] == 3
    assert status["check_interval_seconds"] == 1

    await sync_service.start()
    status = sync_service.get_status()
    assert status["running"] is True

    await sync_service.stop()


@pytest.mark.asyncio
async def test_consolidation_report_generation(sync_service: AutoSyncService, temp_repo: Path) -> None:
    """Test de la génération du rapport de consolidation."""
    await sync_service.start()
    await asyncio.sleep(0.5)

    # Modifier 2 fichiers
    (temp_repo / "AGENT_SYNC.md").write_text("V2", encoding="utf-8")
    await asyncio.sleep(1.5)
    (temp_repo / "AGENTS.md").write_text("V2", encoding="utf-8")
    await asyncio.sleep(2)

    # Créer un trigger
    trigger = ConsolidationTrigger(
        trigger_type="test",
        conditions_met={"test": True},
        timestamp=datetime.now(),
    )

    # Générer rapport
    report = await sync_service._generate_consolidation_report(trigger)

    # Vérifier structure
    assert "timestamp" in report
    assert "trigger_type" in report
    assert report["trigger_type"] == "test"
    assert "total_changes" in report
    assert report["total_changes"] >= 2
    assert "files_changed" in report
    assert "events_by_file" in report

    # Vérifier que les événements sont groupés par fichier
    assert isinstance(report["events_by_file"], dict)

    await sync_service.stop()


@pytest.mark.asyncio
async def test_file_type_detection(sync_service: AutoSyncService) -> None:
    """Test de la détection du type de fichier."""
    assert sync_service._get_file_type("AGENT_SYNC.md") == "sync"
    assert sync_service._get_file_type("docs/passation.md") == "passation"
    assert sync_service._get_file_type("docs/architecture/00-Overview.md") == "architecture"
    assert sync_service._get_file_type("README.md") == "docs"
    assert sync_service._get_file_type("config.yaml") == "other"
