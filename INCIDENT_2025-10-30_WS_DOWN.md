# 🚨 Incident 2025-10-30 - WebSocket Down (503 Constant Disconnections)

**Date:** 2025-10-30 09:14 CET
**Durée:** ONGOING (production down)
**Sévérité:** CRITICAL (service entièrement inaccessible)
**Agent:** Claude Code

---

## 🔍 Symptômes Rapportés

**Utilisateur :**
> "C'est toujours la merde en prod, ça déconnecte en permanence!!"

**Logs console frontend :**
```
WebSocket connection to 'wss://emergence-app.ch/ws/{uuid}?thread_id={thread_id}' failed
[WebSocket] error Event
[API Client] Thread {thread_id} introuvable (404)
```

**Tentatives de reconnexion** : Boucle infinie, échecs systématiques

---

## 🔬 Investigation (10 min)

### 1. Hypothèses initiales (FAUSSES)
- ❌ Config WebSocket backend cassée → NON, code OK
- ❌ Cloud Run timeout trop court → NON, 300s configuré
- ❌ Headers WebSocket upgrade bloqués → NON, pas de proxy/LB custom
- ❌ Bug dans le code frontend WebSocket → NON, config OK

### 2. Tests diagnostiques

**Test 1 : Endpoint WebSocket**
```bash
curl -I https://emergence-app-486095406755.europe-west1.run.app/ws
```
**Résultat** : Pas testé WS directement, mais...

**Test 2 : Health check backend**
```bash
curl https://emergence-app-486095406755.europe-west1.run.app/ready
```
**Résultat** :
```
HTTP/2 403
content-length: 13
content-type: text/plain

Access denied
```

**💥 CAUSE RACINE IDENTIFIÉE : IAM Policy révoquée**

---

## 🎯 Cause Racine (ROOT CAUSE)

**Problème** : Cloud Run service IAM policy **ne contient PAS** le binding `allUsers` → `roles/run.invoker`

**Impact** :
- ✅ Backend fonctionne correctement (container running)
- ✅ Code WebSocket OK (FastAPI route `/ws/{session_id}` active)
- ❌ **Toutes les requêtes HTTP/WS bloquées au niveau Cloud Run** (403 avant même d'atteindre l'app)

**Pourquoi ?**

Cloud Run **bloque TOUTES les requêtes** si aucune policy IAM ne permet l'accès.

Le workflow `.github/workflows/deploy.yml` ligne 75-79 est censé ajouter :
```yaml
gcloud run services add-iam-policy-binding emergence-app \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region europe-west1
```

**Mais soit :**
1. Le dernier déploiement a échoué sur cette étape
2. Quelqu'un a révoqué manuellement la policy après le deploy
3. Une autre action GCP a reset la policy

---

## ✅ Solution (2 options)

### Option 1 : Re-déployer (RECOMMANDÉ - fix auto)

**Via GitHub CLI :**
```bash
gh workflow run deploy.yml
```

**Via GitHub UI :**
1. https://github.com/DrKz36/emergencev8/actions
2. "Deploy to Cloud Run" → "Run workflow" → main → Run

**Ce que ça fait :**
- ✅ Rebuild image Docker
- ✅ Deploy sur Cloud Run
- ✅ **Réapplique policy IAM `allUsers`** (auto)
- ✅ Health check de validation

**Durée** : ~5-8 minutes

---

### Option 2 : Fix IAM direct (si gcloud installé)

**Si tu veux juste fix IAM sans rebuild :**

```bash
gcloud run services add-iam-policy-binding emergence-app \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region europe-west1 \
  --quiet
```

**Vérification :**
```bash
gcloud run services get-iam-policy emergence-app \
  --region europe-west1 \
  --format json | grep allUsers
```

**Attendu** : `"members": ["allUsers"]`

**Durée** : ~30 secondes

---

### Option 3 : Hotfix GitHub Actions (sans accès gcloud)

**Pour rétablir l'accès public directement depuis GitHub Actions :**

- Via CLI : `gh workflow run cloud-run-iam-restore.yml -f reason="Hotfix 403"`
- Via UI : Actions → "Restore Cloud Run IAM Access" → Run workflow

**Ce que ça fait :**
- ✅ Réapplique `allUsers → roles/run.invoker`
- ✅ Supprime `allAuthenticatedUsers` si présent
- ✅ Vérifie `/health` automatiquement

**Alternative locale :** `.\scripts\restore-cloud-run-iam.ps1 -Reason "Hotfix 403"`

**Durée** : ~1 minute

---

## 📊 Timeline de l'incident

| Heure | Event |
|-------|-------|
| ~08:00 | 🔴 Service devient inaccessible (403) - cause inconnue |
| 09:00 | 🚨 Utilisateur rapporte "ça déconnecte en permanence" |
| 09:14 | 🔍 Investigation Claude Code commence |
| 09:15 | ✅ Cause racine identifiée (IAM policy manquante) |
| 09:20 | 📝 Solution documentée, attente action utilisateur |

---

## 🛡️ Prévention Future

### Actions immédiates

1. **Activer monitoring IAM policy** - Alerte si `allUsers` révoqué
2. **Health check externe** - Ping `/health` depuis service externe (UptimeRobot)
3. **Log des changements IAM** - Audit trail GCP activé

### Actions long terme

1. **Pre-deploy validation** - Script qui vérifie IAM avant deploy
2. **Post-deploy verification** - Health check obligatoire dans workflow
3. **Documentation** - Ajouter section "403 troubleshooting" dans docs

---

## 🎓 Leçons Apprises

1. **Symptômes trompeurs** : "WebSocket fail" → vraie cause : IAM policy 403
2. **Test l'endpoint HTTP d'abord** : Avant de débugger WS, tester `/health`
3. **IAM policy fragile** : Peut être révoquée manuellement → besoin monitoring
4. **Workflow contient le fix** : Le workflow deploy.yml a déjà la solution (ligne 75-79)

---

## ✅ Checklist de résolution

- [x] Cause racine identifiée
- [x] Solution documentée
- [x] Instructions claires pour utilisateur
- [ ] Utilisateur déclenche re-deploy OU fix IAM
- [ ] Vérification que service répond 200 sur `/health`
- [ ] Vérification que WebSocket se connecte
- [ ] Mise à jour `AGENT_SYNC_CLAUDE.md` + `docs/passation_claude.md`
- [ ] Commit de cet incident report

---

**Status** : 🟡 EN ATTENTE ACTION UTILISATEUR

**Action requise** : Déclencher `gh workflow run deploy.yml` OU exécuter commande gcloud IAM

**ETA résolution** : 5-10 minutes après action utilisateur
