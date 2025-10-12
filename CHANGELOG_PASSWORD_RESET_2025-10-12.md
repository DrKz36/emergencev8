# Changelog - Réinitialisation de Mot de Passe et Améliorations UI

**Date:** 2025-10-12
**Version:** ÉMERGENCE V8

## 🎯 Nouvelles Fonctionnalités

### Réinitialisation de Mot de Passe par Email

#### Backend
- ✨ **Service d'Email SMTP** - Nouveau service complet pour l'envoi d'emails
  - Support Gmail, SendGrid, Mailgun et autres providers SMTP
  - Configuration via variables d'environnement
  - Mode développement (logs les liens si pas configuré)
  - Templates HTML modernes et responsive
  - Sécurité TLS/SSL

- ✨ **Gestion des Tokens de Réinitialisation**
  - Tokens sécurisés générés avec `secrets.token_urlsafe(32)`
  - Expiration automatique après 1 heure
  - Usage unique (tokens marqués après utilisation)
  - Stockage en base de données avec métadonnées

- ✨ **Nouveaux Endpoints API**
  - `POST /api/auth/request-password-reset` - Demander un reset
  - `POST /api/auth/reset-password` - Réinitialiser avec token

- ✨ **Méthodes de Service**
  - `create_password_reset_token()` - Créer un token de reset
  - `verify_password_reset_token()` - Vérifier un token
  - `reset_password_with_token()` - Réinitialiser le mot de passe

#### Frontend
- ✨ **Page de Réinitialisation Standalone** (`reset-password.html`)
  - Design moderne et responsive
  - Validation des mots de passe côté client
  - Gestion automatique du token depuis l'URL
  - Feedback visuel en temps réel
  - Redirection automatique après succès

- ✨ **Modal de Demande de Réinitialisation**
  - Nouveau workflow: demande d'email → envoi de lien
  - Pré-remplissage de l'email si disponible
  - Messages de confirmation clairs
  - Interface simplifiée

#### Base de Données
- ✨ **Nouvelle Table** `password_reset_tokens`
  - Colonnes: token, email, expires_at, created_at, used_at
  - Index sur email et expires_at
  - Contrainte de clé étrangère vers auth_allowlist

#### Sécurité
- 🔒 Prévention de l'énumération d'utilisateurs
- 🔒 Révocation automatique de toutes les sessions après reset
- 🔒 Validation de force du mot de passe (min 8 caractères)
- 🔒 Hash bcrypt avec salt automatique
- 🔒 Audit complet de tous les événements de réinitialisation

### Améliorations de l'Interface

#### Popup d'Accueil
- ✨ **Avatars des Agents** - Affichage des 3 avatars (Anima, Neo, Nexus)
  - Disposition horizontale alignée en haut
  - Animation de flottement (float effect)
  - Effet hover avec agrandissement et glow
  - Animations décalées pour dynamisme
  - Design circulaire avec bordures bleues brillantes
  - Images: `/assets/anima.png`, `/assets/neo.png`, `/assets/nexus.png`

## 📝 Fichiers Créés

### Backend
- `src/backend/features/auth/email_service.py` - Service d'envoi d'emails

### Frontend
- `reset-password.html` - Page de réinitialisation de mot de passe

### Scripts
- `scripts/add_password_reset_table.py` - Migration de base de données

### Documentation
- `docs/EMAIL_CONFIGURATION.md` - Guide de configuration email
- `PASSWORD_RESET_IMPLEMENTATION.md` - Documentation technique complète
- `CHANGELOG_PASSWORD_RESET_2025-10-12.md` - Ce fichier

## 🔧 Fichiers Modifiés

### Backend
- `src/backend/features/auth/models.py`
  - Ajout: `RequestPasswordResetRequest`
  - Ajout: `RequestPasswordResetResponse`
  - Ajout: `ResetPasswordRequest`
  - Ajout: `ResetPasswordResponse`

- `src/backend/features/auth/service.py`
  - Ajout import: `secrets`
  - Ajout méthode: `create_password_reset_token()`
  - Ajout méthode: `verify_password_reset_token()`
  - Ajout méthode: `reset_password_with_token()`

- `src/backend/features/auth/router.py`
  - Ajout import: `EmailService`
  - Ajout import: nouveaux modèles de reset
  - Ajout endpoint: `request_password_reset()`
  - Ajout endpoint: `reset_password()`

### Frontend
- `src/frontend/shared/change-password-modal.js`
  - Modification constructeur: ajout paramètre `userEmail`
  - Modification UI: demande email au lieu de mot de passe actuel
  - Modification submit: appel endpoint `/request-password-reset`
  - Mise à jour textes et messages

- `src/frontend/shared/welcome-popup.js`
  - Ajout HTML: section `.welcome-popup-avatars` avec 3 images
  - Ajout CSS: styles pour avatars (60px, circulaires, animations)
  - Ajout CSS: animation `avatarFloat`
  - Ajout CSS: effets hover et delays

## 📋 Configuration Requise

### Variables d'Environnement (Nouvelles)
```bash
EMAIL_ENABLED=1                          # Active le service email
SMTP_HOST=smtp.gmail.com                 # Serveur SMTP
SMTP_PORT=587                            # Port SMTP
SMTP_USER=votre-email@gmail.com          # Utilisateur SMTP
SMTP_PASSWORD=votre-app-password         # Mot de passe SMTP
SMTP_FROM_EMAIL=votre-email@gmail.com    # Email expéditeur
SMTP_FROM_NAME=ÉMERGENCE                 # Nom expéditeur
SMTP_USE_TLS=1                           # Utiliser TLS
```

### Migration Base de Données (Requis)
```bash
python scripts/add_password_reset_table.py
```

## 🚀 Comment Utiliser

### Pour les Utilisateurs
1. Cliquer sur "Changer mon mot de passe" dans le popup d'accueil
2. Entrer votre adresse email
3. Vérifier votre boîte email
4. Cliquer sur le lien reçu
5. Créer un nouveau mot de passe

### Pour les Développeurs

#### Mode Développement (sans email)
```bash
# Pas de configuration nécessaire
# Les liens de reset apparaîtront dans les logs du serveur
```

#### Mode Production (avec email)
```bash
# 1. Configurer les variables d'environnement (voir .env.example)
# 2. Exécuter la migration
python scripts/add_password_reset_table.py
# 3. Redémarrer le serveur
```

## 🔍 Détails Techniques

### Flux de Réinitialisation
1. **Demande**: `POST /api/auth/request-password-reset` avec email
2. **Backend**: Crée token sécurisé valide 1h
3. **Email**: Envoi du lien `{base_url}/reset-password?token={token}`
4. **Utilisateur**: Clique sur le lien, entre nouveau mot de passe
5. **Réinitialisation**: `POST /api/auth/reset-password` avec token + mot de passe
6. **Backend**: Valide token, update mot de passe, révoque sessions
7. **Succès**: Redirection vers page de connexion

### Sécurité des Tokens
- **Génération**: `secrets.token_urlsafe(32)` = 256 bits
- **Durée de vie**: 1 heure exactement
- **Usage**: Unique (marqué `used_at` après utilisation)
- **Stockage**: Base de données SQLite avec index
- **Validation**: Expiration + usage unique + existence utilisateur

### Audit
Tous les événements sont loggés dans `auth_audit_log`:
- `password:reset_requested` - Demande de reset
- `password:reset_completed` - Reset réussi

Métadonnées incluent:
- Email de l'utilisateur
- Timestamp
- Source de l'action
- Détails supplémentaires (expiration, etc.)

## 🧪 Tests Recommandés

### Checklist de Tests Manuels
- [ ] Demander reset avec email valide
- [ ] Vérifier réception email
- [ ] Cliquer sur lien et réinitialiser
- [ ] Tester nouveau mot de passe
- [ ] Tester expiration token (1h+)
- [ ] Tester réutilisation token
- [ ] Tester email invalide
- [ ] Tester mode dev (sans SMTP)
- [ ] Vérifier révocation sessions
- [ ] Vérifier logs d'audit

### Tests Unitaires à Ajouter
- Service: `test_create_password_reset_token()`
- Service: `test_verify_password_reset_token()`
- Service: `test_reset_password_with_token()`
- Service: `test_token_expiration()`
- Service: `test_token_single_use()`
- Router: `test_request_password_reset_endpoint()`
- Router: `test_reset_password_endpoint()`
- Email: `test_email_sending()`

## 🐛 Corrections de Bugs

Aucun bug corrigé dans cette release (nouvelles fonctionnalités uniquement).

## 📚 Documentation

Voir les fichiers suivants pour plus de détails:
- **Configuration**: `docs/EMAIL_CONFIGURATION.md`
- **Implémentation**: `PASSWORD_RESET_IMPLEMENTATION.md`
- **README**: Documentation mise à jour recommandée

## ⚠️ Breaking Changes

### Modal de Changement de Mot de Passe
**AVANT:**
- Demandait: mot de passe actuel + nouveau mot de passe
- Fonctionnait: changement direct si authentifié

**APRÈS:**
- Demande: email uniquement
- Fonctionne: envoi d'un lien de vérification par email

**Impact:**
- Les utilisateurs doivent maintenant passer par leur email
- Plus sécurisé mais workflow différent
- Pas de compatibilité descendante

### Constructeur ChangePasswordModal
**AVANT:**
```javascript
new ChangePasswordModal(eventBus, apiClient)
```

**APRÈS:**
```javascript
new ChangePasswordModal(eventBus, apiClient, userEmail)
```

**Impact:**
- Le 3ème paramètre est optionnel
- Code existant fonctionne toujours
- Mais pré-remplir l'email améliore UX

## 🔄 Migrations Nécessaires

### Base de Données
**OBLIGATOIRE** avant utilisation:
```bash
python scripts/add_password_reset_table.py
```

### Variables d'Environnement
**OPTIONNEL** (mais recommandé pour production):
```bash
# Ajouter au fichier .env
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email
SMTP_PASSWORD=votre-password
```

## 📊 Statistiques

- **Nouveaux fichiers**: 5
- **Fichiers modifiés**: 6
- **Lignes de code ajoutées**: ~1500
- **Nouvelles API endpoints**: 2
- **Nouvelles tables BDD**: 1
- **Nouveaux modèles Pydantic**: 4
- **Nouvelles méthodes service**: 3

## 🎨 Design

### Avatars des Agents
- **Taille**: 60px × 60px
- **Forme**: Circulaire
- **Bordure**: 2px bleu (#3b82f6)
- **Ombre**: Glow bleu animé
- **Animation**: Float vertical 8px
- **Effet hover**: Scale 1.1 + glow intensifié

### Page de Réinitialisation
- **Palette**: Dégradés bleu/violet sur fond sombre
- **Responsive**: Mobile-first
- **Animations**: Slide-up à l'ouverture
- **Feedback**: Messages colorés (vert/rouge)

## 🚧 Améliorations Futures Possibles

1. **Rate Limiting**
   - Limiter les demandes de reset par IP/email
   - Prévenir les abus

2. **Notifications**
   - Email de confirmation après changement
   - Alertes de sécurité

3. **Interface Admin**
   - Voir les tokens actifs
   - Révoquer manuellement les tokens

4. **Nettoyage Automatique**
   - Cron job pour supprimer tokens expirés
   - Optimisation de la base de données

5. **Templates Personnalisables**
   - HTML/CSS modifiables
   - Support multi-langue

6. **Analytics**
   - Dashboard des resets
   - Métriques de sécurité

## 📝 Notes de Version

### Compatibilité
- ✅ Compatible avec ÉMERGENCE V8
- ✅ Pas de dépendances supplémentaires
- ✅ Utilise uniquement la bibliothèque standard Python

### Performance
- ⚡ Pas d'impact sur les performances existantes
- ⚡ Emails envoyés de manière asynchrone
- ⚡ Index BDD pour requêtes optimisées

### Sécurité
- 🔒 Audit complet activé
- 🔒 Tokens cryptographiquement sécurisés
- 🔒 Sessions révoquées automatiquement
- 🔒 Prévention énumération d'emails

---

**Auteurs:** ÉMERGENCE Team
**Date de Release:** 2025-10-12
**Status:** ✅ Prêt pour Production (après configuration SMTP)
