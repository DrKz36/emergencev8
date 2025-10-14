# Guide d'utilisation - Interface Web d'envoi des invitations Beta

## Accès à l'interface

L'interface est accessible via le fichier HTML:

**URL locale**: `file:///c:/dev/emergenceV8/beta_invitations.html`

Ou si votre serveur est démarré:

**URL serveur**: `http://localhost:8000/beta_invitations.html`
**URL production**: `https://emergence-app.ch/beta_invitations.html`

---

## Utilisation de l'interface

### Vue d'ensemble

L'interface comprend 3 sections principales:

1. **Actions rapides** - Boutons pour les actions courantes
2. **Formulaire d'envoi** - Zone principale pour saisir les emails
3. **Résultats** - Affichage des résultats après envoi

---

## Guide pas à pas

### Méthode 1: Charger depuis l'allowlist (Recommandé)

C'est la méthode la plus simple pour envoyer des invitations à tous vos beta testeurs.

1. **Ouvrir l'interface**
   - Ouvrez le fichier `beta_invitations.html` dans votre navigateur
   - Ou accédez à `http://localhost:8000/beta_invitations.html`

2. **Cliquer sur "📋 Charger l'allowlist"**
   - Cette action récupère automatiquement tous les emails actifs de votre allowlist
   - Les emails s'affichent dans la zone de texte
   - Le compteur s'actualise automatiquement

3. **Vérifier l'URL de base**
   - Par défaut: `https://emergence-app.ch`
   - Modifiez si nécessaire (ex: pour staging/dev)

4. **Cliquer sur "🚀 Envoyer les invitations"**
   - Une confirmation s'affiche avec le nombre d'emails
   - Confirmez l'envoi
   - Un spinner s'affiche pendant l'envoi

5. **Consulter les résultats**
   - Les résultats s'affichent automatiquement
   - Statistiques: Total / Envoyés / Échoués
   - Liste détaillée des emails envoyés et échoués

---

### Méthode 2: Saisie manuelle

Pour envoyer à des emails spécifiques.

1. **Saisir les emails directement**
   - Dans la zone "Liste des emails"
   - Un email par ligne
   - Les lignes vides sont ignorées
   - Les commentaires (lignes commençant par #) sont ignorés

   Exemple:
   ```
   user1@example.com
   user2@example.com
   # Ceci est un commentaire
   user3@example.com
   ```

2. **Le compteur s'actualise automatiquement**
   - Affiche le nombre d'emails valides

3. **Cliquer sur "🚀 Envoyer les invitations"**

---

### Méthode 3: Email de test

Pour tester l'envoi avant d'envoyer à tous.

1. **Cliquer sur "✉️ Email de test"**
2. **Saisir votre email** dans la fenêtre popup
3. **Cliquer sur "🚀 Envoyer les invitations"**
4. **Vérifier votre boîte email** (et spam!)

---

## Fonctionnalités de l'interface

### Actions rapides

#### 📋 Charger l'allowlist
- Récupère automatiquement tous les emails actifs de l'allowlist
- Remplace le contenu actuel de la zone de texte
- Idéal pour envoyer à tous les testeurs en un clic

#### ✉️ Email de test
- Permet d'envoyer une invitation de test à votre propre email
- Utile pour vérifier le contenu et le rendu de l'email

#### 🗑️ Vider la liste
- Efface tous les emails de la zone de texte
- Demande confirmation avant de vider

### Formulaire d'envoi

#### Zone de texte des emails
- Supporte plusieurs formats:
  - Un email par ligne
  - Lignes vides (ignorées)
  - Commentaires avec # (ignorés)
- Détecte automatiquement les doublons (retirés)
- Validation: seules les lignes contenant @ sont considérées

#### URL de base
- URL utilisée dans les liens de l'email
- Par défaut: `https://emergence-app.ch`
- Peut être changée pour:
  - Staging: `https://emergence-app-staging.com`
  - Dev local: `http://localhost:8000`

#### Bouton "Envoyer les invitations"
- Envoie les invitations via l'API
- Affiche un spinner pendant l'envoi
- Désactivé pendant l'envoi (évite les doubles clics)

#### Bouton "Prévisualiser l'email"
- Ouvre le formulaire de rapport dans un nouvel onglet
- Note: Ce n'est pas exactement l'email d'invitation, mais donne une idée du style

### Résultats

#### Statistiques
- **Total**: Nombre total d'emails traités
- **Envoyés ✅**: Nombre d'emails envoyés avec succès
- **Échoués ❌**: Nombre d'emails qui n'ont pas pu être envoyés

#### Listes détaillées
- Liste des emails envoyés avec succès
- Liste des emails échoués avec raison de l'échec

---

## Configuration requise

### Variables d'environnement

L'interface fonctionne **uniquement si le backend est configuré** avec les variables d'environnement:

```bash
EMAIL_ENABLED=1
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=gonzalefernando@gmail.com
SMTP_PASSWORD=dfshbvvsmyqrfkja
SMTP_FROM_EMAIL=gonzalefernando@gmail.com
```

### Serveur backend

Le backend doit être démarré pour que l'interface fonctionne:

```bash
# Démarrer le backend
npm run backend

# Ou avec le projet complet
npm run start
```

---

## Exemples d'utilisation

### Scénario 1: Premier envoi à tous les testeurs

1. Ouvrir `beta_invitations.html`
2. Cliquer sur "📋 Charger l'allowlist"
3. Vérifier les emails chargés
4. Cliquer sur "🚀 Envoyer les invitations"
5. Confirmer
6. Consulter les résultats

**Temps estimé**: 1 minute

---

### Scénario 2: Envoyer à quelques nouveaux testeurs

1. Ouvrir `beta_invitations.html`
2. Saisir les emails manuellement:
   ```
   nouveau1@example.com
   nouveau2@example.com
   nouveau3@example.com
   ```
3. Cliquer sur "🚀 Envoyer les invitations"
4. Confirmer
5. Consulter les résultats

**Temps estimé**: 30 secondes

---

### Scénario 3: Tester avant l'envoi massif

1. Ouvrir `beta_invitations.html`
2. Cliquer sur "✉️ Email de test"
3. Saisir votre email: `gonzalefernando@gmail.com`
4. Cliquer sur "🚀 Envoyer les invitations"
5. Confirmer
6. Vérifier votre boîte email
7. Si OK, charger l'allowlist et envoyer à tous

**Temps estimé**: 2 minutes

---

## Troubleshooting

### L'interface ne charge pas l'allowlist

**Problème**: Erreur lors du clic sur "Charger l'allowlist"

**Solutions**:
1. Vérifier que le backend est démarré
2. Vérifier que vous êtes connecté en tant qu'admin
3. Ouvrir la console du navigateur (F12) pour voir l'erreur exacte

---

### Les invitations ne sont pas envoyées

**Problème**: Erreur lors du clic sur "Envoyer les invitations"

**Solutions**:
1. Vérifier que le backend est démarré
2. Vérifier les variables d'environnement email
3. Vérifier que `EMAIL_ENABLED=1`
4. Consulter les logs du backend pour plus de détails

---

### Les emails arrivent en spam

**Solution**:
- C'est normal pour les premiers envois
- Demander aux destinataires de marquer comme "Pas un spam"
- Attendre quelques jours pour que la réputation s'améliore

---

### Erreur "CORS" dans la console

**Problème**: Erreur CORS si vous ouvrez le fichier HTML directement

**Solution**:
- Accéder via le serveur: `http://localhost:8000/beta_invitations.html`
- Ou déplacer le fichier dans le dossier `public/` de votre serveur

---

## Accès en production

Pour utiliser l'interface en production:

1. **Copier le fichier sur le serveur**
   ```bash
   # Le fichier doit être accessible publiquement
   cp beta_invitations.html /path/to/public/folder/
   ```

2. **Accéder via URL**
   ```
   https://emergence-app.ch/beta_invitations.html
   ```

3. **Sécuriser l'accès** (recommandé)
   - Ajouter une authentification admin
   - Ou garder l'URL secrète
   - Ou utiliser un mot de passe basique

---

## Personnalisation

### Changer l'URL par défaut

Éditez le fichier `beta_invitations.html` ligne ~488:

```html
<input
    type="text"
    id="baseUrl"
    value="https://votre-url.com"
    ...
>
```

### Changer le style

Modifiez la section `<style>` en haut du fichier pour personnaliser:
- Couleurs
- Tailles de police
- Espacements
- Animations

---

## Avantages de l'interface web

✅ **Interface intuitive** - Pas besoin de ligne de commande
✅ **Visuel** - Voir immédiatement le nombre d'emails
✅ **Actions rapides** - Charger l'allowlist en un clic
✅ **Feedback en temps réel** - Résultats détaillés après envoi
✅ **Validation automatique** - Détection des emails invalides
✅ **Gestion des erreurs** - Messages d'erreur clairs
✅ **Responsive** - Fonctionne sur mobile et desktop

---

## Support

Pour toute question:
- **Email**: gonzalefernando@gmail.com
- **Documentation**: [BETA_INVITATIONS.md](docs/BETA_INVITATIONS.md)

---

**Dernière mise à jour**: 2025-10-13
