# ✅ Résolution Complète du Déploiement en Production

## Statut: RÉSOLU

Le déploiement en production sur Cloud Run est maintenant **complètement fonctionnel**.

---

## Problèmes Résolus

### 1. ✅ Emails de réinitialisation de mot de passe
- **Problème**: Variables SMTP manquantes
- **Solution**: Ajout de toutes les variables EMAIL/SMTP dans `stable-service.yaml`
- **Test**: Email de réinitialisation envoyé avec succès ✅

### 2. ✅ Variables d'environnement manquantes (API Keys)
- **Problème**: Le service échouait au démarrage avec "GOOGLE_API_KEY or GEMINI_API_KEY must be provided"
- **Solution**: Ajout de toutes les API keys et configurations dans `stable-service.yaml`
- **Résultat**: Service démarre correctement ✅

### 3. ✅ Erreurs 500 sur les fichiers statiques (CSS/JS)
- **Problème**: Le liveness probe était configuré sur `/health/liveness` (endpoint inexistant)
- **Impact**: Les instances étaient arrêtées après 3 échecs, causant des erreurs 500
- **Solution**: Correction du liveness probe vers `/api/health` dans `stable-service.yaml`
- **Résultat**: Fichiers statiques servis correctement (200 OK) ✅

### 4. ✅ Module papaparse manquant
- **Problème**: `TypeError: Failed to resolve module specifier "papaparse"`
- **Impact**: Le module chat ne se chargeait pas
- **Solution**: Ajout de l'import map dans `index.html` pour:
  - `papaparse@5.4.1`
  - `jspdf@2.5.2`
  - `jspdf-autotable@3.8.3`
- **Résultat**: Module chat se charge sans erreurs ✅

---

## Configuration Finale

### Image Docker
```
europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app@sha256:340f3f39e6d99a37c5b15c2d4a4c8126f673c4acb0bafe83194b4ad2a439adf0
```

### Révision Active
```
emergence-app-00364-xxx (stable)
```

### URL de Production
```
https://emergence-app.ch
https://emergence-app-486095406755.europe-west1.run.app
```

---

## Fichiers Modifiés

### 1. `stable-service.yaml`
**Modifications apportées**:
- ✅ Correction du liveness probe: `/health/liveness` → `/api/health`
- ✅ Ajout de toutes les variables EMAIL/SMTP
- ✅ Ajout de toutes les API keys (OPENAI, GEMINI, ANTHROPIC, ELEVENLABS)
- ✅ Ajout de la configuration OAuth (CLIENT_ID, CLIENT_SECRET)
- ✅ Ajout de la configuration des agents IA (ANIMA, NEO, NEXUS)
- ✅ Ajout de la configuration Cache/Telemetry

**Variables configurées** (93 lignes):
```yaml
env:
  # Configuration système (lignes 36-47)
  - GOOGLE_CLOUD_PROJECT, AUTH_DEV_MODE, SESSION_*, CONCEPT_RECALL_METRICS_ENABLED

  # Email/SMTP (lignes 48-67)
  - EMAIL_ENABLED, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, etc.

  # API Keys (lignes 68-88)
  - OPENAI_API_KEY, GEMINI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY

  # OAuth (lignes 89-106)
  - GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_ALLOWED_EMAILS, etc.

  # AI Agents (lignes 108-120)
  - ANIMA_PROVIDER/MODEL, NEO_PROVIDER/MODEL, NEXUS_PROVIDER/MODEL

  # ElevenLabs Voice (lignes 121-127)
  - ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID

  # Telemetry & Cache (lignes 128-140)
  - ANONYMIZED_TELEMETRY, CHROMA_DISABLE_TELEMETRY, RAG_CACHE_*
```

### 2. `index.html`
**Modification**: Ajout de l'import map pour les modules ESM
```html
<script type="importmap">
  {
    "imports": {
      "react": "https://esm.sh/react@18.3.1",
      "react-dom/client": "https://esm.sh/react-dom@18.3.1/client",
      "papaparse": "https://esm.sh/papaparse@5.4.1",
      "jspdf": "https://esm.sh/jspdf@2.5.2",
      "jspdf-autotable": "https://esm.sh/jspdf-autotable@3.8.3"
    }
  }
</script>
```

### 3. `canary-service.yaml`
**Modification**: Ajout des mêmes variables EMAIL/SMTP que stable

---

## Commandes de Déploiement

### Déploiement standard (recommandé)
```bash
# 1. Construire l'image Docker
docker build -t europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:latest .

# 2. Pousser vers GCR
docker push europe-west1-docker.pkg.dev/emergence-469005/emergence-repo/emergence-app:latest

# 3. Déployer avec le YAML
gcloud run services replace stable-service.yaml --region=europe-west1 --project=emergence-469005
```

### Vérification post-déploiement
```bash
# 1. Vérifier que le service démarre
curl https://emergence-app.ch/api/health
# Réponse attendue: {"status":"ok","message":"Emergence Backend is running."}

# 2. Vérifier les fichiers statiques
curl -I https://emergence-app.ch/src/frontend/main.js
# Réponse attendue: HTTP/1.1 200 OK

# 3. Tester l'envoi d'email
curl -X POST https://emergence-app.ch/api/auth/request-password-reset \
  -H "Content-Type: application/json" \
  -d '{"email":"gonzalefernando@gmail.com"}'
# Réponse attendue: {"success":true,"message":"..."}

# 4. Vérifier les logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app" \
  --project=emergence-469005 --limit=10 --freshness=5m
```

---

## Leçons Apprises

### ✅ Bonnes Pratiques

1. **Utiliser `gcloud run services replace`** avec un YAML complet
   - Permet un contrôle total sur la configuration
   - Les health probes sont correctement configurés
   - Toutes les variables sont définies en un seul endroit

2. **Référencer les secrets via `secretKeyRef`**
   ```yaml
   - name: SMTP_PASSWORD
     valueFrom:
       secretKeyRef:
         name: SMTP_PASSWORD
         key: '3'
   ```

3. **Utiliser le digest SHA256 pour forcer le redéploiement**
   - Évite les problèmes de cache d'images
   - `image: europe-west1-docker.pkg.dev/.../app@sha256:xxx`

4. **Configurer correctement les health probes**
   ```yaml
   livenessProbe:
     httpGet:
       path: /api/health  # ← Endpoint qui existe vraiment
       port: 8080
   ```

### ❌ Pièges à Éviter

1. **NE PAS utiliser `gcloud run services update --set-env-vars`**
   - Écrase toutes les variables existantes
   - Peut causer des erreurs inattendues

2. **NE PAS oublier l'import map pour les modules ESM**
   - Les imports bare (comme `import Papa from 'papaparse'`) nécessitent un import map
   - Sans cela, le navigateur ne peut pas résoudre les modules

3. **NE PAS utiliser `:latest` seul en production**
   - Peut causer des problèmes de cache
   - Utiliser le digest SHA256 pour garantir la bonne version

---

## Architecture Finale

```
┌─────────────────────────────────────────────────┐
│         emergence-app.ch (Cloudflare)           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│     Google Cloud Run Service: emergence-app     │
│                                                  │
│  Revision: emergence-app-00364-xxx              │
│  Image: ...@sha256:340f3f39...                  │
│  CPU: 2, Memory: 4Gi                            │
│  Min Instances: 1, Max: 10                      │
│                                                  │
│  ✅ Health Probe: /api/health                   │
│  ✅ Email SMTP: Configured                      │
│  ✅ API Keys: All configured                    │
│  ✅ Static Files: Served correctly              │
│  ✅ Import Map: papaparse, jspdf configured     │
└─────────────────────────────────────────────────┘
```

---

## État des Services

| Service | Statut | URL | Notes |
|---------|--------|-----|-------|
| Backend API | ✅ Running | https://emergence-app.ch/api/health | 200 OK |
| Frontend | ✅ Running | https://emergence-app.ch | HTML/JS/CSS loaded |
| Email SMTP | ✅ Working | - | Password reset emails sent |
| Chat Module | ✅ Working | - | No papaparse errors |
| Static Files | ✅ Working | - | All 200 OK |

---

## Historique des Déploiements

| Date | Révision | Statut | Description |
|------|----------|--------|-------------|
| 2025-10-16 | emergence-app-00364 | ✅ Success | Configuration complète avec toutes les corrections |
| 2025-10-16 | emergence-app-00363 | ⚠️ Partial | Liveness probe corrigé, import map manquant |
| 2025-10-16 | emergence-app-00360 | ⚠️ Partial | Variables env ajoutées, liveness probe incorrect |
| 2025-10-16 | emergence-app-00359 | ✅ Success | Première version avec variables EMAIL |
| 2025-10-16 | emergence-app-00358 | ❌ Failed | Variables API keys manquantes |

---

## Support & Maintenance

### Mise à jour des secrets
```bash
# Exemple: Mettre à jour le mot de passe SMTP
echo -n "nouveau_mot_de_passe" | gcloud secrets versions add SMTP_PASSWORD --data-file=-

# Redéployer pour utiliser la nouvelle version
gcloud run services replace stable-service.yaml --region=europe-west1 --project=emergence-469005
```

### Monitoring
```bash
# Logs en temps réel
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=emergence-app" \
  --project=emergence-469005

# Métriques
gcloud run services describe emergence-app \
  --region=europe-west1 \
  --project=emergence-469005 \
  --format="value(status.conditions)"
```

---

**Date de résolution**: 2025-10-16
**Temps total**: ~2 heures
**Statut final**: ✅ Production stable et opérationnelle
