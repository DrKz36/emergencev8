# 🔧 GITHUB ACTIONS - CONFIGURATION GCP

**Guide de configuration des workflows CI/CD pour déploiement automatique Cloud Run**

**Version:** 1.0.0
**Date:** 2025-10-21

---

## 📋 Vue d'Ensemble

**Workflows créés:**
1. **tests.yml** - Tests automatiques + validation Guardian sur chaque push/PR
2. **deploy.yml** - Déploiement automatique Cloud Run sur push vers `main`

**Ce guide explique comment configurer le secret `GCP_SA_KEY` nécessaire pour les déploiements.**

---

## 🎯 Objectifs

- ✅ Créer un Service Account GCP pour GitHub Actions
- ✅ Donner les permissions nécessaires
- ✅ Générer une clé JSON
- ✅ Ajouter le secret dans GitHub
- ✅ Tester les workflows

---

## 🔑 ÉTAPE 1: Créer Service Account GCP

**Prérequis:** gcloud CLI installé et authentifié

```bash
# Authentifier
gcloud auth login

# Configurer le projet
gcloud config set project emergence-469005

# Créer le service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions - CI/CD" \
  --description="Service account for GitHub Actions CI/CD pipeline"
```

**Vérifier:**
```bash
gcloud iam service-accounts list | grep github-actions
```

---

## 🔐 ÉTAPE 2: Donner les Permissions

**Permissions nécessaires:**
- `roles/run.admin` - Déployer et gérer Cloud Run services
- `roles/storage.admin` - Push images Docker vers GCR
- `roles/iam.serviceAccountUser` - Utiliser service account

```bash
# Role Cloud Run Admin
gcloud projects add-iam-policy-binding emergence-469005 \
  --member="serviceAccount:github-actions@emergence-469005.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Role Storage Admin (pour GCR)
gcloud projects add-iam-policy-binding emergence-469005 \
  --member="serviceAccount:github-actions@emergence-469005.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Role Service Account User
gcloud projects add-iam-policy-binding emergence-469005 \
  --member="serviceAccount:github-actions@emergence-469005.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

**Vérifier les permissions:**
```bash
gcloud projects get-iam-policy emergence-469005 \
  --flatten="bindings[].members" \
  --filter="bindings.members:github-actions@emergence-469005.iam.gserviceaccount.com"
```

---

## 📄 ÉTAPE 3: Générer la Clé JSON

```bash
# Créer la clé JSON
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@emergence-469005.iam.gserviceaccount.com

# Vérifier que le fichier a été créé
ls -lh github-actions-key.json

# Afficher le contenu (pour copier)
cat github-actions-key.json
```

**⚠️ ATTENTION:**
- **Ne jamais commit ce fichier** dans Git
- Le supprimer après l'avoir copié dans GitHub
- Garder une copie sécurisée dans un password manager si besoin

---

## 🔐 ÉTAPE 4: Ajouter le Secret dans GitHub

### Via l'Interface GitHub

1. **Aller sur le dépôt GitHub:**
   ```
   https://github.com/DrKz36/emergencev8
   ```

2. **Naviguer vers Settings → Secrets and variables → Actions**

3. **Cliquer sur "New repository secret"**

4. **Remplir:**
   - **Name:** `GCP_SA_KEY`
   - **Secret:** [Copier TOUT le contenu de `github-actions-key.json`]

5. **Cliquer sur "Add secret"**

### Via GitHub CLI (Optionnel)

Si tu as `gh` CLI installé:

```bash
# Installer gh CLI (si pas déjà fait)
# Windows: winget install GitHub.cli
# macOS: brew install gh
# Linux: voir https://cli.github.com/

# Authentifier
gh auth login

# Ajouter le secret
gh secret set GCP_SA_KEY < github-actions-key.json
```

---

## 🧹 ÉTAPE 5: Nettoyer

**Supprimer la clé locale (important!):**

```bash
# Supprimer le fichier JSON local
rm github-actions-key.json

# OU sur Windows PowerShell
Remove-Item github-actions-key.json
```

**Vérifier que le fichier est supprimé:**
```bash
ls -la | grep github-actions-key.json  # Ne doit rien afficher
```

---

## ✅ ÉTAPE 6: Tester les Workflows

### Test 1: Workflow Tests (tests.yml)

**Créer une branche de test:**
```bash
git checkout -b test/github-actions-setup
echo "# Test GitHub Actions" >> README_TEST.md
git add README_TEST.md
git commit -m "test: vérifier workflow tests.yml"
git push origin test/github-actions-setup
```

**Vérifier:**
1. Aller sur GitHub → Actions
2. Le workflow "Tests & Guardian Validation" doit se lancer
3. Vérifier que les 3 jobs passent:
   - ✅ Backend Tests (Python 3.11)
   - ✅ Frontend Tests (Node 18)
   - ✅ Guardian Validation

**Artifacts:**
- Les rapports Guardian seront uploadés comme artifacts
- Visibles dans l'onglet "Artifacts" du workflow

---

### Test 2: Workflow Deploy (deploy.yml) - ATTENTION

**⚠️ CE WORKFLOW DÉPLOIE EN PRODUCTION !**

Le workflow `deploy.yml` se déclenche automatiquement sur chaque push vers `main`.

**Test sécurisé:**

```bash
# Option 1: Désactiver temporairement le workflow
# Aller sur GitHub → Actions → Deploy to Cloud Run → Disable workflow

# Option 2: Merger la branche de test vers main
git checkout main
git merge test/github-actions-setup
git push origin main

# Le workflow deploy.yml va se lancer automatiquement
```

**Vérifier:**
1. GitHub → Actions → "Deploy to Cloud Run"
2. Vérifier les étapes:
   - ✅ Build Docker image
   - ✅ Push to GCR
   - ✅ Deploy to Cloud Run
   - ✅ Health Check

3. Vérifier le déploiement:
   ```bash
   gcloud run services describe emergence-app --region=europe-west1
   ```

---

## 🐛 Troubleshooting

### Erreur: "Permission denied" lors du déploiement

**Cause:** Service account n'a pas les bonnes permissions

**Solution:**
```bash
# Vérifier les permissions actuelles
gcloud projects get-iam-policy emergence-469005 \
  --flatten="bindings[].members" \
  --filter="bindings.members:github-actions@emergence-469005.iam.gserviceaccount.com"

# Re-donner les permissions si nécessaire (voir ÉTAPE 2)
```

---

### Erreur: "Secret GCP_SA_KEY not found"

**Cause:** Le secret n'est pas configuré dans GitHub

**Solution:**
1. Vérifier que le secret existe: GitHub → Settings → Secrets and variables → Actions
2. Le nom doit être exactement `GCP_SA_KEY` (majuscules)
3. Re-créer le secret si nécessaire (voir ÉTAPE 4)

---

### Erreur: "Invalid JSON in GCP_SA_KEY"

**Cause:** Le secret contient des caractères invalides ou n'est pas du JSON complet

**Solution:**
1. Supprimer le secret actuel dans GitHub
2. Re-générer une nouvelle clé JSON (voir ÉTAPE 3)
3. Copier TOUT le contenu du fichier (y compris `{` et `}`)
4. Re-créer le secret dans GitHub

---

### Erreur: "Docker build failed"

**Cause:** Dockerfile manquant ou invalide

**Solution:**
```bash
# Vérifier que le Dockerfile existe
ls -la Dockerfile

# Tester le build localement
docker build -t test-emergence .
```

---

### Erreur: "Health check failed"

**Cause:** L'endpoint `/health` ne répond pas après déploiement

**Solution:**
1. Vérifier que l'endpoint `/health` existe dans le backend
2. Vérifier les logs Cloud Run:
   ```bash
   gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="emergence-app"' --limit=50
   ```
3. Augmenter le timeout du health check dans `deploy.yml` (ligne `sleep 10` → `sleep 30`)

---

### Workflow bloqué sur "Waiting for approval"

**Cause:** GitHub Actions peut nécessiter une approbation pour les workflows modifiant les secrets

**Solution:**
1. Aller sur GitHub → Actions → Workflow bloqué
2. Cliquer sur "Approve and run"

---

## 🔒 Sécurité

### Bonnes Pratiques

**✅ FAIRE:**
- Utiliser des service accounts dédiés (pas votre compte perso)
- Donner uniquement les permissions nécessaires (principe du moindre privilège)
- Stocker les clés JSON dans GitHub Secrets (jamais dans le code)
- Supprimer les clés JSON locales après usage
- Renouveler les clés régulièrement (tous les 90 jours)
- Utiliser des environnements GitHub pour prod/staging

**❌ NE PAS FAIRE:**
- Committer les clés JSON dans Git
- Utiliser le même service account pour dev et prod
- Donner `roles/owner` ou `roles/editor` (trop de permissions)
- Partager les clés JSON par email/Slack
- Laisser les clés JSON sur le disque local

---

### Rotation des Clés

**Renouveler tous les 90 jours:**

```bash
# 1. Créer une nouvelle clé
gcloud iam service-accounts keys create github-actions-key-new.json \
  --iam-account=github-actions@emergence-469005.iam.gserviceaccount.com

# 2. Mettre à jour le secret GitHub
gh secret set GCP_SA_KEY < github-actions-key-new.json

# 3. Supprimer l'ancienne clé (après avoir vérifié que la nouvelle fonctionne)
gcloud iam service-accounts keys list \
  --iam-account=github-actions@emergence-469005.iam.gserviceaccount.com

gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=github-actions@emergence-469005.iam.gserviceaccount.com

# 4. Supprimer le fichier local
rm github-actions-key-new.json
```

---

### Audit des Permissions

**Vérifier régulièrement:**

```bash
# Lister tous les service accounts
gcloud iam service-accounts list

# Voir les permissions d'un service account
gcloud projects get-iam-policy emergence-469005 \
  --flatten="bindings[].members" \
  --filter="bindings.members:github-actions@emergence-469005.iam.gserviceaccount.com"

# Voir les clés d'un service account
gcloud iam service-accounts keys list \
  --iam-account=github-actions@emergence-469005.iam.gserviceaccount.com
```

---

## 📚 Ressources

**Documentation:**
- [GitHub Actions - GCP Auth](https://github.com/google-github-actions/setup-gcloud)
- [GCP Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [Cloud Run Deployment](https://cloud.google.com/run/docs/deploying)
- [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

**Workflows:**
- [.github/workflows/tests.yml](../.github/workflows/tests.yml)
- [.github/workflows/deploy.yml](../.github/workflows/deploy.yml)

**Guides:**
- [docs/GUARDIAN_COMPLETE_GUIDE.md](GUARDIAN_COMPLETE_GUIDE.md)
- [DEPLOYMENT_SUCCESS.md](../DEPLOYMENT_SUCCESS.md)

---

## ✅ Checklist Finale

**Configuration GCP:**
- [ ] Service account `github-actions` créé
- [ ] Permissions `run.admin`, `storage.admin`, `iam.serviceAccountUser` données
- [ ] Clé JSON générée
- [ ] Clé JSON ajoutée dans GitHub secret `GCP_SA_KEY`
- [ ] Clé JSON locale supprimée

**Tests:**
- [ ] Workflow `tests.yml` testé sur une branche
- [ ] Les 3 jobs passent (backend, frontend, guardian)
- [ ] Artifacts Guardian uploadés
- [ ] Workflow `deploy.yml` testé (optionnel, déploie en prod)
- [ ] Déploiement Cloud Run réussi
- [ ] Health check passé

**Sécurité:**
- [ ] Pas de clé JSON dans le dépôt Git
- [ ] Secret `GCP_SA_KEY` configuré dans GitHub uniquement
- [ ] Permissions minimales données au service account
- [ ] Plan de rotation des clés (90 jours)

---

**Configuration terminée ! Les workflows GitHub Actions sont maintenant actifs.** 🚀

---

**Dernière mise à jour:** 2025-10-21
**Version:** 1.0.0
**Auteur:** Claude Code Agent
