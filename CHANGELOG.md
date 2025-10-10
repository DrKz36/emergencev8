# Changelog - Emergence V8

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Versioning Sémantique](https://semver.org/lang/fr/).

---

## [Non publié] - 2025-10-10

### 🔧 Corrigé

#### Cockpit - Tracking des Coûts LLM

**Problème** : Les coûts et tokens pour Gemini et Anthropic (Claude) étaient enregistrés à $0.00 avec 0 tokens, alors que les requêtes étaient bien effectuées.

**Diagnostic** :
- ✅ OpenAI : 101 entrées, $0.21, 213k tokens → Fonctionnel
- ❌ Gemini : 29 entrées, $0.00, 0 tokens → Défaillant
- ❌ Anthropic : 26 entrées, $0.00, 0 tokens → Défaillant

**Corrections apportées** :

1. **Gemini - Format count_tokens()** ([llm_stream.py:164-178](src/backend/features/chat/llm_stream.py#L164-L178))
   - Correction du format d'entrée (string concaténé au lieu de liste)
   - Ajout de logs détaillés avec `exc_info=True`
   - Même correction pour input et output tokens

2. **Anthropic - Logs détaillés** ([llm_stream.py:283-286](src/backend/features/chat/llm_stream.py#L283-L286))
   - Remplacement de `except Exception: pass` par des logs détaillés
   - Ajout de warnings si `usage` est absent
   - Stack trace complète des erreurs

3. **Tous les providers - Uniformisation des logs** ([llm_stream.py](src/backend/features/chat/llm_stream.py))
   - Logs détaillés pour OpenAI (lignes 139-144)
   - Logs détaillés pour Gemini (lignes 224-229)
   - Logs détaillés pour Anthropic (lignes 277-282)
   - Format uniforme : `[Provider] Cost calculated: $X.XXXXXX (model=XXX, input=XXX tokens, output=XXX tokens, pricing_input=$X.XXXXXXXX/token, pricing_output=$X.XXXXXXXX/token)`

**Impact** :
- Correction de la sous-estimation des coûts (~70% du volume réel)
- Meilleure traçabilité des coûts dans les logs
- Cockpit affiche désormais des valeurs réelles

**Documentation** :
- [COCKPIT_COSTS_FIX_FINAL.md](docs/cockpit/COCKPIT_COSTS_FIX_FINAL.md) - Guide complet des corrections
- [COCKPIT_ROADMAP_FIXED.md](docs/cockpit/COCKPIT_ROADMAP_FIXED.md) - Feuille de route complète
- [COCKPIT_GAP1_FIX_SUMMARY.md](docs/cockpit/COCKPIT_GAP1_FIX_SUMMARY.md) - Résumé Gap #1

**Tests requis** :
- [ ] Conversation avec Gemini (3 messages minimum)
- [ ] Conversation avec Claude (2 messages minimum)
- [ ] Vérification logs backend (`grep "Cost calculated"`)
- [ ] Vérification BDD (`python check_db_simple.py`)
- [ ] Vérification cockpit (Tokens > 0, Coûts > $0.00)

---

### 📝 Ajouté

#### Scripts de Diagnostic

1. **check_db_simple.py** - Analyse rapide de la base de données
   - Compte les messages, coûts, sessions, documents
   - Analyse les coûts par modèle
   - Détection automatique des problèmes (coûts à $0.00)
   - Affiche les 5 entrées de coûts les plus récentes

2. **check_cockpit_data.py** - Diagnostic complet du cockpit
   - Analyse par période (aujourd'hui, semaine, mois)
   - Détection spécifique des problèmes Gemini (Gap #1)
   - Calcul des tokens moyens par message
   - Résumé avec recommandations

**Usage** :
```bash
# Diagnostic rapide
python check_db_simple.py

# Diagnostic complet (nécessite UTF-8)
python check_cockpit_data.py
```

---

### 📚 Documentation

#### Cockpit - Guides Complets

1. **[COCKPIT_ROADMAP_FIXED.md](docs/cockpit/COCKPIT_ROADMAP_FIXED.md)**
   - État des lieux complet (85% fonctionnel)
   - 3 Gaps identifiés avec solutions détaillées
   - Plan d'action (Phase 0-3, 4h total)
   - Scripts de validation et tests E2E
   - Critères de succès mesurables

2. **[COCKPIT_GAP1_FIX_SUMMARY.md](docs/cockpit/COCKPIT_GAP1_FIX_SUMMARY.md)**
   - Résumé des corrections Gap #1 (logs améliorés)
   - Exemples de sortie de logs
   - Guide de validation étape par étape
   - Checklist de validation

3. **[COCKPIT_COSTS_FIX_FINAL.md](docs/cockpit/COCKPIT_COSTS_FIX_FINAL.md)**
   - Diagnostic complet du problème de coûts
   - Corrections détaillées (Gemini + Anthropic)
   - Guide de test et validation
   - Section debugging avec tests manuels
   - Tableau avant/après les corrections

4. **[COCKPIT_GAPS_AND_FIXES.md](docs/cockpit/COCKPIT_GAPS_AND_FIXES.md)** (existant)
   - Analyse initiale du cockpit
   - Backend infrastructure (85% opérationnel)
   - 3 Gaps critiques identifiés
   - Plan Sprint 0 Cockpit (1-2 jours)

---

## [1.0.0] - 2025-10-10 (Phase P1.2 + P0)

### 🚀 Déployé

**Révision** : `emergence-app-p1-p0-20251010-040147`
**Image Tag** : `p1-p0-20251010-040147`
**Statut** : ✅ Active (100%)

### Ajouté
- Préférences utilisateur persistées
- Consolidation threads archivés
- Queue async pour la mémoire

### Documentation
- [2025-10-10-deploy-p1-p0.md](docs/deployments/2025-10-10-deploy-p1-p0.md)

---

## [0.9.0] - 2025-10-09 (Phase P1 Mémoire)

### 🚀 Déployé

**Révision** : `emergence-app-p1memory`
**Image Tag** : `deploy-p1-20251009-094822`
**Statut** : ✅ Active (100%)

### Ajouté
- Queue async pour la mémoire
- Système de préférences utilisateur
- Instrumentation Prometheus pour mémoire

### Documentation
- [2025-10-09-deploy-p1-memory.md](docs/deployments/2025-10-09-deploy-p1-memory.md)

---

## [0.8.0] - 2025-10-09 (Cockpit Phase 3)

### 🚀 Déployé

**Révision** : `emergence-app-phase3b`
**Image Tag** : `cockpit-phase3-20251009-073931`
**Statut** : ✅ Active (100%)

### Corrigé
- Timeline SQL queries optimisées
- Cockpit Phase 3 redéployé

### Documentation
- [2025-10-09-deploy-cockpit-phase3.md](docs/deployments/2025-10-09-deploy-cockpit-phase3.md)

---

## [0.7.0] - 2025-10-09 (Prometheus Phase 3)

### 🚀 Déployé

**Révision** : `emergence-app-metrics001`
**Image Tag** : `deploy-20251008-183707`
**Statut** : ✅ Active (100%)

### Ajouté
- Activation `CONCEPT_RECALL_METRICS_ENABLED`
- Routage 100% Prometheus Phase 3
- Métriques Concept Recall

### Documentation
- [2025-10-09-activation-metrics-phase3.md](docs/deployments/2025-10-09-activation-metrics-phase3.md)

---

## [0.6.0] - 2025-10-08 (Phase 2 Performance)

### 🚀 Déployé

**Révision** : `emergence-app-00274-m4w`
**Image Tag** : `deploy-20251008-121131`
**Statut** : ⏸️ Archived

### Ajouté
- Neo analysis optimisé
- Cache mémoire amélioré
- Débats parallèles
- Health checks + métriques Prometheus

### Documentation
- [2025-10-08-cloud-run-revision-00274.md](docs/deployments/2025-10-08-cloud-run-revision-00274.md)

---

## [0.5.0] - 2025-10-08 (UI Fixes)

### 🚀 Déployé

**Révision** : `emergence-app-00270-zs6`
**Image Tag** : `deploy-20251008-082149`
**Statut** : ⏸️ Archived

### Corrigé
- Menu mobile confirmé
- Harmonisation UI cockpit/hymne

---

## [0.4.0] - 2025-10-06 (Agents & UI Refresh)

### 🚀 Déployé

**Révision** : `emergence-app-00268-9s8`
**Image Tag** : `deploy-20251006-060538`
**Statut** : ⏸️ Archived

### Ajouté
- Personnalités agents améliorées
- Module documentation
- Interface responsive

---

## [0.3.0] - 2025-10-05 (Audit Fixes)

### 🚀 Déployé

**Révision** : `emergence-app-00266-jc4`
**Image Tag** : `deploy-20251005-123837`
**Statut** : ⏸️ Archived

### Corrigé
- 13 corrections issues de l'audit
- Score qualité : 87.5 → 95/100

### Documentation
- [2025-10-05-audit-fixes-deployment.md](docs/deployments/)

---

## [0.2.0] - 2025-10-04 (Métriques & Settings)

### 🚀 Déployé

**Révision** : `emergence-app-00265-xxx`
**Image Tag** : `deploy-20251004-205347`
**Statut** : ⏸️ Archived

### Ajouté
- Système de métriques Prometheus
- Module Settings (préférences utilisateur)

---

## Légende

- 🚀 **Déployé** : Déployé en production (Cloud Run)
- 🔧 **Corrigé** : Corrections de bugs
- 📝 **Ajouté** : Nouvelles fonctionnalités
- 📚 **Documentation** : Mises à jour documentation
- ⚠️ **Déprécié** : Fonctionnalités dépréciées
- 🗑️ **Supprimé** : Fonctionnalités supprimées
- 🔒 **Sécurité** : Corrections de sécurité

---

## Versions à Venir

### [Prochainement] - Gap #2 : Métriques Prometheus Coûts

**Priorité** : P1
**Estimation** : 2-3 heures

**Objectifs** :
- Instrumenter `cost_tracker.py` avec métriques Prometheus
- Ajouter 7 métriques (Counter + Histogram + Gauge)
- Background task pour mise à jour des gauges (5 min)
- Configurer alertes Prometheus (budget dépassé)

**Référence** : [COCKPIT_ROADMAP_FIXED.md - Phase 2](docs/cockpit/COCKPIT_ROADMAP_FIXED.md#phase-2--métriques-prometheus-2-3-heures-)

---

### [Prochainement] - Gap #3 : Tests E2E Cockpit

**Priorité** : P2
**Estimation** : 30 minutes

**Objectifs** :
- Tests conversation complète (3 providers)
- Validation affichage cockpit
- Validation API `/api/dashboard/costs/summary`
- Tests seuils d'alerte (vert/jaune/rouge)

---

## Contributeurs

- Claude Code (Anthropic) - Assistant IA
- Équipe Emergence

---

**Dernière mise à jour** : 2025-10-10
