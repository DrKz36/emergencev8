# 💰 Theia (CostWatcher) - AI Model Cost Optimizer

**Rôle** : Gardienne des coûts et optimisatrice des modèles IA
**Type** : Agent de surveillance et d'analyse
**Fréquence** : Hebdomadaire (ou à la demande)
**Priority** : MEDIUM (stratégique mais non critique)

---

## 📋 Mission

Theia analyse automatiquement les modèles d'IA utilisés dans l'environnement ÉMERGENCE pour :

1. **Identifier** les modèles réellement utilisés dans les flux de production
2. **Évaluer** leur coût par token (entrée/sortie)
3. **Repérer** les versions plus récentes et performantes disponibles
4. **Simuler** le surcoût ou l'économie d'un basculement
5. **Générer** un rapport synthétique avec recommandations

---

## 🎯 Objectifs

### Objectif Principal
Optimiser les coûts d'utilisation des modèles IA tout en maximisant les performances.

### Objectifs Secondaires
- Éviter de payer pour des modèles obsolètes
- Détecter les opportunités d'upgrade cost-effective
- Identifier les sous-utilisations de modèles coûteux
- Anticiper les changements de pricing des fournisseurs

---

## 🔍 Méthodologie

### Étape 1 : Scan de l'environnement

**Cibles de scan** :
```
src/backend/**/*.py          # Backend Python
src/frontend/**/*.js         # Frontend JavaScript
.env, .env.local             # Variables d'environnement
config/**/*.{json,yaml}      # Fichiers de configuration
scripts/**/*.{py,ps1}        # Scripts d'automatisation
```

**Patterns recherchés** :
- `model=["']([^"']+)["']`
- `engine=["']([^"']+)["']`
- `provider=["']([^"']+)["']`
- `OPENAI_MODEL`, `GEMINI_MODEL`, `ANTHROPIC_MODEL`
- `gpt-`, `gemini-`, `claude-`, `llama-`

**Output** : Liste des modèles utilisés avec contexte (fichier, ligne, usage)

### Étape 2 : Base de données des prix

**Structure** :
```json
{
  "openai": {
    "gpt-4o": {
      "input_cost_per_1k": 2.50,
      "output_cost_per_1k": 10.00,
      "context_window": 128000,
      "released": "2024-05-13",
      "status": "current"
    },
    "gpt-4o-mini": {
      "input_cost_per_1k": 0.15,
      "output_cost_per_1k": 0.60,
      "context_window": 128000,
      "released": "2024-07-18",
      "status": "current"
    }
  },
  "google": {
    "gemini-1.5-pro": {
      "input_cost_per_1k": 1.25,
      "output_cost_per_1k": 5.00,
      "context_window": 2000000,
      "released": "2024-05-14",
      "status": "current"
    },
    "gemini-1.5-flash": {
      "input_cost_per_1k": 0.075,
      "output_cost_per_1k": 0.30,
      "context_window": 1000000,
      "released": "2024-05-14",
      "status": "current"
    }
  },
  "anthropic": {
    "claude-3-5-sonnet-20241022": {
      "input_cost_per_1k": 3.00,
      "output_cost_per_1k": 15.00,
      "context_window": 200000,
      "released": "2024-10-22",
      "status": "current"
    },
    "claude-3-5-haiku-20241022": {
      "input_cost_per_1k": 0.80,
      "output_cost_per_1k": 4.00,
      "context_window": 200000,
      "released": "2024-11-04",
      "status": "current"
    }
  }
}
```

**Sources de pricing** :
- OpenAI : https://platform.openai.com/docs/pricing
- Google : https://ai.google.dev/gemini-api/docs/pricing
- Anthropic : https://www.anthropic.com/api#pricing

**Mise à jour** : Automatique via scraping ou API (si disponible)

### Étape 3 : Analyse comparative

Pour chaque modèle trouvé, calculer :

**Métriques de base** :
- Coût actuel par 1k tokens (input/output)
- Coût moyen par requête (basé sur usage réel ou estimé)
- Coût mensuel estimé (si logs disponibles)

**Comparaisons** :
- Modèles équivalents moins chers du même fournisseur
- Modèles équivalents d'autres fournisseurs
- Versions plus récentes avec meilleur rapport qualité/prix

**Simulations** :
- Impact financier d'un changement pour 10k, 100k, 1M requêtes
- Break-even point (à partir de combien de requêtes le changement est rentable)

### Étape 4 : Scoring et recommandations

**Score d'optimisation** (0-100) :
```
Score = (0.4 × Δ_cost) + (0.3 × Δ_performance) + (0.2 × Δ_context) + (0.1 × recency)

Où :
- Δ_cost : Économie potentielle (%)
- Δ_performance : Amélioration benchmarks (%)
- Δ_context : Amélioration context window (%)
- recency : Âge du modèle actuel vs nouveau (mois)
```

**Recommandations** :
- **UPGRADE IMMÉDIAT** : Score > 75 + économie > 20%
- **À ENVISAGER** : Score > 50
- **SURVEILLER** : Score 30-50
- **GARDER** : Score < 30

---

## 📊 Format de Rapport

### Rapport Markdown

**Fichier** : `reports/ai_model_cost_audit_YYYYMMDD.md`

**Sections** :

1. **Executive Summary**
   - Nombre de modèles analysés
   - Économie totale potentielle ($/mois)
   - Top 3 recommandations

2. **Modèles Actuels**
   - Tableau détaillé par modèle
   - Coût actuel et volume d'usage

3. **Opportunités d'Optimisation**
   - Tableau comparatif avec alternatives
   - Calcul économies/surcoûts

4. **Recommandations Prioritaires**
   - Actions à court terme (< 1 mois)
   - Actions à moyen terme (1-3 mois)
   - Actions à surveiller (> 3 mois)

5. **Historique des Prix**
   - Évolution des coûts détectée
   - Tendances par fournisseur

### Rapport JSON

**Fichier** : `reports/ai_model_cost_audit_YYYYMMDD.json`

**Structure** :
```json
{
  "timestamp": "2025-01-17T12:00:00Z",
  "summary": {
    "models_analyzed": 8,
    "total_monthly_cost": 1250.50,
    "potential_savings": 187.25,
    "optimization_score": 68
  },
  "current_models": [
    {
      "model": "gpt-4o-mini",
      "provider": "openai",
      "usage_locations": ["src/backend/features/chat/service.py:42"],
      "current_cost": {
        "input_per_1k": 0.15,
        "output_per_1k": 0.60
      },
      "estimated_monthly_volume": {
        "requests": 50000,
        "input_tokens": 2500000,
        "output_tokens": 1250000
      },
      "monthly_cost": 1125.00
    }
  ],
  "recommendations": [
    {
      "current_model": "gpt-4o-mini",
      "suggested_model": "gemini-1.5-flash",
      "reason": "40% cost reduction with similar performance",
      "impact": {
        "cost_change_percent": -40,
        "monthly_savings": 450.00,
        "performance_delta": -5
      },
      "priority": "HIGH",
      "action": "UPGRADE"
    }
  ]
}
```

---

## 🔄 Intégration Guardian

### Déclenchement

**Automatique** :
- Hebdomadaire (dimanche 23h00)
- Lors de mise à jour pricing détectée

**Manuel** :
```bash
python claude-plugins/integrity-docs-guardian/scripts/analyze_ai_costs.py
```

**Via API** :
```bash
curl -X POST http://localhost:8000/api/guardian/theia/analyze
```

### Workflow

```
1. Theia scanne le codebase
2. Récupère pricing à jour
3. Analyse et génère rapport
4. Poste notification si économies > 15%
5. Sauvegarde rapport dans reports/
6. Met à jour Nexus (rapport unifié)
```

### Notifications

**Seuils d'alerte** :
- 🔴 **CRITICAL** : Économie potentielle > 30% (>$500/mois)
- 🟡 **WARNING** : Nouveau modèle disponible avec upgrade recommandé
- 🟢 **INFO** : Rapport hebdomadaire standard

---

## 🛠️ Configuration

**Fichier** : `claude-plugins/integrity-docs-guardian/config/theia_config.json`

```json
{
  "scan_paths": [
    "src/backend/**/*.py",
    "src/frontend/**/*.js",
    ".env*",
    "config/**/*.{json,yaml}"
  ],
  "providers": ["openai", "google", "anthropic"],
  "update_pricing_automatically": true,
  "alert_thresholds": {
    "critical_savings_percent": 30,
    "critical_savings_amount": 500,
    "warning_upgrade_available": true
  },
  "estimation_baseline": {
    "avg_input_tokens": 500,
    "avg_output_tokens": 250,
    "monthly_requests": 10000
  },
  "exclude_patterns": [
    "**/test_*.py",
    "**/node_modules/**",
    "**/.venv/**"
  ]
}
```

---

## 📈 Métriques Collectées

### Usage Patterns
- Modèles par fonctionnalité (chat, embeddings, analysis, etc.)
- Volume par modèle (requêtes/jour)
- Tokens moyens par requête

### Cost Tracking
- Coût total par modèle
- Coût total par fournisseur
- Tendance mensuelle

### Performance Indicators
- Latence moyenne par modèle
- Taux d'erreur par modèle
- Taux de retry

---

## 🔗 Intégration avec Autres Agents

### Anima (DocKeeper)
- Vérifie que changements de modèle sont documentés
- Suggère mise à jour docs si nouveau modèle recommandé

### Neo (IntegrityWatcher)
- Vérifie compatibilité API lors de changement de modèle
- Détecte breaking changes dans signatures

### ProdGuardian
- Corrèle coûts avec erreurs en production
- Identifie modèles causant des problèmes (timeout, rate limit)

### Nexus (Coordinator)
- Intègre rapport Theia dans rapport unifié
- Priorise recommandations avec autres agents

---

## 📚 Exemples de Détections

### Exemple 1 : Modèle Obsolète Détecté

**Détection** :
```
FOUND: gpt-3.5-turbo in src/backend/features/chat/service.py:42
CURRENT COST: $0.50 / $1.50 per 1M tokens
RECOMMENDED: gpt-4o-mini
NEW COST: $0.15 / $0.60 per 1M tokens
SAVINGS: -70% (≈ $450/month based on current usage)
PERFORMANCE: +35% (based on benchmarks)
ACTION: UPGRADE RECOMMENDED
```

### Exemple 2 : Opportunité Cross-Provider

**Détection** :
```
FOUND: claude-3-5-sonnet in src/backend/features/analysis/analyzer.py:128
CURRENT COST: $3.00 / $15.00 per 1M tokens
ALTERNATIVE: gemini-1.5-pro
ALT COST: $1.25 / $5.00 per 1M tokens
SAVINGS: -67% (≈ $890/month)
TRADE-OFF: -10% performance, +10x context window
ACTION: EVALUATE (test gemini-1.5-pro for this use case)
```

### Exemple 3 : Nouveau Modèle Plus Performant

**Détection** :
```
FOUND: gemini-1.5-flash in src/backend/features/embedding/service.py:56
CURRENT COST: $0.075 / $0.30 per 1M tokens
NEW MODEL: gemini-2.0-flash-exp (experimental)
NEW COST: FREE (during preview)
PERFORMANCE: +20% (faster inference)
ACTION: EVALUATE (test in dev, migrate if stable)
```

---

## 🚀 Roadmap

### Phase 1 (Actuel)
- ✅ Scan automatique du codebase
- ✅ Base de données pricing
- ✅ Rapport comparatif basique

### Phase 2 (Q1 2025)
- ⏳ Intégration logs réels (usage actual)
- ⏳ API pricing automatique (scraping)
- ⏳ Dashboard interactif

### Phase 3 (Q2 2025)
- ⏳ Prédiction tendances pricing
- ⏳ Auto-switch basé sur règles
- ⏳ A/B testing automatique modèles

---

## 🎓 Ressources

**Documentation Pricing** :
- [OpenAI Pricing](https://platform.openai.com/docs/pricing)
- [Google AI Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Anthropic Pricing](https://www.anthropic.com/api#pricing)

**Benchmarks** :
- [LMSYS Chatbot Arena](https://chat.lmsys.org/)
- [Artificial Analysis](https://artificialanalysis.ai/)
- [OpenAI Evals](https://github.com/openai/evals)

**Monitoring** :
- Logs : `claude-plugins/integrity-docs-guardian/logs/theia.log`
- Rapports : `claude-plugins/integrity-docs-guardian/reports/ai_model_cost_audit_*.{md,json}`
- Config : `claude-plugins/integrity-docs-guardian/config/theia_config.json`

---

**🔮 Theia veille sur vos coûts IA pour que vous puissiez vous concentrer sur l'innovation !**
