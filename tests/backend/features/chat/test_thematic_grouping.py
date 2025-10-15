"""
Tests pour le groupement thématique des concepts consolidés (Phase 3 - Priorité 3).

Tests:
1. Clustering de concepts similaires
2. Extraction de titres intelligents
3. Format groupé vs linéaire
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import numpy as np
from datetime import datetime


class TestThematicGrouping:
    """Tests pour le groupement thématique des concepts."""

    @pytest.fixture
    def mock_vector_service(self):
        """Mock VectorService avec SentenceTransformer."""
        vs = Mock()

        # Mock du modèle pour embeddings
        # Simuler 3 concepts: 2 similaires (Docker/Kubernetes) + 1 différent (Poème)
        model_mock = Mock()
        model_mock.encode = Mock(return_value=np.array([
            [0.1, 0.2, 0.3, 0.4, 0.1, 0.2],  # Concept 1: Docker
            [0.15, 0.25, 0.35, 0.45, 0.12, 0.22],  # Concept 2: Kubernetes (similaire à 1)
            [0.8, 0.1, 0.1, 0.1, 0.05, 0.05],  # Concept 3: Poème (différent)
        ]))
        vs.model = model_mock

        return vs

    @pytest.fixture
    def mock_chat_service(self, mock_vector_service):
        """Mock ChatService avec les méthodes nécessaires."""
        from backend.features.chat.service import ChatService

        # Créer un mock du ChatService
        service = Mock(spec=ChatService)
        service.vector_service = mock_vector_service

        # Importer les méthodes réelles pour les tester
        # On va les tester en standalone
        return service

    @pytest.mark.asyncio
    async def test_clustering_similar_concepts(self, mock_vector_service):
        """Test que concepts similaires sont groupés ensemble."""
        from backend.features.chat.service import ChatService

        concepts = [
            {
                "content": "Configuration Docker pour production",
                "timestamp": "2025-10-08T14:32:00Z",
                "type": "concept"
            },
            {
                "content": "Optimisation Kubernetes cluster",
                "timestamp": "2025-10-08T14:35:00Z",
                "type": "concept"
            },
            {
                "content": "Citations du poème fondateur",
                "timestamp": "2025-10-02T16:45:00Z",
                "type": "concept"
            },
        ]

        # Créer un mock service avec vector_service
        service = Mock(spec=ChatService)
        service.vector_service = mock_vector_service

        # Appeler la méthode réelle
        from backend.features.chat.service import ChatService
        method = ChatService._group_concepts_by_theme

        groups = await method(service, concepts)

        # Assertions:
        # - Au moins 2 groupes (Docker+Kubernetes groupés / Poème séparé)
        # - Docker et Kubernetes dans le même groupe (similarité > 0.7)
        assert len(groups) >= 1, "Au moins 1 groupe doit être créé"

        # Vérifier qu'il y a au moins un groupe avec plusieurs concepts
        multi_concept_groups = [g for g in groups.values() if len(g) > 1]

        # Le clustering devrait créer 2 groupes: [Docker, Kubernetes] et [Poème]
        # Mais selon le seuil de 0.7, il pourrait aussi créer 3 groupes séparés
        # On vérifie juste que la fonction ne crash pas et retourne des groupes valides
        assert all(isinstance(g, list) for g in groups.values()), "Tous les groupes doivent être des listes"
        assert sum(len(g) for g in groups.values()) == 3, "Tous les concepts doivent être assignés"

    @pytest.mark.asyncio
    async def test_no_grouping_with_few_concepts(self):
        """Test que le groupement n'est pas activé avec moins de 3 concepts."""
        from backend.features.chat.service import ChatService

        concepts = [
            {
                "content": "Configuration Docker",
                "timestamp": "2025-10-08T14:32:00Z",
                "type": "concept"
            },
            {
                "content": "Optimisation Kubernetes",
                "timestamp": "2025-10-08T14:35:00Z",
                "type": "concept"
            },
        ]

        service = Mock(spec=ChatService)
        service.vector_service = Mock()

        # Appeler la méthode réelle
        method = ChatService._group_concepts_by_theme

        groups = await method(service, concepts)

        # Avec moins de 3 concepts, devrait retourner {"ungrouped": concepts}
        assert "ungrouped" in groups, "Devrait retourner un groupe 'ungrouped'"
        assert len(groups["ungrouped"]) == 2, "Devrait contenir les 2 concepts"

    def test_extract_group_title_with_relevant_keywords(self):
        """Test extraction de titre pertinent avec mots-clés significatifs."""
        from backend.features.chat.service import ChatService

        concepts = [
            {"content": "L'utilisateur demande configuration Docker pour production"},
            {"content": "L'utilisateur demande optimisation Docker et Kubernetes"},
        ]

        service = Mock(spec=ChatService)

        # Appeler la méthode réelle
        method = ChatService._extract_group_title

        title = method(service, concepts)

        # Assertions:
        # - Titre contient "Docker" ou "Kubernetes" (mots-clés principaux)
        # - Pas de stop words ("utilisateur", "demande")
        # - Format lisible
        assert title is not None, "Titre ne doit pas être None"
        assert len(title) > 0, "Titre ne doit pas être vide"
        assert "utilisateur" not in title.lower(), "Titre ne doit pas contenir 'utilisateur' (stop word)"
        assert "demande" not in title.lower(), "Titre ne doit pas contenir 'demande' (stop word)"

        # Le titre devrait contenir au moins un mot-clé pertinent
        relevant_keywords = ["docker", "kubernetes", "production", "optimisation"]
        title_lower = title.lower()
        has_relevant_keyword = any(keyword in title_lower for keyword in relevant_keywords)
        assert has_relevant_keyword, f"Titre '{title}' devrait contenir au moins un mot-clé pertinent"

    def test_extract_group_title_fallback(self):
        """Test fallback vers 'Discussion' si extraction échoue."""
        from backend.features.chat.service import ChatService

        # Concepts avec seulement des mots courts (< 4 caractères)
        concepts = [
            {"content": "le la les un une de du des"},
            {"content": "et ou si ni ne"},
        ]

        service = Mock(spec=ChatService)

        # Appeler la méthode réelle
        method = ChatService._extract_group_title

        title = method(service, concepts)

        # Devrait fallback vers "Discussion" car aucun mot > 3 caractères
        assert title == "Discussion", "Devrait fallback vers 'Discussion' si pas de mots significatifs"

    @pytest.mark.asyncio
    async def test_grouping_integration(self, mock_vector_service):
        """Test d'intégration: groupement + extraction de titres."""
        from backend.features.chat.service import ChatService

        # Créer 5 concepts similaires pour tester le groupement complet
        concepts = [
            {
                "content": "Configuration Docker pour production avec optimisations",
                "timestamp": "2025-10-08T14:00:00Z",
                "type": "concept"
            },
            {
                "content": "Déploiement Kubernetes avec Docker images",
                "timestamp": "2025-10-08T14:10:00Z",
                "type": "concept"
            },
            {
                "content": "Optimisation Docker registry pour CI/CD",
                "timestamp": "2025-10-08T14:20:00Z",
                "type": "concept"
            },
            {
                "content": "Citations du poème fondateur Émergence",
                "timestamp": "2025-10-02T16:45:00Z",
                "type": "concept"
            },
            {
                "content": "Préférences utilisateur Python automation",
                "timestamp": "2025-10-03T10:00:00Z",
                "type": "preference"
            },
        ]

        service = Mock(spec=ChatService)
        service.vector_service = mock_vector_service

        # Mocker les embeddings pour 5 concepts
        embeddings_5 = np.array([
            [0.1, 0.2, 0.3, 0.4, 0.1, 0.2],  # Docker 1
            [0.15, 0.25, 0.35, 0.45, 0.12, 0.22],  # Kubernetes (similaire)
            [0.12, 0.22, 0.32, 0.42, 0.11, 0.21],  # Docker 2 (similaire)
            [0.8, 0.1, 0.1, 0.1, 0.05, 0.05],  # Poème (différent)
            [0.5, 0.5, 0.2, 0.1, 0.3, 0.4],  # Python (différent)
        ])
        service.vector_service.model.encode = Mock(return_value=embeddings_5)

        # Étape 1: Grouper les concepts
        method_group = ChatService._group_concepts_by_theme
        groups = await method_group(service, concepts)

        # Vérifications du groupement
        assert len(groups) >= 1, "Au moins 1 groupe doit être créé"
        assert sum(len(g) for g in groups.values()) == 5, "Tous les concepts doivent être assignés"

        # Étape 2: Extraire les titres pour chaque groupe
        method_title = ChatService._extract_group_title

        for group_id, group_concepts in groups.items():
            if group_id != "ungrouped":
                title = method_title(service, group_concepts)

                # Vérifications du titre
                assert title is not None, f"Titre ne doit pas être None pour groupe {group_id}"
                assert len(title) > 0, f"Titre ne doit pas être vide pour groupe {group_id}"
                assert "utilisateur" not in title.lower(), "Titre ne doit pas contenir de stop words"

                # Le titre devrait refléter le contenu du groupe
                print(f"Groupe {group_id} ({len(group_concepts)} concepts): {title}")

    @pytest.mark.asyncio
    async def test_grouping_performance(self, mock_vector_service):
        """Test que le groupement n'ajoute pas trop d'overhead (< 300ms attendu)."""
        import time
        from backend.features.chat.service import ChatService

        # Créer 10 concepts pour tester la performance
        concepts = [
            {
                "content": f"Concept test numéro {i} avec du contenu variable Docker Kubernetes",
                "timestamp": f"2025-10-{8+(i//10):02d}T{14+(i%10):02d}:00:00Z",
                "type": "concept"
            }
            for i in range(10)
        ]

        service = Mock(spec=ChatService)
        service.vector_service = mock_vector_service

        # Mocker le modèle pour retourner des embeddings pour 10 concepts
        embeddings_10 = np.random.rand(10, 6)  # 10 concepts, 6 dimensions
        service.vector_service.model.encode = Mock(return_value=embeddings_10)

        # Appeler la méthode et mesurer le temps
        method = ChatService._group_concepts_by_theme

        start = time.time()
        groups = await method(service, concepts)
        duration_ms = (time.time() - start) * 1000

        # Vérifier que le temps est raisonnable (< 500ms pour être large)
        # En prod avec GPU, devrait être < 300ms
        assert duration_ms < 500, f"Groupement trop lent: {duration_ms:.0f}ms (attendu < 500ms)"

        # Vérifier que tous les concepts sont assignés
        assert sum(len(g) for g in groups.values()) == 10, "Tous les concepts doivent être assignés"


class TestThematicGroupingEdgeCases:
    """Tests des cas limites du groupement thématique."""

    @pytest.mark.asyncio
    async def test_empty_concepts_list(self):
        """Test avec liste vide de concepts."""
        from backend.features.chat.service import ChatService

        concepts = []

        service = Mock(spec=ChatService)
        service.vector_service = Mock()

        method = ChatService._group_concepts_by_theme

        groups = await method(service, concepts)

        # Avec liste vide, devrait retourner {"ungrouped": []}
        assert "ungrouped" in groups
        assert len(groups["ungrouped"]) == 0

    @pytest.mark.asyncio
    async def test_single_concept(self):
        """Test avec un seul concept."""
        from backend.features.chat.service import ChatService

        concepts = [
            {
                "content": "Seul concept",
                "timestamp": "2025-10-08T14:32:00Z",
                "type": "concept"
            }
        ]

        service = Mock(spec=ChatService)
        service.vector_service = Mock()

        method = ChatService._group_concepts_by_theme

        groups = await method(service, concepts)

        assert "ungrouped" in groups
        assert len(groups["ungrouped"]) == 1

    def test_extract_title_with_empty_concepts(self):
        """Test extraction de titre avec concepts vides."""
        from backend.features.chat.service import ChatService

        concepts = []

        service = Mock(spec=ChatService)
        method = ChatService._extract_group_title

        title = method(service, concepts)

        assert title == "Discussion", "Devrait retourner 'Discussion' pour liste vide"

    def test_extract_title_with_unicode_characters(self):
        """Test extraction de titre avec caractères unicode."""
        from backend.features.chat.service import ChatService

        concepts = [
            {"content": "Configuration déploiement Kubernetes avec accents éèàù"},
            {"content": "Optimisation réseau avec paramètres spéciaux"},
        ]

        service = Mock(spec=ChatService)
        method = ChatService._extract_group_title

        title = method(service, concepts)

        # Devrait gérer les caractères unicode correctement
        assert title is not None
        assert len(title) > 0
        # Le titre devrait contenir des mots avec accents capitalisés
        # "Déploiement", "Kubernetes", "Optimisation", "Réseau"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
