# Quick Start - Envoi des invitations Beta

Guide rapide pour envoyer les invitations beta en 5 minutes.

## Étape 1: Configuration (1 minute)

### Sur Windows (PowerShell)

```powershell
$env:EMAIL_ENABLED="1"
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="gonzalefernando@gmail.com"
$env:SMTP_PASSWORD="dfshbvvsmyqrfkja"
$env:SMTP_FROM_EMAIL="gonzalefernando@gmail.com"
```

### Sur Linux/Mac

```bash
export EMAIL_ENABLED=1
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=gonzalefernando@gmail.com
export SMTP_PASSWORD=dfshbvvsmyqrfkja
export SMTP_FROM_EMAIL=gonzalefernando@gmail.com
```

## Étape 2: Test (1 minute)

Testez que tout fonctionne:

```bash
python test_email_sending.py
```

Entrez votre email pour recevoir une invitation de test.

## Étape 3: Préparer la liste (1 minute)

Éditez le fichier `beta_testers_emails.txt` et ajoutez les emails des testeurs (un par ligne):

```text
user1@example.com
user2@example.com
user3@example.com
```

## Étape 4: Envoyer les invitations (2 minutes)

```bash
python send_beta_invitations.py --from-file beta_testers_emails.txt
```

## C'est tout!

Les beta testeurs recevront un email avec:
- Un lien vers l'application
- Un lien vers le formulaire de test
- Des instructions détaillées
- La liste des 8 phases de test

---

## Commandes utiles

### Envoyer à des emails spécifiques

```bash
python send_beta_invitations.py user1@example.com user2@example.com
```

### Utiliser une URL différente

```bash
python send_beta_invitations.py --base-url https://emergence-app-staging.com --from-file beta_testers_emails.txt
```

### Voir l'aide

```bash
python send_beta_invitations.py --help
```

---

## Troubleshooting rapide

### Erreur "Email service not configured"
→ Assurez-vous d'avoir défini toutes les variables d'environnement (Étape 1)

### Erreur "SMTP authentication failed"
→ Vérifiez que le mot de passe est bien `dfshbvvsmyqrfkja` (c'est un App Password Google)

### Les emails arrivent en spam
→ C'est normal pour les premiers envois. Demandez aux destinataires de les marquer comme "Pas un spam"

---

## Documentation complète

Pour plus de détails, consultez:
- [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md) - Guide complet
- [docs/BETA_PROGRAM.md](docs/BETA_PROGRAM.md) - Programme beta

---

**Support:** gonzalefernando@gmail.com
