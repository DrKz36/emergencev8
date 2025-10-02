# Investigation préliminaire — Cloud Run revision `emergence-app-00261-z79`

## Contexte
Faute d'accès direct aux journaux Cloud Run depuis cet environnement, les éléments ci-dessous recensent :

* Les étapes recommandées pour collecter les logs de la révision mentionnée.
* Les contrôles côté application susceptibles d'expliquer les deux anomalies décrites (page de login non affichée et cockpit cassé).
* Des actions correctives ou de diagnostic supplémentaires à réaliser dès que les journaux seront disponibles.

## 1. Collecte des logs Cloud Run
1. Lister les révisions récentes afin de valider l'identifiant `emergence-app-00261-z79` :
   ```bash
   gcloud run services describe emergence-app \
     --region=europe-west1 \
     --format='value(status.trafficStatuses.revisionName,status.trafficStatuses.percent)' 
   ```
2. Récupérer les journaux de la révision :
   ```bash
   gcloud run services logs read emergence-app \
     --region=europe-west1 \
     --revision=emergence-app-00261-z79 \
     --limit=200 \
     --enable-structured-logs
   ```
3. Exporter les journaux applicatifs structurés vers un fichier pour partage :
   ```bash
   gcloud logging read \
     'resource.type="cloud_run_revision" AND resource.labels.service_name="emergence-app" AND resource.labels.revision_name="emergence-app-00261-z79"' \
     --limit=200 \
     --format=json > emergence-app-00261-z79-logs.json
   ```

## 2. Diagnostic — Redirection vers une session admin
### Observations côté frontend
* Le bootstrap du client applique un comportement « auto-auth » : si un token est présent dans le stockage local ou les cookies (`emergence.id_token`, `id_token`, etc.), l'application marque l'utilisateur comme connecté et lance immédiatement la connexion WebSocket.【F:src/frontend/main.js†L66-L120】【F:src/frontend/main.js†L292-L369】
* Lorsqu'aucun token n'est trouvé et que l'on est en local (`localhost`, `127.0.0.1`, `0.0.0.0`), une fenêtre d'authentification développeur est automatiquement ouverte pour faciliter les tests.【F:src/frontend/main.js†L93-L110】【F:src/frontend/main.js†L333-L364】

### Hypothèses
1. **Token persistant dans le navigateur** : un `id_token` appartenant à `dev@local` est peut-être stocké côté client ; l'app réutilise alors ce token au chargement.
2. **Mode développeur actif côté backend** : si la variable d'environnement `AUTH_DEV_MODE` est positionnée (`1`, `true`, `yes`), certains endpoints tolèrent des identifiants fournis via en-têtes (`X-User-ID`) ou WebSocket sans contrôle complet du JWT.【F:src/backend/shared/dependencies.py†L49-L112】
3. **Allowlist figée** : en production, l'allowlist s'appuie sur `GOOGLE_ALLOWED_EMAILS`/`GOOGLE_ALLOWED_HD`. Si ces variables ne sont pas mises à jour au déploiement, l'utilisateur `dev@local` reste autorisé alors que les nouveaux comptes sont refusés.【F:src/backend/shared/dependencies.py†L49-L112】

### Actions recommandées
* Purger les cookies / `localStorage` sur le domaine Cloud Run afin de valider que la page de login s'affiche en l'absence de token.
* Vérifier la configuration Cloud Run :
  ```bash
  gcloud run services describe emergence-app --region=europe-west1 --format='yaml(spec.template.spec.containers[0].env)'
  ```
  Confirmer que `AUTH_DEV_MODE` est désactivé et que `GOOGLE_ALLOWED_EMAILS` ou `GOOGLE_ALLOWED_HD` reflètent la liste autorisée.
* Après mise à jour de l'allowlist, redéployer pour s'assurer que le nouveau hash de configuration est pris en compte. Cloud Run ne propage pas toujours les modifications d'env vars sans nouvelle révision.

## 3. Diagnostic — Cockpit cassé
Sans les logs, deux pistes principales ressortent :

1. **Échec d'authentification des APIs « cockpit »** : toutes les routes `/api/*` (chat, documents, dashboard, etc.) appliquent la dépendance `enforce_allowlist`. Un JWT invalide ou non allowlisté provoque une réponse `401/403`, ce qui peut casser l'UI cockpit.【F:src/backend/api.py†L5-L22】【F:src/backend/shared/dependencies.py†L49-L112】
2. **Connexion WebSocket rompue** : le client cockpit dépend de la connexion WebSocket pour le flux chat et certains états. Les erreurs d'initialisation (token manquant, sous-protocole `jwt` absent, allowlist KO) conduisent à une fermeture immédiate du socket.【F:src/backend/shared/dependencies.py†L114-L205】【F:src/frontend/main.js†L292-L369】

### Étapes de validation
* Inspecter les réponses réseau (Chrome DevTools, onglet Network) pour identifier les statuts HTTP renvoyés lors du chargement du cockpit.
* Vérifier les journaux applicatifs (section 1) pour repérer des `HTTPException` ou des messages `WS: token absent`.
* Confirmer que le frontend reçoit bien un événement `EVENTS.APP_READY` et que le loader est retiré ; sinon, il faut vérifier que le module `App` n'échoue pas dans son constructeur.

## 4. Prochaines étapes après réception des logs
1. Rechercher les entrées contenant `allowlist` ou `HTTPException` dans les logs structurés :
   ```bash
   jq 'select(.jsonPayload.message? | test("allowlist"))' emergence-app-00261-z79-logs.json
   ```
2. Identifier les erreurs 4xx/5xx pour corréler avec les tentatives d'accès cockpit.
3. Partager les extraits pertinents afin de confirmer ou infirmer les hypothèses ci-dessus.

---
_NB : ce document sera mis à jour dès que les journaux détaillés seront disponibles._
