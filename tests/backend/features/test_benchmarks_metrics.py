"""Tests pour les métriques d'évaluation de ranking (nDCG temporelle)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.features.benchmarks.metrics import ndcg_time_at_k


class TestNDCGTimeAtK:
    """Tests pour la métrique nDCG@k temporelle."""

    def test_empty_list(self) -> None:
        """Liste vide retourne 0.0."""
        score = ndcg_time_at_k([], k=5)
        assert score == 0.0

    def test_single_item_perfect(self) -> None:
        """Un seul item récent et pertinent donne score parfait."""
        now = datetime.now(timezone.utc)
        items = [{"rel": 3.0, "ts": now}]
        score = ndcg_time_at_k(items, k=1, now=now)
        assert 0.99 <= score <= 1.0  # Proche de 1.0

    def test_temporal_decay_old_item(self) -> None:
        """Classement avec item ancien en premier a un score plus faible."""
        now = datetime.now(timezone.utc)

        # Cas 1 : item récent en premier (bon classement)
        recent_first = [
            {"rel": 3.0, "ts": now - timedelta(days=1)},  # récent en 1er
            {"rel": 3.0, "ts": now - timedelta(days=30)},  # ancien en 2e
        ]

        # Cas 2 : item ancien en premier (mauvais classement)
        old_first = [
            {"rel": 3.0, "ts": now - timedelta(days=30)},  # ancien en 1er
            {"rel": 3.0, "ts": now - timedelta(days=1)},  # récent en 2e
        ]

        score_recent_first = ndcg_time_at_k(
            recent_first, k=2, now=now, T_days=7.0, lam=0.3
        )
        score_old_first = ndcg_time_at_k(old_first, k=2, now=now, T_days=7.0, lam=0.3)

        # Le bon classement (récent en premier) doit avoir un meilleur score
        assert score_recent_first > score_old_first
        assert 0.0 < score_old_first < 1.0
        assert 0.0 < score_recent_first <= 1.0

    def test_relevance_vs_freshness_tradeoff(self) -> None:
        """Vérifie le trade-off entre pertinence et fraîcheur."""
        now = datetime.now(timezone.utc)

        # Item 1: très pertinent mais ancien
        # Item 2: moins pertinent mais récent
        items_case_a = [
            {"rel": 5.0, "ts": now - timedelta(days=30)},  # 1er : très pertinent, vieux
            {"rel": 2.0, "ts": now - timedelta(days=1)},  # 2e : moins pertinent, récent
        ]

        # Même liste mais inversée
        items_case_b = [
            {
                "rel": 2.0,
                "ts": now - timedelta(days=1),
            },  # 1er : moins pertinent, récent
            {"rel": 5.0, "ts": now - timedelta(days=30)},  # 2e : très pertinent, vieux
        ]

        score_a = ndcg_time_at_k(items_case_a, k=2, now=now, T_days=7.0, lam=0.3)
        score_b = ndcg_time_at_k(items_case_b, k=2, now=now, T_days=7.0, lam=0.3)

        # Les deux scores doivent être différents (l'ordre compte)
        assert score_a != score_b
        # Les deux doivent être valides
        assert 0.0 <= score_a <= 1.0
        assert 0.0 <= score_b <= 1.0

    def test_perfect_ranking(self) -> None:
        """Classement idéal donne nDCG = 1.0."""
        now = datetime.now(timezone.utc)
        items = [
            {
                "rel": 5.0,
                "ts": now - timedelta(days=1),
            },  # Meilleur : très pertinent, récent
            {"rel": 3.0, "ts": now - timedelta(days=2)},  # Moyen
            {"rel": 1.0, "ts": now - timedelta(days=10)},  # Pire : peu pertinent, vieux
        ]
        score = ndcg_time_at_k(items, k=3, now=now)
        assert 0.99 <= score <= 1.0  # Très proche de 1.0

    def test_worst_ranking(self) -> None:
        """Classement inversé donne score < 1.0."""
        now = datetime.now(timezone.utc)
        items = [
            {"rel": 1.0, "ts": now - timedelta(days=30)},  # Pire en 1er
            {"rel": 3.0, "ts": now - timedelta(days=10)},  # Moyen en 2e
            {"rel": 5.0, "ts": now - timedelta(days=1)},  # Meilleur en dernier
        ]
        score = ndcg_time_at_k(items, k=3, now=now)
        assert 0.0 < score < 0.99  # Score dégradé

    def test_k_cutoff(self) -> None:
        """Seuls les k premiers items sont considérés."""
        now = datetime.now(timezone.utc)
        items = [
            {"rel": 3.0, "ts": now},
            {"rel": 2.0, "ts": now},
            {"rel": 5.0, "ts": now},  # Ce meilleur item est en 3e position
        ]
        score_k1 = ndcg_time_at_k(items, k=1, now=now)
        score_k3 = ndcg_time_at_k(items, k=3, now=now)

        # Avec k=1, on ne voit que le 1er item (rel=3.0)
        # Avec k=3, on voit le meilleur item (rel=5.0) en 3e position
        # Donc k=3 devrait avoir un meilleur score idéal
        assert score_k1 != score_k3

    def test_missing_timestamp_treated_as_old(self) -> None:
        """Items sans timestamp sont pénalisés comme très anciens."""
        now = datetime.now(timezone.utc)

        # Cas 1 : item avec TS en premier (bon)
        ts_first = [
            {"rel": 3.0, "ts": now},
            {"rel": 3.0, "ts": None},  # sans TS en 2e
        ]

        # Cas 2 : item sans TS en premier (mauvais)
        no_ts_first = [
            {"rel": 3.0, "ts": None},  # sans TS en 1er
            {"rel": 3.0, "ts": now},
        ]

        score_ts_first = ndcg_time_at_k(ts_first, k=2, now=now)
        score_no_ts_first = ndcg_time_at_k(no_ts_first, k=2, now=now)

        # Item avec TS en premier doit donner meilleur score
        assert score_ts_first > score_no_ts_first
        assert 0.0 < score_no_ts_first < 1.0
        assert 0.0 < score_ts_first <= 1.0

    def test_all_zero_relevance(self) -> None:
        """Tous items avec rel=0 donnent nDCG=1.0 (vide parfait)."""
        now = datetime.now(timezone.utc)
        items = [
            {"rel": 0.0, "ts": now},
            {"rel": 0.0, "ts": now},
        ]
        score = ndcg_time_at_k(items, k=2, now=now)
        assert score == 1.0  # DCG et IDCG tous deux nuls → 1.0

    def test_lambda_zero_no_decay(self) -> None:
        """Avec λ=0, pas de pénalisation temporelle (nDCG classique)."""
        now = datetime.now(timezone.utc)
        items = [
            {"rel": 3.0, "ts": now - timedelta(days=1)},
            {"rel": 3.0, "ts": now - timedelta(days=365)},  # Très ancien
        ]
        # Avec lam=0, exp(-0 * Δt) = 1 toujours → pas de décroissance
        score = ndcg_time_at_k(items, k=2, now=now, lam=0.0)
        # Les deux items ont même rel et même pénalité (1.0), donc classement parfait
        assert 0.99 <= score <= 1.0

    def test_lambda_high_strong_decay(self) -> None:
        """Avec λ élevé, l'ordre récent vs ancien a plus d'impact."""
        now = datetime.now(timezone.utc)

        # Classement suboptimal : ancien en premier
        items = [
            {"rel": 5.0, "ts": now - timedelta(days=30)},  # ancien
            {"rel": 5.0, "ts": now - timedelta(days=1)},  # récent
        ]

        score_low_lam = ndcg_time_at_k(items, k=2, now=now, lam=0.1)
        score_high_lam = ndcg_time_at_k(items, k=2, now=now, lam=1.0)

        # Avec λ plus élevé, la pénalité temporelle est plus forte
        # Donc un mauvais classement (ancien en 1er) est plus pénalisé
        assert score_high_lam < score_low_lam
        assert 0.0 < score_high_lam < 1.0
        assert 0.0 < score_low_lam < 1.0

    def test_invalid_k_raises(self) -> None:
        """k <= 0 lève une erreur."""
        now = datetime.now(timezone.utc)
        items = [{"rel": 1.0, "ts": now}]

        with pytest.raises(ValueError, match="k doit être > 0"):
            ndcg_time_at_k(items, k=0, now=now)

        with pytest.raises(ValueError, match="k doit être > 0"):
            ndcg_time_at_k(items, k=-5, now=now)

    def test_invalid_T_days_raises(self) -> None:
        """T_days <= 0 lève une erreur."""
        now = datetime.now(timezone.utc)
        items = [{"rel": 1.0, "ts": now}]

        with pytest.raises(ValueError, match="T_days doit être > 0"):
            ndcg_time_at_k(items, k=1, now=now, T_days=0)

        with pytest.raises(ValueError, match="T_days doit être > 0"):
            ndcg_time_at_k(items, k=1, now=now, T_days=-7)

    def test_invalid_lambda_raises(self) -> None:
        """λ < 0 lève une erreur."""
        now = datetime.now(timezone.utc)
        items = [{"rel": 1.0, "ts": now}]

        with pytest.raises(ValueError, match="lam doit être >= 0"):
            ndcg_time_at_k(items, k=1, now=now, lam=-0.5)

    def test_default_now_is_utc(self) -> None:
        """Si now=None, utilise datetime.now(utc) automatiquement."""
        items = [{"rel": 3.0, "ts": datetime.now(timezone.utc)}]
        score = ndcg_time_at_k(items, k=1)  # now=None par défaut
        assert 0.0 <= score <= 1.0  # Fonctionne sans erreur

    def test_real_world_scenario(self) -> None:
        """Test avec un scénario réaliste : recherche de documents."""
        now = datetime.now(timezone.utc)

        # Simule des résultats de recherche avec pertinence et timestamps variés
        # Bon classement : items récents ET pertinents en premier
        good_ranking = [
            {
                "rel": 4.0,
                "ts": now - timedelta(days=2),
            },  # Top 1 : très pertinent, récent
            {
                "rel": 3.0,
                "ts": now - timedelta(hours=6),
            },  # Top 2 : pertinent, très récent
            {
                "rel": 2.0,
                "ts": now - timedelta(days=5),
            },  # Top 3 : peu pertinent, récent
            {
                "rel": 5.0,
                "ts": now - timedelta(days=60),
            },  # Top 4 : le plus pertinent mais ancien
            {
                "rel": 1.0,
                "ts": now - timedelta(days=90),
            },  # Top 5 : peu pertinent, très ancien
        ]

        # Mauvais classement : items anciens en premier
        bad_ranking = [
            {"rel": 5.0, "ts": now - timedelta(days=60)},  # Top 1 : ancien (mauvais !)
            {
                "rel": 1.0,
                "ts": now - timedelta(days=90),
            },  # Top 2 : très ancien (pire !)
            {"rel": 4.0, "ts": now - timedelta(days=2)},  # Top 3 : bon item relégué
            {
                "rel": 3.0,
                "ts": now - timedelta(hours=6),
            },  # Top 4 : excellent item relégué
            {"rel": 2.0, "ts": now - timedelta(days=5)},  # Top 5
        ]

        score_good = ndcg_time_at_k(good_ranking, k=5, now=now, T_days=7.0, lam=0.3)
        score_bad = ndcg_time_at_k(bad_ranking, k=5, now=now, T_days=7.0, lam=0.3)

        # Le bon classement doit avoir un score nettement supérieur
        assert score_good > score_bad
        assert 0.9 < score_good <= 1.0  # Bon classement proche de parfait
        assert 0.3 < score_bad < 0.8  # Mauvais classement pénalisé

        # Vérifier que les scores sont dans [0, 1]
        assert 0.0 <= score_good <= 1.0
        assert 0.0 <= score_bad <= 1.0
