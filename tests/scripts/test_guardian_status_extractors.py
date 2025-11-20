"""Tests unitaires pour les extracteurs de statuts Guardian.

Tests pour les fonctions normalize_status() et extract_status()
utilisées dans guardian_email_report.py et run_audit.py.
"""

from __future__ import annotations

import pytest
from typing import Any, Sequence


# Copie des fonctions à tester (pour éviter imports circulaires)
def normalize_status(raw_status: Any) -> str:
    """Normalise un statut brut vers un format standard."""
    if raw_status is None:
        return "UNKNOWN"
    status_str = str(raw_status).strip()
    if not status_str:
        return "UNKNOWN"
    upper = status_str.upper()
    if upper in {"OK", "HEALTHY", "SUCCESS"}:
        return "OK"
    if upper in {"WARNING", "WARN"}:
        return "WARNING"
    if upper in {"NEEDS_UPDATE", "STALE"}:
        return "NEEDS_UPDATE"
    if upper in {"ERROR", "FAILED", "FAILURE"}:
        return "ERROR"
    if upper in {"CRITICAL", "SEVERE"}:
        return "CRITICAL"
    return upper


def resolve_path(data: Any, path: Sequence[str]) -> Any:
    """Résout un chemin dans une structure de données imbriquée."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def extract_status(report_name: str, report_data: dict[str, Any]) -> tuple[str, str]:
    """Extrait le statut et timestamp d'un rapport Guardian.

    Args:
        report_name: Nom du rapport (ex: 'prod_report.json')
        report_data: Données du rapport

    Returns:
        Tuple (status, timestamp)
    """
    candidates = [report_data.get("status")]

    executive_summary = report_data.get("executive_summary")
    if isinstance(executive_summary, dict):
        candidates.append(executive_summary.get("status"))

    if report_name == "orchestration_report.json":
        candidates.append(report_data.get("global_status"))

    status = "UNKNOWN"
    for candidate in candidates:
        normalized = normalize_status(candidate)
        if normalized != "UNKNOWN":
            status = normalized
            break

    timestamp = report_data.get("timestamp")
    if not timestamp:
        metadata = report_data.get("metadata")
        if isinstance(metadata, dict):
            timestamp = metadata.get("timestamp")

    return status, timestamp or "N/A"


class TestNormalizeStatus:
    """Tests pour la fonction normalize_status()."""

    def test_normalize_ok_variants(self) -> None:
        """Test normalisation variantes OK."""
        assert normalize_status("OK") == "OK"
        assert normalize_status("ok") == "OK"
        assert normalize_status("healthy") == "OK"
        assert normalize_status("HEALTHY") == "OK"
        assert normalize_status("success") == "OK"
        assert normalize_status("SUCCESS") == "OK"

    def test_normalize_warning_variants(self) -> None:
        """Test normalisation variantes WARNING."""
        assert normalize_status("WARNING") == "WARNING"
        assert normalize_status("warning") == "WARNING"
        assert normalize_status("warn") == "WARNING"
        assert normalize_status("WARN") == "WARNING"

    def test_normalize_error_variants(self) -> None:
        """Test normalisation variantes ERROR."""
        assert normalize_status("ERROR") == "ERROR"
        assert normalize_status("error") == "ERROR"
        assert normalize_status("failed") == "ERROR"
        assert normalize_status("FAILED") == "ERROR"
        assert normalize_status("failure") == "ERROR"
        assert normalize_status("FAILURE") == "ERROR"

    def test_normalize_critical_variants(self) -> None:
        """Test normalisation variantes CRITICAL."""
        assert normalize_status("CRITICAL") == "CRITICAL"
        assert normalize_status("critical") == "CRITICAL"
        assert normalize_status("severe") == "CRITICAL"
        assert normalize_status("SEVERE") == "CRITICAL"

    def test_normalize_needs_update_variants(self) -> None:
        """Test normalisation variantes NEEDS_UPDATE."""
        assert normalize_status("NEEDS_UPDATE") == "NEEDS_UPDATE"
        assert normalize_status("needs_update") == "NEEDS_UPDATE"
        assert normalize_status("stale") == "NEEDS_UPDATE"
        assert normalize_status("STALE") == "NEEDS_UPDATE"

    def test_normalize_unknown_cases(self) -> None:
        """Test cas retournant UNKNOWN."""
        assert normalize_status(None) == "UNKNOWN"
        assert normalize_status("") == "UNKNOWN"
        assert normalize_status("   ") == "UNKNOWN"

    def test_normalize_custom_status(self) -> None:
        """Test statut custom non mappé."""
        # Statut custom doit être retourné uppercase
        assert normalize_status("CUSTOM_STATUS") == "CUSTOM_STATUS"
        assert normalize_status("custom_status") == "CUSTOM_STATUS"

    def test_normalize_whitespace(self) -> None:
        """Test normalisation avec espaces."""
        assert normalize_status("  OK  ") == "OK"
        assert normalize_status("\t\nWARNING\n\t") == "WARNING"


class TestResolvePath:
    """Tests pour la fonction resolve_path()."""

    def test_resolve_simple_path(self) -> None:
        """Test résolution chemin simple."""
        data = {"key1": "value1"}
        assert resolve_path(data, ["key1"]) == "value1"

    def test_resolve_nested_path(self) -> None:
        """Test résolution chemin imbriqué."""
        data = {"level1": {"level2": {"level3": "deep_value"}}}
        assert resolve_path(data, ["level1", "level2", "level3"]) == "deep_value"

    def test_resolve_missing_key(self) -> None:
        """Test résolution clé manquante."""
        data = {"key1": "value1"}
        assert resolve_path(data, ["missing"]) is None

    def test_resolve_invalid_structure(self) -> None:
        """Test résolution structure invalide."""
        data = {"key1": "not_a_dict"}
        assert resolve_path(data, ["key1", "nested"]) is None

    def test_resolve_empty_path(self) -> None:
        """Test résolution chemin vide."""
        data = {"key": "value"}
        assert resolve_path(data, []) == data


class TestExtractStatus:
    """Tests pour la fonction extract_status()."""

    def test_extract_direct_status(self) -> None:
        """Test extraction statut direct."""
        report = {"status": "OK", "timestamp": "2025-10-21T10:00:00"}
        status, timestamp = extract_status("prod_report.json", report)
        assert status == "OK"
        assert timestamp == "2025-10-21T10:00:00"

    def test_extract_executive_summary_fallback(self) -> None:
        """Test extraction depuis executive_summary."""
        report = {
            "executive_summary": {"status": "WARNING"},
            "timestamp": "2025-10-21T10:00:00",
        }
        status, timestamp = extract_status("global_report.json", report)
        assert status == "WARNING"
        assert timestamp == "2025-10-21T10:00:00"

    def test_extract_orchestration_global_status(self) -> None:
        """Test extraction global_status pour orchestration_report."""
        report = {"global_status": "CRITICAL", "timestamp": "2025-10-21T10:00:00"}
        status, timestamp = extract_status("orchestration_report.json", report)
        assert status == "CRITICAL"
        assert timestamp == "2025-10-21T10:00:00"

    def test_extract_timestamp_from_metadata(self) -> None:
        """Test extraction timestamp depuis metadata."""
        report = {"status": "OK", "metadata": {"timestamp": "2025-10-21T11:00:00"}}
        status, timestamp = extract_status("docs_report.json", report)
        assert status == "OK"
        assert timestamp == "2025-10-21T11:00:00"

    def test_extract_unknown_status(self) -> None:
        """Test extraction sans statut valide."""
        report: dict[str, Any] = {}
        status, timestamp = extract_status("empty_report.json", report)
        assert status == "UNKNOWN"
        assert timestamp == "N/A"

    def test_extract_priority_order(self) -> None:
        """Test ordre de priorité extraction statut."""
        # Status direct a priorité sur executive_summary
        report = {
            "status": "OK",
            "executive_summary": {"status": "WARNING"},
            "timestamp": "2025-10-21T10:00:00",
        }
        status, timestamp = extract_status("prod_report.json", report)
        assert status == "OK"  # Status direct gagne

    def test_extract_normalized_status(self) -> None:
        """Test que les statuts sont normalisés."""
        report = {
            "status": "healthy",  # Lowercase
            "timestamp": "2025-10-21T10:00:00",
        }
        status, timestamp = extract_status("prod_report.json", report)
        assert status == "OK"  # Normalisé en OK

    def test_extract_real_prod_report_structure(self) -> None:
        """Test avec structure réelle rapport prod."""
        report: dict[str, Any] = {
            "timestamp": "2025-10-21T07:42:30.233071",
            "service": "emergence-app",
            "status": "OK",
            "summary": {"errors": 0, "warnings": 0},
        }
        status, timestamp = extract_status("prod_report.json", report)
        assert status == "OK"
        assert timestamp == "2025-10-21T07:42:30.233071"

    def test_extract_real_global_report_structure(self) -> None:
        """Test avec structure réelle rapport global."""
        report: dict[str, Any] = {
            "timestamp": "2025-10-21T08:00:00",
            "executive_summary": {"status": "OK", "summary": "All systems operational"},
        }
        status, timestamp = extract_status("global_report.json", report)
        assert status == "OK"
        assert timestamp == "2025-10-21T08:00:00"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
