# Production Health Check Script

## 📋 Description

Script PowerShell pour vérifier la santé de la production Emergence V8 (Cloud Run) avec authentification JWT.

Résout le problème: Production répond 403 sur `/ready` et autres endpoints car ils requièrent authentification.

## 🚀 Usage

### Prérequis

1. **JWT_SECRET** configuré dans `.env`:
   ```bash
   cp .env.example .env
   # Éditer .env et ajouter JWT_SECRET=<ton_secret_prod>
   ```

2. **Python 3 + PyJWT** installé:

   **Windows:**
   ```powershell
   # Utilise python standard (pas python3 WindowsApps)
   python -m pip install pyjwt
   # Ou si tu as py launcher
   py -m pip install pyjwt
   ```

   **Linux/Mac:**
   ```bash
   pip3 install pyjwt
   # Ou
   python3 -m pip install pyjwt
   ```

   **Note:** Le script détecte automatiquement l'OS et utilise la commande Python appropriée (`python` sur Windows, `python3` sur Linux/Mac).

   ```bash
   pip install pyjwt
   ```

3. **gcloud CLI** (optionnel, pour métriques et logs):
   ```bash
   gcloud auth login
   gcloud config set project emergence-469005
   ```

### Commandes

**Basic usage:**
```powershell
pwsh -File scripts/check-prod-health.ps1
```

**Verbose mode:**
```powershell
pwsh -File scripts/check-prod-health.ps1 -Verbose
```

**Custom output path:**
```powershell
pwsh -File scripts/check-prod-health.ps1 -OutputPath "reports/health-$(Get-Date -Format 'yyyyMMdd-HHmmss').md"
```

## 📊 Ce que le script fait

1. ✅ **Génère JWT** depuis .env (AUTH_JWT_SECRET ou JWT_SECRET)
2. ✅ **Healthcheck /ready** avec Bearer token
3. ✅ **Healthcheck /api/monitoring/health** (optionnel)
4. ⚠️  **Métriques Cloud Run** (si gcloud CLI dispo)
5. ⚠️  **Logs récents** (20 derniers, si gcloud CLI dispo)
6. ✅ **Rapport Markdown** généré dans `reports/prod-health-report.md`
7. ✅ **Exit code**: 0=OK, 1=FAIL

## 📝 Exemple Output

```
🏥 Production Health Check - emergence-app
============================================================
🔑 Génération JWT depuis .env...
   Secret trouvé (32 caractères)
   ✅ JWT généré avec succès

🔍 Healthchecks avec authentification...
   Testing /ready...
   ✅ /ready: OK (200)
   Testing /api/monitoring/health...
   ✅ /api/monitoring/health: OK

📊 Récupération métriques Cloud Run...
   ✅ Métriques Cloud Run récupérées

📜 Récupération logs récents...
   ✅ Logs récents récupérés

📝 Génération rapport markdown...
   ✅ Rapport sauvegardé: reports/prod-health-report.md

============================================================
✅ PRODUCTION HEALTHY
============================================================
```

## 🐛 Troubleshooting

### Erreur: JWT_SECRET introuvable

**Cause:** Pas de .env ou JWT_SECRET manquant

**Solution:**
```bash
# Créer .env depuis example
cp .env.example .env

# Ajouter le secret (demander à l'admin)
echo "JWT_SECRET=<secret_prod>" >> .env
```

### Erreur: gcloud CLI non configuré

**Cause:** gcloud pas installé ou pas authentifié

**Solution:**
```bash
# Installer gcloud
# https://cloud.google.com/sdk/docs/install

# Authentifier
gcloud auth login
gcloud config set project emergence-469005
```

### Erreur: PyJWT non installé

**Windows:**
```powershell
python -m pip install pyjwt
# Ou avec py launcher
py -m pip install pyjwt
```

**Linux/Mac:**
```bash
pip3 install pyjwt
# Ou
python3 -m pip install pyjwt
```

### Erreur: Python non trouvé (Windows)

**Cause:** `python3` WindowsApps sans PyJWT

**Solution:** Installe Python standard depuis python.org et ajoute au PATH
```powershell
# Télécharge depuis https://www.python.org/downloads/
# Puis installe PyJWT
python -m pip install pyjwt
**Solution:**
```bash
pip install pyjwt
```

## 🔐 Sécurité

⚠️ **IMPORTANT:** Ne jamais commit le fichier `.env` (déjà dans .gitignore).

Le JWT généré est **temporaire** (expire après 60 minutes) et utilisé uniquement pour healthchecks.

## 📚 Voir aussi

- **Workflow complet:** `docs/CLAUDE_CODE_WORKFLOW.md`
- **Tests complets:** `scripts/run-all-tests.ps1`
- **Déploiement:** `DEPLOYMENT_MANUAL.md`
