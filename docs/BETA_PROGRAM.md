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

Le système de rapport beta utilise une approche **mailto** pour la simplicité et la fiabilité :

1. L'utilisateur remplit le formulaire interactif sur [beta_report.html](../beta_report.html)
2. À la soumission, le navigateur génère un email pré-rempli
3. Le client email de l'utilisateur s'ouvre automatiquement
4. L'utilisateur vérifie et envoie l'email à `gonzalefernando@gmail.com`

### Avantages de cette approche

✅ **Aucune dépendance backend** - pas de problème de routage ou d'API
✅ **Fonctionne toujours** - utilise le client email natif
✅ **Simple à débugger** - l'utilisateur voit le contenu avant envoi
✅ **Pas de limite de taille** - contrairement aux APIs REST
✅ **Attachements possibles** - l'utilisateur peut joindre des screenshots

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

### Format de l'email généré

```
EMERGENCE Beta 1.0 - Rapport de Test
========================================

Email: user@example.com
Navigateur/OS: Chrome 120 / Windows 11
Progression: 35/55 (64%)

Phase 1 (Auth & Onboarding): 5/5
  Commentaires: RAS, tout fonctionne

Phase 2 (Chat agents): 4/5
  Commentaires: Nexus répond lentement parfois

...

BUGS:
[Description des bugs]

SUGGESTIONS:
[Suggestions d'amélioration]

COMMENTAIRES:
[Commentaires libres]
```

---

## Checklist de test

### Phase 1: Authentification & Onboarding (15 min)

- [ ] Créer un compte / Se connecter
- [ ] Vérifier l'affichage du dashboard initial + consulter le tutoriel (pop-up)
- [ ] Tester le lien "Mot de passe oublié"
- [ ] Se déconnecter et se reconnecter
- [ ] Vérifier la persistance de session

### Phase 2: Chat simple avec agents (20 min)

- [ ] Lancer une conversation avec Anima (3-5 questions variées)
- [ ] Lancer une conversation avec Neo (questions techniques)
- [ ] Lancer une conversation avec Nexus (synthèse/coordination)
- [ ] Créer plusieurs threads et basculer entre eux
- [ ] Supprimer un thread

### Phase 3: Système de mémoire (25 min)

- [ ] Activer l'analyse mémoire (bouton "Analyser")
- [ ] Ouvrir le Centre Mémoire et consulter l'historique
- [ ] Faire référence à une information passée (vérifier badge "Mémoire injectée")
- [ ] Tester le "Clear" mémoire (purge STM + LTM)
- [ ] Tester la détection de topic shift (changer de sujet radicalement)

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

- [ ] Ouvrir le Cockpit et consulter résumé coûts
- [ ] Filtrer par période (7j, 30j, 90j, 1 an)
- [ ] Consulter répartition par agent
- [ ] Monitoring santé (health checks)
- [ ] Dashboard admin (si applicable)

### Phase 7: Tests de robustesse (20 min)

- [ ] Envoyer 10 messages rapidement
- [ ] Uploader 3 documents simultanément
- [ ] Forcer une déconnexion WebSocket (fermer/rouvrir navigateur)
- [ ] Tester sur connexion lente (throttling)
- [ ] Session très longue (50+ messages)

### Phase 8: Edge cases & bugs connus (15 min)

- [ ] Tester cache mémoire intensif (20+ consolidations)
- [ ] Accès concurrents (2 onglets, même session)
- [ ] Document corrompu (upload PDF invalide)
- [ ] Débat sans sujet (validation champs vides)
- [ ] Clear pendant consolidation

---

## Bugs connus

### 🔴 Critiques

#### 1. Fuite mémoire cache préférences
**Description:** Le cache des préférences (`MemoryContextBuilder`) peut grossir indéfiniment
**Impact:** Consommation mémoire excessive après utilisation prolongée
**Workaround:** Redémarrer l'application périodiquement
**Priorité:** P0
**Statut:** À corriger en Beta 1.1

#### 2. Race conditions dictionnaires partagés
**Description:** Accès concurrents aux dictionnaires partagés sans locks
**Impact:** Peut causer des erreurs intermittentes
**Workaround:** Éviter les actions simultanées multiples
**Priorité:** P0
**Statut:** À corriger en Beta 1.1

#### 3. Consolidation mémoire sessions longues
**Description:** La consolidation peut échouer sur sessions >100 messages
**Impact:** Perte de contexte mémoire
**Workaround:** Créer un nouveau thread après 100 messages
**Priorité:** P0
**Statut:** À corriger en Beta 1.1

### 🟠 Modérés

#### 4. Timeout RAG documents volumineux
**Description:** Recherches vectorielles lentes sur gros volumes
**Impact:** Latence élevée (>5s) sur documents >50 pages
**Workaround:** Découper les documents en plus petits fichiers
**Priorité:** P1
**Statut:** Optimisation prévue Beta 1.1

#### 5. WebSocket reconnexion manuelle
**Description:** Après déconnexion, la reconnexion automatique peut échouer
**Impact:** Nécessite refresh manuel
**Workaround:** Rafraîchir la page (F5)
**Priorité:** P1
**Statut:** À corriger en Beta 1.1

#### 6. Collisions uploads simultanés
**Description:** Risque de collisions si uploads multiples rapides
**Impact:** Un document peut ne pas être traité
**Workaround:** Uploader les documents un par un
**Priorité:** P1
**Statut:** À corriger en Beta 1.1

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

**Dernière mise à jour:** 2025-10-13
**Maintenu par:** Équipe EMERGENCE
