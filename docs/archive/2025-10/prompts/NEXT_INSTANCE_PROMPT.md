# Prompt — Prochaine Instance Claude Code

**Date** : 2025-01-04
**Projet** : Emergence V8 — Système multi-agents (Anima, Neo, Nexus)
**Commit actuel** : `85855d8` - feat: add concept recall system for recurring topic detection

---

## 🎯 Mission prioritaire

**Valider et activer le système de détection de concepts récurrents** qui vient d'être implémenté.

---

## 📋 Tâches immédiates (ordre prioritaire)

### 1. Migration des données (15 min)
```bash
# Enrichir les concepts existants avec métadonnées temporelles
python scripts/migrate_concept_metadata.py

# Vérifier logs : X concepts migrés
```

### 2. Activation événements WebSocket (5 min)
```bash
# Ajouter dans .env.local
echo "CONCEPT_RECALL_EMIT_EVENTS=true" >> .env.local

# Redémarrer backend
pwsh -File scripts/run-backend.ps1
```

### 3. QA manuelle — Test détection (20 min)

**Scénario** :
1. Ouvrir UI → Créer thread "DevOps Setup"
2. Message : `"Comment setup une CI/CD pipeline GitHub Actions ?"`
3. Attendre réponse agent
4. API : `POST /api/memory/tend-garden` (consolider mémoire)
5. Créer nouveau thread "Automation"
6. Message : `"Je veux automatiser mon pipeline CI/CD sur AWS"`
7. **Vérifier** :
   - Banner 🔗 "Concept déjà abordé : CI/CD pipeline" s'affiche
   - Métadonnées correctes (date, thread count)
   - Bouton "Ignorer" fonctionne
   - Auto-hide après 15 secondes

### 4. Tests automatisés (30 min)
```bash
# Backend (22 tests)
pytest tests/backend/features/test_memory_gardener_enrichment.py -v
pytest tests/backend/features/test_concept_recall_tracker.py -v
pytest tests/backend/features/test_memory_concept_search.py -v

# Identifier et fixer échecs (si présents)
```

---

## 📚 Documentation de référence

**Contexte complet** : [docs/passation/2025-01-04_concept-recall-next-steps.md](docs/passation/2025-01-04_concept-recall-next-steps.md)

**Architecture système** : [docs/architecture/CONCEPT_RECALL.md](docs/architecture/CONCEPT_RECALL.md)

**Code clé** :
- Backend tracker : [src/backend/features/memory/concept_recall.py](src/backend/features/memory/concept_recall.py)
- Frontend banner : [src/frontend/features/chat/concept-recall-banner.js](src/frontend/features/chat/concept-recall-banner.js)
- API endpoint : [src/backend/features/memory/router.py](src/backend/features/memory/router.py#L603-L652)

---

## ⚠️ Points de vigilance

1. **Banner ne s'affiche pas** → Vérifier console browser pour warnings
2. **Migration échoue** → Vérifier présence `created_at` dans concepts existants
3. **Détection ne fonctionne pas** → Logs backend : chercher `[ConceptRecall]`
4. **Performance lente (>500ms)** → Logger temps exécution `detect_recurring_concepts()`

---

## ✅ Checklist succès

- [ ] Migration : X concepts enrichis sans erreurs
- [ ] WS events actifs : `CONCEPT_RECALL_EMIT_EVENTS=true`
- [ ] QA : Banner s'affiche avec données correctes
- [ ] Tests : 22/22 passent (ou fixes documentés)
- [ ] Logs : Aucun ERROR lié à concept recall
- [ ] Performance : Détection < 500ms

---

## 🚀 Si QA réussie → Prochaines étapes

**Améliorations suggérées** (par ordre priorité) :

1. **Modal "Voir l'historique"** :
   - Timeline interactive des mentions
   - Liens vers threads concernés
   - Graphique évolution `mention_count`

2. **Métriques monitoring** :
   - Prometheus : `concept_recalls_detected_total`
   - Dashboard Grafana : tendances détection

3. **Toggle utilisateur** :
   - Paramètre "Désactiver rappels concepts"
   - Cooldown 24h par concept (anti-spam)

4. **Clustering sémantique** (Phase 5 future) :
   - Détecter "CI/CD" ≈ "pipeline automatique"
   - UI admin pour merge concepts similaires

---

## 📝 Consignes générales

- **Lire** [CODEV_PROTOCOL.md](CODEV_PROTOCOL.md) et [AGENTS.md](AGENTS.md)
- **Documenter** changements dans `docs/passation.md`
- **Ne pas commit/push** sans validation tests
- **Logger** tout problème rencontré pour debug
- **Respecter** architecture existante (pas de refactoring majeur)

---

**Commence par la migration + activation WS, puis valide QA manuelle. Bon courage ! 💪**
