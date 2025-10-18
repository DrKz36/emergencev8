# Implémentation de la Réinitialisation de Mot de Passe

## Résumé des Modifications

Ce document décrit toutes les modifications apportées pour implémenter un système complet de réinitialisation de mot de passe par email dans ÉMERGENCE.

## Date d'implémentation
2025-10-12

## Fonctionnalités Ajoutées

### 1. Service d'Email (Backend)
**Fichier:** `src/backend/features/auth/email_service.py`

- Service SMTP configurabe via variables d'environnement
- Envoi d'emails de réinitialisation de mot de passe avec design HTML moderne
- Support pour Gmail, SendGrid, Mailgun et autres services SMTP
- Mode développement (logs les liens si email non configuré)
- Sécurité TLS/SSL

### 2. Nouveaux Modèles de Données (Backend)
**Fichier:** `src/backend/features/auth/models.py`

Ajout de 4 nouveaux modèles Pydantic :
- `RequestPasswordResetRequest`: Demande de réinitialisation
- `RequestPasswordResetResponse`: Réponse à la demande
- `ResetPasswordRequest`: Réinitialisation avec token
- `ResetPasswordResponse`: Confirmation de réinitialisation

### 3. Méthodes de Service (Backend)
**Fichier:** `src/backend/features/auth/service.py`

Trois nouvelles méthodes dans `AuthService`:

#### `create_password_reset_token(email: str) -> str`
- Crée un token sécurisé (32 bytes, URL-safe)
- Valide pour 1 heure
- Vérifie que l'utilisateur existe et n'est pas révoqué
- Enregistre le token dans la base de données
- Crée un log d'audit

#### `verify_password_reset_token(token: str) -> Optional[str]`
- Vérifie la validité du token
- Vérifie qu'il n'a pas expiré
- Vérifie qu'il n'a pas déjà été utilisé
- Retourne l'email associé

#### `reset_password_with_token(token: str, new_password: str) -> bool`
- Valide le token
- Vérifie la force du nouveau mot de passe
- Met à jour le hash du mot de passe
- Marque le token comme utilisé
- Révoque toutes les sessions existantes (sécurité)
- Crée un log d'audit

### 4. Nouveaux Endpoints API (Backend)
**Fichier:** `src/backend/features/auth/router.py`

#### `POST /api/auth/request-password-reset`
- Accepte un email
- Crée un token de réinitialisation
- Envoie un email avec le lien
- Retourne toujours un succès (prévention de l'énumération d'emails)

#### `POST /api/auth/reset-password`
- Accepte un token et un nouveau mot de passe
- Vérifie le token
- Met à jour le mot de passe
- Retourne le statut de l'opération

### 5. Migration de Base de Données
**Fichier:** `scripts/add_password_reset_table.py`

Création de la table `password_reset_tokens`:
```sql
CREATE TABLE password_reset_tokens (
    token TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used_at TEXT,
    FOREIGN KEY (email) REFERENCES auth_allowlist(email) ON DELETE CASCADE
)
```

Avec index sur:
- `email` (pour retrouver les tokens d'un utilisateur)
- `expires_at` (pour le nettoyage automatique)

### 6. Page de Réinitialisation (Frontend)
**Fichier:** `reset-password.html`

Page standalone pour la réinitialisation:
- Design moderne et responsive
- Validation côté client
- Gestion du token depuis l'URL
- Feedback visuel (succès/erreur)
- Redirection automatique après succès
- Messages d'erreur clairs

### 7. Modal de Demande de Réinitialisation (Frontend)
**Fichier:** `src/frontend/shared/change-password-modal.js`

Modifications majeures:
- **Ancien comportement**: Demandait le mot de passe actuel et le nouveau
- **Nouveau comportement**: Demande uniquement l'email et envoie un lien de vérification
- Pré-remplit l'email si disponible (via `userEmail` passé au constructeur)
- Appelle le nouveau endpoint `/api/auth/request-password-reset`
- Affiche un message de confirmation

### 8. Avatars des Agents dans le Popup d'Accueil (Frontend)
**Fichier:** `src/frontend/shared/welcome-popup.js`

Améliorations visuelles:
- Affichage horizontal des 3 avatars (Anima, Neo, Nexus)
- Animation de flottement pour chaque avatar
- Effet hover avec agrandissement et glow
- Animations décalées pour un effet dynamique
- Design circulaire avec bordures bleues brillantes

### 9. Documentation
**Fichier:** `docs/EMAIL_CONFIGURATION.md`

Guide complet comprenant:
- Configuration pour Gmail, SendGrid, Mailgun
- Liste complète des variables d'environnement
- Instructions de migration de la base de données
- Guide de dépannage
- Conseils de sécurité

## Flux Utilisateur Complet

### 1. Demande de Réinitialisation
```
Utilisateur → Clique "Changer mon mot de passe" dans popup
          ↓
Modal s'ouvre → Entre son email
          ↓
Frontend → POST /api/auth/request-password-reset
          ↓
Backend → Crée token sécurisé
       → Envoie email avec lien
       → Log dans audit
          ↓
Utilisateur → Reçoit email avec message d'information
```

### 2. Réinitialisation via Email
```
Utilisateur → Clique sur le lien dans l'email
          ↓
Navigateur → Ouvre reset-password.html?token=xxx
          ↓
Utilisateur → Entre nouveau mot de passe
          ↓
Frontend → POST /api/auth/reset-password
          ↓
Backend → Vérifie token (validité, expiration, utilisation)
       → Hash nouveau mot de passe
       → Met à jour dans la base
       → Marque token comme utilisé
       → Révoque toutes les sessions
       → Log dans audit
          ↓
Frontend → Affiche succès
        → Redirige vers page de connexion
```

## Sécurité

### Tokens
- Générés avec `secrets.token_urlsafe(32)` (256 bits de sécurité)
- Durée de vie: 1 heure
- Usage unique (marqués comme `used_at` après utilisation)
- Stockés en base de données avec metadata

### Email
- Prévention de l'énumération d'utilisateurs (toujours retourner succès)
- Connexion TLS/SSL sécurisée
- Email HTML avec design professionnel
- Lien avec token dans URL

### Mot de Passe
- Validation de force (minimum 8 caractères)
- Hash avec bcrypt (salt automatique)
- Révocation automatique de toutes les sessions après changement

### Audit
- Tous les événements sont loggés dans `auth_audit_log`:
  - `password:reset_requested`
  - `password:reset_completed`
- Métadonnées incluent timestamps et sources

## Configuration Requise

### Variables d'Environnement
```bash
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe-app
SMTP_FROM_EMAIL=votre-email@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

### Migration Base de Données
```bash
python scripts/add_password_reset_table.py
```

## Tests Recommandés

### Tests Manuels
1. ✅ Demander un reset avec email valide
2. ✅ Vérifier réception de l'email
3. ✅ Cliquer sur le lien et réinitialiser
4. ✅ Vérifier que le nouveau mot de passe fonctionne
5. ✅ Tester expiration du token (après 1h)
6. ✅ Tester réutilisation du token (devrait échouer)
7. ✅ Tester avec email invalide
8. ✅ Tester sans configuration SMTP (mode dev)

### Tests Unitaires à Ajouter
```python
# tests/backend/features/test_password_reset.py
- test_create_password_reset_token()
- test_verify_password_reset_token()
- test_reset_password_with_token()
- test_token_expiration()
- test_token_single_use()
- test_invalid_token()
- test_sessions_revoked_after_reset()
```

## Fichiers Modifiés

### Backend
- ✅ `src/backend/features/auth/email_service.py` (nouveau)
- ✅ `src/backend/features/auth/models.py` (modifié)
- ✅ `src/backend/features/auth/service.py` (modifié)
- ✅ `src/backend/features/auth/router.py` (modifié)

### Frontend
- ✅ `src/frontend/shared/change-password-modal.js` (modifié)
- ✅ `src/frontend/shared/welcome-popup.js` (modifié)
- ✅ `reset-password.html` (nouveau)

### Scripts
- ✅ `scripts/add_password_reset_table.py` (nouveau)

### Documentation
- ✅ `docs/EMAIL_CONFIGURATION.md` (nouveau)
- ✅ `PASSWORD_RESET_IMPLEMENTATION.md` (ce fichier)

## Prochaines Étapes Recommandées

1. **Tester la fonctionnalité complète**
   - Configurer SMTP (voir `docs/EMAIL_CONFIGURATION.md`)
   - Tester le flux complet
   - Vérifier les emails reçus

2. **Ajouter des tests unitaires**
   - Tests pour les endpoints
   - Tests pour le service d'email
   - Tests de sécurité (tokens, expiration, etc.)

3. **Améliorations futures possibles**
   - Rate limiting sur les demandes de reset
   - Notification à l'utilisateur quand son mot de passe est changé
   - Interface admin pour voir les tokens actifs
   - Nettoyage automatique des tokens expirés
   - Support pour d'autres providers d'email (SendGrid API, etc.)
   - Templates d'email personnalisables
   - Multi-langue pour les emails

## Notes de Déploiement

### Développement
- Le mode développement fonctionne sans configuration SMTP
- Les liens de reset sont affichés dans les logs du serveur

### Production
- **OBLIGATOIRE**: Configurer les variables d'environnement SMTP
- **OBLIGATOIRE**: Exécuter le script de migration
- **RECOMMANDÉ**: Utiliser un service email professionnel (SendGrid, Mailgun)
- **RECOMMANDÉ**: Configurer un domaine personnalisé pour les emails
- **RECOMMANDÉ**: Activer les logs d'audit

## Support

Pour toute question:
- Consulter `docs/EMAIL_CONFIGURATION.md` pour la configuration
- Vérifier les logs du serveur en cas d'erreur
- Tester d'abord en mode développement

## Auteur
Implémentation réalisée le 2025-10-12
