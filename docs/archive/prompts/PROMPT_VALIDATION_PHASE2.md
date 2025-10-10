# 🔬 SESSION SUIVANTE : VALIDATION PHASE 2 EN PRODUCTION

**Date** : 2025-10-08
**Contexte** : Phase 3 (Prometheus) déployée ✅ | Phase 2 code présent mais non testé
**Révision** : `emergence-app-00275-2jb`

---

## 🎯 MISSION

Valider les 3 optimisations Phase 2 en production :
1. ✅ **neo_analysis** (GPT-4o-mini) fonctionne
2. ✅ **Cache** enregistre HIT/MISS
3. ✅ **Métriques Prometheus** trackent les événements

**Durée estimée** : 15-30 min
**Complexité** : Faible (3 tâches indépendantes)

---

## 📚 CONTEXTE RAPIDE

### Déjà Fait
- Phase 2 : neo_analysis + cache in-memory + débats parallèles (déployé)
- Phase 3 : 13 métriques Prometheus exposées (`/api/metrics`)
- Infrastructure : Health OK, endpoint metrics OK
- Logs analysés : Aucune erreur, aucune requête utilisateur

### À Faire (Maintenant)
- Tester Phase 2 avec **vraies requêtes utilisateur**
- Vérifier logs Cloud Run
- Créer rapport validation

### Docs Disponibles
- `docs/deployments/2025-10-08-phase2-perf.md`
- `docs/deployments/2025-10-08-phase3-monitoring.md`
- `docs/deployments/2025-10-08-deploy-phase3.md`

---

## 🚀 TÂCHE 1 : TESTER NEO_ANALYSIS

### Setup
```bash
export SERVICE_URL="https://emergence-app-486095406755.europe-west1.run.app"
```

### Trouver une session
```bash
python -c "
import sqlite3
conn = sqlite3.connect('src/backend/data/db/emergence_v7.db')
rows = conn.execute('SELECT session_id, COUNT(*) FROM messages GROUP BY session_id ORDER BY COUNT(*) DESC LIMIT 3').fetchall()
for r in rows:
    print(f'{r[0]}: {r[1]} messages')
"
```

Note la session (ex: `aa327d90-3547-4396-a409-f565182db61a`)

### Analyser
```bash
export TEST_SESSION="[SESSION_ID]"

curl -X POST $SERVICE_URL/api/memory/analyze \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$TEST_SESSION\",\"force\":true}" \
  -w "\nTime: %{time_total}s\n"
```

**Attendu** : 200, 1-4s, JSON avec `"status":"completed"`

### Vérifier logs
```bash
gcloud logging read \
  "resource.labels.service_name=emergence-app AND textPayload=~'neo_analysis'" \
  --limit 5 --freshness 5m --format "value(textPayload)"
```

**Attendu** : `"Analyse réussie avec neo_analysis"`

### Vérifier métriques
```bash
curl -s $SERVICE_URL/api/metrics | grep memory_analysis_success
```

**Attendu** : `memory_analysis_success_total{provider="neo_analysis"} 1.0`

### ✅ Succès si :
- [ ] 200 avec résultats
- [ ] Log "neo_analysis" présent
- [ ] Métrique incrémentée
- [ ] Latence <5s

---

## 🚀 TÂCHE 2 : TESTER CACHE

### Premier appel (MISS)
```bash
time curl -X POST $SERVICE_URL/api/memory/analyze \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$TEST_SESSION\",\"force\":true}"
```

**Attendu** : 1-4s (calcul complet)

### Deuxième appel (HIT cache BDD)
```bash
time curl -X POST $SERVICE_URL/api/memory/analyze \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$TEST_SESSION\"}"
```

**Attendu** : <100ms, `"status":"skipped"`, `"reason":"already_analyzed"`

### Vérifier logs cache
```bash
gcloud logging read \
  "resource.labels.service_name=emergence-app AND textPayload=~'Cache'" \
  --limit 10 --freshness 5m --format "value(textPayload)"
```

**Attendu** : `"Cache SAVED"` ou `"already_analyzed"`

### Vérifier métriques
```bash
curl -s $SERVICE_URL/api/metrics | grep cache
```

**Attendu** : `memory_analysis_cache_size >= 1`

### ✅ Succès si :
- [ ] 1er appel : 1-4s
- [ ] 2e appel : <100ms
- [ ] Log cache présent
- [ ] Métrique `cache_size` >= 1

---

## 🚀 TÂCHE 3 : CRÉER RAPPORT

### Créer fichier
```bash
cat > docs/deployments/2025-10-08-validation-phase2.md << 'EOF'
# Validation Phase 2 Production

**Date** : 2025-10-08
**Session** : [SESSION_ID]
**Révision** : 00275-2jb

## Test 1 : neo_analysis
- Statut : [✅/❌]
- Latence : [X]s
- Logs : [Oui/Non]
- Métriques : [OK/KO]

## Test 2 : Cache
- Cache BDD : [✅/❌]
- Latence 2e appel : [X]ms
- Logs : [Oui/Non]
- Métriques : [OK/KO]

## Métriques Prometheus
```
[Coller output curl /api/metrics | grep memory]
```

## Conclusion
Phase 2 : [VALIDÉE/ÉCHOUÉE]
Prochaines étapes : [...]
EOF
```

### Commit
```bash
git add docs/deployments/2025-10-08-validation-phase2.md
git commit -m "docs: validation Phase 2 production - neo_analysis & cache"
git push
```

### ✅ Succès si :
- [ ] Rapport créé
- [ ] Documentation commitée
- [ ] Résultats documentés

---

## 📊 COMMANDES ULTRA-RAPIDES

```bash
# Setup
export SERVICE_URL="https://emergence-app-486095406755.europe-west1.run.app"

# Trouver session
python -c "import sqlite3; conn = sqlite3.connect('src/backend/data/db/emergence_v7.db'); print('\n'.join([f'{r[0]}: {r[1]}' for r in conn.execute('SELECT session_id, COUNT(*) FROM messages GROUP BY session_id ORDER BY COUNT(*) DESC LIMIT 3')]))"

# Test (remplacer SESSION_ID)
curl -X POST $SERVICE_URL/api/memory/analyze -H "Content-Type: application/json" -d '{"session_id":"SESSION_ID","force":true}' -w "\nTime: %{time_total}s\n"

# Logs
gcloud logging read "textPayload=~'neo_analysis'" --limit 5 --freshness 5m --format "value(textPayload)"

# Métriques
curl -s $SERVICE_URL/api/metrics | grep memory_analysis
```

---

## ✅ CHECKLIST

- [ ] Service URL configuré
- [ ] Session trouvée
- [ ] Tâche 1 : neo_analysis testé
- [ ] Tâche 2 : Cache testé
- [ ] Tâche 3 : Rapport créé
- [ ] Tout committé

---

**C'est parti !** 🚀
