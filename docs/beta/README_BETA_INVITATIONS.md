# 📧 Système d'envoi des invitations Beta ÉMERGENCE

## 🚀 Démarrage rapide - 3 étapes

### 1️⃣ Configurer l'email (une seule fois)

Créez un fichier `.env` ou définissez ces variables:

```bash
EMAIL_ENABLED=1
SMTP_USER=gonzalefernando@gmail.com
SMTP_PASSWORD=dfshbvvsmyqrfkja
```

### 2️⃣ Démarrer le backend

```bash
npm run backend
```

### 3️⃣ Ouvrir l'interface et envoyer

Double-cliquez sur **`beta_invitations.html`**

Puis:
1. Cliquez sur "📋 Charger l'allowlist"
2. Cliquez sur "🚀 Envoyer les invitations"

**C'est tout! 🎉**

---

## 📚 Documentation

| Fichier | Description | Temps |
|---------|-------------|-------|
| [COMMENT_ENVOYER_INVITATIONS.md](COMMENT_ENVOYER_INVITATIONS.md) | **Guide ultra-simple avec visuels** | 2 min |
| [GUIDE_INTERFACE_BETA.md](GUIDE_INTERFACE_BETA.md) | Guide complet de l'interface web | 5 min |
| [BETA_QUICK_START.md](BETA_QUICK_START.md) | Guide rapide scripts Python | 5 min |
| [BETA_INVITATIONS_SUMMARY.md](BETA_INVITATIONS_SUMMARY.md) | Récapitulatif technique complet | 10 min |
| [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md) | Documentation complète avec troubleshooting | 15 min |

---

## 🎯 Choix de la méthode

### Méthode 1: Interface Web 🌐 (Recommandé)
**Pour**: Utilisation simple et visuelle
**Fichier**: `beta_invitations.html`
**Guide**: [GUIDE_INTERFACE_BETA.md](GUIDE_INTERFACE_BETA.md)

**Avantages**:
- ✅ Interface graphique intuitive
- ✅ Chargement de l'allowlist en 1 clic
- ✅ Résultats en temps réel
- ✅ Aucune ligne de commande

---

### Méthode 2: Scripts Python 💻
**Pour**: Automatisation et batch processing
**Fichier**: `send_beta_invitations.py`
**Guide**: [BETA_QUICK_START.md](BETA_QUICK_START.md)

**Avantages**:
- ✅ Automatisable avec cron/scheduled tasks
- ✅ Scriptable
- ✅ Logs détaillés

---

### Méthode 3: API REST 🔌
**Pour**: Intégration dans d'autres applications
**Endpoint**: `POST /api/beta-invite`
**Guide**: [BETA_INVITATIONS_SUMMARY.md](BETA_INVITATIONS_SUMMARY.md#api-rest)

**Avantages**:
- ✅ Intégration avec d'autres systèmes
- ✅ Automatisation avancée

---

## 📁 Fichiers créés

### Interface & Scripts
- `beta_invitations.html` - Interface web principale
- `send_beta_invitations.py` - Script d'envoi en masse
- `test_email_sending.py` - Script de test
- `fetch_allowlist_emails.py` - Récupération de l'allowlist

### Configuration
- `.env.beta.example` - Template de configuration
- `beta_testers_emails.txt` - Template liste emails

### Documentation
- `README_BETA_INVITATIONS.md` - Ce fichier (point d'entrée)
- `COMMENT_ENVOYER_INVITATIONS.md` - Guide ultra-simple
- `GUIDE_INTERFACE_BETA.md` - Guide interface web
- `BETA_QUICK_START.md` - Guide scripts Python
- `BETA_INVITATIONS_SUMMARY.md` - Récapitulatif technique
- `docs/BETA_INVITATIONS.md` - Documentation complète

### Code Backend
- `src/backend/features/auth/email_service.py` (modifié)
- `src/backend/features/beta_report/router.py` (modifié)

---

## ✉️ Contenu de l'email

Les testeurs recevront:
- 🎉 Message de bienvenue au programme Beta 1.0
- 📅 Dates: 13 octobre - 3 novembre 2025
- 🔗 Lien vers l'application: https://emergence-app.ch
- 📝 Lien vers le formulaire: https://emergence-app.ch/beta_report.html
- ✅ Description des 8 phases de test
- 💡 Conseils et instructions
- 📧 Contact: gonzalefernando@gmail.com

Format: **HTML professionnel + texte brut**

---

## 🔧 Configuration technique

### Variables d'environnement requises

```bash
EMAIL_ENABLED=1                              # Activer le service email
SMTP_HOST=smtp.gmail.com                     # Serveur SMTP Gmail
SMTP_PORT=587                                # Port TLS
SMTP_USER=gonzalefernando@gmail.com          # Votre email Gmail
SMTP_PASSWORD=dfshbvvsmyqrfkja               # App Password Google
SMTP_FROM_EMAIL=gonzalefernando@gmail.com    # Email expéditeur
```

**Note**: Le mot de passe (`dfshbvvsmyqrfkja`) est un **App Password Google**, pas votre mot de passe Gmail habituel.

---

## 📊 Limites

- **Gmail Standard**: 500 emails/jour
- **Recommandation**: Max 100 emails/heure
- **Solution si dépassement**: Attendre 24h ou utiliser un service professionnel

---

## 🆘 Aide rapide

### Problème: L'interface ne charge pas l'allowlist
✅ **Solution**:
1. Vérifier que le backend est démarré
2. Accéder via `http://localhost:8000/beta_invitations.html` (pas `file://`)

### Problème: Erreur "Email service not configured"
✅ **Solution**: Définir les variables d'environnement (voir section Configuration)

### Problème: "SMTP authentication failed"
✅ **Solution**: Vérifier que le mot de passe est exactement `dfshbvvsmyqrfkja`

### Autres problèmes
📖 Consultez [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md#troubleshooting)

---

## 🎯 Workflows typiques

### Workflow 1: Premier envoi à tous les testeurs
```
1. Ouvrir beta_invitations.html
2. Cliquer "📋 Charger l'allowlist"
3. Cliquer "🚀 Envoyer les invitations"
4. ✅ Fait en 30 secondes!
```

### Workflow 2: Envoyer à quelques nouveaux testeurs
```
1. Ouvrir beta_invitations.html
2. Saisir les emails manuellement
3. Cliquer "🚀 Envoyer les invitations"
4. ✅ Fait en 1 minute!
```

### Workflow 3: Test avant envoi massif
```
1. Ouvrir beta_invitations.html
2. Cliquer "✉️ Email de test"
3. Saisir gonzalefernando@gmail.com
4. Cliquer "🚀 Envoyer les invitations"
5. Vérifier l'email reçu
6. Si OK → Envoyer à tous
7. ✅ Fait en 2 minutes!
```

---

## 📞 Support

- **Email**: gonzalefernando@gmail.com
- **Doc Beta**: [docs/BETA_PROGRAM.md](docs/BETA_PROGRAM.md)
- **Doc Invitations**: [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md)

---

## 🎉 Récapitulatif

Vous avez maintenant **3 méthodes** pour envoyer des invitations:

1. **Interface Web** (`beta_invitations.html`) - **RECOMMANDÉ**
2. **Scripts Python** (`send_beta_invitations.py`)
3. **API REST** (`POST /api/beta-invite`)

Choisissez celle qui vous convient le mieux!

**Pour commencer immédiatement**: Lisez [COMMENT_ENVOYER_INVITATIONS.md](COMMENT_ENVOYER_INVITATIONS.md)

---

**Créé le**: 2025-10-13
**Statut**: ✅ Prêt pour production
**Système testé**: ✅ Oui
