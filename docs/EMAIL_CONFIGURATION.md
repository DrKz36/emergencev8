# Configuration du Service d'Email

Ce document explique comment configurer le service d'email pour activer la fonctionnalité de réinitialisation de mot de passe dans ÉMERGENCE.

## Prérequis

Vous avez besoin d'un compte SMTP pour envoyer des emails. Voici quelques options populaires :

- **Gmail** (recommandé pour le développement)
- **SendGrid**
- **Mailgun**
- **Amazon SES**
- Tout autre service SMTP

## Configuration avec Gmail

### 1. Activer l'accès pour les applications moins sécurisées

Pour utiliser Gmail avec SMTP, vous devez créer un "App Password" :

1. Allez sur votre compte Google : https://myaccount.google.com/
2. Sécurité > Validation en deux étapes (activez-la si ce n'est pas déjà fait)
3. Sécurité > Mots de passe des applications
4. Créez un nouveau mot de passe d'application
5. Notez le mot de passe de 16 caractères généré

### 2. Configuration des variables d'environnement

Ajoutez ces variables à votre fichier `.env` :

```bash
# Email Configuration
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe-app
SMTP_FROM_EMAIL=votre-email@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

## Configuration avec d'autres services

### SendGrid

```bash
EMAIL_ENABLED=1
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=votre-api-key-sendgrid
SMTP_FROM_EMAIL=noreply@votredomaine.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

### Mailgun

```bash
EMAIL_ENABLED=1
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@votredomaine.mailgun.org
SMTP_PASSWORD=votre-mot-de-passe-mailgun
SMTP_FROM_EMAIL=noreply@votredomaine.com
SMTP_FROM_NAME=ÉMERGENCE
SMTP_USE_TLS=1
```

## Variables d'environnement disponibles

| Variable | Description | Défaut | Requis |
|----------|-------------|--------|--------|
| `EMAIL_ENABLED` | Active/désactive le service d'email | `0` | Oui |
| `SMTP_HOST` | Serveur SMTP | `smtp.gmail.com` | Oui |
| `SMTP_PORT` | Port SMTP | `587` | Oui |
| `SMTP_USER` | Nom d'utilisateur SMTP | - | Oui |
| `SMTP_PASSWORD` | Mot de passe SMTP | - | Oui |
| `SMTP_FROM_EMAIL` | Adresse email de l'expéditeur | Même que `SMTP_USER` | Non |
| `SMTP_FROM_NAME` | Nom de l'expéditeur | `ÉMERGENCE` | Non |
| `SMTP_USE_TLS` | Utiliser TLS | `1` | Non |

## Migration de la base de données

Avant d'utiliser la fonctionnalité de réinitialisation de mot de passe, vous devez exécuter la migration de la base de données :

```bash
python scripts/add_password_reset_table.py
```

Cela créera la table `password_reset_tokens` nécessaire pour stocker les tokens de réinitialisation.

## Test de la configuration

### Mode développement (sans email configuré)

Si `EMAIL_ENABLED=0` ou si la configuration SMTP n'est pas complète, le système fonctionnera en mode développement :

- Les tokens de réinitialisation seront créés normalement
- Les liens de réinitialisation seront affichés dans les logs du serveur
- Vous pouvez copier/coller le lien depuis les logs pour tester

### Mode production (avec email configuré)

Une fois la configuration SMTP activée :

1. Cliquez sur "Changer mon mot de passe" dans le popup d'accueil
2. Entrez votre adresse email
3. Vérifiez votre boîte email
4. Cliquez sur le lien dans l'email
5. Créez votre nouveau mot de passe

## Sécurité

- Les tokens de réinitialisation sont valables **1 heure** seulement
- Chaque token ne peut être utilisé qu'**une seule fois**
- Les tokens sont générés de manière cryptographiquement sécurisée
- Toutes les sessions existantes sont révoquées après une réinitialisation de mot de passe
- Les emails utilisent une connexion TLS sécurisée par défaut

## Dépannage

### L'email n'est pas envoyé

1. Vérifiez que `EMAIL_ENABLED=1`
2. Vérifiez vos identifiants SMTP
3. Consultez les logs du serveur pour voir les erreurs
4. Assurez-vous que le port SMTP n'est pas bloqué par votre pare-feu

### Erreur d'authentification SMTP

- Pour Gmail : assurez-vous d'utiliser un "App Password" et non votre mot de passe normal
- Vérifiez que la validation en deux étapes est activée sur Gmail
- Vérifiez que `SMTP_USER` et `SMTP_PASSWORD` sont correctement définis

### Le lien de réinitialisation ne fonctionne pas

- Les liens expirent après 1 heure
- Chaque lien ne peut être utilisé qu'une seule fois
- Demandez un nouveau lien si nécessaire

## Support

Pour toute question ou problème, consultez la documentation ou contactez l'administrateur système.
