# Programme Beta EMERGENCE V8

**Date de création:** 2025-10-13
**Version:** Beta 1.0
**Statut:** Actif

---

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Système de rapport](#système-de-rapport)
3. [Checklist de test](#checklist-de-test)
4. [Bugs connus](#bugs-connus)
5. [Planning beta](#planning-beta)
6. [Contact](#contact)

---

## Vue d'ensemble

Le programme beta EMERGENCE V8 permet à un groupe restreint d'utilisateurs (allowlist) de tester la plateforme avant son lancement public.

### Objectifs

- Identifier les bugs critiques et modérés
- Valider l'expérience utilisateur
- Tester la charge et la performance
- Recueillir des feedbacks sur les fonctionnalités

### Accès

- **URL production:** https://emergence-app.ch
- **URL dev/staging:** https://emergence-app-486095406755.europe-west1.run.app
- **Formulaire de rapport:** https://emergence-app.ch/beta_report.html

---

## Système de rapport

### Fonctionnement

Le système de rapport beta utilise une **API REST backend** pour un envoi automatique et fiable :

1. L'utilisateur remplit le formulaire interactif sur [beta_report.html](../beta_report.html)
2. À la soumission, le formulaire envoie les données via `POST /api/beta-report`
3. Le backend sauvegarde le rapport localement et l'envoie automatiquement par email
4. L'utilisateur reçoit une confirmation immédiate : "Merci de votre contribution, vos retours seront analysés afin d'améliorer ÉMERGENCE."

### Avantages de cette approche

✅ **Envoi automatique** - l'utilisateur n'a qu'à cliquer une fois
✅ **Confirmation en temps réel** - feedback immédiat de succès ou d'erreur
✅ **Sauvegarde serveur** - tous les rapports sont conservés dans `data/beta_reports/`
✅ **Fiabilité** - garantie d'envoi avec retry possible
✅ **Analytics** - données exploitables pour statistiques futures

### Structure du formulaire

Le formulaire est divisé en 8 phases de test :

```
Phase 1: Authentification & Onboarding (5 tests)
Phase 2: Chat simple avec agents (5 tests)
Phase 3: Système de mémoire (5 tests)
Phase 4: Documents & RAG (6 tests)
Phase 5: Débats autonomes (5 tests)
Phase 6: Cockpit & Analytics (5 tests)
Phase 7: Tests de robustesse (5 tests)
Phase 8: Edge cases & bugs connus (5 tests)

Total: 55 points de contrôle
```

### Données collectées

- Email du testeur
- Navigateur et système d'exploitation
- Progression par phase (tests complétés)
- Commentaires par phase
- Bugs critiques rencontrés
- Suggestions d'amélioration
- Commentaires libres

### Format de l'email envoyé automatiquement

**Destinataire:** gonzalefernando@gmail.com
**Sujet:** `EMERGENCE Beta Report - user@example.com (64%)`

**Corps:**
```
EMERGENCE Beta 1.0 - Rapport de Test
=====================================

Date: 2025-10-14 05:30:15
Utilisateur: user@example.com
Navigateur/OS: Chrome 120 / Windows 11

PROGRESSION GLOBALE
-------------------
Complété: 35/55 (64%)

DÉTAIL PAR PHASE
----------------

Phase 1: Authentification & Onboarding
  Complété: 5/5 (100%)
  Commentaires:
    RAS, tout fonctionne

Phase 2: Chat simple avec agents
  Complété: 4/5 (80%)
  Commentaires:
    Nexus répond lentement parfois

...

CHECKLIST DÉTAILLÉE
-------------------
✅ Créer un compte / Se connecter
✅ Vérifier l'affichage du dashboard initial
...

FEEDBACK GÉNÉRAL
----------------

BUGS CRITIQUES:
[Description des bugs]

SUGGESTIONS:
[Suggestions d'amélioration]

COMMENTAIRES LIBRES:
[Commentaires libres]


---
Rapport généré automatiquement par EMERGENCE Beta Report System
```

**Note:** Les rapports sont également sauvegardés localement sur le serveur dans `data/beta_reports/` aux formats TXT et JSON.

---

## Checklist de test

### Phase 1: Authentification & Onboarding (15 min)

- [ ] Créer un compte / Se connecter
- [ ] Vérifier l'affichage du dashboard initial
- [ ] Ouvrir et consulter la documentation intégrée (Paramètres > Documentation ou liens "?" dans l'interface)
- [ ] Se déconnecter et se reconnecter
- [ ] Vérifier la persistance de session (token JWT 7 jours)

### Phase 2: Chat simple avec agents (20 min)

- [ ] Lancer une conversation avec Anima (3-5 questions variées)
- [ ] Lancer une conversation avec Neo (questions techniques)
- [ ] Lancer une conversation avec Nexus (synthèse/coordination)
- [ ] Créer plusieurs threads et basculer entre eux
- [ ] Supprimer un thread

### Phase 3: Système de mémoire (25 min)

- [ ] Ouvrir le Centre Mémoire (menu principal > Mémoire)
- [ ] Lancer une consolidation mémoire (bouton "Consolider mémoire") - observer la barre de progression
- [ ] Consulter l'historique des concepts extraits et préférences
- [ ] Faire référence à une information passée dans une nouvelle conversation (vérifier badge "Mémoire LTM")
- [ ] Tester le "Clear" mémoire (purge STM et/ou LTM - avec confirmation)

### Phase 4: Documents & RAG (30 min)

- [ ] Uploader un document PDF simple (<5 pages)
- [ ] Uploader un document TXT contenant un poème
- [ ] Activer le RAG et poser des questions sur le document
- [ ] Tester avec document volumineux (>20 pages)
- [ ] Supprimer un document
- [ ] Tester isolation documents (2 sessions différentes)

### Phase 5: Débats autonomes (25 min)

- [ ] Lancer un débat simple (2 tours)
- [ ] Vérifier la synthèse finale du médiateur
- [ ] Lancer un débat avec RAG activé
- [ ] Tester débat long (4+ tours)
- [ ] Consulter les métriques du débat (coûts par agent)

### Phase 6: Cockpit & Analytics (15 min)

- [ ] Ouvrir le Cockpit et consulter résumé coûts personnels
- [ ] Consulter répartition par agent (Anima, Neo, Nexus)
- [ ] Vérifier les statistiques d'activité (sessions, documents, conversations)
- [ ] Tester le rafraîchissement automatique (30s) ou manuel
- [ ] Dashboard admin (si rôle administrateur uniquement)

### Phase 7: Tests de robustesse (20 min)

- [ ] Envoyer 10 messages rapidement (vérifier pas de perte)
- [ ] Uploader 3 documents simultanément (vérifier traitement séquentiel)
- [ ] Fermer et rouvrir le navigateur (vérifier reconnexion WebSocket automatique)
- [ ] Conversation très longue (50+ messages) - vérifier performance
- [ ] Tester avec documents volumineux (>20 pages - observer latence RAG)

### Phase 8: Edge cases & bugs connus (15 min)

- [ ] Tester consolidation mémoire avec beaucoup de messages (50+)
- [ ] Accès multi-onglets (2 onglets, même compte - vérifier synchronisation)
- [ ] Upload document invalide/corrompu (vérifier gestion d'erreur)
- [ ] Débat avec sujet vide ou trop court (<10 caractères - validation)
- [ ] Tester le système de hold après débat (30s verrouillage - nouveau débat bloqué)

---

## Bugs connus

### 🔴 Critiques

#### 1. Fuite mémoire cache préférences
**Description:** Le cache des préférences (`MemoryContextBuilder`) peut grossir indéfiniment
**Impact:** Consommation mémoire excessive après utilisation prolongée
**Workaround:** Redémarrer l'application périodiquement
**Priorité:** P0
**Statut:** À corriger en Beta 1.1

#### 2. Système de hold débats (30s)
**Description:** Après un débat, les résultats sont verrouillés pendant 30 secondes
**Impact:** Impossible de lancer un nouveau débat immédiatement (message "Résultats verrouillés Xs")
**Workaround:** Attendre l'expiration du timer ou changer d'onglet
**Priorité:** P1 (fonctionnement normal, amélioration UX possible)
**Statut:** Comportement intentionnel - amélioration feedback utilisateur prévue Beta 1.1

#### 3. Consolidation mémoire sessions longues
**Description:** La consolidation peut être lente sur sessions >100 messages (>2min)
**Impact:** Timeout possible ou attente longue
**Workaround:** Consolider régulièrement (tous les 20-30 messages)
**Priorité:** P1
**Statut:** Optimisation prévue Beta 1.1 (chunking incrémental)

### 🟠 Modérés

#### 4. Timeout RAG documents volumineux
**Description:** Recherches vectorielles lentes sur gros volumes
**Impact:** Latence élevée (>5s) sur documents >50 pages
**Workaround:** Découper les documents en plus petits fichiers
**Priorité:** P1
**Statut:** Optimisation prévue Beta 1.1

#### 5. WebSocket reconnexion automatique
**Description:** La reconnexion WebSocket après fermeture/réouverture du navigateur fonctionne mais peut prendre quelques secondes
**Impact:** Léger délai avant rétablissement de la connexion temps réel
**Workaround:** Attendre quelques secondes ou rafraîchir (F5) si nécessaire
**Priorité:** P2
**Statut:** Optimisation du feedback visuel prévue Beta 1.1

#### 6. Uploads simultanés multiples
**Description:** Les uploads simultanés sont traités séquentiellement côté serveur
**Impact:** Peut sembler plus lent avec plusieurs fichiers, mais garantit l'intégrité
**Workaround:** Attendre la fin du traitement ou uploader un par un pour plus de contrôle
**Priorité:** P2
**Statut:** Fonctionnement normal - amélioration feedback visuel prévue Beta 1.2

### 🟡 Mineurs

#### 7. UI responsive mobile
**Description:** Quelques éléments UI non optimisés sur mobile
**Impact:** Expérience dégradée sur petits écrans
**Workaround:** Utiliser un navigateur desktop
**Priorité:** P2
**Statut:** Améliorations prévues Beta 1.2

#### 8. Toasts multiples
**Description:** Peut afficher plusieurs notifications simultanément
**Impact:** Encombrement visuel
**Workaround:** Fermer manuellement les toasts
**Priorité:** P2
**Statut:** À améliorer Beta 1.2

---

## Planning beta

### Beta 1.0 (13 octobre - 3 novembre 2025)
**Objectifs:**
- Test initial avec allowlist restreinte
- Identification bugs critiques
- Validation fonctionnalités principales
- Collecte premiers feedbacks

**Livrables:**
- Rapport de bugs consolidé
- Métriques d'utilisation
- Liste de priorités pour Beta 1.1

### Beta 1.1 (4 novembre - 24 novembre 2025)
**Objectifs:**
- Correction bugs P0 (critiques)
- Correction bugs P1 (modérés)
- Optimisations performance
- Amélioration UX basée sur feedbacks

**Livrables:**
- Version stabilisée
- Documentation utilisateur complète
- Guide de déploiement production

### Release Candidate (25 novembre - 15 décembre 2025)
**Objectifs:**
- Tests de charge
- Validation sécurité
- Tests d'acceptation finaux
- Préparation launch public

**Livrables:**
- Version RC prête pour production
- Plan de communication launch
- Support documentation

### Launch Public (Janvier 2026)
**Objectifs:**
- Ouverture publique
- Onboarding nouveaux utilisateurs
- Support actif
- Monitoring continu

---

## Contact

### Support technique
- **Email:** gonzalefernando@gmail.com
- **Formulaire de rapport:** https://emergence-app.ch/beta_report.html

### Ressources

- **Documentation complète:** [docs/INDEX_DOCUMENTATION.md](INDEX_DOCUMENTATION.md)
- **Guide mémoire:** [docs/Memoire.md](Memoire.md)
- **Guide authentification:** [docs/AUTHENTICATION.md](AUTHENTICATION.md)
- **Architecture:** [docs/architecture/10-Components.md](architecture/10-Components.md)

### Allowlist

La liste des emails autorisés est gérée via l'interface admin :
- Endpoint: `GET /api/auth/admin/allowlist`
- Interface: Admin Dashboard > Utilisateurs > Allowlist

---

**Dernière mise à jour:** 2025-10-17
**Maintenu par:** Équipe EMERGENCE

---

## Changelog

### 2025-10-17
- ✅ Audit et mise à jour de la checklist beta-testeurs
- ✅ Correction Phase 1: Remplacement "tutoriel pop-up" → "documentation intégrée"
- ✅ Correction Phase 3: Précision sur le processus de consolidation mémoire
- ✅ Correction Phase 6: Clarification sur les métriques personnelles vs admin
- ✅ Correction Phase 7 & 8: Ajustement des tests de robustesse et edge cases
- ✅ Mise à jour des bugs connus: Reclassification priorités et statuts réels
- ✅ Suppression "Mot de passe oublié" (non implémenté)

### 2025-10-14
- ✅ Migration du système de rapport de `mailto:` vers API REST backend
- ✅ Envoi automatique des rapports par email via SMTP
- ✅ Sauvegarde locale des rapports (TXT + JSON)
- ✅ Message de confirmation personnalisé
- ✅ Amélioration de l'expérience utilisateur

### 2025-10-13
- Lancement du programme Beta 1.0
- Création du formulaire de rapport interactif
- Documentation initiale
