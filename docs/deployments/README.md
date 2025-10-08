# Historique des Déploiements Cloud Run

Ce dossier contient l'historique chronologique des déploiements de l'application Emergence sur Google Cloud Run.

## Structure des Documents

Chaque déploiement est documenté avec :
- **Révision Cloud Run** et tag image Docker
- **Commits Git** inclus dans le déploiement
- **Résumé des changements** (features, fixes, optimisations)
- **Tests de validation** effectués
- **Processus de déploiement** (commandes Docker/gcloud)
- **Métriques** et impact (si applicable)
- **Points de vérification** post-déploiement

## Déploiements Récents

| Date | Révision | Image Tag | Description |
|------|----------|-----------|-------------|
| 2025-10-08 | `emergence-app-00270-zs6` | `deploy-20251008-082149` | Cloud Run refresh (menu mobile confirmé) |
| 2025-10-08 | `emergence-app-00269-5qs` | `deploy-20251008-064424` | Cloud Run refresh (harmonisation UI cockpit/hymne) |
| 2025-10-06 | `emergence-app-00268-9s8` | `deploy-20251006-060538` | Agents & UI refresh (personnalités, module documentation, responsive) |
| 2025-10-05 | `emergence-app-00266-jc4` | `deploy-20251005-123837` | Corrections audit (13 fixes, score 87.5→95/100) |
| 2025-10-04 | `emergence-app-00265-xxx` | `deploy-20251004-205347` | Ajout système métriques + Settings module |

## Convention de Nommage

### Images Docker
Format : `deploy-YYYYMMDD-HHMMSS`
Exemple : `deploy-20251005-123837`

### Révisions Cloud Run
Format auto-généré : `emergence-app-00XXX-XXXXX`
Exemple : `emergence-app-00266-jc4`

### Documents
Format : `YYYY-MM-DD-description-courte.md`
Exemple : `2025-10-05-audit-fixes-deployment.md`

## Processus de Déploiement Standard

```bash
# 1. Validation locale
npm run build
pytest tests/backend/ -v

# 2. Commit + Push
git add -A
git commit -m "feat: description"
git push origin main

# 3. Build Docker
timestamp=$(date +%Y%m%d-%H%M%S)
docker build --platform linux/amd64 \
  -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp .

# 4. Push Registry
docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp

# 5. Deploy Cloud Run
gcloud run deploy emergence-app \
  --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:deploy-$timestamp \
  --platform managed \
  --region europe-west1 \
  --project emergence-469005 \
  --allow-unauthenticated

# 6. Documenter
# Créer docs/deployments/YYYY-MM-DD-description.md
# Mettre à jour docs/passation.md
# Mettre à jour AGENT_SYNC.md
```

## Rollback Procédure

En cas de problème avec une nouvelle révision :

```bash
# Lister les révisions
gcloud run revisions list --service emergence-app \
  --region europe-west1 --project emergence-469005

# Rollback vers révision précédente
gcloud run services update-traffic emergence-app \
  --to-revisions=emergence-app-00265-xxx=100 \
  --region europe-west1 --project emergence-469005
```

## Monitoring Post-Déploiement

### Logs Cloud Run
```bash
gcloud run services logs read emergence-app \
  --region europe-west1 --project emergence-469005 --limit 100
```

### Métriques
- **Prometheus** : https://emergence-app-486095406755.europe-west1.run.app/api/metrics
- **Health** : https://emergence-app-486095406755.europe-west1.run.app/health
- **Cloud Console** : https://console.cloud.google.com/run/detail/europe-west1/emergence-app

### Alertes à Surveiller
- Erreurs 5xx > 1% des requêtes
- Latence p95 > 2s
- Utilisation mémoire > 80%
- Cold start > 10s

## Checklist Pré-Déploiement

- [ ] Tests backend passent (`pytest`)
- [ ] Tests frontend passent (`npm run build`)
- [ ] Documentation mise à jour (si changements d'API)
- [ ] Variables d'environnement vérifiées (.env.production)
- [ ] Secrets Cloud Run à jour (si nécessaire)
- [ ] Passation complétée ([docs/passation.md](../passation.md))
- [ ] AGENT_SYNC.md mis à jour

## Checklist Post-Déploiement

- [ ] Révision déployée avec succès (100% trafic)
- [ ] Health check OK (`/health` returns 200)
- [ ] Logs sans erreurs critiques (5 premières minutes)
- [ ] Métriques Prometheus exposées (`/api/metrics`)
- [ ] Tests fumée endpoints critiques
- [ ] Document déploiement créé
- [ ] Passation mise à jour
- [ ] Notification équipe (si applicable)

---

**Projet** : Emergence V8
**Cloud Provider** : Google Cloud Platform
**Service** : Cloud Run (europe-west1)
**Registry** : Artifact Registry (europe-west1-docker.pkg.dev)
