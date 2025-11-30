# Module d'Authentification - ÉMERGENCE V8

## Vue d'ensemble

Le module d'authentification d'ÉMERGENCE V8 gère l'authentification des utilisateurs, la gestion des sessions, les permissions basées sur les rôles, et la réinitialisation de mot de passe par email.

**Version:** V2.0 (avec support email)
**Dernière mise à jour:** Novembre 2025 (beta-3.3.39)

## Architecture

### Composants principaux

```
src/backend/features/auth/
├── service.py           # AuthService - logique métier
├── email_service.py     # EmailService - envoi d'emails
├── router.py           # Endpoints FastAPI
├── models.py           # Modèles Pydantic
└── rate_limiter.py     # Rate limiting
```

## Fonctionnalités

### 1. Authentification et Sessions

#### Login avec email/mot de passe
```python
POST /api/auth/login
{
  "email": "user@example.com",
  "password": "********"
}
```

**Réponse:**
```json
{
  "token": "eyJ...",
  "expires_at": "2025-11-14T...",
  "role": "admin",
  "session_id": "uuid",
  "user_id": "hash",
  "email": "user@example.com",
  "password_must_reset": false
}
```

#### Gestion des rôles

Le système supporte 3 rôles principaux :
- **admin** : Accès complet + gestion des utilisateurs
- **member** : Accès standard aux fonctionnalités
- **guest** : Accès limité (lecture seule)

**Logique importante pour les admins:**
- Les comptes admin ne sont **jamais** forcés à réinitialiser leur mot de passe
- `password_must_reset` est automatiquement défini à `0` pour les admins
- Bootstrap SQL au démarrage : `UPDATE auth_allowlist SET password_must_reset = 0 WHERE role = 'admin'`

#### Résilience des sessions (octobre 2025)

`AuthService.verify_token()` restaure désormais une session manquante lorsque l'entrée correspondante a disparu de `auth_sessions` (cas observé lors de bascules entre instances Cloud Run). Le flux :

- re-crée la session à partir des claims JWT (métadonnées `restored_from_claims=true`) ;
- journalise `Auth session %s restored from token claims (email=%s)` pour audit ;
- respecte les garde-fous existants : une session révoquée/expirée ou un compte allowlist révoqué renvoie toujours `401`.

Ce fallback élimine les `401 Session inconnue` tout en préservant la sécurité.

#### Dev Login (mode développement)
```python
POST /api/auth/dev/login
{
  "email": "dev@local"  # Optional
}
```

Auto-crée ou réactive un compte admin pour le développement local.

### 2. Réinitialisation de mot de passe

#### Demander un lien de réinitialisation
```python
POST /api/auth/request-password-reset
{
  "email": "user@example.com"
}
```

**Comportement:**
- Crée un token sécurisé valide 1 heure
- Envoie un email avec lien de réinitialisation
- Retourne toujours succès (prévention énumération d'emails)
- Si email service désactivé, log le token en console

#### Réinitialiser avec token
```python
POST /api/auth/reset-password
{
  "token": "secure_token_abc123",
  "new_password": "NewSecurePassword123!"
}
```

**Actions automatiques:**
- Valide le token (non expiré, non utilisé)
- Hash le nouveau mot de passe avec bcrypt
- Met à jour `password_must_reset = 0`
- Révoque toutes les sessions existantes
- Marque le token comme utilisé

#### Changer son mot de passe
```python
POST /api/auth/change-password
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

Nécessite authentification. Vérifie l'ancien mot de passe avant mise à jour.

### 3. Service Email (EmailService)

Le `EmailService` gère l'envoi d'emails via SMTP (Gmail par défaut).

#### Configuration (variables d'environnement)

```bash
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

**Note importante pour Gmail:** Utilisez un "mot de passe d'application" généré sur [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

#### Types d'emails

**Email de réinitialisation de mot de passe:**
```python
await email_service.send_password_reset_email(
    to_email="user@example.com",
    reset_token="secure_token",
    base_url="https://your-domain.com"
)
```

**Email d'invitation Beta:**
```python
await email_service.send_beta_invitation_email(
    to_email="beta-tester@example.com",
    base_url="https://emergence-app.ch"
)
```

Contient :
- Lien d'accès à la plateforme
- Dates du programme beta
- 8 phases de test détaillées
- Lien vers le formulaire de rapport

#### Templates email

Les emails sont envoyés avec :
- **Version HTML** : Design moderne avec dégradés, logo, sections
- **Version texte** : Fallback pour clients email basiques
- **UTF-8** : Support complet des caractères français

### 4. Allowlist Management (Admin)

#### Lister les utilisateurs autorisés
```python
GET /api/admin/allowlist?status=active&search=user&page=1&page_size=20
```

#### Ajouter/modifier un utilisateur
```python
POST /api/admin/allowlist
{
  "email": "newuser@example.com",
  "role": "member",
  "note": "Beta tester",
  "generate_password": true
}
```

**Options:**
- `generate_password`: Génère un mot de passe sécurisé automatiquement
- `password`: Définir un mot de passe manuellement (si `generate_password=false`)

**Comportement pour les admins:**
- Si `role = "admin"` → `password_must_reset = 0` automatiquement
- Si `role = "member"` → `password_must_reset = 1` (doit réinitialiser au premier login)

#### Supprimer un utilisateur (révocation)
```python
DELETE /api/admin/allowlist/{email}
```

Révoque l'utilisateur et toutes ses sessions actives.

#### Seed automatique (Cloud Run)
- **Objectif** : conserver l'allowlist après recréation de la base SQLite sur Cloud Run.
- **Variables supportées** :
  - `AUTH_ALLOWLIST_SEED` : JSON (liste d'objets `{email, role, note?, password}`).
  - `AUTH_ALLOWLIST_SEED_PATH` / `AUTH_ALLOWLIST_SEED_FILE` : chemin vers un fichier JSON (pratique avec Secret Manager).
- **Bootstrap** : `AuthService.bootstrap()` lit le payload au démarrage, hash les mots de passe, applique `password_must_reset=0` pour les admins et journalise les entrées ignorées.
- **Génération du payload** :
  ```bash
  python scripts/generate_allowlist_seed.py --output allowlist_seed.json
  python scripts/generate_allowlist_seed.py --push AUTH_ALLOWLIST_SEED --create-secret
  ```
- **Important** : publier le secret **avant** chaque déploiement (sinon tous les logins renvoient `401`).

### 5. Sessions Management

#### Obtenir les sessions actives
```python
GET /api/admin/sessions?status_filter=active
```

#### Révoquer une session
```python
POST /api/admin/sessions/revoke
{
  "session_id": "uuid"
}
```

Ferme immédiatement la connexion WebSocket associée.

### 6. Rate Limiting

Protection contre le brute force :
- **5 tentatives** par email/IP dans une fenêtre de **15 minutes**
- Sliding window algorithm
- Réponse HTTP 429 avec header `Retry-After`

Reset automatique après login réussi.

## Base de données

### Tables

#### `auth_allowlist`
```sql
CREATE TABLE auth_allowlist (
    email TEXT PRIMARY KEY,
    role TEXT NOT NULL DEFAULT 'member',
    note TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT,
    revoked_at TEXT,
    revoked_by TEXT,
    password_hash TEXT,
    password_updated_at TEXT,
    password_must_reset INTEGER DEFAULT 1  -- 0 pour admin, 1 pour member
);
```

#### `auth_sessions`
```sql
CREATE TABLE auth_sessions (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    user_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT,
    revoked_by TEXT,
    metadata TEXT  -- JSON
);
```

#### `password_reset_tokens`
```sql
CREATE TABLE password_reset_tokens (
    token TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used_at TEXT
);
```

#### `auth_audit_log`
```sql
CREATE TABLE auth_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,  -- login, logout, password:reset, allowlist:add, etc.
    email TEXT,
    actor TEXT,
    metadata TEXT,  -- JSON
    created_at TEXT NOT NULL
);
```

## Sécurité

### Hashage des mots de passe

- **Algorithme:** bcrypt avec salt automatique
- **Coût:** Default bcrypt rounds (adaptif)
- **Validation:** Minimum 8 caractères

### Tokens JWT

- **Algorithme:** HS256
- **Durée de vie:** 7 jours (configurable via `AUTH_JWT_TTL_DAYS`)
- **Claims:**
  - `iss`: Issuer (emergence.local)
  - `aud`: Audience (emergence-app)
  - `sub`: User ID (hash SHA256 de l'email)
  - `email`: Email de l'utilisateur
  - `role`: Rôle (admin/member/guest)
  - `sid`: Session ID
- `iat`: Issued at
- `exp`: Expiration

### Secret JWT obligatoire (Novembre 2025)

- `AUTH_JWT_SECRET` doit être défini dans l'environnement (min. 32 caractères alphanumériques).  
- Les valeurs par défaut/weak (`change-me`, `changeme`, `secret`, `test`) sont désormais refusées : **le backend ne démarre plus** pour éviter l'exposition des sessions.  
- En mode développement (`AUTH_DEV_MODE=1`), un secret temporaire est généré automatiquement et journalisé. Ce secret est volatil et ne doit jamais être utilisé en production.

### Tokens de réinitialisation

- **Génération:** `secrets.token_urlsafe(32)` (cryptographiquement sécurisé)
- **Durée de vie:** 1 heure
- **Usage unique:** Marqué comme utilisé après réinitialisation
- **Stockage:** Base de données SQLite

## Configuration

### Variables d'environnement

```bash
# Auth Configuration
AUTH_JWT_SECRET=your-secret-key-here
AUTH_JWT_ISSUER=emergence.local
AUTH_JWT_AUDIENCE=emergence-app
AUTH_JWT_TTL_DAYS=7
AUTH_ADMIN_EMAILS=admin@example.com,admin2@example.com

# Dev Mode
AUTH_DEV_MODE=0
AUTH_DEV_DEFAULT_EMAIL=dev@local

# Email Configuration
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

## Tests

### Test d'envoi d'email
```bash
python test_email_simple.py
```

### Test d'invitation beta
```bash
python test_beta_invitation.py
```

### Test de réinitialisation de mot de passe
```bash
# Via l'interface web
GET /reset-password.html
```

## Logs et Audit

Tous les événements d'authentification sont loggés dans `auth_audit_log` :

- `login` / `login:dev`
- `logout`
- `password:reset_requested`
- `password:reset_completed`
- `password:changed`
- `allowlist:add` / `allowlist:update` / `allowlist:remove`
- `allowlist:password_generated`
- `session:revoke` / `session:revoke_all`

## Troubleshooting

### Email ne s'envoie pas

1. **Vérifier la configuration:**
   ```python
   from backend.features.auth.email_service import EmailService
   service = EmailService()
   print(service.is_enabled())
   ```

2. **Gmail: Erreur 535 (authentication failed)**
   - Utiliser un mot de passe d'application, pas votre mot de passe Gmail
   - Créer sur: https://myaccount.google.com/apppasswords

3. **Timeout SMTP**
   - Vérifier le firewall (port 587 pour TLS)
   - Essayer SMTP_PORT=465 avec SMTP_USE_TLS=0 (SSL direct)

### Admin forcé à réinitialiser le mot de passe

Ce bug a été corrigé dans la **V2.1.2** (octobre 2025). Solutions :

**1. Fix automatique dans `_upsert_allowlist()` (lignes 1218-1222):**
```python
password_must_reset = CASE
    WHEN excluded.role = 'admin' THEN 0
    WHEN excluded.password_hash IS NOT NULL THEN 0
    ELSE auth_allowlist.password_must_reset
END
```

La logique SQL CASE garantit que:
- Les admins ont toujours `password_must_reset = 0`
- Quand un mot de passe est défini/changé, le flag est réinitialisé à `0`
- Sinon, la valeur existante est préservée

**2. UPDATE explicite après changement de mot de passe:**
- `set_allowlist_password()` (lignes 952-956)
- `change_own_password()` (lignes 1006-1011)

Ces fonctions exécutent un `UPDATE` explicite pour garantir que `password_must_reset = 0` après un changement de mot de passe.

**3. Mise à jour automatique au démarrage:**
   Le bootstrap SQL s'exécute à chaque démarrage du backend
   ```sql
   UPDATE auth_allowlist SET password_must_reset = 0
   WHERE role = 'admin' AND password_must_reset != 0
   ```

**4. Mise à jour manuelle (si nécessaire):**
   ```python
   python scripts/disable_password_reset.py
   ```

**5. Vérifier en base:**
   ```sql
   SELECT email, role, password_must_reset FROM auth_allowlist WHERE role = 'admin';
   ```

## Changelog

### V3.3.39 (Novembre 2025)
- 🔐 Démarrage bloqué si `AUTH_JWT_SECRET` est vide/weak (`change-me`, `secret`, etc.) ; en mode dev (`AUTH_DEV_MODE=1`) un secret temporaire est généré automatiquement.
- 🧪 Chargement automatique du fichier `.env` lors du démarrage local afin que `AUTH_DEV_MODE`/`AUTH_JWT_SECRET` soient disponibles sans configuration supplémentaire.
- 📌 Documentation README/architecture mise à jour pour rappeler le durcissement (CORS explicites + JWT admin sur monitoring).

### V2.1.2 (Octobre 2025)
- ✅ **FIX CRITIQUE:** Bug password_must_reset résolu définitivement
  - Fix SQL CASE statement dans `_upsert_allowlist()` (lignes 1218-1222)
  - Ajout UPDATE explicites dans `change_own_password()` et `set_allowlist_password()`
  - Les membres ne sont plus demandés de réinitialiser leur mot de passe à chaque connexion
  - Les admins ne sont jamais forcés à réinitialiser
- ✅ Synchronisation versioning (package.json, index.html, monitoring/router.py)
- ✅ Validation accès conversations archivées via `include_archived=True` dans l'API

### V2.0 (Octobre 2025)
- ✅ Service email complet avec templates HTML
- ✅ Réinitialisation de mot de passe par email
- ✅ Invitations beta par email
- ✅ Fix initial: admins ne sont plus forcés à réinitialiser
- ✅ Bootstrap SQL pour corriger les admins existants
- ✅ Support Gmail avec mot de passe d'application

### V1.0 (Septembre 2025)
- Authentification basique email/password
- JWT sessions
- Allowlist management
- Rate limiting
- Dev mode

## Références

- [Router API](/src/backend/features/auth/router.py)
- [Service Auth](/src/backend/features/auth/service.py)
- [Service Email](/src/backend/features/auth/email_service.py)
- [Models](/src/backend/features/auth/models.py)
- [Guide Beta Invitations](/docs/BETA_INVITATIONS.md)
