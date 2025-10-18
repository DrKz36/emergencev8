# Système d'invitations Beta ÉMERGENCE - Récapitulatif

## Résumé de la solution

Vous disposez maintenant d'un système complet et automatisé pour envoyer des invitations beta par email en utilisant votre compte Gmail (`gonzalefernando@gmail.com`) avec le mot de passe d'application fourni.

## Fichiers créés

### 1. Code Backend

#### [src/backend/features/auth/email_service.py](src/backend/features/auth/email_service.py)
- **Modifié** : Ajout de la méthode `send_beta_invitation_email()`
- Envoie des emails HTML stylisés avec templates professionnels
- Utilise SMTP Gmail avec authentification sécurisée

#### [src/backend/features/beta_report/router.py](src/backend/features/beta_report/router.py)
- **Modifié** : Ajout de l'endpoint `/api/beta-invite`
- Endpoint REST pour envoyer des invitations en masse
- Intégration avec le service email
- Gestion automatique des succès/échecs

### 2. Scripts Python

#### [send_beta_invitations.py](send_beta_invitations.py)
**Script principal pour envoyer les invitations**

```bash
# Envoyer à des emails spécifiques
python send_beta_invitations.py user1@example.com user2@example.com

# Envoyer depuis un fichier
python send_beta_invitations.py --from-file beta_testers_emails.txt
```

#### [test_email_sending.py](test_email_sending.py)
**Script de test pour vérifier la configuration**

```bash
python test_email_sending.py
```

#### [fetch_allowlist_emails.py](fetch_allowlist_emails.py)
**Script pour récupérer automatiquement les emails de l'allowlist**

```bash
python fetch_allowlist_emails.py
```

### 3. Configuration

#### [.env.beta.example](.env.beta.example)
Template pour les variables d'environnement avec vos identifiants Gmail pré-remplis.

#### [beta_testers_emails.txt](beta_testers_emails.txt)
Fichier template pour la liste des emails des beta testeurs.

### 4. Interface Web

#### [beta_invitations.html](beta_invitations.html)
**Interface graphique intuitive pour envoyer les invitations**
- Chargement automatique de l'allowlist en un clic
- Saisie manuelle d'emails
- Email de test
- Affichage des résultats en temps réel
- Design moderne et responsive

[📖 Guide complet de l'interface](GUIDE_INTERFACE_BETA.md)

### 5. Documentation

#### [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md)
Guide complet et détaillé avec:
- Instructions de configuration
- Toutes les méthodes d'utilisation
- Troubleshooting complet
- Exemples pratiques

#### [BETA_QUICK_START.md](BETA_QUICK_START.md)
Guide rapide en 5 minutes pour démarrer immédiatement.

#### [GUIDE_INTERFACE_BETA.md](GUIDE_INTERFACE_BETA.md)
Guide d'utilisation de l'interface web.

#### [BETA_INVITATIONS_SUMMARY.md](BETA_INVITATIONS_SUMMARY.md)
Ce fichier - récapitulatif de tous les composants.

---

## 🌟 Guide d'utilisation rapide

### ⚡ MÉTHODE RECOMMANDÉE: Interface Web (30 secondes!)

C'est la méthode la plus simple et intuitive:

1. **Ouvrir** `beta_invitations.html` dans votre navigateur
2. **Cliquer** sur "📋 Charger l'allowlist"
3. **Cliquer** sur "🚀 Envoyer les invitations"
4. **Confirmer** et c'est tout!

[📖 Guide complet de l'interface](GUIDE_INTERFACE_BETA.md)

---

### 💻 Méthode alternative: Scripts Python

## Guide d'utilisation rapide

### Étape 1: Configuration (1 minute)

Sur **Windows PowerShell**:

```powershell
$env:EMAIL_ENABLED="1"
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="gonzalefernando@gmail.com"
$env:SMTP_PASSWORD="dfshbvvsmyqrfkja"
$env:SMTP_FROM_EMAIL="gonzalefernando@gmail.com"
```

Sur **Linux/Mac**:

```bash
export EMAIL_ENABLED=1
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=gonzalefernando@gmail.com
export SMTP_PASSWORD=dfshbvvsmyqrfkja
export SMTP_FROM_EMAIL=gonzalefernando@gmail.com
```

### Étape 2: Test (optionnel)

```bash
python test_email_sending.py
```

### Étape 3: Récupérer les emails de l'allowlist

```bash
python fetch_allowlist_emails.py
```

Cela créera automatiquement `beta_testers_emails.txt` avec tous les emails actifs.

### Étape 4: Envoyer les invitations

```bash
python send_beta_invitations.py --from-file beta_testers_emails.txt
```

---

## Contenu de l'email d'invitation

Les beta testeurs recevront un email professionnel contenant:

### En-tête
- Logo ÉMERGENCE
- Titre accrocheur: "🎉 Bienvenue dans le programme Beta ÉMERGENCE V8"

### Corps de l'email
1. **Message de bienvenue**
2. **Dates de la beta**: 13 octobre - 3 novembre 2025
3. **Accès à la plateforme**: Lien cliquable vers https://emergence-app.ch
4. **8 phases de test** détaillées:
   - Phase 1: Authentification & Onboarding
   - Phase 2: Chat avec agents
   - Phase 3: Système de mémoire
   - Phase 4: Documents & RAG
   - Phase 5: Débats autonomes
   - Phase 6: Cockpit & Analytics
   - Phase 7: Tests de robustesse
   - Phase 8: Edge cases
5. **Lien vers le formulaire**: https://emergence-app.ch/beta_report.html
6. **Conseils pratiques**
7. **Bugs connus** (mention)
8. **Informations de contact**: gonzalefernando@gmail.com

### Format
- Email **HTML** avec design moderne et professionnel
- Email **texte brut** en fallback pour compatibilité maximale
- Responsive et lisible sur tous les appareils

---

## Architecture technique

### Flux d'envoi d'email

```
Script Python
    ↓
EmailService (email_service.py)
    ↓
Configuration SMTP (variables d'env)
    ↓
Gmail SMTP (smtp.gmail.com:587)
    ↓
Beta Testeur
```

### Sécurité

- **App Password Google**: Le mot de passe fourni (`dfshbvvsmyqrfkja`) est un App Password, pas votre mot de passe Gmail réel
- **TLS/SSL**: Connexion chiffrée avec Gmail
- **Variables d'environnement**: Pas de credentials hardcodés dans le code
- **Logging**: Toutes les tentatives d'envoi sont loggées

### Gestion des erreurs

Le système gère automatiquement:
- Échecs d'authentification SMTP
- Timeouts de connexion
- Emails invalides
- Limites de taux Gmail
- Erreurs réseau

Chaque email est traité individuellement, donc un échec n'affecte pas les autres.

---

## API REST

### Endpoint: POST /api/beta-invite

**Request:**
```json
{
  "emails": ["user1@example.com", "user2@example.com"],
  "base_url": "https://emergence-app.ch"
}
```

**Response:**
```json
{
  "status": "completed",
  "total": 2,
  "sent": 2,
  "failed": 0,
  "sent_to": ["user1@example.com", "user2@example.com"],
  "failed_emails": [],
  "timestamp": "2025-10-13T14:30:00"
}
```

**Exemple curl:**
```bash
curl -X POST "http://localhost:8000/api/beta-invite" \
  -H "Content-Type: application/json" \
  -d '{"emails": ["test@example.com"], "base_url": "https://emergence-app.ch"}'
```

---

## Workflow recommandé

### Pour la Beta 1.0

1. **Récupérer les emails de l'allowlist**
   ```bash
   python fetch_allowlist_emails.py
   ```

2. **Vérifier la liste**
   - Ouvrir `beta_testers_emails.txt`
   - Vérifier que tous les emails sont corrects
   - Ajouter/supprimer des emails si nécessaire

3. **Tester avec votre propre email**
   ```bash
   python send_beta_invitations.py gonzalefernando@gmail.com
   ```

4. **Envoyer à tous les testeurs**
   ```bash
   python send_beta_invitations.py --from-file beta_testers_emails.txt
   ```

5. **Vérifier les résultats**
   - Le script affiche un résumé avec le nombre d'envois réussis/échoués
   - Consulter les logs pour plus de détails

### Pour des invitations supplémentaires

Si vous devez inviter d'autres personnes plus tard:

```bash
# Ajouter les emails à beta_testers_emails.txt, puis:
python send_beta_invitations.py user.new@example.com

# Ou envoyer à plusieurs nouveaux testeurs:
python send_beta_invitations.py user1@new.com user2@new.com user3@new.com
```

---

## Limites et quotas

### Gmail Standard (compte personnel)
- **500 emails par jour** maximum
- Recommandation: Ne pas dépasser 100 emails par heure

### Solutions si vous dépassez les limites
1. **Attendre 24h** pour que le quota se réinitialise
2. **Envoyer en plusieurs batches** sur plusieurs jours
3. **Utiliser un service professionnel**: SendGrid, AWS SES, Mailgun (nécessite modification du code)

---

## Troubleshooting

### Erreur commune: "Email service not configured"
→ Variables d'environnement non définies. Exécutez les commandes de l'Étape 1.

### Erreur: "SMTP authentication failed"
→ Vérifiez que le mot de passe est exactement `dfshbvvsmyqrfkja`

### Emails en spam
→ Normal pour les premiers envois. Demandez aux testeurs de marquer comme "Pas un spam"

### Script ne trouve pas les modules
→ Assurez-vous d'être à la racine du projet (`c:\dev\emergenceV8`)

Pour plus de détails, consultez [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md)

---

## Prochaines étapes

1. **Tester l'envoi** avec votre propre email
2. **Récupérer la liste des testeurs** depuis l'allowlist
3. **Envoyer les invitations** à tous les testeurs
4. **Monitorer les réceptions** et répondre aux questions

---

## Support

- **Email**: gonzalefernando@gmail.com
- **Documentation Beta**: [docs/BETA_PROGRAM.md](docs/BETA_PROGRAM.md)
- **Guide invitations**: [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md)

---

**Date de création**: 2025-10-13
**Système prêt pour la Beta 1.0**
