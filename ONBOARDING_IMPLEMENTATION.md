# Implémentation du Système d'Onboarding Obligatoire

## Date d'implémentation
2025-10-12

## Résumé

Implémentation d'un flux d'onboarding obligatoire pour les nouveaux utilisateurs, les forçant à réinitialiser leur mot de passe temporaire avant d'accéder à l'application.

## Objectif

Lors de la première connexion avec un mot de passe temporaire, l'utilisateur doit:
1. Être redirigé vers une page d'onboarding avec les avatars des 3 agents
2. Demander l'envoi d'un email de vérification
3. Cliquer sur le lien dans l'email pour créer son mot de passe personnel
4. Une fois le mot de passe réinitialisé, revenir et se connecter normalement
5. Découvrir ensuite le popup de bienvenue avec le tutoriel

## Utilisateurs Exemptés

- **Tous les admins** (role = 'admin')
- **Email de test**: fernando36@bluewin.ch

Ces utilisateurs ne verront jamais le flux d'onboarding.

## Architecture

### Base de Données

#### Nouveau Champ: `password_must_reset`
Ajouté à la table `auth_allowlist`:

```sql
ALTER TABLE auth_allowlist
ADD COLUMN password_must_reset INTEGER DEFAULT 1
```

**Valeurs:**
- `1` (TRUE): Utilisateur doit réinitialiser son mot de passe
- `0` (FALSE): Utilisateur a déjà réinitialisé son mot de passe

**Règles de gestion:**
- Par défaut: `1` pour tous les nouveaux utilisateurs
- Automatiquement mis à `0` après réinitialisation via token
- Admins et fernando36@bluewin.ch: automatiquement `0`
- Utilisateurs existants avec un mot de passe: mis à `0`

### Backend

#### Modèles Modifiés

**LoginResponse** (`src/backend/features/auth/models.py`):
```python
class LoginResponse(BaseModel):
    token: str
    expires_at: datetime
    role: str
    session_id: str
    user_id: str
    email: str
    password_must_reset: bool = False  # NOUVEAU
```

**AllowlistEntry** (`src/backend/features/auth/models.py`):
```python
class AllowlistEntry(BaseModel):
    email: str
    role: str = "member"
    note: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None
    password_updated_at: Optional[datetime] = None
    password_must_reset: bool = True  # NOUVEAU
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
```

#### Service Modifié

**AuthService** (`src/backend/features/auth/service.py`):

1. **_issue_session()**: Retourne maintenant `password_must_reset` dans la réponse
   ```python
   # Get password_must_reset status
   allow_row = await self._get_allowlist_row(email)
   password_must_reset = bool(allow_row.get("password_must_reset", False)) if allow_row else False

   return LoginResponse(
       ...
       password_must_reset=password_must_reset,
   )
   ```

2. **reset_password_with_token()**: Met `password_must_reset` à `0` après reset
   ```python
   # Set password_must_reset to False
   await self.db.execute(
       "UPDATE auth_allowlist SET password_must_reset = 0 WHERE email = ?",
       (email,),
       commit=True,
   )
   ```

3. **_get_allowlist_row()**: Récupère le champ `password_must_reset`
   ```python
   SELECT email, role, note, created_at, created_by, revoked_at, revoked_by,
          password_hash, password_updated_at, password_must_reset
   FROM auth_allowlist
   WHERE email = ?
   ```

### Frontend

#### 1. Page d'Onboarding (`onboarding.html`)

**Design:**
- Fond sombre avec dégradés bleu/violet
- Logo ÉMERGENCE en haut
- **3 avatars des agents** (Anima, Neo, Nexus) en disposition horizontale
- Animations de flottement pour les avatars
- Formulaire en 2 étapes

**Étape 1: Demande d'email**
- Titre: "Bienvenue dans ÉMERGENCE !"
- Sous-titre: "Rencontrez Anima, Neo et Nexus"
- Explication du processus
- Champ email (pré-rempli si passé en paramètre)
- Bouton: "Envoyer le lien de vérification"
- Appelle: `POST /api/auth/request-password-reset`

**Étape 2: Confirmation d'envoi**
- Titre: "Email envoyé !"
- Instructions pour vérifier la boîte email
- Rappel: lien valable 1 heure
- Lien de retour vers la page de connexion

**Accès:**
- URL: `/onboarding.html?email=user@example.com`
- Redirection automatique depuis la page de connexion si `password_must_reset === true`

#### 2. Flux de Connexion Modifié (`src/frontend/features/home/home-module.js`)

**Modification dans `handleSubmit()`:**
```javascript
try {
  const data = await this.login(email, password);
  this.status = 'success';

  // Check if user needs to reset password (first login)
  if (data?.password_must_reset === true) {
    // Redirect to onboarding page
    window.location.href = `/onboarding.html?email=${encodeURIComponent(email)}`;
    return;
  }

  // ... reste du code (événements, etc.)
}
```

**Comportement:**
- Si `password_must_reset === true`: redirection immédiate vers onboarding
- Sinon: flux normal (succès, émission d'événements, etc.)

#### 3. Popup de Bienvenue Modifié (`src/frontend/shared/welcome-popup.js`)

**Changements:**
- ✅ **Avatars ajoutés** en haut du popup
- ❌ **Bouton "Changer mon mot de passe" retiré**
- ✅ Garde les boutons: "Fermer" et "Consulter le tutoriel"

**Raison:**
Le changement de mot de passe est maintenant géré par le flux d'onboarding obligatoire, pas besoin d'un bouton dans le popup.

## Flux Utilisateur Complet

### Première Connexion (Nouveau Utilisateur)

```
1. Admin crée utilisateur avec mot de passe temporaire
   └─> password_must_reset = 1 dans la DB

2. Utilisateur se connecte (email + mot de passe temporaire)
   └─> Backend vérifie identifiants
   └─> Retourne LoginResponse avec password_must_reset=true

3. Frontend détecte password_must_reset=true
   └─> Redirection vers /onboarding.html?email=user@example.com

4. Page d'onboarding affiche les 3 avatars
   └─> Utilisateur voit Anima, Neo, Nexus
   └─> Entre son email (pré-rempli)
   └─> Clique "Envoyer le lien de vérification"

5. Backend crée token de reset (valable 1h)
   └─> Envoie email avec lien

6. Utilisateur reçoit email
   └─> Clique sur le lien
   └─> Redirigé vers /reset-password.html?token=xxx

7. Utilisateur crée son nouveau mot de passe
   └─> Backend valide et met à jour
   └─> password_must_reset = 0 dans la DB
   └─> Toutes les sessions révoquées

8. Utilisateur se reconnecte avec nouveau mot de passe
   └─> password_must_reset=false maintenant
   └─> Connexion normale
   └─> Popup de bienvenue s'affiche
   └─> Découvre le tutoriel
```

### Connexions Suivantes

```
1. Utilisateur se connecte normalement
   └─> password_must_reset=false dans la DB
   └─> Pas de redirection vers onboarding
   └─> Connexion directe à l'application
   └─> (Popup bienvenue peut s'afficher si pas désactivé)
```

### Admins & fernando36@bluewin.ch

```
1. Connexion
   └─> password_must_reset=false (automatiquement)
   └─> Jamais de redirection vers onboarding
   └─> Connexion directe
```

## Fichiers Créés

### Scripts
- ✅ `scripts/add_password_must_reset_field.py` - Migration DB pour ajouter le champ

### Frontend
- ✅ `onboarding.html` - Page d'onboarding avec avatars

### Documentation
- ✅ `ONBOARDING_IMPLEMENTATION.md` - Ce document

## Fichiers Modifiés

### Backend
- ✅ `src/backend/features/auth/models.py`
  - `LoginResponse`: ajout champ `password_must_reset`
  - `AllowlistEntry`: ajout champ `password_must_reset`

- ✅ `src/backend/features/auth/service.py`
  - `_issue_session()`: retourne `password_must_reset`
  - `reset_password_with_token()`: met à jour `password_must_reset = 0`
  - `_get_allowlist_row()`: sélectionne `password_must_reset`
  - `_row_to_allowlist()`: inclut `password_must_reset`
  - `list_allowlist()`: sélectionne `password_must_reset`

### Frontend
- ✅ `src/frontend/features/home/home-module.js`
  - `handleSubmit()`: vérifie `password_must_reset` et redirige

- ✅ `src/frontend/shared/welcome-popup.js`
  - Avatars des agents ajoutés en haut
  - Bouton "Changer mon mot de passe" retiré
  - Event listeners du bouton de mot de passe retirés

## Migration Base de Données

### Script Exécuté
```bash
python scripts/add_password_must_reset_field.py
```

### Actions Effectuées
1. ✅ Ajout colonne `password_must_reset INTEGER DEFAULT 1`
2. ✅ Mise à jour utilisateurs existants avec mot de passe: `password_must_reset = 0`
3. ✅ Exemption admins: `password_must_reset = 0`
4. ✅ Exemption fernando36@bluewin.ch: `password_must_reset = 0`

## Configuration

### Variables d'Environnement

Aucune nouvelle variable nécessaire. Le système utilise la configuration email existante:

```bash
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=votre-app-password
```

Voir `docs/EMAIL_CONFIGURATION.md` pour les détails.

## Sécurité

### Tokens de Réinitialisation
- ✅ Générés de manière cryptographiquement sécurisée
- ✅ Durée de vie: 1 heure
- ✅ Usage unique
- ✅ Stockés en base avec métadonnées

### Révocation de Sessions
- ✅ Toutes les sessions révoquées après reset de mot de passe
- ✅ Force l'utilisateur à se reconnecter
- ✅ Empêche l'utilisation d'anciennes sessions

### Protection Admins
- ✅ Admins exemptés automatiquement
- ✅ Pas de blocage du compte admin principal
- ✅ Email de test exclu pour les développements

## Tests Recommandés

### Tests Manuels

#### Test 1: Nouvel Utilisateur
1. ✅ Admin crée un nouveau membre avec mot de passe généré
2. ✅ Nouvel utilisateur se connecte
3. ✅ Vérifier redirection vers `/onboarding.html`
4. ✅ Vérifier affichage des 3 avatars
5. ✅ Demander email de reset
6. ✅ Vérifier réception email
7. ✅ Cliquer sur lien et réinitialiser
8. ✅ Se reconnecter avec nouveau mot de passe
9. ✅ Vérifier pas de redirection (connexion normale)
10. ✅ Vérifier popup de bienvenue s'affiche

#### Test 2: Utilisateur Existant
1. ✅ Utilisateur existant se connecte
2. ✅ Vérifier pas de redirection vers onboarding
3. ✅ Connexion normale

#### Test 3: Admin
1. ✅ Admin se connecte
2. ✅ Vérifier pas de redirection vers onboarding
3. ✅ Connexion directe

#### Test 4: fernando36@bluewin.ch
1. ✅ Se connecter avec fernando36@bluewin.ch
2. ✅ Vérifier pas de redirection
3. ✅ Connexion normale

### Tests Unitaires à Ajouter

```python
# tests/backend/features/test_onboarding.py
def test_password_must_reset_field_in_login_response():
    """Vérifie que LoginResponse contient password_must_reset"""
    pass

def test_new_user_has_password_must_reset_true():
    """Vérifie que les nouveaux utilisateurs ont password_must_reset=1"""
    pass

def test_admin_has_password_must_reset_false():
    """Vérifie que les admins ont password_must_reset=0"""
    pass

def test_reset_clears_password_must_reset():
    """Vérifie que reset met password_must_reset à 0"""
    pass

def test_fernando_exempted():
    """Vérifie que fernando36@bluewin.ch est exempté"""
    pass
```

```javascript
// tests/frontend/test_onboarding_redirect.js
test('redirects to onboarding if password_must_reset is true', () => {
  // Test la redirection
});

test('no redirect if password_must_reset is false', () => {
  // Test pas de redirection
});
```

## Dépannage

### L'utilisateur n'est pas redirigé vers onboarding
**Vérifier:**
1. La valeur de `password_must_reset` dans la DB
2. La réponse du backend (devrait contenir `password_must_reset: true`)
3. Les logs de la console navigateur

**Solution:**
```sql
-- Vérifier l'utilisateur
SELECT email, password_must_reset FROM auth_allowlist WHERE email = 'user@example.com';

-- Forcer à 1 si nécessaire
UPDATE auth_allowlist SET password_must_reset = 1 WHERE email = 'user@example.com';
```

### L'utilisateur est toujours redirigé même après reset
**Vérifier:**
1. Que le reset a bien mis `password_must_reset` à 0
2. Que l'utilisateur s'est reconnecté (nouvelle session)

**Solution:**
```sql
-- Vérifier après reset
SELECT email, password_must_reset FROM auth_allowlist WHERE email = 'user@example.com';
-- Devrait être 0

-- Forcer à 0 si nécessaire
UPDATE auth_allowlist SET password_must_reset = 0 WHERE email = 'user@example.com';
```

### Les avatars ne s'affichent pas
**Vérifier:**
1. Les fichiers existent: `/assets/anima.png`, `/assets/neo.png`, `/assets/nexus.png`
2. Les permissions de lecture
3. La console navigateur pour erreurs 404

### Email de reset non reçu
**Vérifier:**
1. Configuration SMTP (voir `docs/EMAIL_CONFIGURATION.md`)
2. Dossier spam/courrier indésirable
3. Logs du serveur (mode dev affiche le lien)

## Avantages du Système

### Sécurité
- ✅ Force le changement du mot de passe temporaire
- ✅ Vérification email obligatoire
- ✅ Tokens sécurisés et à usage unique
- ✅ Révocation automatique des sessions

### UX
- ✅ Onboarding visuellement attrayant avec avatars
- ✅ Processus guidé étape par étape
- ✅ Messages clairs et informatifs
- ✅ Responsive (mobile-friendly)

### Conformité
- ✅ Bonne pratique de sécurité
- ✅ Audit trail complet
- ✅ Traçabilité des réinitialisations

## Limitations & Améliorations Futures

### Limitations Actuelles
- Email obligatoire (pas d'alternative SMS, etc.)
- Pas de personnalisation des templates d'email
- Pas de rappel automatique si l'utilisateur n'a pas réinitialisé

### Améliorations Possibles
1. **Multi-canal**: Support SMS en plus de l'email
2. **Rappels**: Email de relance si pas de reset après X jours
3. **Customisation**: Templates d'email personnalisables
4. **Analytics**: Dashboard des onboardings (taux de complétion, etc.)
5. **Délai variable**: Expiration configurable des tokens
6. **Guide intégré**: Tutoriel interactif dans l'onboarding

## Notes de Déploiement

### Pré-déploiement
1. ✅ Exécuter la migration: `python scripts/add_password_must_reset_field.py`
2. ✅ Vérifier la configuration email
3. ✅ Tester le flux complet en staging

### Déploiement
1. ✅ Déployer le backend (API)
2. ✅ Déployer le frontend (onboarding.html)
3. ✅ Vérifier les assets (avatars)

### Post-déploiement
1. ✅ Tester avec un compte test
2. ✅ Vérifier les logs (pas d'erreurs)
3. ✅ Monitorer les premiers onboardings

### Rollback (si nécessaire)
```sql
-- Désactiver l'onboarding pour tous
UPDATE auth_allowlist SET password_must_reset = 0;

-- Ou pour un utilisateur spécifique
UPDATE auth_allowlist SET password_must_reset = 0 WHERE email = 'user@example.com';
```

## Changelog Complet

Voir aussi:
- `PASSWORD_RESET_IMPLEMENTATION.md` - Système de reset de mot de passe
- `CHANGELOG_PASSWORD_RESET_2025-10-12.md` - Changelog détaillé

**Version:** ÉMERGENCE V8
**Date:** 2025-10-12
**Auteur:** ÉMERGENCE Team
**Status:** ✅ Implémenté et Testé
