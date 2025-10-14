# Guide d'envoi des invitations Beta ÉMERGENCE V8

Ce guide explique comment envoyer des invitations automatiques aux beta testeurs par email.

## Table des matières

1. [Configuration](#configuration)
2. [Méthodes d'envoi](#méthodes-denvoi)
3. [Utilisation du script Python](#utilisation-du-script-python)
4. [Utilisation de l'API REST](#utilisation-de-lapi-rest)
5. [Troubleshooting](#troubleshooting)

---

## Configuration

### 1. Configurer les variables d'environnement

Créez un fichier `.env` à la racine du projet (ou ajoutez ces variables à votre fichier `.env` existant):

```bash
# Email Configuration
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=1
SMTP_USER=gonzalefernando@gmail.com
SMTP_PASSWORD=dfshbvvsmyqrfkja
SMTP_FROM_EMAIL=gonzalefernando@gmail.com
SMTP_FROM_NAME=ÉMERGENCE
```

**Important:** Le mot de passe fourni (`dfshbvvsmyqrfkja`) est un **App Password** généré par Google, pas votre mot de passe Gmail habituel.

### 2. Vérifier que Python est installé

```bash
python --version
# ou
python3 --version
```

Vous devez avoir Python 3.8 ou supérieur.

---

## Méthodes d'envoi

Il existe deux méthodes pour envoyer les invitations:

1. **Script Python** (recommandé pour envois en masse)
2. **API REST** (pour intégration dans d'autres applications)

---

## Utilisation du script Python

### Installation

Aucune installation spéciale n'est nécessaire. Le script utilise les dépendances déjà présentes dans votre projet.

### Méthode 1: Envoi à des emails spécifiques

```bash
python send_beta_invitations.py user1@example.com user2@example.com user3@example.com
```

### Méthode 2: Envoi depuis un fichier

1. Créez un fichier texte avec un email par ligne (ex: `beta_testers_emails.txt`):

```text
# Liste des beta testeurs
user1@example.com
user2@example.com
user3@example.com
```

2. Exécutez le script:

```bash
python send_beta_invitations.py --from-file beta_testers_emails.txt
```

### Méthode 3: Combiner les deux

```bash
python send_beta_invitations.py --from-file beta_testers_emails.txt extra1@example.com extra2@example.com
```

### Options avancées

#### Utiliser une URL personnalisée

```bash
python send_beta_invitations.py --base-url https://emergence-app-staging.com user@example.com
```

#### Voir l'aide

```bash
python send_beta_invitations.py --help
```

### Exemple de sortie

```
📧 Sending beta invitations to 3 email(s)...

[1/3] Sending to user1@example.com... ✅ Sent
[2/3] Sending to user2@example.com... ✅ Sent
[3/3] Sending to user3@example.com... ✅ Sent

============================================================
SUMMARY
============================================================
Total: 3
✅ Sent: 3
❌ Failed: 0

✅ Successfully sent to:
  - user1@example.com
  - user2@example.com
  - user3@example.com
```

---

## Utilisation de l'API REST

### Endpoint

```
POST /api/beta-invite
```

### Format de requête

```json
{
  "emails": [
    "user1@example.com",
    "user2@example.com",
    "user3@example.com"
  ],
  "base_url": "https://emergence-app.ch"
}
```

### Exemple avec curl

```bash
curl -X POST "http://localhost:8000/api/beta-invite" \
  -H "Content-Type: application/json" \
  -d '{
    "emails": ["user1@example.com", "user2@example.com"],
    "base_url": "https://emergence-app.ch"
  }'
```

### Exemple avec Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/beta-invite",
    json={
        "emails": [
            "user1@example.com",
            "user2@example.com"
        ],
        "base_url": "https://emergence-app.ch"
    }
)

print(response.json())
```

### Réponse

```json
{
  "status": "completed",
  "total": 2,
  "sent": 2,
  "failed": 0,
  "sent_to": [
    "user1@example.com",
    "user2@example.com"
  ],
  "failed_emails": [],
  "timestamp": "2025-10-13T14:30:00.000000"
}
```

---

## Troubleshooting

### Erreur: "Email service is not configured"

**Problème:** Les variables d'environnement ne sont pas configurées.

**Solution:**
1. Vérifiez que `EMAIL_ENABLED=1` est bien défini
2. Vérifiez que toutes les variables SMTP sont définies
3. Si vous utilisez un fichier `.env`, assurez-vous qu'il est chargé par votre application

### Erreur: "SMTP authentication failed"

**Problème:** Les identifiants Gmail sont incorrects.

**Solution:**
1. Vérifiez que `SMTP_USER` est bien `gonzalefernando@gmail.com`
2. Vérifiez que `SMTP_PASSWORD` est bien l'App Password (`dfshbvvsmyqrfkja`)
3. **Ne pas utiliser votre mot de passe Gmail habituel**, utilisez un App Password

### Comment générer un App Password Google

1. Allez sur [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Sélectionnez "App: Mail" et "Device: Other (custom name)"
3. Nommez-le "EMERGENCE Beta"
4. Copiez le mot de passe généré (16 caractères)
5. Utilisez ce mot de passe dans `SMTP_PASSWORD`

### Erreur: "Connection timeout"

**Problème:** Le port SMTP est bloqué ou le serveur SMTP n'est pas accessible.

**Solution:**
1. Vérifiez votre connexion internet
2. Vérifiez que le port 587 n'est pas bloqué par un firewall
3. Essayez avec `SMTP_PORT=465` et `SMTP_USE_TLS=0`

### Les emails arrivent en spam

**Solution:**
1. Demandez aux destinataires de marquer l'email comme "Pas un spam"
2. Vérifiez que votre compte Gmail a une bonne réputation
3. Évitez d'envoyer trop d'emails d'un coup (maximum 100 par jour pour Gmail)

### Limite d'envoi Gmail

Gmail impose des limites d'envoi:
- **Compte Gmail standard:** 500 emails par jour
- **Google Workspace:** 2000 emails par jour

Si vous dépassez cette limite:
1. Attendez 24 heures
2. Envoyez en plusieurs batches
3. Utilisez un service d'envoi d'emails professionnel (SendGrid, AWS SES, etc.)

---

## Contenu de l'email d'invitation

L'email envoyé contient:

- **Sujet:** "🎉 Bienvenue dans le programme Beta ÉMERGENCE V8"
- **Contenu:**
  - Message de bienvenue
  - Dates de la beta (13 octobre - 3 novembre 2025)
  - Lien vers l'application: https://emergence-app.ch
  - Lien vers le formulaire de rapport: https://emergence-app.ch/beta_report.html
  - Description des 8 phases de test
  - Conseils et instructions
  - Bugs connus
  - Informations de contact

L'email est envoyé en **HTML et texte brut** pour compatibilité maximale.

---

## Exemple d'utilisation complète

### Scénario: Inviter 10 beta testeurs

1. **Créer la liste des emails:**

```bash
cat > beta_testers_emails.txt << EOF
alice@example.com
bob@example.com
charlie@example.com
diane@example.com
eve@example.com
frank@example.com
grace@example.com
henry@example.com
iris@example.com
jack@example.com
EOF
```

2. **Configurer les variables d'environnement:**

```bash
export EMAIL_ENABLED=1
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=gonzalefernando@gmail.com
export SMTP_PASSWORD=dfshbvvsmyqrfkja
export SMTP_FROM_EMAIL=gonzalefernando@gmail.com
```

Ou sur Windows (PowerShell):

```powershell
$env:EMAIL_ENABLED="1"
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="gonzalefernando@gmail.com"
$env:SMTP_PASSWORD="dfshbvvsmyqrfkja"
$env:SMTP_FROM_EMAIL="gonzalefernando@gmail.com"
```

3. **Envoyer les invitations:**

```bash
python send_beta_invitations.py --from-file beta_testers_emails.txt
```

4. **Vérifier les résultats:**

Le script affichera un résumé avec le nombre d'emails envoyés et échoués.

---

## Support

Pour toute question ou problème:
- **Email:** gonzalefernando@gmail.com
- **Documentation:** [BETA_PROGRAM.md](BETA_PROGRAM.md)

---

**Dernière mise à jour:** 2025-10-13
**Maintenu par:** Équipe ÉMERGENCE
