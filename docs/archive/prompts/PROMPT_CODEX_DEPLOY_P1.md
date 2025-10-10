# 🚀 PROMPT CODEX : DÉPLOIEMENT PHASE P1 ENRICHISSEMENT MÉMOIRE

**Date** : 2025-10-09
**Agent destinataire** : Codex (cloud)
**Branche** : `main`
**Commit de référence** : `588c5dc` feat(P1): enrichissement mémoire - déportation async + extraction préférences + métriques

---

## 🎯 MISSION

Déployer la **Phase P1 enrichissement mémoire** en production Cloud Run.

**Phase P1 complétée** :
- ✅ **P1.1** - Déportation asynchrone (`MemoryTaskQueue` avec workers asyncio)
- ✅ **P1.2** - Extension extraction (préférences/intentions/contraintes via `PreferenceExtractor`)
- ✅ **P1.3** - Instrumentation métriques (8 métriques Prometheus : 5 préférences + 3 cache)

**Résultats locaux** :
- ✅ 15/15 tests mémoire passent
- ✅ ruff check : All checks passed
- ✅ Serveur local : Workers 0 & 1 démarrent/arrêtent proprement
- ✅ `/api/health` : OK
- ✅ `/api/metrics` : Prometheus exposé

---

## 📋 CHECKLIST PRÉ-DÉPLOIEMENT

### 1. Lecture obligatoire
```bash
# Ordre de lecture
1. AGENT_SYNC.md (section Claude Code - Session 2025-10-09 08:30-09:30)
2. docs/memory-roadmap.md (section P1 complétée)
3. AGENTS.md + CODEV_PROTOCOL.md
4. docs/passation.md (3 dernières entrées)
```

### 2. Synchronisation Git
```bash
git fetch --all --prune
git status
git log --oneline -10

# Vérifier commits attendus
# 4bde612 docs: sync Phase P1 enrichissement mémoire (AGENT_SYNC + roadmap)
# 588c5dc feat(P1): enrichissement mémoire - déportation async + extraction préférences + métriques
```

### 3. Validation environnement local
```bash
# Tests backend
python -m pytest tests/memory/ -v
# Attendu : 15/15 tests passent (7 existants + 8 nouveaux P1)

# Qualité code
python -m ruff check src/backend/features/memory/
# Attendu : All checks passed

python -m mypy src/backend/features/memory/ --ignore-missing-imports
# Attendu : Success

# Tests complets (optionnel)
python -m pytest
# Attendu : 154/154 tests passent (État Phase 3)

# Build frontend
npm run build
# Attendu : Build successful
```

---

## 🐳 BUILD & PUSH DOCKER IMAGE

### Étape 1 : Générer timestamp pour tag image
```bash
timestamp=$(date +%Y%m%d-%H%M%S)
echo "IMAGE_TAG=deploy-p1-$timestamp" > build_tag.txt
echo "Building image: deploy-p1-$timestamp"
```

### Étape 2 : Build image Docker (multi-platform linux/amd64)
```bash
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-p1-$timestamp \
  -f Dockerfile \
  .
```

**Durée attendue** : 10-15 minutes

**Points de vigilance** :
- Vérifier que le build utilise bien `--platform linux/amd64` (requis pour Cloud Run)
- Surveiller taille image finale (cible <2GB, actuel ~13GB avec optimisations possibles)
- Logs de build devraient montrer :
  - Installation dépendances Python (requirements.txt)
  - Copie fichiers backend/frontend
  - Embedding model téléchargé (~183MB)

### Étape 3 : Push image vers Artifact Registry
```bash
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-p1-$timestamp
```

**Durée attendue** : 5-10 minutes

**Vérification** :
```bash
gcloud artifacts docker images list \
  europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app \
  --project emergence-469005 \
  --include-tags \
  --filter="tags:deploy-p1-$timestamp"
```

---

## ☁️ DÉPLOIEMENT CLOUD RUN

### Étape 4 : Déployer nouvelle révision Cloud Run
```bash
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-p1-$timestamp \
  --project emergence-469005 \
  --region europe-west1 \
  --platform managed \
  --allow-unauthenticated \
  --revision-suffix p1-memory \
  --timeout 300 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10 \
  --set-env-vars "$(cat env.yaml | grep -v '^#' | grep -v '^$' | sed 's/: /=/' | paste -sd,)"
```

**Note env vars** : Si erreur sur `--set-env-vars`, utiliser `--env-vars-file env.yaml` à la place.

**Durée attendue** : 5-10 minutes

**Points de vigilance** :
- Nouvelle révision créée : `emergence-app-00XXX-p1-memory` (numéro incrémental)
- Trafic routé automatiquement vers nouvelle révision (ou manuellement si `--no-traffic`)
- Révision précédente conservée (`emergence-app-phase3b` actuellement 100% trafic)

### Étape 5 : Vérifier santé nouvelle révision
```bash
# Lister révisions
gcloud run revisions list \
  --service emergence-app \
  --region europe-west1 \
  --project emergence-469005

# Récupérer URL révision
REVISION_URL=$(gcloud run services describe emergence-app \
  --region europe-west1 \
  --project emergence-469005 \
  --format='value(status.url)')

echo "Production URL: $REVISION_URL"

# Health check
curl -s $REVISION_URL/api/health
# Attendu : {"status":"ok","message":"Emergence Backend is running."}

# Vérifier métriques Prometheus
curl -s $REVISION_URL/api/metrics | grep "memory_"
# Attendu :
# - memory_preferences_extracted_total (nouveau P1)
# - memory_preferences_confidence (nouveau P1)
# - memory_preferences_extraction_duration_seconds (nouveau P1)
# - memory_preferences_lexical_filtered_total (nouveau P1)
# - memory_preferences_llm_calls_total (nouveau P1)
# - memory_analysis_cache_hits_total (Phase 3 existant)
# - memory_analysis_cache_misses_total (Phase 3 existant)
# - memory_analysis_cache_size (Phase 3 existant)
```

### Étape 6 : Vérifier logs démarrage
```bash
# Logs récents (dernière minute)
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app AND resource.labels.revision_name~'p1-memory'" \
  --project emergence-469005 \
  --limit 50 \
  --format json

# Rechercher logs critiques
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app AND resource.labels.revision_name~'p1-memory' AND (textPayload:'MemoryTaskQueue' OR textPayload:'Worker')" \
  --project emergence-469005 \
  --limit 20
```

**Logs attendus** :
```
✅ MemoryTaskQueue started with 2 workers
✅ Worker 0 started
✅ Worker 1 started
✅ MemoryAnalyzer V3.4 initialise
✅ Application startup complete
```

**Erreurs à surveiller** :
- ❌ Timeout startup (>300s)
- ❌ Import errors sur `task_queue.py` ou `preference_extractor.py`
- ❌ Erreurs SQL (peu probable, aucune migration P1)
- ❌ Erreurs Prometheus (metrics déjà testées localement)

---

## 🔀 ROUTAGE TRAFIC (SI NÉCESSAIRE)

### Option A : Routage automatique (défaut)
Le déploiement route automatiquement 100% du trafic vers la nouvelle révision.

### Option B : Routage progressif (canary)
```bash
# Routage 10% nouvelle révision, 90% phase3b
gcloud run services update-traffic emergence-app \
  --to-revisions REVISION_P1_MEMORY=10,emergence-app-phase3b=90 \
  --region europe-west1 \
  --project emergence-469005

# Attendre 5-10 minutes, surveiller logs/métriques

# Si OK, basculer 100% nouvelle révision
gcloud run services update-traffic emergence-app \
  --to-latest \
  --region europe-west1 \
  --project emergence-469005
```

### Option C : Rollback (si problème)
```bash
# Revenir à phase3b
gcloud run services update-traffic emergence-app \
  --to-revisions emergence-app-phase3b=100 \
  --region europe-west1 \
  --project emergence-469005
```

---

## ✅ VALIDATION POST-DÉPLOIEMENT

### 1. Tests API critiques
```bash
# Health
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/health

# Metrics (valider 8 nouvelles métriques P1)
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/metrics | grep "memory_preferences"
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/metrics | grep "memory_analysis_cache"

# Sessions (basique)
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/sessions
```

### 2. Tests fonctionnels mémoire (optionnel mais recommandé)
```bash
# Déclencher consolidation mémoire pour incrémenter métriques
# Via UI : créer conversation avec préférences explicites
# Exemple : "Je préfère utiliser Python pour mes projets"

# Vérifier métriques après consolidation
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/metrics | grep "memory_preferences_extracted_total"
# Attendu : counter incrémenté (ex: memory_preferences_extracted_total{type="preference"} 1.0)
```

### 3. Smoke tests complets
```bash
# Si credentials disponibles
pwsh -File tests/run_all.ps1 \
  -BaseUrl https://emergence-app-486095406755.europe-west1.run.app \
  -SmokeEmail <email> \
  -SmokePassword <password>

# Attendu :
# ✅ Backend health check
# ✅ Upload document
# ✅ Memory clear
# ✅ Benchmarks
```

### 4. Vérifier révisions actives
```bash
gcloud run revisions list \
  --service emergence-app \
  --region europe-west1 \
  --project emergence-469005 \
  --format="table(metadata.name,status.conditions[0].status,spec.containers[0].image.split('/')[-1],metadata.creationTimestamp)"
```

**État attendu** :
```
REVISION              ACTIVE  IMAGE                    CREATED
emergence-app-00XXX-p1-memory  Yes  deploy-p1-20251009-HHMMSS  2025-10-09T...
emergence-app-phase3b         Yes  cockpit-phase3-20251009-...  2025-10-09T07:47
```

---

## 📝 DOCUMENTATION POST-DÉPLOIEMENT

### Créer fichier déploiement
Fichier : `docs/deployments/2025-10-09-deploy-p1-memory.md`

```markdown
# Déploiement Phase P1 - Enrichissement Mémoire

**Date** : 2025-10-09
**Agent** : Codex (cloud)
**Révision** : `emergence-app-00XXX-p1-memory`
**Image** : `deploy-p1-YYYYMMDD-HHMMSS`
**Commit** : `588c5dc` feat(P1): enrichissement mémoire

## Changements Phase P1

### P1.1 - Déportation asynchrone
- ✅ `MemoryTaskQueue` avec 2 workers asyncio
- ✅ `analyze_session_async()` non-bloquante
- ✅ Lifecycle startup/shutdown

### P1.2 - Extension extraction
- ✅ `PreferenceExtractor` modulaire
- ✅ Pipeline hybride (filtrage lexical + LLM + normalisation)
- ✅ Extraction préférences/intentions/contraintes

### P1.3 - Métriques Prometheus
- ✅ 5 nouvelles métriques préférences
- ✅ 3 métriques cache existantes (Phase 3)

## Résultats déploiement

### Build & Push
- **Image** : `deploy-p1-YYYYMMDD-HHMMSS`
- **Durée build** : XX min
- **Durée push** : XX min
- **Taille image** : XX GB

### Déploiement Cloud Run
- **Révision** : `emergence-app-00XXX-p1-memory`
- **Durée déploiement** : XX min
- **Routage trafic** : 100% nouvelle révision (ou canary X%)
- **Santé** : ✅ Healthy

### Validation
- ✅ `/api/health` : 200 OK
- ✅ `/api/metrics` : 8 métriques P1 exposées
- ✅ Logs démarrage : Workers 0 & 1 started
- ✅ Smoke tests : [si exécutés]

## Métriques post-déploiement

### Nouvelles métriques P1
```
# Préférences extraites
memory_preferences_extracted_total{type="preference"} X
memory_preferences_extracted_total{type="intent"} X
memory_preferences_extracted_total{type="constraint"} X

# Confiance (histogram)
memory_preferences_confidence_bucket{le="0.6"} X
memory_preferences_confidence_bucket{le="0.8"} X

# Durée extraction
memory_preferences_extraction_duration_seconds_count X
memory_preferences_extraction_duration_seconds_sum X

# Pipeline
memory_preferences_lexical_filtered_total X
memory_preferences_llm_calls_total X
```

### Métriques cache (Phase 3)
```
memory_analysis_cache_hits_total X
memory_analysis_cache_misses_total X
memory_analysis_cache_size X
```

## Logs représentatifs

[Copier logs startup clés]

## Problèmes rencontrés

[Si applicable]

## Rollback

[Si nécessaire, procédure utilisée]

## Next steps

1. Monitoring métriques P1 (24h)
2. Validation extraction préférences en usage réel
3. Préparer Phase P2 - Réactivité proactive
```

### Mettre à jour index déploiements
Fichier : `docs/deployments/README.md`

Ajouter entrée :
```markdown
### 2025-10-09 - Phase P1 Enrichissement Mémoire
- **Révision** : `emergence-app-00XXX-p1-memory`
- **Image** : `deploy-p1-YYYYMMDD-HHMMSS`
- **Commit** : `588c5dc`
- **Changements** : Déportation async + extraction préférences + 8 métriques
- **Doc** : [2025-10-09-deploy-p1-memory.md](2025-10-09-deploy-p1-memory.md)
- **Statut** : ✅ Deployed (100% trafic)
```

### Mettre à jour AGENT_SYNC.md
Section "Codex (cloud)" :

```markdown
- **Dernier sync** : 2025-10-09 XX:XX CEST (déploiement Phase P1 mémoire)
- **Statut** : Révision `emergence-app-00XXX-p1-memory` stable (P1.1 + P1.2 + P1.3)
- **Session 2025-10-09 (XX:XX-XX:XX)** :
  1. ✅ Lecture consignes (AGENT_SYNC, memory-roadmap, PROMPT_CODEX_DEPLOY_P1)
  2. ✅ Build image `deploy-p1-YYYYMMDD-HHMMSS` + push Artifact Registry
  3. ✅ Déploiement Cloud Run révision `emergence-app-00XXX-p1-memory`
  4. ✅ Validation : health, metrics (8 nouvelles P1), logs (Workers 0 & 1)
  5. ✅ Documentation : `docs/deployments/2025-10-09-deploy-p1-memory.md`
- **Tests / vérifications** :
  - ✅ `curl /api/health` → 200 OK
  - ✅ `curl /api/metrics | grep memory_preferences` → 5 nouvelles métriques
  - ✅ Logs startup : MemoryTaskQueue + Workers 0 & 1 démarrés
  - ✅ Smoke tests : [si exécutés]
- **Next** :
  1. Monitoring métriques P1 pendant 24h
  2. Valider extraction préférences en usage réel
  3. Préparer Phase P2 - Réactivité proactive
```

### Mettre à jour docs/passation.md
```markdown
## 2025-10-09 - Déploiement Phase P1 Enrichissement Mémoire (Codex)

**Travaux réalisés** :
1. Build image Docker `deploy-p1-YYYYMMDD-HHMMSS` (10-15 min)
2. Push Artifact Registry (5-10 min)
3. Déploiement Cloud Run révision `emergence-app-00XXX-p1-memory`
4. Validation santé + métriques + logs
5. Documentation complète

**Changements Phase P1** :
- P1.1 : Déportation asynchrone (`MemoryTaskQueue`, workers asyncio)
- P1.2 : Extension extraction (`PreferenceExtractor`, pipeline hybride)
- P1.3 : Instrumentation (8 métriques Prometheus)

**Résultats** :
- ✅ Révision healthy
- ✅ 8 nouvelles métriques P1 exposées
- ✅ Workers 0 & 1 démarrent correctement
- ✅ [Smoke tests : si exécutés]

**Blocages** : Aucun

**Next** : Monitoring métriques P1 + validation extraction préférences en usage réel
```

---

## 🔧 TROUBLESHOOTING

### Problème : Build Docker échoue
**Symptômes** : Erreur pendant `docker build`

**Solutions** :
1. Vérifier Dockerfile existe et est valide
2. Vérifier `requirements.txt` à jour
3. Augmenter mémoire Docker (Settings > Resources > Memory > 8GB)
4. Nettoyer cache : `docker builder prune -a`

### Problème : Push Artifact Registry timeout
**Symptômes** : Timeout après 15+ minutes

**Solutions** :
1. Vérifier authentification : `gcloud auth configure-docker europe-west1-docker.pkg.dev`
2. Vérifier connexion réseau
3. Réessayer : `docker push ...`

### Problème : Révision Cloud Run ne démarre pas
**Symptômes** : Révision reste "Deploying" ou passe "Failed"

**Solutions** :
1. Vérifier logs : `gcloud logging read ...`
2. Erreurs Python import : vérifier `requirements.txt` complet
3. Timeout startup : augmenter `--timeout` (actuellement 300s)
4. Mémoire insuffisante : augmenter `--memory` (actuellement 2Gi)

### Problème : Workers ne démarrent pas
**Symptômes** : Logs montrent erreurs `MemoryTaskQueue`

**Solutions** :
1. Vérifier import `task_queue.py` dans logs
2. Vérifier lifecycle startup dans `main.py`
3. Rollback si nécessaire : `gcloud run services update-traffic ... --to-revisions phase3b=100`

### Problème : Métriques P1 absentes
**Symptômes** : `/api/metrics` ne montre pas `memory_preferences_*`

**Solutions** :
1. Vérifier `prometheus_client` installé : `pip list | grep prometheus`
2. Vérifier import dans `preference_extractor.py`
3. Les métriques apparaissent après première extraction (déclencher consolidation mémoire)

---

## 📞 ESCALATION

**Si blocage** :
1. Documenter dans `docs/passation.md` (section "Blocages")
2. Rollback si nécessaire : `gcloud run services update-traffic ... --to-revisions phase3b=100`
3. Ping FG (architecte) pour résolution

**Principe** : Production d'abord - Ne pas laisser service dégradé

---

## ✅ CHECKLIST FINALE

Avant de considérer le déploiement terminé :

- [ ] Image Docker buildée et pushée
- [ ] Révision Cloud Run déployée
- [ ] `/api/health` retourne 200 OK
- [ ] `/api/metrics` expose 8 métriques P1
- [ ] Logs montrent Workers 0 & 1 démarrés
- [ ] Trafic routé vers nouvelle révision
- [ ] Documentation créée (`docs/deployments/2025-10-09-deploy-p1-memory.md`)
- [ ] `docs/deployments/README.md` mis à jour
- [ ] `AGENT_SYNC.md` mis à jour (section Codex)
- [ ] `docs/passation.md` mis à jour (nouvelle entrée)
- [ ] Smoke tests exécutés (si credentials disponibles)

---

**Durée totale estimée** : 30-45 minutes (build 10-15min + push 5-10min + deploy 5-10min + validation 10min)

**Bon courage Codex ! 🚀**

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
Session : 2025-10-09 08:30-09:30
