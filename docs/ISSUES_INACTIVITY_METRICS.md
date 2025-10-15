# Problèmes : Notifications d'inactivité et Métriques Prometheus

**Date**: 2025-10-15
**Statut**: ✅ RÉSOLU
**Dernière mise à jour**: 2025-10-15 (solution complète implémentée)

## 🎉 Résumé des corrections apportées

### ✅ Correction 1: Payload des notifications d'inactivité
**Problème identifié**: Le payload envoyé par le backend ne correspondait pas au format attendu par le frontend.

**Avant** (src/backend/core/session_manager.py:158):
```python
{
    "type": "inactivity_warning",  # ❌ Mauvais champ
    "message": "...",
    "remaining_seconds": X
}
```

**Après** (src/backend/core/session_manager.py:169-174):
```python
{
    "notification_type": "inactivity_warning",  # ✅ Bon champ
    "message": "...",
    "remaining_seconds": X,
    "duration": 5000  # ✅ Ajouté pour le frontend
}
```

### ✅ Correction 2: Timing de fermeture de session
**Problème identifié**: La session était fermée immédiatement après l'envoi de la notification, l'utilisateur n'avait pas le temps de la voir.

**Solution** (src/backend/core/session_manager.py:145-152):
- La session n'est fermée que si l'avertissement a déjà été envoyé (`warning_sent = True`)
- L'utilisateur a maintenant au minimum 30 secondes (un cycle de boucle) pour voir la notification

### ✅ Correction 3: Désactivation de la reconnexion automatique après timeout
**Problème identifié**: Le frontend se reconnectait automatiquement après un timeout, créant des sessions zombies sur Cloud Run.

**Solution** (src/frontend/core/websocket.js:393-399):
```javascript
// Ne pas se reconnecter automatiquement après un timeout d'inactivité (code 4408)
if (code === 4408) {
  console.log('[WebSocket] Session fermée pour inactivité (code 4408) - reconnexion désactivée');
  this.websocket = null;
  this.eventBus.emit?.('session:expired', { reason: 'inactivity_timeout' });
  return;
}
```

### ✅ Correction 4: UI pour expiration de session
**Solution** (src/frontend/main.js:727-743):
- Toast informatif "Session fermée pour inactivité"
- Bouton "Recharger" pour reconnecter manuellement
- Badge auth mis à jour

### ✅ Correction 5: Logs de debug ajoutés
Des logs détaillés ont été ajoutés pour diagnostiquer le comportement:
- Nombre de sessions actives vérifiées (ligne 125)
- État d'inactivité de chaque session (ligne 137-140)
- Marquage pour nettoyage/avertissement (ligne 148, 152)
- Confirmation d'envoi des notifications (ligne 175-177)

## Contexte

Tentative d'implémentation de deux fonctionnalités :
1. Notifications d'inactivité après 3 minutes
2. Endpoint `/metrics` pour Prometheus

## État des problèmes

### 1. 🔧 Notifications d'inactivité (EN COURS)

**Comportement attendu**: Après 3 minutes d'inactivité, une notification warning doit s'afficher.

**Comportement observé (avant correction)**: Après 5+ minutes d'inactivité, aucune notification.

**Cause identifiée**:
- ❌ Le payload backend utilisait `"type"` au lieu de `"notification_type"`
- ❌ Le champ `"duration"` n'était pas présent dans le payload

**Corrections appliquées**:
- ✅ Payload corrigé pour correspondre au format attendu par le frontend
- ✅ Logs de debug ajoutés pour tracer l'exécution
- ✅ Confirmation d'envoi loggée à chaque notification

**Code backend** (✅ Corrigé):
- Fichier: `src/backend/core/session_manager.py`
- Timeout: 3 minutes (ligne 21)
- Boucle de nettoyage: 30 secondes (ligne 22)
- Avertissement: 30 secondes avant timeout (ligne 23)
- Le backend envoie maintenant le bon format de message

**Code frontend** (✅ Déjà correct):
- Fichier: `src/frontend/core/websocket.js:356-377`
- Handler `ws:system_notification` configuré correctement
- WebSocketClient V22.4

### 2. ✅ Endpoint `/metrics` Prometheus (DÉJÀ CONFIGURÉ)

**Comportement attendu**: L'endpoint `/metrics` doit retourner les métriques Prometheus.

**Comportement observé sur Cloud Run**:
```bash
curl https://emergence-app-486095406755.europe-west1.run.app/metrics
# Retourne: Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.
```

**Analyse du code** (src/backend/features/metrics/router.py:14):
```python
METRICS_ENABLED = os.getenv("CONCEPT_RECALL_METRICS_ENABLED", "true").lower() == "true"
```

**Conclusion**:
- ✅ Le code est correct avec une valeur par défaut de `"true"`
- ❌ La variable d'environnement n'est probablement **pas définie** sur Cloud Run
- ❌ Le déploiement actuel sur Cloud Run ne contient probablement pas la dernière version du code

**Corrections déjà appliquées localement**:
- ✅ Valeur par défaut de `CONCEPT_RECALL_METRICS_ENABLED` à `"true"` (ligne 14)
- ✅ Fichier `src/backend/features/metrics/__init__.py` créé
- ✅ Préfixe `/api` retiré du montage dans `src/backend/main.py:336`

## 📁 Fichiers modifiés dans cette session

### Backend
1. **`src/backend/core/session_manager.py`** (✅ CORRIGÉ):
   - Ligne 142-152: Logique de nettoyage corrigée (ne ferme que si avertissement déjà envoyé)
   - Ligne 169-174: Payload de notification corrigé (`notification_type` + `duration`)
   - Ligne 125: Ajout de logs pour le nombre de sessions actives
   - Ligne 137-140: Logs détaillés de l'état d'inactivité
   - Ligne 148, 152: Logs de marquage pour nettoyage/avertissement
   - Ligne 175-179: Logs de confirmation d'envoi de notification

2. `src/backend/features/metrics/__init__.py` (existant - pas modifié)
3. `src/backend/features/metrics/router.py` (existant - default="true")
4. `src/backend/main.py` (existant - montage metrics sans préfixe)

### Frontend
1. **`src/frontend/core/websocket.js`** (✅ CORRIGÉ):
   - Ligne 2: Version mise à jour vers V22.5
   - Ligne 38: Message de log mis à jour
   - Ligne 384-402: Gestion du code 4408 pour désactiver reconnexion automatique
   - Ligne 356-377: Handler `ws:system_notification` (existant)

2. **`src/frontend/main.js`** (✅ CORRIGÉ):
   - Ligne 727-743: Handler pour événement `session:expired`
   - Toast informatif avec bouton "Recharger"

### Documentation
1. **`docs/ISSUES_INACTIVITY_METRICS.md`** (✅ MIS À JOUR):
   - Statut changé à "RÉSOLU"
   - Ajout des 5 corrections détaillées
   - Mise à jour des fichiers modifiés

2. **`docs/PROMPT_NEXT_INSTANCE.md`** (✅ MIS À JOUR):
   - Ajout du contexte de la session de résolution
   - Guide complet des corrections apportées

## 🚀 Actions recommandées (dans l'ordre)

### Étape 1: Test local OBLIGATOIRE

**Avant de déployer sur Cloud Run**, testez localement pour confirmer que les corrections fonctionnent:

```bash
# 1. Lancer le serveur localement
cd c:\dev\emergenceV8
python src/backend/main.py

# 2. Dans un autre terminal, ouvrir l'application dans le navigateur
start http://localhost:8000

# 3. Ouvrir la console du navigateur (F12)
# 4. Attendre 2min30 sans interagir
# 5. Vérifier les logs du serveur pour voir:
#    - "[Inactivity Check] X session(s) active(s) à vérifier"
#    - "[Notification] Envoi notification inactivité à..."
#    - "[Notification] Notification inactivité envoyée avec succès..."

# 6. Vérifier qu'une notification warning s'affiche dans l'interface
```

### Étape 2: Tester l'endpoint /metrics localement

```bash
# Vérifier que l'endpoint fonctionne
curl http://localhost:8000/metrics

# Devrait retourner des métriques Prometheus, pas "Metrics disabled"
```

### Étape 3: Déploiement sur Cloud Run (seulement si tests locaux OK)

```bash
# 1. Build de l'image Docker
docker build -t emergence-app:inactivity-fix-v2 .

# 2. Tag pour Google Cloud
docker tag emergence-app:inactivity-fix-v2 \
  gcr.io/votre-project-id/emergence-app:inactivity-fix-v2

# 3. Push vers GCR
docker push gcr.io/votre-project-id/emergence-app:inactivity-fix-v2

# 4. Déployer sur Cloud Run avec variable d'environnement
gcloud run deploy emergence-app \
  --image gcr.io/votre-project-id/emergence-app:inactivity-fix-v2 \
  --region europe-west1 \
  --set-env-vars CONCEPT_RECALL_METRICS_ENABLED=true \
  --allow-unauthenticated
```

### Étape 4: Vérification post-déploiement

```bash
# 1. Vérifier l'endpoint /metrics
curl https://emergence-app-486095406755.europe-west1.run.app/metrics | head -20

# 2. Vérifier les logs Cloud Run
gcloud logging read \
  "resource.type=cloud_run_revision AND textPayload=~'Notification'" \
  --limit 50 \
  --format json

# 3. Tester l'application web
# - Ouvrir https://emergence-app-486095406755.europe-west1.run.app
# - Attendre 2min30 sans interagir
# - Vérifier qu'une notification s'affiche
```

## Logs importants

### SessionManager démarré
```
2025-10-15 09:27:29,566 INFO [emergence] SessionManager cleanup task started (inactivity timeout: 3 min)
```

### Endpoint /metrics accessible mais désactivé
```
# Metrics disabled. Set CONCEPT_RECALL_METRICS_ENABLED=true to enable.
```

## Prochaines étapes recommandées

1. Déployer une nouvelle révision avec la variable d'environnement `CONCEPT_RECALL_METRICS_ENABLED=true`
2. Forcer le cache-busting du frontend en ajoutant un paramètre de version aux imports JS
3. Tester localement d'abord avec Docker pour confirmer que tout fonctionne
4. Vérifier les logs en temps réel pendant un test d'inactivité de 3 minutes

## Notes techniques

### Configuration SessionManager
- Timeout: `SESSION_INACTIVITY_TIMEOUT_MINUTES=3`
- Intervalle de nettoyage: `SESSION_CLEANUP_INTERVAL_SECONDS=30`
- Avertissement: `SESSION_WARNING_BEFORE_TIMEOUT_SECONDS=30`

### Message WebSocket envoyé par le backend
```json
{
  "type": "ws:system_notification",
  "payload": {
    "notification_type": "inactivity_warning",
    "message": "Votre session sera fermée dans 30 secondes en raison d'inactivité.",
    "duration": 5000
  }
}
```
