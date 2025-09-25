# Home Landing QA

## Objectif
- Vérifier l’écran d’accueil `HomeModule` (landing auth) avant l’accès au cockpit/chat.
- Couvrir le parcours `POST /api/auth/login` + stockage token + bootstrap App/WS.

## Parcours
1. Arriver sans token (`localStorage.emergence.id_token` vide). Le `body` expose la classe `home-active`, `#home-root` est visible.
2. Le formulaire email (placeholder `prenom@entreprise.com`) valide le format et affiche les erreurs inline.
3. Soumettre un email autorisé -> spinner bouton, appel `POST /api/auth/login` (payload `{ email, meta:{ locale, user_agent, timezone } }`).
4. Réponse 200 -> message succès, token stocké (`localStorage` + `sessionStorage`), événement `auth:login:success` émis.
5. `HomeModule` se démonte, `body.home-active` retiré, App `module:show('chat')` + connexion WS.
6. Logout (`auth:logout`) purge le token, remet `home-active` et réactive l’écoute `storage` (dev auth).

## États d’erreur
- **401** : message "Adresse non autorisée" + QA recorder `home_login_error` avec `status` 401.
- **429** : message rate-limit, bouton réactivé après retour.
- **423** : message session verrouillée.
- **Autres** : message générique (erreur serveur).

## QA rapide
- [ ] Sans token → le bandeau auth (badge) affiche "Connexion requise" et `home-active` est présent.
- [ ] Soumission email invalide → message inline, pas d’appel réseau.
- [ ] Email autorisé → message succès, App visible, WS se connecte.
- [ ] Logout → retour immédiat sur landing + nouvel enregistrement QA metrics (`home_login_submit`).
- [ ] Post-login avec backend HS : observer `AuthBanner` en `AUTH_MISSING` (double evenement) et la remise en place de `home-active`.
- [ ] Script `node scripts/qa/home-qa.mjs` capture l’écran home + console QA (`home-auth-required-YYYYMMDD.png`).

## Observations auth:missing (QA 2025-09-25)
- Scenario: apres un login 200, la reconnection WS a echoue (backend indisponible) et `eventBus` a emis `auth:missing`.
- Effets observes : `AuthBanner` bascule en `AUTH_MISSING` deux fois (raisons `missing_or_invalid_token`, `4401`) et le compteur `missingCount` augmente dans `window.__EMERGENCE_QA_METRICS__.authRequired`.
- Evidence: voir `docs/assets/ui/home-console-log-20250925.txt` lignes 37-45 pour les traces console generes pendant le run QA.
- Action QA : consigner toute repetition de `auth:missing` post-login (backend HS) et verifier que le HomeModule reactive `body.home-active` + listener `storage`.

## QA Metrics
`window.__EMERGENCE_QA_METRICS__.authRequired.events` enregistre :
- `home_login_submit`
- `home_login_success`
- `home_login_error`



