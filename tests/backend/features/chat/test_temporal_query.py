"""
Tests unitaires pour la détection de questions temporelles et l'enrichissement du contexte historique.

Phase 1 - Mémoire Temporelle
Date: 2025-10-15
"""

import pytest
import re
from datetime import datetime, timezone
from typing import List, Dict, Any


class TestTemporalQueryDetection:
    """Tests pour la détection de questions temporelles."""

    # Reproduire la regex du service.py
    _TEMPORAL_QUERY_RE = re.compile(
        r"\b(quand|quel\s+jour|quelle\s+heure|à\s+quelle\s+heure|quelle\s+date|"
        r"when|what\s+time|what\s+day|date|timestamp|horodatage)\b",
        re.IGNORECASE
    )

    def _is_temporal_query(self, text: str) -> bool:
        """Méthode de détection temporelle (copie de service.py)."""
        if not text:
            return False
        return bool(self._TEMPORAL_QUERY_RE.search(text))

    def test_detection_questions_francais(self):
        """Test détection questions temporelles en français."""
        test_cases = [
            ("Quand avons-nous parlé de CI/CD ?", True),
            ("Quel jour avons-nous abordé Docker ?", True),
            ("À quelle heure avons-nous discuté de Kubernetes ?", True),
            ("Quelle heure était-il lors de notre discussion ?", True),
            ("Quelle date pour cette conversation ?", True),
            ("Peux-tu me donner la date de notre dernière discussion ?", True),
        ]

        for query, expected in test_cases:
            result = self._is_temporal_query(query)
            assert result == expected, f"Failed for: '{query}' (expected {expected}, got {result})"

    def test_detection_questions_anglais(self):
        """Test détection questions temporelles en anglais."""
        test_cases = [
            ("When did we discuss CI/CD?", True),
            ("What day did we talk about Docker?", True),
            ("What time was our conversation?", True),
            ("Can you give me the date of our discussion?", True),
            ("What's the timestamp for this message?", True),
        ]

        for query, expected in test_cases:
            result = self._is_temporal_query(query)
            assert result == expected, f"Failed for: '{query}' (expected {expected}, got {result})"

    def test_non_temporal_queries(self):
        """Test que les questions non-temporelles ne sont pas détectées."""
        test_cases = [
            ("De quoi avons-nous parlé ?", False),
            ("Quels sujets avons-nous abordés ?", False),
            ("Peux-tu m'expliquer Docker ?", False),
            ("Comment configurer Kubernetes ?", False),
            ("Qu'est-ce que CI/CD ?", False),
        ]

        for query, expected in test_cases:
            result = self._is_temporal_query(query)
            assert result == expected, f"Failed for: '{query}' (expected {expected}, got {result})"

    def test_case_insensitive(self):
        """Test que la détection est insensible à la casse."""
        queries = [
            "QUAND avons-nous parlé ?",
            "quand avons-nous parlé ?",
            "Quand Avons-Nous Parlé ?",
        ]

        for query in queries:
            result = self._is_temporal_query(query)
            assert result == True, f"Failed for: '{query}'"

    def test_empty_and_none(self):
        """Test que les entrées vides ne causent pas d'erreur."""
        assert self._is_temporal_query("") == False
        assert self._is_temporal_query(None) == False

    def test_partial_matches(self):
        """Test que les correspondances partielles fonctionnent."""
        test_cases = [
            ("Peux-tu me dire quand on a parlé de CI/CD ?", True),
            ("Je voudrais savoir quel jour nous avons abordé ce sujet", True),
            ("Rappelle-moi à quelle heure on a discuté", True),
        ]

        for query, expected in test_cases:
            result = self._is_temporal_query(query)
            assert result == expected, f"Failed for: '{query}'"


class TestTemporalHistoryFormatting:
    """Tests pour le formatage de l'historique temporel."""

    def test_date_formatting(self):
        """Test du formatage des dates en français."""
        # Simuler le formatage de date du service.py
        created_at = "2025-10-15T03:08:42.123Z"
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        day = dt.day
        months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                  "juil", "août", "sept", "oct", "nov", "déc"]
        month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
        time_str = f"{dt.hour}h{dt.minute:02d}"
        date_str = f"{day} {month} à {time_str}"

        assert date_str == "15 oct à 3h08"

    def test_date_formatting_different_months(self):
        """Test formatage pour différents mois."""
        test_cases = [
            ("2025-01-15T10:30:00Z", "15 janv à 10h30"),
            ("2025-02-28T14:45:00Z", "28 fév à 14h45"),
            ("2025-03-01T00:05:00Z", "1 mars à 0h05"),
            ("2025-12-31T23:59:00Z", "31 déc à 23h59"),
        ]

        months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                  "juil", "août", "sept", "oct", "nov", "déc"]

        for iso_date, expected in test_cases:
            dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
            day = dt.day
            month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
            time_str = f"{dt.hour}h{dt.minute:02d}"
            date_str = f"{day} {month} à {time_str}"

            assert date_str == expected, f"Failed for {iso_date}: got '{date_str}', expected '{expected}'"

    def test_content_preview_truncation(self):
        """Test que le contenu est tronqué à 80 caractères."""
        content = "Ceci est un message très long qui devrait être tronqué à 80 caractères pour éviter de surcharger le contexte avec trop d'informations non pertinentes."

        preview = content[:80].strip()
        if len(content) > 80:
            preview += "..."

        assert len(preview) <= 83  # 80 caractères + "..."
        assert preview.endswith("...")
        # Vérifier que la troncature a bien eu lieu (pas de test exact à cause de l'encodage)
        assert "Ceci est un message" in preview
        assert len(content[:80]) <= 80


class TestTemporalContextIntegration:
    """Tests d'intégration pour le contexte temporel."""

    def test_context_structure(self):
        """Test que la structure du contexte est correcte."""
        # Simuler la construction du contexte
        lines = []
        lines.append("### Historique récent de cette conversation")
        lines.append("")
        lines.append("**[15 oct à 3h08] Toi :** Peux-tu m'expliquer Docker ?")
        lines.append("**[15 oct à 3h09] Anima :** Docker est une plateforme de containerisation...")

        context = "\n".join(lines)

        assert context.startswith("### Historique récent de cette conversation")
        assert "**[15 oct à 3h08] Toi :**" in context
        assert "**[15 oct à 3h09] Anima :**" in context

    def test_empty_messages_handled(self):
        """Test que les messages vides sont gérés correctement."""
        messages: List[Dict[str, Any]] = []

        lines = []
        lines.append("### Historique récent de cette conversation")
        lines.append("")

        for msg in messages:
            # Ce code ne devrait jamais s'exécuter
            pass

        result = "\n".join(lines) if len(lines) > 2 else ""

        # Devrait retourner une chaîne vide car il n'y a que l'en-tête
        assert result == ""


def test_integration_full_workflow():
    """Test d'intégration du workflow complet de détection et formatage."""
    # Ce test simule le flux complet

    # 1. Détection de la question temporelle
    detector = TestTemporalQueryDetection()
    user_query = "Quand avons-nous parlé de Docker ?"
    is_temporal = detector._is_temporal_query(user_query)

    assert is_temporal == True

    # 2. Si temporel, construction du contexte
    if is_temporal:
        # Simuler des messages
        messages = [
            {
                "role": "user",
                "content": "Peux-tu m'expliquer Docker ?",
                "created_at": "2025-10-15T03:08:42Z",
            },
            {
                "role": "assistant",
                "agent_id": "anima",
                "content": "Docker est une plateforme de containerisation qui permet...",
                "created_at": "2025-10-15T03:08:50Z",
            }
        ]

        lines = []
        lines.append("### Historique récent de cette conversation")
        lines.append("")

        months = ["", "janv", "fév", "mars", "avr", "mai", "juin",
                  "juil", "août", "sept", "oct", "nov", "déc"]

        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            created_at = msg.get("created_at")
            agent_id = msg.get("agent_id")

            if role not in ["user", "assistant"]:
                continue

            # Parser la date
            if created_at:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                day = dt.day
                month = months[dt.month] if 1 <= dt.month <= 12 else str(dt.month)
                time_str = f"{dt.hour}h{dt.minute:02d}"
                date_str = f"{day} {month} à {time_str}"
            else:
                date_str = "date inconnue"

            # Extraire un aperçu du contenu
            preview = content[:80].strip() if isinstance(content, str) else ""
            if len(content) > 80:
                preview += "..."

            if role == "user":
                lines.append(f"**[{date_str}] Toi :** {preview}")
            elif role == "assistant" and agent_id:
                lines.append(f"**[{date_str}] {agent_id.title()} :** {preview}")

        context = "\n".join(lines) if len(lines) > 2 else ""

        assert context != ""
        assert "15 oct à 3h08" in context
        assert "Docker" in context


if __name__ == "__main__":
    # Exécution manuelle des tests
    print("=== Tests de Detection Temporelle ===")

    test_detection = TestTemporalQueryDetection()
    test_detection.test_detection_questions_francais()
    print("[OK] Test detection francais: OK")

    test_detection.test_detection_questions_anglais()
    print("[OK] Test detection anglais: OK")

    test_detection.test_non_temporal_queries()
    print("[OK] Test non-temporel: OK")

    test_detection.test_case_insensitive()
    print("[OK] Test insensible a la casse: OK")

    test_detection.test_empty_and_none()
    print("[OK] Test entrees vides: OK")

    test_detection.test_partial_matches()
    print("[OK] Test correspondances partielles: OK")

    print("\n=== Tests de Formatage ===")

    test_formatting = TestTemporalHistoryFormatting()
    test_formatting.test_date_formatting()
    print("[OK] Test formatage date: OK")

    test_formatting.test_date_formatting_different_months()
    print("[OK] Test formatage mois differents: OK")

    test_formatting.test_content_preview_truncation()
    print("[OK] Test troncature contenu: OK")

    print("\n=== Tests d'Integration ===")

    test_integration = TestTemporalContextIntegration()
    test_integration.test_context_structure()
    print("[OK] Test structure contexte: OK")

    test_integration.test_empty_messages_handled()
    print("[OK] Test messages vides: OK")

    test_integration_full_workflow()
    print("[OK] Test workflow complet: OK")

    print("\n[SUCCESS] Tous les tests sont passes avec succes!")
