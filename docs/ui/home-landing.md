# Home Landing QA

## Objectif
- Verifier l''ecran d''accueil `HomeModule` (landing auth) avant l''acces au cockpit/chat.
- Couvrir le parcours `POST /api/auth/login` + stockage token + bootstrap App/WS.

## Parcours
1. Arriver sans token (`localStorage.emergence.id_token` vide). Le `body` expose la classe `home-active`, `#home-root` est visible.
2. Le formulaire email + mot de passe (placeholders `prenom@entreprise.com` et `Mot de passe (8 caracteres min.)`) valide les champs et affiche les erreurs inline.
3. Le hero recentre le logo anime + le badge `Beta 1.0` (classe `.home__version`) sans ruban highlights ni tagline additionnelle.
4. Le bouton `Recevoir l''acces` est centre, style metallise (classe `button-metal`), et se desactive pendant le login.
5. Soumettre un email autorise + mot de passe valide -> spinner sur le bouton, appel `POST /api/auth/login` (payload `{ email, password, meta:{ locale, user_agent, timezone } }`).
6. Reponse 200 -> message succes, token stocke (`localStorage` + `sessionStorage` + cookie `id_token`), evenement `auth:login:success` emis et cookie `emergence_session_id` mis a jour.
7. `HomeModule` se demonte, `body.home-active` retire, App `module:show('chat')` + connexion WS.
8. Logout (`auth:logout`) purge le token, remet `home-active`, reactive l''ecoute `storage` (dev auth) et l''API renvoie `Set-Cookie` vides (`id_token`, `emergence_session_id`) avec `SameSite=Lax`.

## Etats d''erreur
- **401** : message "Adresse non autorisee" pour email hors allowlist OU "Mot de passe invalide" pour un couple email/mot de passe incorrect. QA recorder `home_login_error` avec `status` 401.
- **429** : message rate-limit, bouton reactive apres retour.
- **423** : message session verrouillee.
- **400** : champs manquants ou mot de passe trop court (validation client).
- **Autres** : message generique (erreur serveur).

## QA rapide
- [ ] Le badge `Beta 1.0` est visible sous le titre, hero sans scroll supplementaire.
- [ ] Aucun overlay d''onboarding ne s''affiche (bandeau "1/3 Dialoguer" desactive).
- [ ] Le bouton `Recevoir l''acces` adopte bien le style metallique et se desactive pendant la requete.
- [ ] Soumission email invalide -> message inline, pas d''appel reseau.
- [ ] Email autorise -> message succes, App visible, WS se connecte.
- [ ] Logout -> retour immediat sur landing + nouvel enregistrement QA metrics (`home_login_submit`).
- [ ] Post-login backend HS : observer `AuthBanner` en `AUTH_MISSING` et la remise en place de `home-active`.
- [ ] Script `node scripts/qa/home-qa.mjs` capture l''ecran home + console QA (`home-auth-required-YYYYMMDD.png`).

## Observations auth:missing (QA 2025-09-25)
- Scenario: apres un login 200, la reconnection WS a echoue (backend indisponible) et `eventBus` a emis `auth:missing`.
- Effets observes : `AuthBanner` bascule en `AUTH_MISSING` deux fois (raisons `missing_or_invalid_token`, `4401`) et le compteur `missingCount` augmente dans `window.__EMERGENCE_QA_METRICS__.authRequired`.
- Evidence: voir `docs/assets/ui/home-console-log-20250925.txt` lignes 35-37 pour les traces console generes pendant le run QA.
- Metrics: la capture `home-authenticated-console-20250925.png` confirme `missingCount: 2` et la sequence restored -> missing -> missing -> restored.
- Action QA : consigner toute repetition de `auth:missing` post-login (backend HS) et verifier que le HomeModule reactive `body.home-active` + listener `storage`.

## QA Metrics
`window.__EMERGENCE_QA_METRICS__.authRequired.events` enregistre :
- `home_login_submit`
- `home_login_success`
- `home_login_error`

