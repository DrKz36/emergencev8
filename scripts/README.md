# Scripts de Migration FastAPI 0.119 & Chroma 0.5

Ce dossier contient les outils pour évaluer et migrer vers FastAPI 0.119 et ChromaDB 0.5.x.

## 📁 Fichiers Disponibles

### 1. `test_fastapi_upgrade.py`
**Objectif** : Valider la compatibilité FastAPI 0.119

**Tests inclus** :
- ✅ Dependency yield cleanup timing
- ✅ StreamingResponse stabilité
- ✅ WebSocket + Depends
- ✅ Pydantic v2 models
- ✅ BackgroundTasks
- ✅ Lifespan context manager

**Usage** :
```bash
# Test avec version actuelle (0.109.2)
python scripts/test_fastapi_upgrade.py

# Test après upgrade (0.119.0)
pip install fastapi==0.119.0
python scripts/test_fastapi_upgrade.py
```

**Output attendu** :
```
✓ Dependency yield cleanup timing: Cleanup order correct: [...]
✓ StreamingResponse not interrupted by cleanup: All 10 chunks sent successfully
✓ Pydantic v2 model compatibility: Pydantic v2 models work correctly
✓ WebSocket with Depends compatibility: WebSocket with Depends works correctly
✓ BackgroundTasks execution: BackgroundTasks executed successfully
✓ Lifespan context manager: Lifespan events: ['startup', 'shutdown']

TOTAL: 6/6 tests passed
```

---

### 2. `benchmark_chroma_upgrade.py`
**Objectif** : Évaluer performance ChromaDB 0.4.22 vs 0.5.x

**Benchmarks inclus** :
- 📊 Upsert performance (100, 1k, 10k items)
- 🔍 Query avec métadata filters
- 🔎 Regex search capability
- ⚙️ HNSW parameter optimization (M=8, 16, 32)

**Usage** :
```bash
# Baseline avec version actuelle (0.4.22)
python scripts/benchmark_chroma_upgrade.py > baseline_0422.txt

# Après upgrade (0.5.x)
pip install chromadb==0.5.3
python scripts/benchmark_chroma_upgrade.py > results_05x.txt

# Comparer
diff baseline_0422.txt results_05x.txt
```

**Output attendu** :
```
BENCHMARK RESULTS SUMMARY
================================================
📊 UPSERT PERFORMANCE:
  • 100 items: 0.421s (237 items/sec)
  • 1000 items: 4.105s (244 items/sec)

🔍 QUERY PERFORMANCE:
  • 100 queries: 0.543s (184 queries/sec)
  • Speed: 184 queries/sec
  • Avg latency: 5.43ms

🔎 REGEX SEARCH:
  • Support: partial
  • Note: Chroma supports $contains, $in but not full regex (as of 0.4.x-0.5.x)

⚙️  HNSW OPTIMIZATION:
  • M=8: 165 queries/sec
  • M=16: 184 queries/sec  ← Optimal
  • M=32: 178 queries/sec
```

---

### 3. `example_regex_filter_patch.py`
**Objectif** : Démonstration implémentation regex filtering

**Contenu** :
- ✅ Fonction `regex_filter_results()` complète
- 📝 3 exemples d'usage (email, phone, user_id)
- 🔧 Patch pour `MemoryAnalyzer`
- 📊 Benchmark de performance

**Usage** :
```bash
# Examiner les exemples
python scripts/example_regex_filter_patch.py

# Appliquer le patch manuellement
# 1. Copier regex_filter_results() dans hybrid_retriever.py
# 2. Importer dans analyzer.py
# 3. Utiliser comme montré dans les exemples
```

**Exemple d'intégration** :
```python
# Dans hybrid_retriever.py
def regex_filter_results(results, field_path, pattern):
    # ... (copier depuis example_regex_filter_patch.py)

# Dans analyzer.py
from .hybrid_retriever import regex_filter_results

class MemoryAnalyzer:
    async def search_by_email_domain(self, domain_pattern: str):
        results = self.vector_service.query(
            self.ltm_collection,
            query_text="user preferences",
            n_results=100,
        )
        return regex_filter_results(results, "metadata.email", domain_pattern)
```

---

## 🚀 Workflow Recommandé

### Étape 1 : Baseline (Avant Upgrade)
```bash
# 1. Tests FastAPI actuels
python scripts/test_fastapi_upgrade.py

# 2. Benchmark Chroma actuel
python scripts/benchmark_chroma_upgrade.py > results/baseline_chroma_0422.txt
```

### Étape 2 : Environnement de Test
```bash
# Créer environnement isolé
python -m venv venv_upgrade_test
source venv_upgrade_test/bin/activate  # Windows: venv_upgrade_test\Scripts\activate

# Installer nouvelles versions
pip install fastapi==0.119.0 chromadb==0.5.3

# Installer autres dépendances
pip install -r requirements.txt
```

### Étape 3 : Validation
```bash
# 1. Tests FastAPI 0.119
python scripts/test_fastapi_upgrade.py

# 2. Benchmark Chroma 0.5.x
python scripts/benchmark_chroma_upgrade.py > results/upgrade_chroma_05x.txt

# 3. Comparer
diff results/baseline_chroma_0422.txt results/upgrade_chroma_05x.txt
```

### Étape 4 : Tests Application Complète
```bash
# Tests unitaires
pytest src/backend/tests/ -v

# Tests critiques manuels
# - WebSocket chat (/ws/{session_id})
# - Debate multi-agents
# - RAG/DocumentService
# - MemoryAnalyzer consolidation
```

---

## 📊 Métriques de Réussite

### FastAPI Tests
- ✅ **6/6 tests passent** (100%)
- ⚠️ Si échec : Vérifier cleanup timing et streaming

### Chroma Benchmarks
**Gains attendus (0.4.22 → 0.5.x)** :
- Upsert 1k items : **+20% à +30%**
- Query avec filters : **+15% à +25%**
- Init collection : **-30% à -50%**

**Exemple baseline vs upgrade** :
```
# Baseline (0.4.22)
Upsert 1000: 4.2s (238 items/sec)
Query 100: 0.55s (182 queries/sec)

# Upgrade (0.5.3) - Expected
Upsert 1000: 3.2s (312 items/sec)  ← +31% ✓
Query 100: 0.45s (222 queries/sec)  ← +22% ✓
```

---

## ⚠️ Troubleshooting

### Erreur : "Module not found"
```bash
# Vérifier PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"  # Linux/Mac
set PYTHONPATH=%PYTHONPATH%;%CD%\src          # Windows
```

### Erreur : "Collection not found"
```bash
# Normal pour benchmark (créé à la volée)
# Vérifier que data/vector_store est accessible
ls -la data/vector_store/
```

### Performance dégradée après upgrade
```bash
# 1. Vérifier version Chroma
pip show chromadb

# 2. Benchmark avec données réelles
python scripts/benchmark_chroma_upgrade.py

# 3. Si problème persistant → rollback
pip install chromadb==0.4.22
```

---

## 📚 Références

- [Rapport complet](../reports/fastapi_chroma_upgrade_report.md)
- [Notes de mise à jour](../UPGRADE_NOTES.md)
- [FastAPI 0.119 Release](https://github.com/tiangolo/fastapi/releases/tag/0.119.0)
- [ChromaDB Changelog](https://github.com/chroma-core/chroma/releases)

---

## 🆘 Support

**En cas de problème** :
1. Consulter [reports/fastapi_chroma_upgrade_report.md](../reports/fastapi_chroma_upgrade_report.md) section "Risques & Mitigation"
2. Vérifier logs : `tail -f logs/emergence.log`
3. Rollback rapide : `git checkout main -- requirements.txt && pip install -r requirements.txt`

**Contacts** :
- Tech Lead : [Votre équipe]
- DevOps : [Cloud Run support]

---

**Dernière mise à jour** : 2025-10-14
