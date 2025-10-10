# 🔴 PROMPT CRITIQUE - Fix PreferenceExtractor Production

**Date** : 2025-10-10 08:50 UTC
**Priorité** : 🔴 **CRITIQUE** - Blocage système extraction préférences
**Durée Estimée** : 1-2 heures
**Agent** : Claude Code / Codex

---

## 🚨 Contexte Urgent

Suite au déploiement P2 Sprint 3 (révision `emergence-app-00348-rih`), **le système d'extraction de préférences ne fonctionne PAS en production**.

**Symptôme** :
```
WARNING [backend.features.memory.analyzer] [PreferenceExtractor]
Cannot extract: no user identifier (user_sub or user_id) found for session XXX
```

**Impact** :
- ❌ **Métriques Prometheus** : `memory_preferences_extracted_total = 0` (depuis déploiement)
- ❌ **Aucune préférence persistée** dans ChromaDB
- ❌ **7+ sessions impactées** dans les dernières 24h
- ❌ **Fonctionnalité P1 cassée** : Préférences utilisateur non mémorisées

**Cause racine identifiée** :
- `PreferenceExtractor.extract()` ne reçoit **jamais** `user_sub` ou `user_id`
- Le paramètre est soit non passé, soit `None` lors de l'appel depuis `MemoryAnalyzer`

**Documentation complète** :
- [docs/monitoring/POST_P2_SPRINT3_MONITORING_REPORT.md](docs/monitoring/POST_P2_SPRINT3_MONITORING_REPORT.md)
- [docs/passation.md](docs/passation.md) - Entrée 2025-10-10 08:35

---

## 🎯 Objectif Mission

**Corriger le passage de `user_sub`/`user_id` au PreferenceExtractor pour rétablir l'extraction de préférences en production.**

**Critères de succès** :
1. ✅ `memory_preferences_extracted_total` > 0 après exécution script QA
2. ✅ Logs Cloud Run : `[PreferenceExtractor] Extracted X preferences for user YYY`
3. ✅ Aucun warning "no user identifier"
4. ✅ Tests existants passent (20/20 tests préférences)
5. ✅ Déployé et validé en production

---

## 🔍 Étape 1 : Diagnostic Précis (15 min)

### 1.1 Localiser l'Appel DefectueuxVérifier où `PreferenceExtractor.extract()` est appelé dans le code.

**Fichier principal** : `src/backend/features/memory/analyzer.py`

**Actions** :
```bash
# Rechercher tous les appels à PreferenceExtractor.extract()
grep -n "preference_extractor.extract" src/backend/features/memory/analyzer.py

# Vérifier la signature de la méthode extract()
grep -A 10 "async def extract" src/backend/features/memory/preference_extractor.py
```

**Questions à répondre** :
1. L'appel à `extract()` passe-t-il le paramètre `user_sub=` ?
2. Si oui, quelle est la variable passée ? (ex: `user_sub`, `uid`, `kwargs.get("user_sub")`)
3. D'où vient cette variable ? (paramètre de `analyze_session_for_concepts()` ?)
4. Est-elle `None` au moment de l'appel ?

**Résultat attendu** :
```python
# Trouver la ligne exacte (probablement ligne ~409-423)
prefs = await self.preference_extractor.extract(
    messages=history,
    user_sub=???,  # ← IDENTIFIER CETTE VALEUR
    thread_id=thread_id,
    session_id=session_id
)
```

---

### 1.2 Vérifier la Signature de `analyze_session_for_concepts()`

**Fichier** : `src/backend/features/memory/analyzer.py`

**Actions** :
```bash
# Trouver la définition de la méthode
grep -A 5 "async def analyze_session_for_concepts" src/backend/features/memory/analyzer.py
```

**Questions** :
1. La méthode reçoit-elle `user_sub` ou `user_id` en paramètre ?
2. Si oui, est-ce un paramètre requis ou optionnel (`Optional[str]`) ?
3. Quel est le nom exact du paramètre ? (peut être `user_id`, `uid`, `user_sub`)

**Résultat attendu** :
```python
async def analyze_session_for_concepts(
    self,
    thread_id: str,
    session_id: str,
    user_id: Optional[str] = None,  # ← VÉRIFIER CE PARAMÈTRE
    # ... autres paramètres
):
```

---

### 1.3 Tracer l'Origine de l'Appel

**Qui appelle `analyze_session_for_concepts()` ?**

**Fichiers à vérifier** :
1. `src/backend/features/chat/service.py` - ChatService (appel principal)
2. `src/backend/features/memory/gardener.py` - MemoryGardener (consolidation batch)
3. `src/backend/features/memory/router.py` - Endpoints API mémoire

**Actions** :
```bash
# Trouver tous les appels
grep -rn "analyze_session_for_concepts" src/backend/features/

# Focus sur ChatService
grep -A 10 "analyze_session_for_concepts" src/backend/features/chat/service.py
```

**Questions** :
1. L'appelant passe-t-il `user_sub` ou `user_id` ?
2. Si oui, d'où vient la valeur ? (contexte request, session, thread ?)
3. Si non, pourquoi ? (oubli, indisponible, refactoring incomplet ?)

---

## 🛠️ Étape 2 : Implémentation du Fix (30-45 min)

### Option A : Fix Simple (si `user_id` disponible mais non passé)

**Si le diagnostic montre que `user_id` est disponible dans le contexte mais non passé :**

#### 2.1 Modifier l'Appel dans `analyzer.py`

**Fichier** : `src/backend/features/memory/analyzer.py` (ligne ~409-423)

**Avant** (hypothèse) :
```python
async def analyze_session_for_concepts(
    self,
    thread_id: str,
    session_id: str,
    user_id: Optional[str] = None,  # ← Paramètre existe mais non utilisé
    # ...
):
    # ...
    prefs = await self.preference_extractor.extract(
        messages=history,
        # user_sub=user_id,  ← LIGNE MANQUANTE
        thread_id=thread_id,
        session_id=session_id
    )
```

**Après** (fix) :
```python
async def analyze_session_for_concepts(
    self,
    thread_id: str,
    session_id: str,
    user_id: Optional[str] = None,
    # ...
):
    # ...
    prefs = await self.preference_extractor.extract(
        messages=history,
        user_sub=user_id,  # ✅ AJOUTER CETTE LIGNE
        user_id=user_id,   # ✅ Passer aussi user_id pour fallback
        thread_id=thread_id,
        session_id=session_id
    )
```

**Justification** :
- Le `PreferenceExtractor` accepte `user_sub` ou `user_id` (fallback implémenté dans P0)
- En passant les deux, on maximise les chances de succès

---

#### 2.2 Vérifier les Appelants Passent `user_id`

**Fichier** : `src/backend/features/chat/service.py` (ligne ~1380-1395 environ)

**Rechercher l'appel** :
```bash
grep -A 15 "analyze_session_for_concepts" src/backend/features/chat/service.py
```

**Vérifier que l'appel ressemble à** :
```python
await self.memory_analyzer.analyze_session_for_concepts(
    thread_id=thread_id,
    session_id=session_id,
    user_id=user_id,  # ✅ CETTE LIGNE DOIT EXISTER
    # ... autres paramètres
)
```

**Si la ligne `user_id=user_id` est absente**, l'ajouter :
```python
# Récupérer user_id depuis le contexte (déjà disponible dans ChatService)
user_id = self._get_user_id_from_context()  # ou équivalent

await self.memory_analyzer.analyze_session_for_concepts(
    thread_id=thread_id,
    session_id=session_id,
    user_id=user_id,  # ✅ AJOUTER
    # ...
)
```

---

### Option B : Fix avec Fallback (si `user_sub` vraiment absent)

**Si le diagnostic montre que ni `user_sub` ni `user_id` ne sont disponibles :**

#### 2.3 Ajouter Fallback dans `PreferenceExtractor`

**Fichier** : `src/backend/features/memory/preference_extractor.py` (ligne ~60-80 environ)

**Avant** (actuel) :
```python
async def extract(
    self,
    messages: List[Dict[str, Any]],
    user_sub: Optional[str] = None,
    thread_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> List[PreferenceRecord]:
    if not user_sub:
        logger.warning(
            f"[PreferenceExtractor] Cannot extract: user_sub not found "
            f"for session {session_id}"
        )
        PREFERENCE_EXTRACTION_FAILURES.labels(reason="user_identifier_missing").inc()
        return []
```

**Après** (fix avec fallback) :
```python
async def extract(
    self,
    messages: List[Dict[str, Any]],
    user_sub: Optional[str] = None,
    user_id: Optional[str] = None,  # ✅ AJOUTER PARAMÈTRE
    thread_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> List[PreferenceRecord]:
    # ✅ FALLBACK : user_sub → user_id → thread owner
    user_identifier = user_sub or user_id

    if not user_identifier:
        # ✅ DERNIER RECOURS : récupérer user_id depuis thread
        if thread_id:
            try:
                thread = await self._fetch_thread_owner(thread_id)
                user_identifier = thread.get("user_id")
            except Exception as e:
                logger.debug(f"[PreferenceExtractor] Cannot fetch thread owner: {e}")

    # Si toujours absent, échouer gracieusement
    if not user_identifier:
        logger.warning(
            f"[PreferenceExtractor] Cannot extract: no user identifier "
            f"(user_sub, user_id, or thread owner) found for session {session_id}"
        )
        PREFERENCE_EXTRACTION_FAILURES.labels(reason="user_identifier_missing").inc()
        return []

    # Continuer avec user_identifier...
    logger.debug(
        f"[PreferenceExtractor] Extracting preferences for user {user_identifier[:8]}..."
    )
```

**Ajouter helper `_fetch_thread_owner()`** (si nécessaire) :
```python
async def _fetch_thread_owner(self, thread_id: str) -> Dict[str, Any]:
    """Récupère le user_id propriétaire du thread depuis la BDD."""
    from backend.core.database import queries

    db = self.db_manager  # Assuming injected
    thread = await queries.get_thread_by_id(db, thread_id)
    return thread or {}
```

---

### Option C : Fix Complet (recommandé)

**Combiner Option A + Option B pour robustesse maximale.**

#### 2.4 Plan d'Action Complet

**Fichier 1** : `src/backend/features/memory/preference_extractor.py`
- ✅ Ajouter paramètre `user_id: Optional[str] = None`
- ✅ Fallback : `user_identifier = user_sub or user_id`
- ✅ (Optionnel) Dernier recours : fetch thread owner

**Fichier 2** : `src/backend/features/memory/analyzer.py`
- ✅ Passer `user_sub=user_id` ET `user_id=user_id` lors de l'appel `extract()`

**Fichier 3** : `src/backend/features/chat/service.py`
- ✅ Vérifier que `user_id` est bien passé à `analyze_session_for_concepts()`

**Résultat** : Triple sécurité (user_sub → user_id → thread owner)

---

## ✅ Étape 3 : Tests & Validation (20-30 min)

### 3.1 Tests Unitaires Existants

**Tous les tests doivent passer** :
```bash
# Tests préférences (20 tests)
python -m pytest tests/backend/features/test_memory_preferences_persistence.py -v
python -m pytest tests/backend/features/ -k "preference" -v

# Tests intégration
python -m pytest tests/backend/features/test_memory_enhancements.py -v
```

**Résultat attendu** : ✅ 20/20 tests passent (aucune régression)

---

### 3.2 Tests Manuels Locaux

**Lancer backend local** :
```bash
cd src/backend
uvicorn main:app --reload
```

**Créer thread + message avec préférences** (via curl ou Postman) :
```bash
# 1. Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword"}'

# Récupérer token dans réponse

# 2. Créer thread
curl -X POST http://localhost:8000/api/threads \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Préférences"}'

# Récupérer thread_id

# 3. Envoyer message avec préférence
curl -X POST http://localhost:8000/api/chat/send \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Thread-Id: $THREAD_ID" \
  -H "Content-Type: application/json" \
  -d '{"message":"Je préfère utiliser Python pour mes projets backend"}'

# 4. Déclencher consolidation
curl -X POST http://localhost:8000/api/memory/tend-garden \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"'"$THREAD_ID"'"}'
```

**Vérifier logs backend** :
```bash
grep "PreferenceExtractor" logs/backend.log | tail -20

# Attendu :
# [PreferenceExtractor] Extracting preferences for user abc12345...
# [PreferenceExtractor] Extracted 1 preferences for user abc12345
# [PreferenceExtractor] Saved 1/1 preferences to ChromaDB
```

---

### 3.3 Vérification BDD Locale

```bash
sqlite3 instance/emergence.db

# Vérifier documents ChromaDB (via table ou logs)
SELECT COUNT(*) FROM chroma_documents WHERE metadata LIKE '%preference%';

# Ou vérifier via Python
python -c "
from backend.core.vector_service import VectorService
vs = VectorService()
coll = vs.get_or_create_collection('emergence_knowledge')
results = coll.get(where={'type': 'preference'})
print(f'Total preferences: {len(results[\"documents\"])}')
"
```

**Résultat attendu** : Au moins 1 préférence persistée

---

## 🚀 Étape 4 : Déploiement Production (20-30 min)

### 4.1 Tests Pre-Deploy

**Checklist obligatoire** :
```bash
# 1. Tests pytest
python -m pytest tests/backend/features/ -k "preference" -v
# ✅ 20/20 passants

# 2. Mypy
python -m mypy src/backend/features/memory/
# ✅ 0 erreur

# 3. Ruff
ruff check src/backend/features/memory/
# ✅ All checks passed

# 4. Tests manuels locaux
# ✅ Logs "Extracted X preferences" présents
# ✅ BDD contient préférences
```

---

### 4.2 Build & Push Docker

```bash
# Build image
timestamp=$(date +%Y%m%d-%H%M%S)
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:fix-preferences-$timestamp .

# Push registry
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:fix-preferences-$timestamp
```

---

### 4.3 Deploy Cloud Run

```bash
# Deploy nouvelle révision
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:fix-preferences-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --tag fix-preferences

# Récupérer URL révision
gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005 --format="value(name,status)" | head -1
```

---

### 4.4 Tests Smoke Production

**Script QA automatisé** :
```bash
cd scripts/qa
python trigger_preferences_extraction.py
```

**Résultat attendu** :
```
[SUCCESS] QA P1 completed successfully!
Thread ID: XXXXXXX
Messages sent: 5
Consolidation: {"status":"success","new_concepts":X}
```

**Vérifier métriques Prometheus** :
```bash
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep memory_preferences_extracted_total

# Attendu : memory_preferences_extracted_total{type="preference"} > 0
```

**Vérifier logs Cloud Run** :
```bash
gcloud logging read \
  'resource.type=cloud_run_revision
   AND resource.labels.service_name=emergence-app
   AND textPayload=~"PreferenceExtractor.*Extracted"' \
  --limit 10 \
  --format="value(timestamp,textPayload)" \
  --project emergence-469005

# Attendu : Logs "[PreferenceExtractor] Extracted X preferences for user YYY"
```

---

### 4.5 Basculer Trafic (si tests OK)

```bash
# Basculer 100% trafic sur nouvelle révision
gcloud run services update-traffic emergence-app \
  --to-tags fix-preferences=100 \
  --region europe-west1 \
  --project emergence-469005
```

---

## 📊 Étape 5 : Validation Post-Déploiement (15 min)

### 5.1 Monitoring Métriques (30 min post-deploy)

**Requêtes Prometheus à exécuter** :
```bash
# 1. Préférences extraites (doit augmenter)
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep memory_preferences_extracted_total

# 2. Taux de succès extraction (doit être > 90%)
# rate(memory_preferences_extracted_total[5m]) / rate(memory_analysis_success_total[5m])

# 3. Échecs extraction (doit rester 0)
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep memory_preferences_extraction_failures_total

# 4. Confiance préférences (doit avoir des valeurs)
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/metrics | grep memory_preferences_confidence_count
```

**Baseline attendue (après 1h trafic réel)** :
| Métrique | Avant Fix | Après Fix |
|----------|-----------|-----------|
| `memory_preferences_extracted_total` | **0** 🔴 | **> 0** ✅ |
| `memory_preferences_extraction_failures_total{reason="user_identifier_missing"}` | ~7/24h | **0** ✅ |
| `memory_preferences_confidence_count` | 0 | **> 0** ✅ |

---

### 5.2 Logs Cloud Run (vérification warnings)

```bash
# Vérifier absence de warnings "no user identifier"
gcloud logging read \
  'resource.type=cloud_run_revision
   AND resource.labels.service_name=emergence-app
   AND severity=WARNING
   AND textPayload=~"PreferenceExtractor.*no user identifier"' \
  --limit 20 \
  --project emergence-469005

# Attendu : 0 résultat (ou beaucoup moins qu'avant)
```

---

### 5.3 Validation ChromaDB

**Via endpoint API** :
```bash
curl -s https://emergence-app-47nct44nma-ew.a.run.app/api/memory/user/stats \
  -H "Authorization: Bearer $TOKEN"

# Vérifier champ "preferences_count" > 0
```

**Via logs backend (si accès DB direct)** :
```bash
# Compter documents type "preference" dans ChromaDB
gcloud logging read \
  'resource.type=cloud_run_revision
   AND textPayload=~"Saved .*/.*preferences to ChromaDB"' \
  --limit 10 \
  --project emergence-469005
```

---

## 📝 Étape 6 : Documentation (10 min)

### 6.1 Mettre à Jour Rapport Monitoring

**Fichier** : `docs/monitoring/POST_P2_SPRINT3_MONITORING_REPORT.md`

**Ajouter section** :
```markdown
## ✅ Résolution Anomalie #1 : User Identifier Manquant

**Date Fix** : 2025-10-10 XX:XX UTC
**Révision Déployée** : `emergence-app-00XXX-XXX`

### Modifications Apportées

**Fichiers modifiés** :
1. `src/backend/features/memory/preference_extractor.py` (+10 lignes)
   - Ajout paramètre `user_id: Optional[str] = None`
   - Fallback : `user_identifier = user_sub or user_id`

2. `src/backend/features/memory/analyzer.py` (+2 lignes)
   - Passage `user_sub=user_id` ET `user_id=user_id` lors de l'appel `extract()`

3. (Si modifié) `src/backend/features/chat/service.py`
   - Ajout passage `user_id` à `analyze_session_for_concepts()`

### Tests Validés

- ✅ 20/20 tests préférences passants
- ✅ Tests manuels locaux : préférences persistées
- ✅ Script QA production : succès
- ✅ Métriques Prometheus : `memory_preferences_extracted_total` > 0
- ✅ Logs Cloud Run : aucun warning "no user identifier"

### Métriques Post-Fix (après 1h trafic)

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| `memory_preferences_extracted_total` | 0 | XX | +∞ |
| `memory_preferences_extraction_failures` (user_id) | 7/24h | 0 | -100% |
| `memory_preferences_confidence_count` | 0 | XX | +∞ |

### Validation Finale

- ✅ Anomalie #1 résolue
- ✅ Extraction préférences fonctionnelle
- ✅ Aucune régression détectée
```

---

### 6.2 Mettre à Jour Passation

**Fichier** : `docs/passation.md`

**Ajouter nouvelle entrée** :
```markdown
## [2025-10-10 XX:XX] - Agent: [Nom] (Fix Critique PreferenceExtractor)

### Fichiers modifiés
- `src/backend/features/memory/preference_extractor.py` — ajout fallback user_id
- `src/backend/features/memory/analyzer.py` — passage user_id à extract()
- `docs/monitoring/POST_P2_SPRINT3_MONITORING_REPORT.md` — section résolution
- `docs/passation.md` — nouvelle entrée

### Contexte
Suite au monitoring post-P2 Sprint 3, anomalie critique détectée : PreferenceExtractor
ne recevait jamais user_sub/user_id → métriques à zéro. Correction appliquée avec triple
fallback (user_sub → user_id → thread owner).

### Actions Complétées
1. ✅ Diagnostic : appel extract() ne passait pas user_id
2. ✅ Fix : ajout paramètre user_id + fallback dans PreferenceExtractor
3. ✅ Fix : passage user_id dans analyzer.py
4. ✅ Tests : 20/20 passants, tests manuels OK
5. ✅ Deploy : révision `emergence-app-00XXX-XXX` déployée
6. ✅ Validation : métriques > 0, logs sans warnings

### Tests
- ✅ pytest tests préférences (20/20)
- ✅ mypy + ruff (0 erreur)
- ✅ Script QA production (succès)
- ✅ Métriques Prometheus validées
- ✅ Logs Cloud Run sans warnings user_id

### Résultat
🟢 Anomalie critique résolue - Extraction préférences fonctionnelle

### Prochaines actions
- 🟢 Monitoring continu 24h (vérifier stabilité)
- 🟢 Analyser taux extraction (objectif >80% messages avec intent)
```

---

### 6.3 Mettre à Jour AGENT_SYNC.md

**Fichier** : `AGENT_SYNC.md`

**Modifier section "Zones de travail en cours"** :
```markdown
### 🟢 [Nom Agent] - Session 2025-10-10 XX:XX (Fix Critique PreferenceExtractor)
- **Statut** : ✅ **RÉSOLU** - Extraction préférences fonctionnelle
- **Priorité** : 🔴 **CRITIQUE** → 🟢 **RÉSOLU**
- **Fichiers touchés** :
  - `src/backend/features/memory/preference_extractor.py` (+10 lignes)
  - `src/backend/features/memory/analyzer.py` (+2 lignes)
  - `docs/monitoring/POST_P2_SPRINT3_MONITORING_REPORT.md` (section résolution)
- **Anomalie résolue** : PreferenceExtractor reçoit maintenant user_id avec fallback
- **Validation** : Métriques > 0, logs sans warnings, 20/20 tests OK
- **Déploiement** : Révision `emergence-app-00XXX-XXX` (tag `fix-preferences`)
```

---

## 🎯 Checklist Finale (Critères de Succès)

**Avant de considérer la mission terminée, vérifier** :

### Code
- [ ] ✅ `PreferenceExtractor.extract()` accepte `user_id` paramètre
- [ ] ✅ Fallback `user_identifier = user_sub or user_id` implémenté
- [ ] ✅ `analyzer.py` passe `user_id` lors de l'appel `extract()`
- [ ] ✅ (Optionnel) Dernier recours : fetch thread owner ajouté

### Tests
- [ ] ✅ 20/20 tests préférences passent
- [ ] ✅ Tests manuels locaux : préférences persistées dans ChromaDB
- [ ] ✅ Mypy 0 erreur
- [ ] ✅ Ruff clean

### Production
- [ ] ✅ Build Docker réussi (linux/amd64)
- [ ] ✅ Push registry réussi
- [ ] ✅ Deploy Cloud Run réussi
- [ ] ✅ Script QA production : succès (messages + consolidation)
- [ ] ✅ **Métriques Prometheus** : `memory_preferences_extracted_total` > 0
- [ ] ✅ **Logs Cloud Run** : présence logs "[PreferenceExtractor] Extracted X preferences"
- [ ] ✅ **Logs Cloud Run** : absence warnings "no user identifier" (ou réduction >90%)

### Validation
- [ ] ✅ Monitoring 30 min post-deploy : métriques stables
- [ ] ✅ Aucune régression autre fonctionnalité
- [ ] ✅ Trafic 100% sur nouvelle révision

### Documentation
- [ ] ✅ Rapport monitoring mis à jour (section résolution)
- [ ] ✅ Passation.md mis à jour (nouvelle entrée)
- [ ] ✅ AGENT_SYNC.md mis à jour (zone travail résolu)
- [ ] ✅ Commit + push avec message détaillé

---

## 🚨 En Cas d'Échec / Rollback

**Si les tests production échouent** :

### Rollback Immédiat

```bash
# Revenir à la révision précédente stable
gcloud run services update-traffic emergence-app \
  --to-tags p2-sprint3=100 \
  --region europe-west1 \
  --project emergence-469005

# Vérifier rollback
gcloud run revisions list --service emergence-app --region europe-west1 --project emergence-469005 | head -5
```

### Analyser Logs d'Erreur

```bash
# Logs dernière révision
gcloud logging read \
  'resource.type=cloud_run_revision
   AND resource.labels.service_name=emergence-app
   AND severity>=ERROR' \
  --limit 50 \
  --project emergence-469005
```

### Investiguer Localement

1. Reproduire l'erreur en local
2. Ajouter logs debug supplémentaires
3. Re-tester avec fixtures
4. Corriger + re-déployer

---

## 📚 Références Techniques

### Code Source
- **PreferenceExtractor** : [src/backend/features/memory/preference_extractor.py](src/backend/features/memory/preference_extractor.py)
- **MemoryAnalyzer** : [src/backend/features/memory/analyzer.py](src/backend/features/memory/analyzer.py)
- **ChatService** : [src/backend/features/chat/service.py](src/backend/features/chat/service.py)

### Tests
- **Tests Préférences** : [tests/backend/features/test_memory_preferences_persistence.py](tests/backend/features/test_memory_preferences_persistence.py)
- **Tests Intégration** : [tests/backend/features/test_memory_enhancements.py](tests/backend/features/test_memory_enhancements.py)

### Documentation
- **Rapport Monitoring** : [docs/monitoring/POST_P2_SPRINT3_MONITORING_REPORT.md](docs/monitoring/POST_P2_SPRINT3_MONITORING_REPORT.md)
- **Résolution P0 Gaps** : [docs/validation/P0_GAPS_RESOLUTION_STATUS.md](docs/validation/P0_GAPS_RESOLUTION_STATUS.md)
- **Capacités Mémoire** : [docs/MEMORY_CAPABILITIES.md](docs/MEMORY_CAPABILITIES.md)

### Métriques Prometheus
```promql
# Préférences extraites
memory_preferences_extracted_total

# Échecs extraction
memory_preferences_extraction_failures_total

# Confiance préférences
memory_preferences_confidence_count

# Durée extraction
memory_preferences_extraction_duration_seconds
```

---

## 💡 Conseils / Best Practices

### Debugging Tips

1. **Toujours logger les variables critiques** :
   ```python
   logger.debug(f"[PreferenceExtractor] Received user_sub={user_sub}, user_id={user_id}")
   ```

2. **Vérifier les None explicitement** :
   ```python
   if user_sub is not None:  # Mieux que if user_sub:
   ```

3. **Utiliser assertions en dev** :
   ```python
   assert user_identifier, "user_identifier must not be None"
   ```

### Testing Tips

1. **Tester tous les cas de fallback** :
   - `user_sub` seul ✅
   - `user_id` seul ✅
   - Les deux ✅
   - Aucun (échec gracieux) ✅

2. **Tester avec données production-like** :
   - Sessions authentifiées
   - Sessions anonymes
   - Threads sans owner

3. **Monitorer métriques Prometheus en continu** :
   ```bash
   watch -n 5 'curl -s http://localhost:8000/api/metrics | grep memory_preferences'
   ```

---

## 🎯 Résumé Exécutif (TL;DR)

**Problème** : PreferenceExtractor ne reçoit jamais `user_sub`/`user_id` → métriques à zéro

**Solution** :
1. Ajouter paramètre `user_id` dans `PreferenceExtractor.extract()`
2. Fallback : `user_identifier = user_sub or user_id`
3. Passer `user_id` depuis `analyzer.py`

**Tests** : 20/20 pytest + manuels locaux + QA production

**Déploiement** : Build → Push → Deploy → Smoke tests → Bascule trafic

**Validation** : Métriques > 0 + logs sans warnings + monitoring 30 min

**Durée Totale Estimée** : 1-2 heures

**Priorité** : 🔴 **CRITIQUE** - Blocage fonctionnalité P1

---

**Document créé le** : 2025-10-10 08:50 UTC
**Auteur** : Claude Code
**Statut** : ✅ **PRÊT POUR EXÉCUTION**
**Next Agent** : À exécuter immédiatement

---

**Bon courage ! 🚀 Le système compte sur toi pour rétablir l'extraction de préférences.**
