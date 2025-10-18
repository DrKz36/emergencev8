# 🎯 DÉMARRAGE - Envoi des invitations Beta

## 🚀 La méthode la plus simple (30 secondes)

### Sur Windows

1. **Double-cliquez** sur ce fichier:
   ```
   📄 envoyer_invitations_beta.bat
   ```

2. Suivez les instructions à l'écran

3. **C'EST TOUT!** 🎉

---

### Sur Mac/Linux

1. **Démarrez le backend**:
   ```bash
   npm run backend
   ```

2. **Configurez l'email** (une seule fois):
   ```bash
   export EMAIL_ENABLED=1
   export SMTP_USER=gonzalefernando@gmail.com
   export SMTP_PASSWORD=dfshbvvsmyqrfkja
   ```

3. **Ouvrez** `beta_invitations.html` dans votre navigateur

4. **Cliquez**:
   - "📋 Charger l'allowlist"
   - "🚀 Envoyer les invitations"

5. **C'EST TOUT!** 🎉

---

## 📚 Documentation complète

Si vous voulez en savoir plus:

| Document | Pour qui ? | Temps |
|----------|-----------|-------|
| **[COMMENT_ENVOYER_INVITATIONS.md](COMMENT_ENVOYER_INVITATIONS.md)** | 🌟 Tout le monde - Guide visuel simple | 2 min |
| [README_BETA_INVITATIONS.md](README_BETA_INVITATIONS.md) | Point d'entrée avec toutes les infos | 3 min |
| [GUIDE_INTERFACE_BETA.md](GUIDE_INTERFACE_BETA.md) | Guide détaillé de l'interface | 5 min |
| [BETA_QUICK_START.md](BETA_QUICK_START.md) | Démarrage rapide avec scripts Python | 5 min |
| [BETA_INVITATIONS_SUMMARY.md](BETA_INVITATIONS_SUMMARY.md) | Récapitulatif technique complet | 10 min |
| [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md) | Documentation exhaustive | 15 min |

**Recommandation**: Commencez par [COMMENT_ENVOYER_INVITATIONS.md](COMMENT_ENVOYER_INVITATIONS.md)

---

## 🎯 Cas d'usage rapides

### Cas 1: Je veux envoyer à TOUS les testeurs
```
👉 Double-cliquez: envoyer_invitations_beta.bat
   Puis suivez les instructions
```

### Cas 2: Je veux envoyer à quelques personnes
```
👉 Ouvrez: beta_invitations.html
   Saisissez les emails manuellement
   Cliquez "🚀 Envoyer"
```

### Cas 3: Je veux tester d'abord
```
👉 Ouvrez: beta_invitations.html
   Cliquez "✉️ Email de test"
   Saisissez votre email
   Vérifiez la réception
```

### Cas 4: Je préfère la ligne de commande
```bash
👉 python send_beta_invitations.py --from-file beta_testers_emails.txt
```

---

## 🛠️ Fichiers importants

### Pour utiliser immédiatement
- `envoyer_invitations_beta.bat` ← **Double-cliquez ici (Windows)**
- `beta_invitations.html` ← **Ouvrez dans le navigateur**

### Scripts Python (optionnel)
- `send_beta_invitations.py` - Envoi en masse
- `test_email_sending.py` - Test de configuration
- `fetch_allowlist_emails.py` - Récupération allowlist

### Configuration (optionnel)
- `.env.beta.example` - Template configuration
- `beta_testers_emails.txt` - Template liste emails

---

## ⚙️ Configuration minimale requise

Pour que tout fonctionne, vous devez avoir:

### 1. Variables d'environnement (automatique avec le .bat)
```
EMAIL_ENABLED=1
SMTP_USER=gonzalefernando@gmail.com
SMTP_PASSWORD=dfshbvvsmyqrfkja
```

### 2. Backend démarré
```bash
npm run backend
```

**C'est tout!** Le reste est automatique.

---

## 🎨 Aperçu

### L'interface web ressemble à ça:

```
╔═══════════════════════════════════════════════════════╗
║        🚀 ÉMERGENCE Beta                              ║
║     Système d'envoi d'invitations beta                ║
╠═══════════════════════════════════════════════════════╣
║  Actions rapides:                                     ║
║  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ║
║  │📋 Charger    │ │✉️ Email de   │ │🗑️ Vider la   │ ║
║  │  l'allowlist │ │   test       │ │   liste      │ ║
║  └──────────────┘ └──────────────┘ └──────────────┘ ║
╠═══════════════════════════════════════════════════════╣
║  📧 Destinataires            [12 email(s)]            ║
║  ┌─────────────────────────────────────────────────┐ ║
║  │ user1@example.com                               │ ║
║  │ user2@example.com                               │ ║
║  │ user3@example.com                               │ ║
║  │ ...                                             │ ║
║  └─────────────────────────────────────────────────┘ ║
║                                                       ║
║  ┌─────────────────────────────────────────────────┐ ║
║  │     🚀 Envoyer les invitations                  │ ║
║  └─────────────────────────────────────────────────┘ ║
╚═══════════════════════════════════════════════════════╝
```

Simple et intuitif!

---

## 💡 Conseils

### Premier envoi
1. **Testez d'abord** avec votre propre email
2. **Vérifiez** que l'email est bien reçu
3. **Puis envoyez** à tous les testeurs

### Si vous avez des doutes
- Lisez [COMMENT_ENVOYER_INVITATIONS.md](COMMENT_ENVOYER_INVITATIONS.md)
- C'est très visuel et facile à suivre!

### Pour aller plus loin
- Consultez [README_BETA_INVITATIONS.md](README_BETA_INVITATIONS.md)
- Toutes les méthodes y sont expliquées

---

## 🆘 Problème ?

### L'interface ne s'ouvre pas
→ Le backend n'est pas démarré. Lancez: `npm run backend`

### L'interface ne charge pas les emails
→ Accédez via `http://localhost:8000/beta_invitations.html` (pas file://)

### Les emails ne partent pas
→ Vérifiez les variables d'environnement (voir .env.beta.example)

### Autre problème
→ Consultez [docs/BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md#troubleshooting)

---

## 📧 Support

**Email**: gonzalefernando@gmail.com

---

## 🎉 Résumé

**Ce que vous devez faire**:
1. Double-cliquez sur `envoyer_invitations_beta.bat` (Windows)
   OU ouvrez `beta_invitations.html` (Mac/Linux)
2. Cliquez sur 2 boutons
3. C'est terminé!

**Temps total**: 30 secondes

**Nombre de clics**: 2

**Difficulté**: ⭐☆☆☆☆ (très facile)

---

**Créé le**: 2025-10-13
**Statut**: ✅ Prêt à l'emploi
**Testé**: ✅ Oui

---

# 👉 PROCHAINE ÉTAPE

**Lisez**: [COMMENT_ENVOYER_INVITATIONS.md](COMMENT_ENVOYER_INVITATIONS.md)

C'est un guide visuel simple qui vous montre exactement quoi faire, étape par étape!
