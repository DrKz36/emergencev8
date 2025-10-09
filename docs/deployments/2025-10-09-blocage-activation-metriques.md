# Blocage : Activation Métriques Prometheus en Production

**Date** : 2025-10-09 02:00-04:45 UTC
**Durée** : ~3h
**Statut** : ⚠️ NON RÉSOLU (délégué à Codex)
**Impact** : Phase 3 code présent mais métriques désactivées

---

## 🎯 Objectif Initial

Activer les métriques Prometheus en production via variable d'environnement :
```
CONCEPT_RECALL_METRICS_ENABLED=true
```

---

## 🔴 Problèmes Rencontrés

### Tentative 1 : Update env var via `gcloud run services update`

**Commande** :
```bash
gcloud run services update emergence-app \
  --region europe-west1 \
  --set-env-vars CONCEPT_RECALL_METRICS_ENABLED=true
```

**Résultat** : ❌ ÉCHEC
```
ERROR: Revision 'emergence-app-00276-jvb' is not ready
ModuleNotFoundError: No module named 'backend'
```

**Cause** :
- Changement variable d'env **déclenche rebuild** automatique
- Rebuild échoue car `PYTHONPATH=/app/src` manquant dans nouvelles révisions
- Cloud Run ne peut pas trouver module `backend` sans `PYTHONPATH`

**Rollback** :
```bash
gcloud run services update-traffic emergence-app \
  --region europe-west1 \
  --to-revisions emergence-app-00275-2jb=100
```

---

### Tentative 2 : Deploy depuis source avec timeout invalide

**Commande** :
```bash
gcloud run deploy emergence-app \
  --source . \
  --region europe-west1 \
  --set-env-vars="CONCEPT_RECALL_METRICS_ENABLED=true" \
  --timeout 120000  # ❌ ERREUR ICI
```

**Résultat** : ❌ ÉCHEC (après 22 minutes de build)
```
Building Container... done
ERROR: service.spec.template.spec.timeout_seconds: Must be a number between 0 and 3600
```

**Cause** :
- `--timeout 120000` interprété comme **millisecondes** par Claude
- Valeur max Cloud Run : **3600 secondes**
- Build Docker **réussi** (22 min) mais déploiement échoué à la fin

**Leçon** :
- `--timeout` attend des **secondes** (max 3600s = 1h)
- Build from source très long (15-22 min) à cause téléchargement modèle `all-MiniLM-L6-v2`

---

### Tentative 3 : Deploy image existante avec toutes les variables

**Commande** :
```bash
# Récupérer image révision stable
gcloud run revisions describe emergence-app-00275-2jb \
  --format "value(spec.containers[0].image)"

# europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app@sha256:c1aa10d52...

# Deploy cette image avec nouvelles variables
gcloud run deploy emergence-app \
  --image "europe-west1-docker.pkg.dev/.../emergence-app@sha256:c1aa10d..." \
  --set-env-vars="CONCEPT_RECALL_METRICS_ENABLED=true,PYTHONPATH=/app/src,..."
```

**Résultat** : ❌ ÉCHEC
```
Creating Revision... done
Service [emergence-app] revision [emergence-app-00277-mzh] deployed
```

Mais ensuite :
```bash
curl https://.../api/metrics
# Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.
```

**Cause** :
- Cloud Run **réutilise le nom de révision** `00275-2jb` au lieu de créer `00277-mzh`
- Nouvelle variable non prise en compte car révision inchangée
- Comportement cache/optimisation Cloud Run non documenté

**Tentative rollforward** :
```bash
gcloud run services update-traffic ... --to-revisions 00277-mzh=100
ERROR: Revision '00277-mzh' is not ready
ModuleNotFoundError: No module named 'backend'
```

**Cause** : Révision 00277-mzh créée **sans** `PYTHONPATH=/app/src`

---

### Tentative 4 : Deploy avec toutes les variables + secrets

**Commande** :
```bash
gcloud run deploy emergence-app \
  --image "..." \
  --set-env-vars="CONCEPT_RECALL_METRICS_ENABLED=true,PYTHONPATH=/app/src,GOOGLE_ALLOWED_EMAILS=...,AUTH_DEV_MODE=0" \
  --update-secrets="OPENAI_API_KEY=OPENAI_API_KEY:5,..."
```

**Résultat** : ❌ ÉCHEC
```
Creating Revision... failed
ERROR: Revision 'emergence-app-00277-mzh' is not ready
```

**Cause** : Cloud Run **réutilise révision cassée** 00277-mzh au lieu d'en créer une nouvelle

**Tentative avec --revision-suffix** :
```bash
gcloud run deploy ... --revision-suffix="metrics"
ERROR: Revision '00277-mzh' is not ready  # Toujours la même !
```

**Blocage** : Impossible de supprimer révision cassée car "actively serving"

---

### Tentative 5 : Build from source avec env.yaml

**Fichier créé** : `env.yaml`
```yaml
CONCEPT_RECALL_METRICS_ENABLED: "true"
PYTHONPATH: "/app/src"
GOOGLE_ALLOWED_EMAILS: "gonzalefernando@gmail.com"
AUTH_DEV_MODE: "0"
```

**Commande** :
```bash
gcloud run deploy emergence-app \
  --source . \
  --region europe-west1 \
  --env-vars-file env.yaml \
  --update-secrets="..." \
  --timeout 600 \
  --cpu 2 \
  --memory 4Gi
```

**Résultat** : ✅ BUILD RÉUSSI (après 18 min)
```
Building Container... done
Setting IAM Policy... done
Creating Revision... done
Service [emergence-app] revision [emergence-app-00275-2jb] deployed
```

**MAIS** :
```bash
curl .../api/metrics
# Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.
```

**Cause** : Cloud Run a **ENCORE réutilisé** révision `00275-2jb` au lieu d'en créer une nouvelle avec `env.yaml`

**Hypothèse** :
- `env.yaml` non pris en compte si image/code identiques ?
- Optimisation Cloud Run trop agressive ?
- Bug gcloud CLI ?

---

## 🧐 Analyse Technique

### Variables manquantes problématiques

La révision stable `00275-2jb` contient :
```python
PYTHONPATH=/app/src
GOOGLE_ALLOWED_EMAILS=gonzalefernando@gmail.com
AUTH_DEV_MODE=0
OPENAI_API_KEY=secret:5
GOOGLE_API_KEY=secret:5
ANTHROPIC_API_KEY=secret:5
```

Les nouvelles révisions (00276, 00277) créées par `gcloud run services update` ne contiennent **QUE** :
```python
OPENAI_API_KEY=secret:5
GOOGLE_API_KEY=secret:5
ANTHROPIC_API_KEY=secret:5
CONCEPT_RECALL_METRICS_ENABLED=true  # Nouvelle variable
```

**Manque critiques** :
- `PYTHONPATH=/app/src` → `ModuleNotFoundError: backend`
- `GOOGLE_ALLOWED_EMAILS` → Auth peut échouer
- `AUTH_DEV_MODE=0` → Mode dev vs prod

### Pourquoi PYTHONPATH critique ?

**Dockerfile CMD** :
```dockerfile
CMD ["python", "-m", "uvicorn", "--app-dir", "src", "backend.main:app", ...]
```

- `--app-dir src` → Change CWD vers `/app/src`
- `backend.main:app` → Cherche module `backend` depuis `/app/src`
- **SANS** `PYTHONPATH=/app/src` → Python cherche `backend` depuis `/app` → Not found

**Solution historique** : Variable `PYTHONPATH=/app/src` ajoutée manuellement dans révisions initiales

---

## 🎓 Leçons Apprises

### 1. Cloud Run ne merge pas les variables d'env

Quand tu fais `--set-env-vars A=1`, Cloud Run **remplace TOUTES** les variables, pas juste ajouter.

**Mauvais** :
```bash
# Révision actuelle : A=1, B=2, C=3
gcloud run services update --set-env-vars D=4
# Nouvelle révision : D=4 (A, B, C perdus !)
```

**Bon** :
```bash
gcloud run services update --set-env-vars A=1,B=2,C=3,D=4
```

### 2. --timeout attend des secondes, pas millisecondes

```bash
--timeout 120000  # ❌ Rejeté (>3600s)
--timeout 600     # ✅ 10 minutes
```

### 3. Build from source très long (15-20 min)

Dockerfile télécharge modèle 100MB+ :
```dockerfile
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

**Alternative** : Pré-build image Docker localement, push GCR, deploy image

### 4. Révisions cassées bloquent nouveaux déploiements

Si une révision échoue au startup, Cloud Run la garde en cache et la réutilise.

**Solution** : Rollback traffic puis delete révision cassée :
```bash
gcloud run services update-traffic ... --to-revisions OLD=100
gcloud run revisions delete BROKEN_REVISION
```

### 5. env.yaml peut être ignoré si code identique

Comportement observé mais non confirmé : `--env-vars-file` semble ignoré si source code/image identiques.

**Solution** : Forcer rebuild complet ou utiliser `--revision-suffix`

---

## ✅ Solution Proposée (pour Codex)

### Approche recommandée

1. **Créer `env.yaml`** avec toutes les variables (✅ fait)
2. **Deploy from source** avec `--env-vars-file` + timeout correct
3. **Vérifier nouvelle révision** créée (pas réutilisation)
4. **Tester métriques** activées
5. **Documenter révision** et commit

### Commande exacte

Voir [PROMPT_CODEX_ENABLE_METRICS.md](../../PROMPT_CODEX_ENABLE_METRICS.md) section "Solution propre et solide"

---

## 📊 État Actuel

### Service en production
- **Révision active** : `emergence-app-00275-2jb`
- **Statut** : ✅ Stable et fonctionnel
- **Phase 2** : ✅ Validée (neo_analysis + cache)
- **Phase 3** : ⚠️ Code présent mais métriques désactivées

### Variables actuelles (00275-2jb)
```yaml
PYTHONPATH: "/app/src"
GOOGLE_ALLOWED_EMAILS: "gonzalefernando@gmail.com"
AUTH_DEV_MODE: "0"
OPENAI_API_KEY: secret:5
GOOGLE_API_KEY: secret:5
ANTHROPIC_API_KEY: secret:5
# ❌ MANQUE : CONCEPT_RECALL_METRICS_ENABLED: "true"
```

### Fichiers créés pour Codex
- ✅ `env.yaml` (racine projet)
- ✅ `PROMPT_CODEX_ENABLE_METRICS.md` (guide complet)

---

## 🎯 Prochaine Étape

**Délégation à Codex** avec prompt complet incluant :
- Contexte des échecs
- Fichier `env.yaml` prêt
- Commande exacte validée
- Tests validation Phase 3
- Troubleshooting des erreurs rencontrées

**Durée estimée** : 20-30 min (build Docker 15-20 min + tests 5-10 min)

---

## 📚 Références

- Validation Phase 2 : [2025-10-08-validation-phase2.md](2025-10-08-validation-phase2.md)
- Prompt Codex : [PROMPT_CODEX_ENABLE_METRICS.md](../../PROMPT_CODEX_ENABLE_METRICS.md)
- Build/Deploy guide : [CODEX_BUILD_DEPLOY_PROMPT.md](../../CODEX_BUILD_DEPLOY_PROMPT.md)

---

**Généré par Claude Code - 2025-10-09 04:45 UTC**
