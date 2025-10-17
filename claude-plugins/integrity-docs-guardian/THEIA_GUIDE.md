# 💰 Theia (CostWatcher) - Guide Utilisateur

**Version:** 1.0
**Date:** 2025-01-17
**Agent:** Theia (CostWatcher)
**Rôle:** Gardienne des coûts et optimisatrice des modèles IA

---

## 🎯 À Quoi Sert Theia ?

Theia est un agent Guardian qui analyse automatiquement **tous les modèles d'IA** utilisés dans ÉMERGENCE pour :

✅ **Identifier** les modèles réellement utilisés
✅ **Calculer** leur coût actuel
✅ **Détecter** les modèles obsolètes ou dépréciés
✅ **Recommander** des alternatives moins chères et/ou plus performantes
✅ **Simuler** l'impact financier d'un changement

---

## 🚀 Utilisation Rapide

### Lancer une Analyse

```bash
# Analyse complète
python claude-plugins/integrity-docs-guardian/scripts/analyze_ai_costs.py
```

**Résultat :**
- Rapport Markdown : `reports/ai_model_cost_audit_YYYYMMDD.md`
- Rapport JSON : `reports/ai_model_cost_audit_YYYYMMDD.json`

---

## 📊 Exemple de Résultat

```
======================================================================
  💰 Theia (CostWatcher) - AI Model Cost Analyzer
======================================================================

🔍 Scanning codebase for AI model usage...
   ✅ Scanned 191 files
   ✅ Found 23 unique model(s)
   ✅ Total 90 usage location(s)

💰 Analyzing costs and generating recommendations...
   ✅ Analyzed 15 model(s)
   💵 Total monthly cost: $859,775.00
   💰 Potential savings: $9,108,575.00
   🔴 High priority recommendations: 125

  🎯 You could save $9,108,575.00/month!
  📋 Review report: reports/ai_model_cost_audit_20251017.md
```

---

## 📋 Que Vérifie Theia ?

### 1. **Modèles Utilisés**
Theia scanne tous ces emplacements :
- `src/backend/**/*.py` (Backend Python)
- `src/frontend/**/*.js` (Frontend JavaScript)
- `.env`, `.env.local` (Variables d'environnement)
- `config/**/*.{json,yaml}` (Fichiers de configuration)

### 2. **Patterns Détectés**
- `model="gpt-4o-mini"`
- `OPENAI_MODEL=gpt-4o-mini`
- Références directes : `gpt-`, `gemini-`, `claude-`

### 3. **Coûts Analysés**
Pour chaque modèle trouvé :
- Coût entrée (par 1k tokens)
- Coût sortie (par 1k tokens)
- Estimation mensuelle (basée sur 10k requêtes)
- Volume d'usage (nombre d'occurrences dans le code)

---

## 💡 Types de Recommandations

### 🔴 **HIGH Priority**
- **Économie > 30%** OU
- **Modèle déprécié** utilisé

**Actions recommandées :**
- Upgrade vers nouvelle version
- Switch vers modèle moins cher
- Downgrade si performance similaire disponible

**Exemple :**
```
Current: claude-3-opus-20240229 ($262,500/mo)
Suggested: claude-3-5-sonnet-20241022 ($52,500/mo)
Savings: $210,000/mo (-80%)
Action: DOWNGRADE
```

### 🟡 **MEDIUM Priority**
- Économie entre 15% et 30%
- Nouvelle version disponible avec mêmes performances

### 🟢 **LOW Priority**
- Économie < 15%
- Trade-offs performance vs coût à évaluer

---

## 📊 Format de Rapport

### Executive Summary
```markdown
## 📊 Executive Summary

- Models Analyzed: 15
- Total Monthly Cost: $859,775.00
- Potential Savings: $9,108,575.00
- Optimization Score: -959/100
- High Priority Recommendations: 125
- Deprecated Models: 4
```

### Tableau des Modèles Actuels
| Model | Provider | Input Cost | Output Cost | Monthly Cost | Locations | Status |
|-------|----------|------------|-------------|--------------|-----------|--------|
| gpt-4o-mini | openai | $0.15 | $0.60 | $2,250.00 | 17 | ✅ current |
| claude-3-haiku | anthropic | $0.25 | $1.25 | $4,375.00 | 5 | ⚠️ deprecated |

### Recommandations Prioritaires
| Current | Suggested | Provider | Savings | Impact | Action |
|---------|-----------|----------|---------|--------|--------|
| claude-3-opus-20240229 | claude-3-5-sonnet-20241022 | anthropic | 💰 $210,000/mo (-80.0%) | 80% cost reduction | DOWNGRADE |

### Emplacements d'Usage
```
### openai: gpt-4o-mini
- src/backend/features/chat/service.py:242
- src/backend/features/memory/preference_extractor.py:232
```

---

## 🔧 Configuration

### Baseline d'Estimation
Par défaut, Theia utilise ces estimations :
- **10,000 requêtes/mois**
- **500 tokens d'entrée** par requête
- **250 tokens de sortie** par requête

### Personnaliser l'Estimation
Pour ajuster selon votre usage réel, modifiez dans `analyze_ai_costs.py` :

```python
DEFAULT_MONTHLY_REQUESTS = 50000  # Vos requêtes réelles
DEFAULT_INPUT_TOKENS = 750        # Vos tokens moyens
DEFAULT_OUTPUT_TOKENS = 300
```

---

## 📈 Base de Données des Prix

Theia maintient une base à jour avec les derniers tarifs (Janvier 2025) :

### OpenAI
- `gpt-4o` : $2.50 / $10.00 (entrée/sortie par 1M tokens)
- `gpt-4o-mini` : $0.15 / $0.60
- `text-embedding-3-large` : $0.13 / $0.00

### Google
- `gemini-1.5-pro` : $1.25 / $5.00
- `gemini-1.5-flash` : $0.075 / $0.30
- `gemini-2.0-flash-exp` : **FREE** (expérimental)

### Anthropic
- `claude-3-5-sonnet-20241022` : $3.00 / $15.00
- `claude-3-5-haiku-20241022` : $0.80 / $4.00
- `claude-3-opus-20240229` : $15.00 / $75.00

**Sources :**
- [OpenAI Pricing](https://platform.openai.com/docs/pricing)
- [Google AI Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Anthropic Pricing](https://www.anthropic.com/api#pricing)

---

## 🔍 Cas d'Usage Pratiques

### Cas 1 : Audit Mensuel
```bash
# Exécute Theia le 1er de chaque mois
python claude-plugins/integrity-docs-guardian/scripts/analyze_ai_costs.py

# Consulte le rapport
cat claude-plugins/integrity-docs-guardian/reports/ai_model_cost_audit_*.md
```

### Cas 2 : Avant un Changement de Modèle
```bash
# 1. Lance Theia pour voir les options
python claude-plugins/integrity-docs-guardian/scripts/analyze_ai_costs.py

# 2. Consulte les recommandations HIGH priority
# 3. Teste le modèle suggéré en dev
# 4. Mesure les performances
# 5. Déploie si satisfait
```

### Cas 3 : Suivi des Dépréciations
```bash
# Theia détecte automatiquement les modèles dépréciés
# et les marque comme HIGH priority

# Exemple de sortie:
# ⚠️ Deprecated models: 4
# - claude-3-haiku-20240307
# - claude-3-sonnet-20240229
# - gpt-3.5-turbo
# - claude-3-opus (old version)
```

---

## 🎯 Interprétation des Recommandations

### Action : **UPGRADE**
**Signification :** Nouvelle version du même modèle disponible
**Exemple :** `claude-3-haiku` → `claude-3-5-haiku-20241022`
**Conseil :** Migration recommandée, souvent sans risque

### Action : **DOWNGRADE**
**Signification :** Version moins chère avec performances similaires
**Exemple :** `gpt-4-turbo` → `gpt-4o-mini`
**Conseil :** Teste en dev d'abord, vérifie que la qualité reste acceptable

### Action : **SWITCH**
**Signification :** Change de fournisseur pour économiser
**Exemple :** `claude-3-opus` → `gemini-1.5-pro`
**Conseil :** Évalue bien les trade-offs (API différente, comportement différent)

### Action : **EVALUATE**
**Signification :** Option à considérer selon use case
**Exemple :** `text-embedding-3-large` → `gemini-1.5-flash`
**Conseil :** Compare performances sur ton workload spécifique

### Action : **KEEP**
**Signification :** Modèle optimal pour le prix
**Conseil :** Aucun changement recommandé

---

## 🚨 Avertissements

### ⚠️ Estimations Basées sur Hypothèses
Les coûts sont **estimés** selon :
- Baseline : 10k requêtes, 500 tokens in, 250 tokens out
- Prix au Janvier 2025

**Pour coûts réels** → utilise tes logs d'usage ou dashboard provider

### ⚠️ Trade-offs Performance
Un modèle moins cher peut :
- Avoir moins bon contexte window
- Produire réponses de moindre qualité
- Ne pas supporter toutes les fonctionnalités

**Teste TOUJOURS en dev** avant production !

### ⚠️ Prix Dynamiques
Les fournisseurs changent parfois leurs prix.
**Met à jour la base de prix** dans `analyze_ai_costs.py` régulièrement.

---

## 🔄 Intégration Guardian

Theia s'intègre dans l'écosystème Guardian :

### Avec Anima (DocKeeper)
- Vérifie que changements de modèle sont documentés
- Suggère mise à jour docs si nouveau modèle recommandé

### Avec Neo (IntegrityWatcher)
- Vérifie compatibilité API lors de changement
- Détecte breaking changes dans signatures

### Avec ProdGuardian
- Corrèle coûts avec erreurs en production
- Identifie modèles causant problèmes (timeout, rate limit)

### Avec Nexus (Coordinator)
- Rapport Theia intégré dans rapport unifié
- Priorise recommandations avec autres agents

---

## 📚 Ressources

### Documentation
- Spécification complète : `agents/theia_costwatcher.md`
- État système : `SYSTEM_STATUS.md`
- Logs : `logs/theia.log` (si configuré)

### Benchmarks
- [LMSYS Chatbot Arena](https://chat.lmsys.org/)
- [Artificial Analysis](https://artificialanalysis.ai/)
- [OpenAI Evals](https://github.com/openai/evals)

### Pricing Officiels
- [OpenAI](https://platform.openai.com/docs/pricing)
- [Google AI](https://ai.google.dev/gemini-api/docs/pricing)
- [Anthropic](https://www.anthropic.com/api#pricing)

---

## 🎊 Résumé

✅ **Theia scanne automatiquement** tous les modèles IA utilisés
✅ **Calcule les coûts** et identifie les économies potentielles
✅ **Recommande des alternatives** moins chères ou plus performantes
✅ **Génère des rapports détaillés** en Markdown et JSON
✅ **S'intègre** avec les autres agents Guardian

**🔮 Theia veille sur vos coûts IA pour que vous puissiez innover sans limite de budget !**

---

**Prochaine étape recommandée :**
```bash
python claude-plugins/integrity-docs-guardian/scripts/analyze_ai_costs.py
```

**Consulte ensuite :**
```bash
cat claude-plugins/integrity-docs-guardian/reports/ai_model_cost_audit_*.md
```

**Et applique les recommandations HIGH priority ! 🎯**
