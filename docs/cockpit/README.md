# 📊 Cockpit - Documentation Complète

**Version** : 1.0
**Dernière mise à jour** : 2025-10-10

---

## 📋 Vue d'Ensemble

Le **Cockpit** est le tableau de bord centralisé d'Emergence qui affiche les métriques d'utilisation (messages, threads, tokens, coûts) pour tous les agents LLM (NEO, ANIMA, NEXUS).

---

## 🗂️ Documentation Disponible

### 🚀 Démarrage Rapide

| Document | Description | Pour Qui |
|----------|-------------|----------|
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Guide de test étape par étape | Développeurs, QA |
| [SCRIPTS_README.md](SCRIPTS_README.md) | Utilisation des scripts de diagnostic | Tous |

### 🔧 Corrections & Fixes

| Document | Description | Statut |
|----------|-------------|--------|
| [COCKPIT_COSTS_FIX_FINAL.md](COCKPIT_COSTS_FIX_FINAL.md) | Corrections Gemini & Anthropic (Gap #1) | ✅ Appliqué |
| [COCKPIT_GAP1_FIX_SUMMARY.md](COCKPIT_GAP1_FIX_SUMMARY.md) | Résumé logs améliorés | ✅ Appliqué |

### 📚 Architecture & Roadmap

| Document | Description | Statut |
|----------|-------------|--------|
| [COCKPIT_ROADMAP_FIXED.md](COCKPIT_ROADMAP_FIXED.md) | Feuille de route complète (Gaps 1-3) | 📋 En cours |
| [COCKPIT_GAPS_AND_FIXES.md](COCKPIT_GAPS_AND_FIXES.md) | Analyse initiale du cockpit | 📋 Référence |

---

## 🎯 État Actuel

### ✅ Ce qui Fonctionne (85%)

#### Backend Infrastructure
- ✅ API `/api/dashboard/costs/summary` - Résumé complet
- ✅ `DashboardService` v11.1 - DTO robuste
- ✅ `get_messages_by_period()` - Messages par période
- ✅ `get_tokens_summary()` - Tokens agrégés
- ✅ `get_costs_summary()` - Coûts par période
- ✅ `CostTracker` v13.1 - Enregistrement async

#### Frontend
- ✅ Module cockpit intégré dans l'application
- ✅ Affichage des métriques (messages, threads, tokens, coûts)
- ✅ Actualisation automatique (2 min)
- ✅ Export des données

#### Tracking Coûts
- ✅ **OpenAI** : Coûts et tokens enregistrés correctement
- ✅ **Gemini** : Corrections appliquées (à tester)
- ✅ **Anthropic** : Corrections appliquées (à tester)

---

### 🔴 Problèmes Identifiés (3 Gaps)

#### Gap #1 : Tracking Coûts LLM ✅ CORRIGÉ

**Problème** : Gemini et Anthropic enregistraient $0.00 avec 0 tokens

**Corrections** :
- ✅ Gemini : Format `count_tokens()` corrigé
- ✅ Anthropic : Logs détaillés ajoutés
- ✅ Tous : Uniformisation des logs

**Documentation** : [COCKPIT_COSTS_FIX_FINAL.md](COCKPIT_COSTS_FIX_FINAL.md)

**Tests requis** : [TESTING_GUIDE.md](TESTING_GUIDE.md)

---

#### Gap #2 : Métriques Prometheus Coûts ⏳ À FAIRE

**Problème** : Aucune métrique Prometheus pour les coûts LLM

**Objectifs** :
- Instrumenter `cost_tracker.py`
- Ajouter 7 métriques (Counter + Histogram + Gauge)
- Background task pour gauges
- Alertes Prometheus

**Priorité** : P1
**Estimation** : 2-3 heures

**Documentation** : [COCKPIT_ROADMAP_FIXED.md - Phase 2](COCKPIT_ROADMAP_FIXED.md#phase-2--métriques-prometheus-2-3-heures-)

---

#### Gap #3 : Tests E2E ⏳ À FAIRE

**Problème** : Validation complète du cockpit manquante

**Objectifs** :
- Tests multi-providers (OpenAI, Gemini, Claude)
- Validation cockpit frontend
- Tests seuils d'alerte

**Priorité** : P2
**Estimation** : 30 minutes

---

## 🧪 Tests

### Scripts de Diagnostic

| Script | Description | Usage |
|--------|-------------|-------|
| [check_db_simple.py](../../check_db_simple.py) | Analyse rapide BDD | `python check_db_simple.py` |
| [check_cockpit_data.py](../../check_cockpit_data.py) | Diagnostic complet | `python check_cockpit_data.py` |

**Guide complet** : [SCRIPTS_README.md](SCRIPTS_README.md)

### Guide de Test

**Document** : [TESTING_GUIDE.md](TESTING_GUIDE.md)

**Tests disponibles** :
1. ✅ Test Baseline - État initial
2. ✅ Test Gemini - 3 messages
3. ✅ Test Anthropic - 2 messages
4. ✅ Test OpenAI - 2 messages (régression)
5. ✅ Test Cockpit - Validation finale
6. ✅ Test API - Validation endpoint

---

## 📊 Métriques Suivies

### Messages
- Total, Aujourd'hui, Cette semaine, Ce mois
- Source : Table `messages`

### Threads (Sessions)
- Total, Actifs, Archivés, Taux d'activité
- Source : Table `sessions`

### Tokens
- Total, Input, Output, Moyenne par message
- Source : Table `costs` (agrégation)

### Coûts
- Total, Aujourd'hui, Cette semaine, Ce mois, Moyenne par message
- Source : Table `costs`
- Par provider : OpenAI, Google (Gemini), Anthropic (Claude)

---

## 🔧 Architecture

### Backend

```
src/backend/
├── features/
│   ├── dashboard/
│   │   ├── router.py          # API endpoints
│   │   ├── service.py         # DTO v11.1
│   │   └── timeline_service.py # Agrégations temporelles
│   └── chat/
│       ├── llm_stream.py      # Streaming + calcul coûts
│       ├── pricing.py         # Tarifs models
│       └── service.py         # Appel record_cost()
└── core/
    ├── cost_tracker.py        # Tracking v13.1
    └── database/
        └── queries.py         # Queries SQL
```

### Frontend

```
src/frontend/
└── features/
    └── cockpit/
        ├── cockpit.js         # Module d'intégration
        ├── cockpit-main.js    # Structure principale
        ├── cockpit-metrics.js # Métriques UI
        ├── cockpit-charts.js  # Graphiques
        └── cockpit-insights.js # Insights
```

---

## 🚀 Déploiement

### Prérequis

1. **Backend** :
   - Python 3.11+
   - Packages : `google-generativeai`, `anthropic`, `openai`
   - Base de données : `data/emergence.db`

2. **Frontend** :
   - Node.js 18+
   - Module cockpit intégré

### Démarrage

```bash
# Backend
python -m uvicorn src.backend.main:app --reload

# Frontend
npm run dev
# OU
npm run build && npm run preview
```

### Vérification

1. **Backend** : `http://localhost:8000/api/dashboard/costs/summary`
2. **Frontend** : `http://localhost:3000/cockpit`
3. **Logs** : `tail -f logs/app.log | grep "Cost calculated"`

---

## 📚 Références Externes

### APIs
- [OpenAI Pricing](https://openai.com/api/pricing/)
- [Google Generative AI Pricing](https://ai.google.dev/pricing)
- [Anthropic Pricing](https://www.anthropic.com/pricing)

### Documentation
- [Google Generative AI SDK](https://github.com/google/generative-ai-python)
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)
- [OpenAI SDK](https://github.com/openai/openai-python)

---

## 🆘 Support

### Problèmes Courants

#### 1. Coûts à $0.00 pour Gemini/Claude

**Solution** : [COCKPIT_COSTS_FIX_FINAL.md - Section Debugging](COCKPIT_COSTS_FIX_FINAL.md#-debugging)

#### 2. Script check_cockpit_data.py échoue (Windows)

**Solution** : [SCRIPTS_README.md - Problème d'Encodage](SCRIPTS_README.md#️-problème-dencodage-windows)

#### 3. Cockpit affiche des valeurs à 0

**Solution** :
1. Vérifier que le backend est démarré
2. Créer une conversation (envoyer des messages)
3. Exécuter `python check_db_simple.py`
4. Actualiser le cockpit

---

## 📝 Changelog

### [Non publié] - 2025-10-10

**Ajouté** :
- Scripts de diagnostic (`check_db_simple.py`, `check_cockpit_data.py`)
- Documentation complète (5 documents)
- Guide de test détaillé

**Corrigé** :
- Gemini : Format `count_tokens()` ([llm_stream.py:164-178](../../src/backend/features/chat/llm_stream.py#L164-L178))
- Anthropic : Logs détaillés ([llm_stream.py:283-286](../../src/backend/features/chat/llm_stream.py#L283-L286))
- Tous providers : Uniformisation logs

**Tests requis** :
- [ ] Conversation Gemini (3 messages)
- [ ] Conversation Claude (2 messages)
- [ ] Vérification logs
- [ ] Vérification BDD
- [ ] Vérification cockpit

---

## 🔜 Prochaines Étapes

1. **Tests** (15 min)
   - Suivre [TESTING_GUIDE.md](TESTING_GUIDE.md)
   - Valider corrections Gap #1

2. **Gap #2 : Prometheus** (2-3h)
   - Instrumenter `cost_tracker.py`
   - Métriques `llm_*`
   - Alertes budget

3. **Gap #3 : Tests E2E** (30 min)
   - Validation complète
   - Tests multi-providers

---

## 📧 Contact

Pour toute question ou problème :
- Consulter la documentation
- Exécuter les scripts de diagnostic
- Vérifier les logs backend

---

**Dernière mise à jour** : 2025-10-10
**Responsable** : Équipe Emergence
**Version** : 1.0
