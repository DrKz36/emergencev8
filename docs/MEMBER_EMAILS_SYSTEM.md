# Système d'Envoi d'Emails aux Membres - ÉMERGENCE V8

## Vue d'ensemble

Ce système permet d'envoyer différents types d'emails aux membres de la waitlist/allowlist de manière flexible et intuitive via l'interface admin.

## Fonctionnalités

### Types d'emails disponibles

1. **Invitation Beta** (`beta_invitation`)
   - Email d'invitation initiale au programme beta
   - Contient les instructions d'accès et les phases de test
   - Template existant mis à jour

2. **Notification Problème d'Authentification** (`auth_issue`)
   - **NOUVEAU** - Email spécifique pour les problèmes d'auth
   - Explique le problème et sa résolution
   - Inclut un lien vers la page de réinitialisation de mot de passe
   - Rappelle l'importance du formulaire de beta-test
   - Encourage à remplir le formulaire même sans problème

3. **Message Personnalisé** (`custom`)
   - Possibilité d'envoyer des messages entièrement personnalisés
   - Nécessite subject, html_body et text_body

## Architecture

### Backend

#### Email Service ([src/backend/features/auth/email_service.py](../src/backend/features/auth/email_service.py))

**Nouvelles méthodes ajoutées :**

```python
async def send_auth_issue_notification_email(
    self,
    to_email: str,
    base_url: str,
) -> bool:
    """
    Envoie une notification sur les problèmes d'authentification
    Inclut:
    - Explication du problème
    - Instructions de réinitialisation de mot de passe
    - Lien vers reset-password.html
    - Rappel du formulaire beta_report.html
    """

async def send_custom_email(
    self,
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
) -> bool:
    """
    Envoie un email personnalisé avec sujet et contenu fournis
    """
```

#### API Endpoints ([src/backend/features/dashboard/admin_router.py](../src/backend/features/dashboard/admin_router.py))

**Nouveau endpoint principal :**

```
POST /api/admin/emails/send
```

**Request body :**
```json
{
  "emails": ["user1@example.com", "user2@example.com"],
  "base_url": "https://emergence-app.ch",
  "email_type": "auth_issue"
}
```

**Email types supportés :**
- `beta_invitation` : Invitation beta
- `auth_issue` : Notification problème d'authentification
- `custom` : Message personnalisé (nécessite `subject`, `html_body`, `text_body`)

**Response :**
```json
{
  "total": 2,
  "sent": 2,
  "failed": 0,
  "sent_to": ["user1@example.com", "user2@example.com"],
  "failed_emails": [],
  "email_type": "auth_issue"
}
```

**Ancien endpoint (deprecated) :**
```
POST /api/admin/beta-invitations/send
```
Redirige automatiquement vers le nouveau endpoint pour rétrocompatibilité.

### Frontend

#### Module Admin ([src/frontend/features/admin/beta-invitations-module.js](../src/frontend/features/admin/beta-invitations-module.js))

**Améliorations :**

1. **Sélecteur de type d'email**
   - Interface dropdown pour choisir le type d'email
   - Mise à jour dynamique du libellé du bouton

2. **Interface adaptative**
   - Titres et messages adaptés au type d'email sélectionné
   - Confirmations contextuelles

3. **Nouveau nom :** "Module d'envoi d'emails aux membres"

#### Interface Admin ([src/frontend/features/admin/admin.js](../src/frontend/features/admin/admin.js))

**Modification :**
- Onglet renommé : ~~"Invitations Beta"~~ → **"Envoi de mails"**

#### Styles ([src/frontend/features/admin/admin-dashboard.css](../src/frontend/features/admin/admin-dashboard.css))

**Ajout des styles pour :**
- `.auth-admin__select` : Sélecteur de type d'email avec theme sombre

## Template Email - Problème d'Authentification

Le nouveau template `send_auth_issue_notification_email` contient :

### Contenu HTML stylisé
- **Header** : Logo et titre ÉMERGENCE
- **Bonne nouvelle** : Problème résolu (encadré vert)
- **Action requise** : Bouton CTA pour réinitialiser le mot de passe
- **Étapes détaillées** : Liste numérotée des actions à faire
- **Warning** : Info pour ceux sans problème (encadré jaune)
- **Formulaire beta** : Bouton CTA vers beta_report.html
- **Importance du feedback** : Liste des bénéfices du formulaire
- **Signature** : L'équipe Émergence (FG, Claude, Codex)
- **Footer** : Contact et info automatique

### Contenu texte brut
Version plain-text complète pour les clients email sans HTML

### Liens inclus
- `{base_url}/reset-password.html` : Réinitialisation mot de passe
- `{base_url}/beta_report.html` : Formulaire de test beta

## Utilisation

### Via l'interface Admin

1. **Se connecter** en tant qu'admin à ÉMERGENCE
2. **Accéder au module Admin** dans la navigation
3. **Cliquer sur l'onglet "Envoi de mails"**
4. **Sélectionner le type d'email** :
   - 🎉 Invitation Beta
   - 🔧 Notification problème d'authentification
5. **Rechercher/Filtrer** les emails si nécessaire
6. **Cocher les destinataires** (ou "Tout sélectionner")
7. **Cliquer sur "Envoyer"**
8. **Confirmer l'envoi**
9. **Voir les résultats** (envoyés/échoués)

### Via API (curl)

```bash
# Envoyer une notification d'auth issue
curl -X POST https://emergence-app.ch/api/admin/emails/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "emails": ["user@example.com"],
    "base_url": "https://emergence-app.ch",
    "email_type": "auth_issue"
  }'
```

### Via Python

```python
import asyncio
from src.backend.features.auth.email_service import EmailService

async def send_auth_notification():
    service = EmailService()
    success = await service.send_auth_issue_notification_email(
        to_email="user@example.com",
        base_url="https://emergence-app.ch"
    )
    return success

asyncio.run(send_auth_notification())
```

## Cas d'usage actuel

### Problème d'authentification résolu

**Contexte :**
Des utilisateurs ont rencontré des problèmes d'authentification pendant la beta. Le problème a été identifié et résolu.

**Action :**
Envoyer une notification à tous les membres de la waitlist pour :
1. Les informer que le problème est résolu
2. Les inviter à réinitialiser leur mot de passe par précaution
3. Leur rappeler de remplir le formulaire de beta-test

**Procédure :**
1. Aller dans Admin → Envoi de mails
2. Sélectionner "Notification problème d'authentification"
3. Sélectionner tous les utilisateurs (ou filtrer selon besoins)
4. Envoyer

## Évolutions futures possibles

### Templates additionnels
- **Mise à jour de fonctionnalité** : Annoncer nouvelles features
- **Fin de beta** : Remercier et annoncer le lancement
- **Rappel inactivité** : Encourager les utilisateurs inactifs
- **Update importante** : Changements critiques

### Fonctionnalités
- **Preview avant envoi** : Aperçu de l'email rendu
- **Envoi programmé** : Planifier l'envoi pour plus tard
- **Variables dynamiques** : Personnaliser par destinataire (nom, etc.)
- **Historique d'envoi** : Voir les emails envoyés précédemment
- **Statistiques** : Taux d'ouverture, clics, etc.

## Fichiers modifiés/créés

### Backend
- ✅ `src/backend/features/auth/email_service.py` - Ajout templates
- ✅ `src/backend/features/dashboard/admin_router.py` - Nouvel endpoint

### Frontend
- ✅ `src/frontend/features/admin/beta-invitations-module.js` - Refonte complète
- ✅ `src/frontend/features/admin/admin.js` - Renommage onglet
- ✅ `src/frontend/features/admin/admin-dashboard.css` - Styles select

### Documentation & Tests
- ✅ `test_member_emails_system.py` - Script de test
- ✅ `docs/MEMBER_EMAILS_SYSTEM.md` - Cette documentation

## Configuration requise

### Variables d'environnement

```env
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

## Sécurité

- ✅ Authentification admin requise
- ✅ Vérification du rôle (admin only)
- ✅ Validation des emails
- ✅ Protection SMTP avec TLS
- ✅ Rate limiting (via SMTP)

## Support

En cas de problème :
1. Vérifier la configuration SMTP
2. Tester avec `test_member_emails_system.py`
3. Consulter les logs backend
4. Contacter gonzalefernando@gmail.com

---

**Créé le :** 16 octobre 2025
**Version :** 2.0
**Auteur :** L'équipe Émergence (FG, Claude, Codex)
