# 📧 Comment envoyer les invitations Beta - Guide Ultra-Simple

## 🎯 Objectif
Envoyer des invitations beta à tous les testeurs inscrits dans l'allowlist.

---

## ⚡ Méthode la plus simple (RECOMMANDÉE)

### Étape 1: Configurer l'email (une seule fois)

**Sur Windows** (PowerShell):
```powershell
$env:EMAIL_ENABLED="1"
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="gonzalefernando@gmail.com"
$env:SMTP_PASSWORD="dfshbvvsmyqrfkja"
$env:SMTP_FROM_EMAIL="gonzalefernando@gmail.com"
```

Ou créez un fichier `.env` avec:
```
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=gonzalefernando@gmail.com
SMTP_PASSWORD=dfshbvvsmyqrfkja
SMTP_FROM_EMAIL=gonzalefernando@gmail.com
```

### Étape 2: Démarrer le backend

```bash
npm run backend
```

Ou si vous utilisez l'environnement virtuel:
```bash
npm run start:venv
```

### Étape 3: Ouvrir l'interface web

1. **Double-cliquez** sur `beta_invitations.html`

   Ou ouvrez dans votre navigateur: `http://localhost:8000/beta_invitations.html`

2. Vous verrez cette interface:

```
╔═══════════════════════════════════════════════════════╗
║        🚀 ÉMERGENCE Beta                              ║
║     Système d'envoi d'invitations beta                ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  Actions rapides:                                     ║
║  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ║
║  │📋 Charger    │ │✉️ Email de   │ │🗑️ Vider la   │ ║
║  │  l'allowlist │ │   test       │ │   liste      │ ║
║  └──────────────┘ └──────────────┘ └──────────────┘ ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
```

### Étape 4: Charger les emails

**Cliquez sur le bouton "📋 Charger l'allowlist"**

→ Tous les emails de l'allowlist apparaissent automatiquement!

### Étape 5: Envoyer!

**Cliquez sur "🚀 Envoyer les invitations"**

→ Confirmez l'envoi

→ Patientez quelques secondes

→ Les résultats s'affichent!

```
╔═══════════════════════════════════════════╗
║  📊 Résultats de l'envoi                  ║
╠═══════════════════════════════════════════╣
║  Total: 10                                ║
║  Envoyés ✅: 10                           ║
║  Échoués ❌: 0                            ║
╠═══════════════════════════════════════════╣
║  ✅ Emails envoyés avec succès:          ║
║    user1@example.com                      ║
║    user2@example.com                      ║
║    ...                                    ║
╚═══════════════════════════════════════════╝
```

**C'EST TOUT! 🎉**

---

## 📱 Cas d'utilisation

### Cas 1: Envoyer à TOUS les testeurs

1. Ouvrir `beta_invitations.html`
2. Cliquer "📋 Charger l'allowlist"
3. Cliquer "🚀 Envoyer les invitations"
4. ✅ Fait!

**Temps**: 30 secondes

---

### Cas 2: Envoyer à quelques personnes spécifiques

1. Ouvrir `beta_invitations.html`
2. Saisir les emails dans la zone de texte:
   ```
   nouveau1@example.com
   nouveau2@example.com
   nouveau3@example.com
   ```
3. Cliquer "🚀 Envoyer les invitations"
4. ✅ Fait!

**Temps**: 1 minute

---

### Cas 3: Tester d'abord avec mon email

1. Ouvrir `beta_invitations.html`
2. Cliquer "✉️ Email de test"
3. Saisir `gonzalefernando@gmail.com`
4. Cliquer "🚀 Envoyer les invitations"
5. Vérifier votre boîte email
6. Si OK, envoyer à tous!

**Temps**: 2 minutes

---

## ❓ Questions fréquentes

### Q: Où trouver le fichier `beta_invitations.html` ?
**R**: À la racine de votre projet: `c:\dev\emergenceV8\beta_invitations.html`

### Q: Comment savoir si l'email est bien configuré ?
**R**: Lancez le test:
```bash
python test_email_sending.py
```

### Q: L'interface ne charge pas l'allowlist
**R**: Vérifiez que:
1. Le backend est démarré (`npm run backend`)
2. Les variables d'environnement sont définies
3. Vous accédez via `http://localhost:8000/beta_invitations.html` (pas `file://`)

### Q: Les emails arrivent en spam
**R**: C'est normal pour les premiers envois. Demandez aux testeurs de:
- Marquer l'email comme "Pas un spam"
- Ajouter `gonzalefernando@gmail.com` à leurs contacts

### Q: Combien d'emails puis-je envoyer ?
**R**: Gmail limite à **500 emails par jour**. C'est largement suffisant pour la beta.

### Q: Je veux automatiser l'envoi
**R**: Utilisez les scripts Python:
```bash
python send_beta_invitations.py --from-file beta_testers_emails.txt
```

---

## 🎨 Aperçu de l'email envoyé

Les testeurs recevront un magnifique email avec:

```
╔═══════════════════════════════════════════════════════╗
║  🎉 ÉMERGENCE V8                                      ║
║  Programme Beta 1.0                                   ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  Bonjour,                                             ║
║                                                       ║
║  Nous sommes ravis de vous inviter au programme      ║
║  Beta ÉMERGENCE V8! 🚀                                ║
║                                                       ║
║  📅 Dates: 13 octobre - 3 novembre 2025              ║
║  🎯 Objectif: Tester la plateforme                   ║
║                                                       ║
║  ┌─────────────────────────────────────────┐         ║
║  │  🚀 Accéder à ÉMERGENCE                 │         ║
║  └─────────────────────────────────────────┘         ║
║                                                       ║
║  ✅ 8 phases de test à explorer:                     ║
║     📝 Phase 1: Authentification & Onboarding        ║
║     💬 Phase 2: Chat avec agents                     ║
║     🧠 Phase 3: Système de mémoire                   ║
║     📄 Phase 4: Documents & RAG                      ║
║     🎭 Phase 5: Débats autonomes                     ║
║     📊 Phase 6: Cockpit & Analytics                  ║
║     ⚡ Phase 7: Tests de robustesse                  ║
║     🐛 Phase 8: Edge cases                           ║
║                                                       ║
║  ┌─────────────────────────────────────────┐         ║
║  │  📝 Remplir le formulaire de test       │         ║
║  └─────────────────────────────────────────┘         ║
║                                                       ║
║  Merci infiniment! 🙏                                 ║
║  L'équipe d'Émergence                                 ║
║  FG, Claude et Codex                                  ║
╚═══════════════════════════════════════════════════════╝
```

---

## 🆘 Besoin d'aide ?

### Option 1: Documentation complète
- [GUIDE_INTERFACE_BETA.md](GUIDE_INTERFACE_BETA.md) - Guide détaillé de l'interface
- [BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md) - Guide complet avec troubleshooting

### Option 2: Scripts Python
Si vous préférez la ligne de commande, consultez:
- [BETA_QUICK_START.md](BETA_QUICK_START.md)

### Option 3: Contact
📧 gonzalefernando@gmail.com

---

## ✅ Checklist finale

Avant d'envoyer les invitations:

- [ ] Backend démarré (`npm run backend`)
- [ ] Variables d'environnement configurées
- [ ] Test effectué avec mon email (`✉️ Email de test`)
- [ ] Email reçu et validé dans ma boîte
- [ ] Prêt à envoyer à tous!

**GO! 🚀**

---

**Dernière mise à jour**: 2025-10-13
**Temps total pour envoyer les invitations**: 30 secondes
