# Instructions Validation P1 — Pour l'Utilisateur

## État Actuel

✅ **Baseline métriques confirmée** (2025-10-10 02:24 UTC)
- Toutes les métriques P1 à `0.0` (attendu)
- Script QA opérationnel
- Rapport baseline : [qa-p1-baseline.json](qa-p1-baseline.json)

⚠️ **Credentials manquants** : Les variables d'environnement `EMERGENCE_SMOKE_EMAIL` et `EMERGENCE_SMOKE_PASSWORD` ne sont pas configurées.

## Option 1 : Validation Automatisée (RECOMMANDÉ)

### Étape 1 : Configurer les credentials

**Windows PowerShell** :
```powershell
$env:EMERGENCE_SMOKE_EMAIL = "votre-email@example.com"
$env:EMERGENCE_SMOKE_PASSWORD = "votre-mot-de-passe"
```

**Ou passer directement en paramètres** :
```bash
python scripts/qa/qa_p1_validation.py \
  --login-email "votre-email@example.com" \
  --login-password "votre-mot-de-passe"
```

### Étape 2 : Exécuter le script complet

```bash
cd C:\dev\emergenceV8
python scripts/qa/qa_p1_validation.py \
  --login-email "votre-email@example.com" \
  --login-password "votre-mot-de-passe" \
  --output qa-p1-report-full.json
```

**Ce que fait le script** :
1. ✅ Fetch baseline métriques P1
2. 🔐 Authentification avec vos credentials
3. 💬 Envoi de 6 messages test (préférences/intentions)
4. ⚙️ Déclenchement consolidation mémoire
5. ⏱️ Attente 30s pour traitement workers
6. 📊 Fetch métriques finales
7. ✅ Validation critères de succès
8. 📝 Génération rapport JSON

**Durée estimée** : 2-3 minutes

### Étape 3 : Vérifier les résultats

```bash
# Afficher le rapport
cat qa-p1-report-full.json

# Vérifier le statut
python -c "import json; r=json.load(open('qa-p1-report-full.json')); print('SUCCESS' if r['success'] else 'FAILED')"
```

**Résultats attendus** :
```json
{
  "success": true,
  "metrics_delta": {
    "extracted_preference": 3.0,  // >= 1 attendu
    "extracted_intent": 2.0,      // >= 1 attendu
    "average_confidence": 0.75,   // > 0.6 attendu
    "average_duration_seconds": 1.2  // < 2s attendu
  }
}
```

---

## Option 2 : Validation Manuelle via UI

### Étape 1 : Ouvrir l'application en production

URL : https://emergence-app-486095406755.europe-west1.run.app

### Étape 2 : Se connecter et créer une conversation

### Étape 3 : Envoyer les messages test

Copiez-collez ces messages **un par un** dans le chat :

```
Bonjour, je voudrais te parler de mes préférences de développement.
```

```
Je préfère utiliser Python pour mes projets backend, surtout avec FastAPI.
```

```
J'évite d'utiliser jQuery dans mes nouvelles applications web, c'est trop ancien.
```

```
Je vais apprendre TypeScript la semaine prochaine pour améliorer mon code frontend.
```

```
J'aime beaucoup travailler avec Claude Code pour automatiser mes tâches répétitives.
```

```
Je planifie de migrer mon projet principal vers Docker d'ici la fin du mois.
```

### Étape 4 : Attendre consolidation automatique

⏱️ Attendre **5 minutes** (consolidation automatique lors de la persistence de session).

**OU déclencher manuellement** (si vous avez accès) :
```bash
# Récupérer thread_id depuis l'UI (Network > WebSocket > handshake)
curl -X POST https://emergence-app-486095406755.europe-west1.run.app/api/memory/tend-garden \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <votre-token>" \
  -d '{"thread_id": "<thread_id>", "user_sub": "<user_sub>"}'
```

### Étape 5 : Vérifier les métriques

**Attendre 2-3 minutes** après consolidation, puis :

```bash
curl -s https://emergence-app-486095406755.europe-west1.run.app/api/metrics | grep "memory_preferences_extracted_total"
```

**Résultat attendu** :
```prometheus
memory_preferences_extracted_total{type="preference"} 3.0
memory_preferences_extracted_total{type="intent"} 2.0
memory_preferences_extracted_total{type="constraint"} 0.0
```

### Étape 6 : Vérifier les logs Workers

```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.revision_name~'p1memory' AND textPayload:'PreferenceExtractor'" \
  --project emergence-469005 \
  --limit 20 \
  --format "table(timestamp, textPayload)"
```

**Logs attendus** :
```
2025-10-10 XX:XX:XX  Worker 0 processing task: analyze
2025-10-10 XX:XX:XX  PreferenceExtractor: Extracted 5 candidates
2025-10-10 XX:XX:XX  PreferenceExtractor: Classified 5 records (3 preference, 2 intent)
2025-10-10 XX:XX:XX  Worker 0 completed analyze in 1.234s
```

---

## Critères de Succès P1

| Critère | Cible | Validation |
|---------|-------|------------|
| Métriques instrumentées | 5/5 | ✅ Confirmé (baseline) |
| Extraction déclenchée | ✅ | ⏳ À tester |
| Préférences capturées | ≥3 | ⏳ À tester |
| Intentions capturées | ≥2 | ⏳ À tester |
| Confiance médiane | >0.7 | ⏳ À tester |
| Durée extraction | <2s | ⏳ À tester |
| Filtrage lexical | ~70% | ⏳ À tester |
| Logs Workers | OK | ⏳ À tester |

---

## Troubleshooting

### Problème : Métriques restent à 0 après consolidation

**Solutions** :
1. Vérifier logs consolidation : chercher `MemoryGardener` ou `garden_thread`
2. Vérifier Workers actifs : chercher `MemoryTaskQueue started`
3. Vérifier extraction : chercher `PreferenceExtractor` dans les logs

### Problème : Authentication échoue

**Solutions** :
1. Vérifier que l'email/password sont corrects
2. Essayer de se connecter manuellement via l'UI d'abord
3. Utiliser `--dev-bypass` si environnement local

### Problème : WebSocket timeout

**Solutions** :
1. Augmenter timeout (network lent)
2. Envoyer messages plus lentement (attendre 5s entre chaque)
3. Utiliser validation manuelle via UI

---

## Fichiers de Référence

- **Guide validation complet** : [docs/validation/P1-VALIDATION-GUIDE.md](docs/validation/P1-VALIDATION-GUIDE.md)
- **Métriques Prometheus** : [docs/monitoring/prometheus-p1-metrics.md](docs/monitoring/prometheus-p1-metrics.md)
- **Script QA** : [scripts/qa/qa_p1_validation.py](scripts/qa/qa_p1_validation.py)
- **Baseline actuelle** : [qa-p1-baseline.json](qa-p1-baseline.json)

---

## Prochaines Étapes (Après Validation Réussie)

1. **Documenter résultats** : Créer rapport validation dans `docs/validation/`
2. **Archiver metrics** : Sauvegarder snapshot dans `docs/monitoring/snapshots/`
3. **QA complète** : Exécuter `qa_metrics_validation.py --trigger-memory`
4. **Commit résultats** : Git commit avec rapport validation
5. **Planifier P2** : Phase Réactivité Proactive (scoring pertinence)

---

**Dernière mise à jour** : 2025-10-10 02:24 UTC
**Baseline confirmée** : ✅ Toutes métriques à 0
**Statut** : ⏳ En attente credentials pour validation complète
