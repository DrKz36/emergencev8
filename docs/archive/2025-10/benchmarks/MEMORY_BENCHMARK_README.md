# 🧠 Benchmark de Rétention Mémoire - ÉMERGENCE

## 📋 Vue d'ensemble

Ce module permet de **mesurer la capacité de rétention de contexte** des trois agents d'ÉMERGENCE (Neo, Anima, Nexus) sur trois échéances temporelles :

- **T+1h** : Rétention à court terme
- **T+24h** : Rétention à moyen terme
- **T+7j** : Rétention à long terme

Le système injecte des **faits de référence** dans la mémoire de chaque agent, puis teste leur rappel à intervalles réguliers. Les résultats sont agrégés dans des graphiques comparatifs.

---

## 📁 Fichiers du module

```
emergenceV8/
├── prompts/
│   └── ground_truth.yml          # Faits de référence à mémoriser
├── scripts/
│   ├── memory_probe.py           # Script de test de rétention
│   └── plot_retention.py         # Génération des graphiques
├── requirements.txt              # Dépendances (PyYAML, matplotlib, pandas)
├── MEMORY_BENCHMARK_README.md    # Ce fichier
└── memory_results_*.csv          # Résultats (générés)
```

---

## 🚀 Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

Les dépendances spécifiques au benchmark :
- **PyYAML** : Lecture du fichier `ground_truth.yml`
- **matplotlib** : Génération des graphiques
- **pandas** : Agrégation des résultats CSV
- **httpx** : Appels HTTP au backend (déjà installé)

### 2. Configurer le backend

Le benchmark nécessite un backend ÉMERGENCE accessible (local ou Cloud Run).

**Backend local** :
```bash
pwsh -File scripts/run-backend.ps1
```

**Backend Cloud Run** :
```bash
export BACKEND_URL="https://emergence-app-486095406755.europe-west1.run.app"
export JWT_TOKEN="votre_token_jwt"
```

---

## 🧪 Utilisation

### Mode production (délais réels : 1h, 24h, 7j)

**Lancer le test pour un agent** :

```bash
# Neo
AGENT_NAME=Neo python scripts/memory_probe.py

# Anima
AGENT_NAME=Anima python scripts/memory_probe.py

# Nexus
AGENT_NAME=Nexus python scripts/memory_probe.py
```

**⚠️ Attention** : Le test complet dure **7 jours** ! Il est recommandé d'utiliser le mode debug pour des tests rapides.

### Mode debug (délais courts : 1min, 2min, 3min)

Pour valider rapidement que le système fonctionne :

```bash
DEBUG_MODE=true AGENT_NAME=Neo python scripts/memory_probe.py
```

Le test complet dure seulement **3 minutes** au lieu de 7 jours.

### Lancer les tests pour tous les agents en parallèle

**Windows PowerShell** :
```powershell
# Mode debug (3 min)
$env:DEBUG_MODE="true"

Start-Job -ScriptBlock { $env:AGENT_NAME="Neo"; python scripts/memory_probe.py }
Start-Job -ScriptBlock { $env:AGENT_NAME="Anima"; python scripts/memory_probe.py }
Start-Job -ScriptBlock { $env:AGENT_NAME="Nexus"; python scripts/memory_probe.py }

# Surveiller les jobs
Get-Job | Wait-Job
Get-Job | Receive-Job
```

**Linux/macOS** :
```bash
DEBUG_MODE=true AGENT_NAME=Neo python scripts/memory_probe.py &
DEBUG_MODE=true AGENT_NAME=Anima python scripts/memory_probe.py &
DEBUG_MODE=true AGENT_NAME=Nexus python scripts/memory_probe.py &
wait
```

### Générer le graphique comparatif

Une fois les tests terminés pour au moins un agent :

```bash
# Graphique simple (moyenne par agent)
python scripts/plot_retention.py

# Graphique détaillé (par fait F1/F2/F3)
DETAILED=true python scripts/plot_retention.py

# Mode debug (pour ticks courts)
DEBUG_MODE=true python scripts/plot_retention.py
```

**Sortie** :
- `retention_curve_all.png` : Graphique comparatif
- `retention_curve_detailed.png` : Graphique détaillé (si `DETAILED=true`)

---

## 📊 Format des résultats

### Fichiers CSV générés

Chaque exécution de `memory_probe.py` génère un fichier CSV :

```
memory_results_neo.csv
memory_results_anima.csv
memory_results_nexus.csv
```

**Format** :
```csv
timestamp_utc,agent,session,tick,fact_id,score,truth,prediction
2025-10-21T12:00:00.000000,Neo,session-neo-20251021120000,T+1h,F1,1.00,iris-47,iris-47
2025-10-21T12:00:01.000000,Neo,session-neo-20251021120000,T+1h,F2,0.50,Orphée SA,Le client est Orphée SA
2025-10-21T12:00:02.000000,Neo,session-neo-20251021120000,T+1h,F3,0.00,7788,Je ne me souviens pas
```

**Calcul du score** :
- `1.0` : Correspondance exacte (après normalisation)
- `0.5` : Vérité contenue dans la prédiction
- `0.0` : Aucune correspondance

### Graphique de rétention

**Exemple** :

```
Score (0-1)
    ^
1.0 |     ●━━━━●━━━━●    Neo
    |    /         \
0.5 |   ●━━━━●━━━━━●    Anima
    |  /           \
0.0 | ●━━━━━●━━━━━●━━━  Nexus
    |________________________> Temps
      T+1h   T+24h   T+7j
```

---

## 🎯 Personnalisation

### Ajouter des faits de référence

Éditer [`prompts/ground_truth.yml`](prompts/ground_truth.yml) :

```yaml
facts:
  - id: F4
    prompt: "La version actuelle du système est V8.2.1"
    answer: "V8.2.1"

  - id: F5
    prompt: "Le nom du projet est ÉMERGENCE"
    answer: "ÉMERGENCE"
```

### Modifier les échéances

Éditer [`scripts/memory_probe.py`](scripts/memory_probe.py) :

```python
# Ligne 37-41
DELTAS = [
    ("T+15min", 900),      # 15 minutes
    ("T+2h", 7200),        # 2 heures
    ("T+12h", 43200)       # 12 heures
]
```

### Adapter le scoring

Modifier la fonction `score()` dans [`scripts/memory_probe.py`](scripts/memory_probe.py:67) pour implémenter un scoring personnalisé (ex: Levenshtein, embedding similarity, etc.)

---

## 🔗 Intégration future (Phase P3)

### Stockage automatique dans ChromaDB

```python
# Dans memory_probe.py
from chromadb import Client

chroma_client = Client()
collection = chroma_client.get_or_create_collection("emergence_benchmarks")

# Après chaque test
collection.add(
    documents=[f"{fact_id}:{prediction}"],
    metadatas=[{
        "agent": AGENT_NAME,
        "tick": tick,
        "score": score_val,
        "session_id": SESSION_ID
    }],
    ids=[f"{SESSION_ID}_{tick}_{fact_id}"]
)
```

### Corrélation avec métriques Prometheus

Croiser les résultats du benchmark avec les métriques de production :

- `memory_analysis_duration_seconds` : Temps d'analyse mémoire
- `memory_cache_operations_total` : Opérations de cache
- `memory_proactive_hints_generated_total` : Hints générés

```python
import requests

# Récupérer métriques Prometheus
metrics_url = f"{BACKEND_URL}/metrics"
response = requests.get(metrics_url)

# Analyser corrélations
# Ex: Score de rétention VS latence d'analyse mémoire
```

### Automatisation via API `/api/benchmarks/runs`

Créer un endpoint dédié pour lancer les benchmarks :

```python
# src/backend/features/benchmarks/router.py
@router.post("/runs")
async def create_benchmark_run(
    agent: str,
    mode: str = "debug"  # debug | production
):
    # Lance memory_probe.py en arrière-plan
    # Enregistre run_id dans BDD
    # Retourne status + ETA
    pass
```

---

## 📚 Références

**Architecture ÉMERGENCE** :
- [`docs/architecture/00-Overview.md`](docs/architecture/00-Overview.md)
- [`docs/architecture/10-Components.md`](docs/architecture/10-Components.md)

**Système mémoire** :
- [`src/backend/features/memory/`](src/backend/features/memory/)
- Prompts agents : [`prompts/neo_system_v3.md`](prompts/neo_system_v3.md), [`prompts/anima_system_v2.md`](prompts/anima_system_v2.md), [`prompts/nexus_system_v2.md`](prompts/nexus_system_v2.md)

**Métriques Prometheus** :
- Endpoint : `/metrics`
- Dashboard Grafana (si configuré) : voir `scripts/setup_gcp_memory_alerts.py`

---

## ✅ Validation du module

Pour vérifier que tout est correctement configuré :

```bash
# 1. Vérifier la syntaxe des scripts
python -m py_compile scripts/memory_probe.py
python -m py_compile scripts/plot_retention.py

# 2. Vérifier les dépendances
python -c "import yaml, matplotlib, pandas, httpx; print('Toutes les dépendances sont installées ✅')"

# 3. Lancer un test rapide (3 min)
DEBUG_MODE=true AGENT_NAME=Neo python scripts/memory_probe.py

# 4. Générer le graphique
DEBUG_MODE=true python scripts/plot_retention.py

# 5. Vérifier les fichiers générés
ls -lh memory_results_*.csv retention_curve_*.png
```

---

## 🐛 Troubleshooting

### Erreur "Backend not reachable"

**Symptôme** :
```
❌ Erreur de connexion: All connection attempts failed
```

**Solution** :
1. Vérifier que le backend est bien démarré :
   ```bash
   pwsh -File scripts/run-backend.ps1
   ```

2. Tester manuellement l'endpoint :
   ```bash
   curl http://localhost:8000/api/health
   ```

3. Vérifier les variables d'environnement :
   ```bash
   echo $BACKEND_URL
   echo $JWT_TOKEN
   ```

### Erreur "ground_truth.yml not found"

**Symptôme** :
```
❌ Fichier ground truth introuvable: prompts/ground_truth.yml
```

**Solution** :
Le script doit être exécuté depuis la **racine du projet** :
```bash
cd c:\dev\emergenceV8
python scripts/memory_probe.py
```

### Score toujours à 0.0

**Symptôme** :
```
❌ F1: score=0.00 | attendu='iris-47' | obtenu='Je ne sais pas'
```

**Causes possibles** :
1. **Agent ne mémorise pas** : Vérifier que le système mémoire est activé dans le backend
2. **Session différente** : Le `SESSION_ID` change entre injection et rappel
3. **Prompt incomplet** : L'agent ne reçoit pas le contexte mémoire

**Debug** :
1. Activer les logs backend :
   ```bash
   LOG_LEVEL=DEBUG pwsh -File scripts/run-backend.ps1
   ```

2. Vérifier dans les logs :
   - Injection du contexte : `POST /api/chat` avec le message d'injection
   - Requêtes de rappel : `POST /api/chat` avec les questions
   - Analyse mémoire : `MemoryService.analyze_and_retrieve()`

---

## 🤝 Contribution

Pour améliorer le benchmark :

1. **Ajouter de nouveaux faits** dans `prompts/ground_truth.yml`
2. **Améliorer le scoring** dans `memory_probe.py:score()`
3. **Créer de nouveaux graphiques** dans `plot_retention.py`
4. **Documenter les résultats** dans `docs/passation.md`

**Consignes** :
- Suivre les conventions de [`CLAUDE.md`](CLAUDE.md)
- Tester en mode debug avant production
- Mettre à jour [`AGENT_SYNC.md`](AGENT_SYNC.md) après modifications

---

## 📝 Changelog

**v1.0.0 (2025-10-21)** :
- ✅ Création du module de benchmark
- ✅ Scripts `memory_probe.py` et `plot_retention.py`
- ✅ Mode debug avec délais raccourcis
- ✅ Graphiques comparatifs multi-agents
- ✅ Documentation complète

---

**Auteur** : Claude Code
**Dernière mise à jour** : 2025-10-21
**Licence** : Voir LICENSE du projet ÉMERGENCE
