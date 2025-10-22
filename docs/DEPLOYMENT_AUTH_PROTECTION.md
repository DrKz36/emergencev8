# Protection de l'Authentification lors des Déploiements

**Date:** 2025-10-22
**Problème résolu:** Écrasement de la config d'auth par GitHub Actions

---

## 🚨 Problème Initial

Lors d'un déploiement via GitHub Actions, l'utilisateur ne pouvait plus se connecter avec son mot de passe. La config d'authentification (allowlist) avait été **écrasée**.

### Cause Root

Le workflow `.github/workflows/deploy.yml` utilisait :

```bash
gcloud run deploy emergence-app \
  --image gcr.io/emergence-469005/emergence-app:$SHA \
  --allow-unauthenticated \  # ← LE PROBLÈME
  --memory 2Gi \
  --cpu 2 \
  ...
```

**Résultat:** Chaque push sur `main` **réouvrait l'app en mode public** et **perdait toute la config d'auth** (allowlist, variables d'env AUTH_*, etc.).

---

## ✅ Solution Appliquée

### 1. Utiliser `stable-service.yaml` pour les déploiements

Au lieu de `gcloud run deploy` avec des flags CLI, on utilise maintenant `gcloud run services replace` avec le fichier YAML complet.

**Avantages:**
- ✅ Préserve **toutes** les variables d'environnement (auth, OAuth, secrets)
- ✅ Préserve la config IAM (pas de `--allow-unauthenticated` accidentel)
- ✅ Config déclarative versionnée dans Git
- ✅ Reproductible et auditable

### 2. Workflow Modifié

```yaml
# Deploy to Cloud Run using stable-service.yaml
- name: Deploy to Cloud Run
  run: |
    # Update the image in stable-service.yaml
    sed -i "s|image: .*|image: ${{ env.IMAGE_NAME }}:${{ github.sha }}|g" stable-service.yaml

    # Deploy using the YAML config (preserves allowlist & all env vars)
    gcloud run services replace stable-service.yaml \
      --region ${{ env.GCP_REGION }} \
      --quiet

    echo "✅ Deployed with stable-service.yaml (auth config preserved)"
```

### 3. Vérification Automatique

Ajout d'une step qui **vérifie** que l'auth est bien en place après déploiement :

```yaml
# Verify auth configuration
- name: Verify Auth Config
  run: |
    echo "🔐 Verifying authentication is enabled..."
    IAM_POLICY=$(gcloud run services get-iam-policy emergence-app \
      --region europe-west1 \
      --format json)

    # Check if allUsers is NOT in the bindings
    if echo "$IAM_POLICY" | grep -q "allUsers"; then
      echo "❌ WARNING: Service is public (allUsers found)"
      exit 1
    else
      echo "✅ Service is properly authenticated"
    fi
```

**Si `allUsers` est détecté → le workflow ÉCHOUE** et n'écrase pas la prod.

---

## 📋 Checklist de Déploiement Sûr

Avant de modifier un workflow de déploiement Cloud Run :

- [ ] **Utilise `stable-service.yaml`** (PAS de flags CLI `--allow-unauthenticated`)
- [ ] **Update uniquement l'image** dans le YAML (via `sed` ou script)
- [ ] **Vérifie IAM policy** après déploiement (step automatique)
- [ ] **Teste en local d'abord** avec `gcloud run services replace`
- [ ] **Ne jamais bypass l'auth** sauf pour endpoints publics explicites (`/health`, `/docs`)

---

## 🛠️ Commandes Utiles

### Vérifier la config IAM actuelle

```bash
gcloud run services get-iam-policy emergence-app \
  --region europe-west1 \
  --format yaml
```

### Re-déployer avec stable-service.yaml (manuel)

```bash
gcloud run services replace stable-service.yaml \
  --region europe-west1
```

### Vérifier les variables d'env d'une revision

```bash
gcloud run revisions describe emergence-app-REVISION \
  --region europe-west1 \
  --format yaml | grep -A 50 "env:"
```

---

## 🔐 Variables d'Auth Critiques (à ne jamais perdre)

Ces variables **doivent** être dans `stable-service.yaml` :

```yaml
env:
  - name: AUTH_DEV_MODE
    value: '0'  # Production = auth obligatoire
  - name: GOOGLE_ALLOWED_EMAILS
    value: gonzalefernando@gmail.com
  - name: GOOGLE_ALLOWLIST_MODE
    value: email
  - name: AUTH_ADMIN_EMAILS
    value: gonzalefernando@gmail.com
  - name: AUTH_ALLOWLIST_SEED
    valueFrom:
      secretKeyRef:
        name: AUTH_ALLOWLIST_SEED
        key: latest
```

**Si ces vars disparaissent → l'auth ne fonctionne plus.**

---

## 🚀 Prochaines Étapes

1. ✅ **Workflow fixé** - Utilise `stable-service.yaml`
2. ✅ **Vérification auto** - Détecte `allUsers` dans IAM policy
3. 🔄 **À faire:** Ajouter un script de rollback automatique si auth fails
4. 🔄 **À faire:** Monitorer les changements IAM dans ProdGuardian

---

## 📞 En Cas de Problème

**Si l'auth est pétée après un déploiement:**

1. **Rollback immédiat:**
   ```bash
   gcloud run services update-traffic emergence-app \
     --to-revisions PREVIOUS_REVISION=100 \
     --region europe-west1
   ```

2. **Re-déployer avec stable-service.yaml:**
   ```bash
   gcloud run services replace stable-service.yaml \
     --region europe-west1
   ```

3. **Vérifier IAM:**
   ```bash
   gcloud run services get-iam-policy emergence-app \
     --region europe-west1
   ```

4. **Si besoin, remove allUsers:**
   ```bash
   gcloud run services remove-iam-policy-binding emergence-app \
     --member="allUsers" \
     --role="roles/run.invoker" \
     --region europe-west1
   ```

---

**Bordel, plus jamais on perd l'auth sur un deploy automatique. 🔐**
