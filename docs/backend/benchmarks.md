# Benchmarks Module

**Module** : `src/backend/features/benchmarks/`
**Version** : beta-3.1.3
**Responsabilité** : Orchestration des benchmarks agentiques et métriques d'évaluation

---

## Vue d'ensemble

Le module **Benchmarks** fournit une infrastructure pour évaluer les performances des agents dans différents scénarios (ARE, Gaia2) et mesurer la qualité des résultats de ranking avec des métriques avancées.

### Composants principaux

1. **BenchmarksService** (`service.py`)
   - Orchestration du `BenchmarksRunner`
   - Chargement du catalogue de scénarios (ARE/Gaia2)
   - Persistance des résultats en SQLite (+ Firestore optionnel)
   - Exposition des endpoints REST `/api/benchmarks/*`
   - **Nouveau (v3.1.3)** : Méthode `calculate_temporal_ndcg()` pour évaluer la qualité d'un classement avec pénalisation temporelle

2. **BenchmarksRouter** (`router.py`)
   - Endpoints REST pour les benchmarks
   - **Nouveau (v3.1.3)** : Endpoint `/api/benchmarks/metrics/ndcg-temporal` pour calcul métrique nDCG@k temporelle

3. **Métriques d'évaluation** (`metrics/`)
   - **nDCG@k temporelle** (`temporal_ndcg.py`) : Métrique combinant pertinence et fraîcheur temporelle

---

## Endpoints API

### GET /api/benchmarks/results

Récupère les résultats de benchmarks récents.

**Paramètres** :
- `scenario_id` (optionnel) : Filtrer par scénario
- `limit` (optionnel, défaut 5) : Nombre de résultats

**Réponse** :
```json
{
  "results": [
    {
      "matrix_id": "...",
      "scenario_id": "are_v1",
      "created_at": "2025-10-26T...",
      "summary": {
        "success_rate": 0.85,
        "avg_cost": 0.0123,
        "avg_latency_ms": 1200
      }
    }
  ]
}
```

---

### GET /api/benchmarks/scenarios

Liste les scénarios de benchmarks disponibles.

**Réponse** :
```json
{
  "scenarios": [
    {
      "id": "are_v1",
      "name": "AgentArch Reasoning Evaluation",
      "description": "...",
      "success_threshold": 0.75,
      "tasks_total": 10
    }
  ]
}
```

---

### POST /api/benchmarks/run

Déclenche l'exécution d'un benchmark.

**Auth** : Requiert rôle admin

**Payload** :
```json
{
  "scenario_id": "are_v1",
  "context": {},
  "metadata": {}
}
```

**Réponse** : 202 Accepted + résultats de la matrice

---

### POST /api/benchmarks/metrics/ndcg-temporal

**Nouveau (v3.1.3)** : Calcule la métrique nDCG@k temporelle pour évaluer un classement avec pénalisation temporelle.

**Payload** :
```json
{
  "ranked_items": [
    { "rel": 3.0, "ts": "2025-10-26T12:00:00Z" },
    { "rel": 2.0, "ts": "2025-09-26T12:00:00Z" }
  ],
  "k": 10,
  "now": "2025-10-26T14:00:00Z",
  "T_days": 7.0,
  "lam": 0.3
}
```

**Réponse** :
```json
{
  "ndcg_time@k": 0.95,
  "k": 10,
  "num_items": 2,
  "parameters": {
    "T_days": 7.0,
    "lambda": 0.3
  }
}
```

**Usage** : Mesure l'impact des boosts de fraîcheur/entropie dans le moteur de ranking.

---

## Métriques d'évaluation

### nDCG@k temporelle

**Fichier** : `src/backend/features/benchmarks/metrics/temporal_ndcg.py`

**Formule** :
```
DCG^time@k = Σ (2^rel_i - 1) * exp(-λ * Δt_i) / log2(i+1)
nDCG^time@k = DCG^time@k / IDCG^time@k
```

Où :
- `Δt_i = (now - timestamp_i) / T_days` : Âge normalisé du document i
- `λ` : Taux de décroissance exponentielle (défaut 0.3, demi-vie ≈ 8 jours)
- `T_days` : Période de normalisation (défaut 7 jours)

**Paramètres** :
- `k` : Nombre d'items considérés (défaut 10)
- `T_days` : Période de normalisation en jours (défaut 7.0)
- `lam` (λ) : Taux de décroissance exponentielle (défaut 0.3)

**Tests** : 18 tests unitaires dans `tests/backend/features/test_benchmarks_metrics.py`

---

## Configuration

### Variables d'environnement

- `BENCHMARKS_SCENARIO_INDEX` : Chemin vers un fichier JSON custom de scénarios
- `EMERGENCE_FIRESTORE_PROJECT` : Projet Firestore pour persistance cloud (optionnel)
- `GOOGLE_APPLICATION_CREDENTIALS` : Credentials GCP pour Firestore
- `EDGE_MODE=1` : Force fallback SQLite uniquement

### Persistance

- **SQLite** (toujours activé) : Table `benchmark_runs`
- **Firestore** (optionnel) : Collection `benchmark_results`

---

## Architecture

### BenchmarksService

**Responsabilités** :
- Chargement du catalogue de scénarios
- Orchestration du `BenchmarksRunner`
- Persistance des résultats (SQLite + Firestore)
- Exposition de la métrique nDCG@k temporelle

**Méthodes publiques** :
- `run_matrix(scenario_id, context?, metadata?)` : Exécute un benchmark
- `list_results(scenario_id?, limit?)` : Liste les résultats récents
- `get_supported_scenarios()` : Catalogue des scénarios
- **Nouveau (v3.1.3)** : `calculate_temporal_ndcg(ranked_items, k?, **kwargs)` : Calcule nDCG@k temporel

---

## Tests

**Fichiers** :
- `tests/backend/features/test_benchmarks_metrics.py` : Tests métriques (18 tests)
  - Cas edge (liste vide, item unique)
  - Décroissance temporelle
  - Trade-offs pertinence/fraîcheur
  - Validation paramètres (k, T_days, lambda)
  - Scénarios réalistes (recherche documents)

**Commandes** :
```bash
# Tests métriques
pytest tests/backend/features/test_benchmarks_metrics.py -v

# Tests complets module benchmarks
pytest tests/backend/features/ -k benchmark -v
```

---

## Roadmap

- [ ] Nouveaux scénarios de benchmarks (MMLU, HumanEval)
- [ ] Métriques additionnelles (ROUGE, BLEU, BERTScore)
- [ ] Dashboard visualisation résultats benchmarks
- [ ] Intégration CI/CD pour benchmarks automatiques

---

## Références

- Architecture : `docs/architecture/10-Components.md`
- Contrats API : `docs/architecture/30-Contracts.md`
- Code source : `src/backend/features/benchmarks/`
- Tests : `tests/backend/features/test_benchmarks_metrics.py`
