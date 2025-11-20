"""
Métrique nDCG@k temporelle avec pénalisation exponentielle.

Évalue la qualité du classement en intégrant la fraîcheur des documents.
Utilisé pour mesurer l'impact des boosts de fraîcheur et entropie dans ÉMERGENCE V8.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def ndcg_time_at_k(
    ranked: List[Dict[str, Any]],
    k: int = 10,
    now: Optional[datetime] = None,
    T_days: float = 7.0,
    lam: float = 0.3,
) -> float:
    """
    Calcule le nDCG@k avec pénalisation temporelle exponentielle.

    Cette métrique mesure la qualité d'un classement en combinant :
    - La pertinence (relevance) des items
    - La fraîcheur temporelle (timestamp)

    Formule DCG temporelle :
        DCG^time@k = Σ (2^rel_i - 1) * exp(-λ * Δt_i) / log2(i+1)

    où Δt_i = (now - timestamp_i) / T_days (âge normalisé)

    Args:
        ranked: Liste ordonnée d'items avec clés 'rel' (float) et 'ts' (datetime)
                Exemple : [{'rel': 3.0, 'ts': datetime(...)}, ...]
        k: Nombre d'items considérés dans le top-k (défaut: 10)
        now: Timestamp de référence (défaut: UTC now)
        T_days: Période de normalisation temporelle en jours (défaut: 7)
        lam: Taux de décroissance exponentielle (défaut: 0.3, demi-vie ≈ 8 jours)

    Returns:
        float: Score nDCG@k temporel entre 0 (pire) et 1 (parfait)

    Example:
        >>> from datetime import datetime, timedelta
        >>> now = datetime.now(timezone.utc)
        >>> items = [
        ...     {'rel': 3.0, 'ts': now - timedelta(days=1)},  # récent, pertinent
        ...     {'rel': 2.0, 'ts': now - timedelta(days=30)}, # vieux, moins pertinent
        ... ]
        >>> score = ndcg_time_at_k(items, k=2, now=now)
        >>> 0.0 <= score <= 1.0
        True
    """
    if not ranked:
        return 0.0

    if k <= 0:
        raise ValueError(f"k doit être > 0, reçu: {k}")

    if T_days <= 0:
        raise ValueError(f"T_days doit être > 0, reçu: {T_days}")

    if lam < 0:
        raise ValueError(f"lam doit être >= 0, reçu: {lam}")

    # Timestamp de référence (défaut: maintenant UTC)
    reference_time = now or datetime.now(timezone.utc)

    def tau(ts: datetime) -> float:
        """Facteur de pénalisation temporelle : exp(-λ * Δt)"""
        # Calcul de l'âge en secondes, puis normalisation en jours
        age_seconds = max((reference_time - ts).total_seconds(), 0)
        dt_normalized = age_seconds / (T_days * 86400)  # 86400 sec/jour
        return math.exp(-lam * dt_normalized)

    def dcg(items: List[Dict[str, Any]]) -> float:
        """Calcule DCG temporel sur les items donnés."""
        score = 0.0
        for i, item in enumerate(items[:k], start=1):
            rel = item.get("rel", 0.0)
            ts = item.get("ts")
            if ts is None:
                # Si pas de timestamp, on considère l'item comme très ancien
                temporal_factor = 0.0
            else:
                temporal_factor = tau(ts)

            gain = (2**rel - 1) * temporal_factor
            discount = math.log2(i + 1)
            score += gain / discount

        return score

    # DCG observé sur le classement actuel
    dcg_observed = dcg(ranked)

    # IDCG : classement idéal (tri par GAIN temporel réel DESC)
    # Le gain réel = (2^rel - 1) * tau(ts), pas juste rel ou ts séparément
    def compute_temporal_gain(item: Dict[str, Any]) -> float:
        """Calcule le gain temporel réel d'un item."""
        rel = float(item.get("rel", 0.0))
        ts = item.get("ts")
        if ts is None:
            temporal_factor = 0.0
        else:
            temporal_factor = tau(ts)
        gain = (2**rel - 1) * temporal_factor
        return gain

    ideal_ranking = sorted(ranked, key=compute_temporal_gain, reverse=True)
    idcg = dcg(ideal_ranking)

    # Éviter division par zéro
    if idcg < 1e-9:
        # Si IDCG est nul, tous les items ont rel=0 ou sont très vieux
        # Le nDCG est 1.0 si DCG=0 aussi (classement parfait du vide), 0.0 sinon
        return 1.0 if dcg_observed < 1e-9 else 0.0

    return dcg_observed / idcg
