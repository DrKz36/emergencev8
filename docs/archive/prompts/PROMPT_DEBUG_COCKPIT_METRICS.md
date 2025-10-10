# Prompt Debug Cockpit - Validation Métriques Phase 3

## Contexte

**Session précédente terminée** : Métriques coûts enrichies Phase 3 + Dette technique résolue

**État actuel** :
- ✅ Backend : Métriques coûts enrichies implémentées (TimelineService, queries, endpoints API)
- ✅ Frontend : cockpit-metrics.js mis à jour pour utiliser nouvelles métriques API
- ✅ Migration BDD : colonnes user_id/session_id dans table costs + indexes
- ✅ Tests : 154/154 passants, Mypy 0 erreur, Ruff clean
- ⚠️ **Cockpit à valider en local** : métriques réelles + graphiques timeline

**Derniers commits** :
```
1cbdac9 feat: frontend cockpit - intégration métriques enrichies + docs session
625b295 feat: métriques coûts enrichies + timeline dashboard (Phase 3)
604503d docs: sync session stabilisation tests + qualité code
c26c2b2 chore: correction dette technique mypy - 21 erreurs résolues
9467394 fix: tests intégration API memory archives (5 échecs résolus) + qualité code
```

**Fichiers clés modifiés** :
- `src/backend/features/dashboard/timeline_service.py` (nouveau, 261 lignes)
- `src/backend/core/database/queries.py` (+175 lignes) : get_messages_by_period, get_tokens_summary
- `src/backend/features/dashboard/router.py` (+123 lignes) : endpoints /timeline/*
- `src/frontend/features/cockpit/cockpit-metrics.js` : intégration métriques API

---

## 🎯 Tâches Prioritaires - Debug & Validation Cockpit

### 1. Démarrer backend local et valider endpoints API
**Priorité** : HAUTE (pré-requis pour frontend)

**Actions** :
1. Démarrer serveur backend local : `cd src/backend && uvicorn main:app --reload`
2. Tester endpoint métriques : `curl http://localhost:8000/api/dashboard/costs/summary`
3. Vérifier structure JSON retournée contient :
   - `messages` : `{total, today, week, month}`
   - `tokens` : `{total, input, output, avgPerMessage}`
   - `costs` : valeurs existantes
4. Tester nouveaux endpoints timeline :
   ```bash
   curl "http://localhost:8000/api/dashboard/timeline/activity?period=30d"
   curl "http://localhost:8000/api/dashboard/timeline/costs?period=30d"
   curl "http://localhost:8000/api/dashboard/timeline/tokens?period=30d"
   ```
5. Valider codes HTTP 200 + structures JSON attendues

**Résultat attendu** :
- ✅ Endpoints retournent 200 OK
- ✅ Données messages/tokens présentes dans `/costs/summary`
- ✅ Timelines retournent arrays avec {date, ...}

---

### 2. Valider affichage cockpit frontend
**Priorité** : HAUTE (UX critique)

**Actions** :
1. Démarrer frontend : `npm run dev` (si dev server séparé) OU ouvrir `http://localhost:8000` dans navigateur
2. Naviguer vers module **Cockpit** via menu
3. Vérifier affichage des 4 cartes métriques :
   - **Messages** : valeurs réelles (total, today, week, month) au lieu de 0
   - **Tokens** : valeurs calculées (total, input, output, avgPerMessage) au lieu de TODO
   - **Coûts** : valeurs existantes + avgPerMessage calculé
   - **Monitoring** : documents/sessions count
4. Ouvrir DevTools Console (F12) et vérifier :
   - Pas d'erreurs JavaScript
   - Requêtes API `/api/dashboard/costs/summary` réussies
   - Log `[CockpitMetrics] Métriques chargées:` affiche données correctes

**Résultat attendu** :
- ✅ Cartes messages/tokens affichent valeurs réelles
- ✅ Pas d'erreurs console
- ✅ Animations/transitions fluides

---

### 3. Tester graphiques timeline (si implémentés frontend)
**Priorité** : MOYENNE (feature bonus Phase 3)

**Actions** :
1. Vérifier si section graphiques existe dans cockpit HTML
2. Si présente, tester sélection période (7d, 30d, 90d, 1y)
3. Valider affichage graphiques :
   - Timeline activité (messages + threads par jour)
   - Timeline coûts (€ par jour)
   - Timeline tokens (total par jour)
4. Vérifier interactions : zoom, tooltip hover, légendes

**Si graphiques non implémentés frontend** :
- Documenter que API timeline est prête mais UI à implémenter
- Passer à tâche 4

---

### 4. Tester filtrage par session (isolation métriques)
**Priorité** : HAUTE (architecture multi-session)

**Actions** :
1. Dans DevTools Console, exécuter :
   ```javascript
   // Tester avec session_id spécifique
   fetch('/api/dashboard/costs/summary', {
     headers: {'X-Session-Id': 'test-session-123'}
   }).then(r => r.json()).then(console.log)
   ```
2. Vérifier que résultats sont filtrés (ou vides si session inexistante)
3. Tester endpoint dédié :
   ```javascript
   fetch('/api/dashboard/costs/summary/session/test-session-123')
     .then(r => r.json()).then(console.log)
   ```
4. Comparer résultats avec/sans X-Session-Id :
   - Sans header : agrégation toutes sessions user
   - Avec header : filtrage strict session

**Résultat attendu** :
- ✅ Filtrage session fonctionne
- ✅ Métriques isolées par session

---

### 5. Valider calculs métriques (cohérence données)
**Priorité** : HAUTE (fiabilité)

**Actions** :
1. Comparer métriques affichées avec données brutes BDD :
   ```bash
   # Messages count
   sqlite3 data/emergence.db "SELECT COUNT(*) FROM messages WHERE date(created_at) = date('now', 'localtime')"

   # Tokens sum
   sqlite3 data/emergence.db "SELECT SUM(input_tokens), SUM(output_tokens) FROM costs"

   # Costs sum
   sqlite3 data/emergence.db "SELECT SUM(total_cost) FROM costs WHERE date(timestamp) = date('now', 'localtime')"
   ```
2. Vérifier cohérence :
   - Total messages API = COUNT(*) messages BDD
   - Total tokens API = SUM(input+output) costs BDD
   - Moyenne par message = total_cost / message_count
3. Si écarts, investiguer requêtes SQL dans `queries.py`

**Résultat attendu** :
- ✅ Données API = données BDD (±1% marge erreur)
- ✅ Calculs moyennes corrects

---

## 🐛 Problèmes Connus & Solutions

### Issue 1 : Colonnes user_id/session_id manquantes dans costs
**Symptôme** : Erreur SQL "no such column: costs.user_id"

**Solution** :
- Vérifier migration appliquée : `sqlite3 data/emergence.db "PRAGMA table_info(costs);"`
- Si colonnes manquantes, appliquer : `sqlite3 data/emergence.db < src/backend/core/database/migrations/20251009_enrich_costs.sql`

### Issue 2 : TimelineService non trouvé (503 Service Unavailable)
**Symptôme** : Erreur "Timeline service unavailable"

**Solution** :
- Vérifier import dans `containers.py` ligne 359
- Redémarrer serveur backend pour recharger DI container

### Issue 3 : Métriques affichent 0 malgré données existantes
**Symptôme** : Cards cockpit affichent `0` partout

**Solution** :
1. Vérifier réponse API dans DevTools Network : structure JSON correcte ?
2. Si `messages: {}` vide, vérifier table `messages` a des données
3. Si `tokens: {}` vide, vérifier table `costs` a `input_tokens`/`output_tokens` non NULL

---

## 📋 Checklist Validation Finale

```markdown
- [ ] Backend démarre sans erreur (uvicorn)
- [ ] Endpoint /api/dashboard/costs/summary retourne 200 + données messages/tokens
- [ ] Endpoints /timeline/* retournent 200 + arrays de données
- [ ] Cockpit affiche métriques réelles (pas de 0 ou TODO)
- [ ] Console browser sans erreurs JavaScript
- [ ] Filtrage par session_id fonctionne (header X-Session-Id)
- [ ] Calculs cohérents avec données BDD (sqlite queries)
- [ ] Tests pytest passent : `python -m pytest tests/test_memory_archives.py -v`
- [ ] Qualité code OK : `mypy src && ruff check`
```

---

## 🚀 Prochaines Étapes (Post-Validation)

**Dès que validation cockpit OK** :

1. **Commit final coordination mémoire** :
   - Attendre commit implémentation mémoire de l'autre session
   - Vérifier pas de conflits git
   - Commit global si nécessaire

2. **Build & Deploy Cloud Run** :
   ```bash
   # Build image
   timestamp=$(date +%Y%m%d-%H%M%S)
   docker build --platform linux/amd64 \
     -t europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:metrics-phase3-$timestamp .

   # Push registry
   docker push europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:metrics-phase3-$timestamp

   # Deploy nouvelle révision
   gcloud run deploy emergence-app \
     --image europe-west1-docker.pkg.dev/emergence-469005/app/emergence-app:metrics-phase3-$timestamp \
     --project emergence-469005 \
     --region europe-west1 \
     --platform managed \
     --allow-unauthenticated \
     --revision-suffix metrics-phase3
   ```

3. **Validation production** :
   - Tester endpoints prod : `https://emergence-app-47nct44nma-ew.a.run.app/api/dashboard/costs/summary`
   - Vérifier métriques Prometheus : `/api/metrics`
   - Valider graphiques Grafana (si configurés)

4. **Documentation** :
   - Mettre à jour `AGENT_SYNC.md` avec résultats validation
   - Créer entrée `docs/passation.md` : session debug cockpit
   - Screenshot cockpit avec métriques réelles

---

## 💡 Commandes Rapides

```bash
# Démarrer backend
cd src/backend && uvicorn main:app --reload

# Tester API (PowerShell)
Invoke-WebRequest http://localhost:8000/api/dashboard/costs/summary | Select-Object -ExpandProperty Content | ConvertFrom-Json

# Tester API (bash/curl)
curl http://localhost:8000/api/dashboard/costs/summary | jq

# Vérifier BDD
sqlite3 data/emergence.db "SELECT COUNT(*) as total_messages FROM messages"
sqlite3 data/emergence.db "SELECT SUM(total_cost) as total_costs FROM costs"

# Tests
python -m pytest tests/test_memory_archives.py -v
mypy src --ignore-missing-imports
ruff check

# Logs backend (si erreurs)
tail -f logs/backend.log  # Si logs fichier configurés
```

---

## 🎯 Objectif Session

**Valider cockpit métriques Phase 3 en local, corriger bugs éventuels, puis coordonner deploy production avec implémentation mémoire.**

**Success criteria** :
- ✅ Cockpit affiche métriques réelles (messages, tokens, coûts avec moyennes)
- ✅ API timeline fonctionnelle (même si UI graphiques pas finalisée)
- ✅ Isolation par session opérationnelle
- ✅ Aucune erreur backend/frontend
- ✅ Prêt pour deploy production

---

**Note importante** : Ne pas toucher au code déployé en prod (révision `metrics001` stable). Focus sur validation locale puis deploy nouvelle révision coordonnée.
