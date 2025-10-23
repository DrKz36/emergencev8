# 🗺️ ROADMAP OFFICIELLE EMERGENCE V8
> **Document Unique et Officiel** - Toute référence à d'autres roadmaps doit renvoyer à ce fichier.

**Date de création** : 2025-10-15
**Dernière mise à jour** : 2025-10-15
**Statut** : 📋 EN COURS - Document de référence unique
**Objectif** : Implémenter toutes les fonctionnalités décrites dans le tutoriel

---

## 📊 Vue d'Ensemble

Cette roadmap consolide l'audit complet des fonctionnalités d'Emergence V8 et définit un plan d'action clair pour combler les gaps entre le tutoriel et l'implémentation actuelle.

### Métriques Globales
- ✅ **Fonctionnalités complètes** : 8 / 23 (35%)
- 🟡 **Fonctionnalités partielles** : 3 / 23 (13%)
- 🔴 **Fonctionnalités manquantes** : 12 / 23 (52%)

---

## 🎯 PHASE P0 - QUICK WINS (3-5 jours)
> **Priorité** : CRITIQUE - Backend déjà prêt, UI à finaliser

### Objectif
Activer les fonctionnalités dont le backend est opérationnel mais l'UI manquante/incomplète.

### 1. Archivage des Conversations (UI)
**Statut** : 🟡 Backend ✅ / UI ❌
**Temps estimé** : 1 jour
**Fichiers** : [threads.js](src/frontend/features/threads/threads.js), [threads-service.js](src/frontend/features/threads/threads-service.js)

**Tâches** :
- [ ] Ajouter onglet "Archives" dans la sidebar threads
- [ ] Créer filtre "Actifs / Archivés" dans threads.js
- [ ] Implémenter bouton "Désarchiver" dans le menu contextuel
- [ ] Ajouter compteur threads archivés dans le dashboard
- [ ] Tests : archiver → vérifier retrait liste → désarchiver → vérifier réapparition

**Acceptance Criteria** :
- ✅ Clic droit sur thread → "Archiver" → disparaît de la liste active
- ✅ Onglet "Archives" affiche threads archivés
- ✅ Clic sur "Désarchiver" → thread revient dans actifs
- ✅ Badge compteur "X archivés" visible

---

### 2. Graphe de Connaissances Interactif
**Statut** : 🟡 Composant créé ✅ / Intégration ❌
**Temps estimé** : 1 jour
**Fichiers** : [concept-graph.js](src/frontend/features/memory/concept-graph.js), [memory-center.js](src/frontend/features/memory/memory-center.js)

**Tâches** :
- [ ] Ajouter onglet "Graphe" dans le Centre Mémoire
- [ ] Intégrer ConceptGraph dans memory-center.js
- [ ] Ajouter bouton "Voir le graphe" dans la liste des concepts
- [ ] Implémenter filtres (par type de concept, par date)
- [ ] Ajouter tooltip sur nœuds (nom + description + relations)
- [ ] Tests : ouvrir graphe → vérifier nœuds affichés → zoom/pan → sélection nœud

**Acceptance Criteria** :
- ✅ Onglet "Graphe" accessible depuis Centre Mémoire
- ✅ Nœuds affichés avec positions force-directed
- ✅ Interactions : zoom, pan, drag nodes
- ✅ Tooltip sur hover nœud
- ✅ Filtres fonctionnels (type, date)

---

### 3. Export Conversations (CSV/PDF)
**Statut** : 🟡 JSON/TXT ✅ / CSV/PDF ❌
**Temps estimé** : 2 jours
**Fichiers** : [threads.js](src/frontend/features/threads/threads.js), [chat.js](src/frontend/features/chat/chat.js)

**Tâches** :
- [ ] Installer `papaparse` (CSV) et `jspdf` + `jspdf-autotable` (PDF)
- [ ] Implémenter fonction `exportToCSV(threadId)` dans threads.js
- [ ] Implémenter fonction `exportToPDF(threadId)` avec formatage markdown
- [ ] Ajouter menu "Exporter → JSON / CSV / PDF / TXT" dans clic droit thread
- [ ] Formater correctement métadonnées (date, agent, tokens, coûts)
- [ ] Tests : exporter CSV → ouvrir Excel → vérifier colonnes / exporter PDF → vérifier rendu

**Acceptance Criteria** :
- ✅ Export CSV avec colonnes : timestamp, role, agent, content, tokens, cost
- ✅ Export PDF avec formatage markdown (gras, code, listes)
- ✅ Export JSON existant conservé
- ✅ Export TXT existant conservé
- ✅ Nom fichier : `conversation_[nom]_[date].csv|pdf`

---

## 🎯 PHASE P1 - UX ESSENTIELLE (5-7 jours)
> **Priorité** : HAUTE - Améliore significativement l'expérience utilisateur

### 4. Hints Proactifs (UI)
**Statut** : 🟡 Backend ✅ / UI limitée ❌
**Temps estimé** : 2 jours
**Fichiers** : [ProactiveHintsUI.js](src/frontend/features/memory/ProactiveHintsUI.js), [chat-ui.js](src/frontend/features/chat/chat-ui.js)

**Tâches** :
- [ ] Intégrer ProactiveHintsUI dans le chat (banners contextuels)
- [ ] Afficher hints au-dessus de la zone de saisie (max 3 simultanés)
- [ ] Implémenter actions : "Appliquer" (injecte dans input), "Ignorer", "Snooze 1h"
- [ ] Ajouter compteur hints dans dashboard mémoire
- [ ] Styling : gradient par type (💡 preference, 📋 intent, ⚠️ constraint)
- [ ] Tests : trigger hint → vérifier affichage → clic "Appliquer" → vérifier injection input

**Acceptance Criteria** :
- ✅ Hints apparaissent automatiquement selon contexte conversation
- ✅ Max 3 hints simultanés, tri par relevance
- ✅ Clic "Appliquer" → texte injecté dans input chat
- ✅ Snooze 1h → hint disparaît temporairement (localStorage)
- ✅ Auto-dismiss après 10s si non interagi

---

### 5. Thème Clair/Sombre (Toggle Utilisateur)
**Statut** : 🔴 Non implémenté
**Temps estimé** : 2 jours
**Fichiers** : [settings-ui.js](src/frontend/features/settings/settings-ui.js), styles globaux

**Tâches** :
- [ ] Créer variables CSS pour thème clair (couleurs, backgrounds, textes)
- [ ] Implémenter toggle dans Paramètres > Interface
- [ ] Sauvegarder préférence dans localStorage (`emergence.theme`)
- [ ] Appliquer classe `theme-light` ou `theme-dark` sur `<body>`
- [ ] Ajuster tous les composants pour supporter les 2 thèmes
- [ ] Tests : toggle thème → vérifier changement immédiat → recharger page → vérifier persistence

**Acceptance Criteria** :
- ✅ Toggle "Thème" visible dans Paramètres > Interface
- ✅ Clic toggle → changement instantané des couleurs
- ✅ Thème sauvegardé et restauré au rechargement
- ✅ Tous les composants lisibles dans les 2 thèmes
- ✅ Contraste WCAG AA respecté

---

### 6. Gestion Avancée des Concepts (Édition)
**Statut** : 🔴 Non implémenté (lecture seule actuellement)
**Temps estimé** : 3 jours
**Fichiers** : [concept-list.js](src/frontend/features/memory/concept-list.js), [concept-editor.js](src/frontend/features/memory/concept-editor.js)

**Tâches** :
- [ ] Backend : endpoints `PUT /api/memory/concepts/{id}` et `DELETE /api/memory/concepts/{id}`
- [ ] UI : bouton "Éditer" sur chaque concept dans la liste
- [ ] Modal d'édition avec champs : nom, description, tags, relations
- [ ] Implémentation tags personnalisés (ajout/suppression)
- [ ] Gestion des relations : "lié à" autre concept (dropdown autocomplete)
- [ ] Suppression sélective avec confirmation
- [ ] Tests : éditer concept → sauvegarder → vérifier BDD / supprimer → vérifier disparition

**Acceptance Criteria** :
- ✅ Clic "Éditer" sur concept → modal s'ouvre
- ✅ Modification nom/description → sauvegarde → mise à jour liste
- ✅ Ajout tags → sauvegarde → tags visibles dans liste
- ✅ Création relation → sauvegarde → relation affichée dans graphe
- ✅ Suppression concept → confirmation → disparition liste + graphe

---

## 🎯 PHASE P2 - ADMINISTRATION & SÉCURITÉ (4-6 jours)
> **Priorité** : MOYENNE - Important mais moins urgent

### 7. Dashboard Administrateur Avancé
**Statut** : 🟡 Basique ✅ / Avancé ❌
**Temps estimé** : 3 jours
**Fichiers** : [admin.js](src/frontend/features/admin/admin.js), [admin-dashboard.js](src/frontend/features/admin/admin-dashboard.js)

**Tâches** :
- [ ] Backend : endpoint `GET /api/admin/analytics` (coûts par utilisateur)
- [ ] Créer onglet "Analytics" dans l'interface admin
- [ ] Graphique : répartition coûts par utilisateur (top 10)
- [ ] Graphique : historique coûts journaliers (7 derniers jours)
- [ ] Liste sessions actives avec bouton "Révoquer"
- [ ] Métriques système : uptime, latence moyenne, taux d'erreur
- [ ] Tests : vérifier stats correctes / révoquer session → vérifier déconnexion

**Acceptance Criteria** :
- ✅ Onglet "Analytics" accessible pour admins uniquement
- ✅ Top 10 consommateurs avec % du total
- ✅ Graphique historique coûts (Chart.js ou similar)
- ✅ Liste sessions actives avec timestamp + user
- ✅ Révocation session → déconnexion immédiate utilisateur
- ✅ Métriques système actualisées en temps réel

---

### 8. Gestion Multi-Sessions
**Statut** : 🔴 Non implémenté
**Temps estimé** : 2 jours
**Fichiers** : [settings-security.js](src/frontend/features/settings/settings-security.js), backend auth

**Tâches** :
- [ ] Backend : endpoint `GET /api/auth/sessions` (liste sessions utilisateur)
- [ ] Backend : endpoint `DELETE /api/auth/sessions/{id}` (révocation)
- [ ] UI : onglet "Sessions" dans Paramètres > Sécurité
- [ ] Liste sessions avec : device, IP, date création, date dernière activité
- [ ] Bouton "Révoquer" sur chaque session (sauf actuelle)
- [ ] Bouton "Révoquer toutes" (avec confirmation)
- [ ] Tests : créer 2 sessions (2 navigateurs) → révoquer depuis navigateur 1 → vérifier déconnexion navigateur 2

**Acceptance Criteria** :
- ✅ Onglet "Sessions" visible dans Paramètres > Sécurité
- ✅ Liste affiche toutes les sessions actives
- ✅ Session actuelle marquée (badge "Actuelle")
- ✅ Révocation session → confirmation → déconnexion immédiate
- ✅ "Révoquer toutes" → déconnecte tous sauf session actuelle

---

### 9. Authentification 2FA (TOTP)
**Statut** : 🔴 Non implémenté
**Temps estimé** : 3 jours
**Fichiers** : backend auth service, frontend login

**Tâches** :
- [ ] Backend : installer `pyotp` (TOTP generation/validation)
- [ ] Backend : endpoints `POST /api/auth/2fa/enable`, `POST /api/auth/2fa/verify`, `POST /api/auth/2fa/disable`
- [ ] Backend : champ `totp_secret` dans table users
- [ ] Backend : génération QR code (base64 image) lors de l'activation
- [ ] UI : onglet "Authentification" dans Paramètres > Sécurité
- [ ] UI : bouton "Activer 2FA" → affiche QR code + code de secours
- [ ] UI : lors du login, demander code TOTP si 2FA activé
- [ ] Tests : activer 2FA → scanner QR → vérifier code → désactiver → vérifier désactivation

**Acceptance Criteria** :
- ✅ Onglet "Authentification" dans Paramètres > Sécurité
- ✅ Activation 2FA → QR code affiché (compatible Google Authenticator)
- ✅ Codes de secours générés (10 codes à usage unique)
- ✅ Login avec 2FA → demande code TOTP après mot de passe
- ✅ Code invalide → erreur explicite
- ✅ Désactivation 2FA → confirmation + code TOTP requis

---

## 🎯 PHASE P3 - FONCTIONNALITÉS AVANCÉES (8-12 jours)
> **Priorité** : BASSE - Nice-to-have, améliore la plateforme

### 10. Mode Hors Ligne (PWA)
**Statut** : 🔴 Non implémenté
**Temps estimé** : 4 jours

**Tâches** :
- [ ] Créer `manifest.json` (PWA configuration)
- [ ] Implémenter Service Worker avec stratégie cache-first
- [ ] Cacher conversations récentes (IndexedDB)
- [ ] UI : indicateur "Mode hors ligne" quand pas de connexion
- [ ] Synchronisation automatique au retour en ligne
- [ ] Tests : désactiver réseau → vérifier conversations disponibles → réactiver → vérifier sync

**Acceptance Criteria** :
- ✅ Application installable (bouton "Installer" navigateur)
- ✅ Conversations récentes accessibles hors ligne
- ✅ Indicateur visuel "Hors ligne" affiché
- ✅ Messages envoyés hors ligne stockés localement
- ✅ Retour en ligne → sync automatique vers serveur

---

### 11. Webhooks et Intégrations
**Statut** : 🔴 Non implémenté
**Temps estimé** : 3 jours

**Tâches** :
- [ ] Backend : table `webhooks` (user_id, url, events, secret)
- [ ] Backend : endpoints `POST /api/webhooks`, `GET /api/webhooks`, `DELETE /api/webhooks/{id}`
- [ ] Backend : système d'événements (nouvelle conversation, analyse terminée, etc.)
- [ ] Backend : envoi POST vers webhook URL avec signature HMAC
- [ ] UI : onglet "Webhooks" dans Paramètres > Intégrations
- [ ] UI : formulaire ajout webhook (URL, événements, secret)
- [ ] Tests : créer webhook → déclencher événement → vérifier POST reçu

**Acceptance Criteria** :
- ✅ Onglet "Webhooks" dans Paramètres
- ✅ Ajout webhook avec sélection événements (checkboxes)
- ✅ Événement déclenché → POST envoyé avec payload JSON
- ✅ Signature HMAC-SHA256 dans header `X-Webhook-Signature`
- ✅ Retry automatique si webhook échoue (3 tentatives)

---

### 12. API Publique Développeurs
**Statut** : 🔴 Non implémenté
**Temps estimé** : 5 jours

**Tâches** :
- [ ] Backend : système de clés API (table `api_keys`)
- [ ] Backend : endpoints CRUD pour clés API
- [ ] Backend : middleware authentification par API key (header `X-API-Key`)
- [ ] Backend : rate limiting par clé API (100 req/min)
- [ ] Documentation : OpenAPI spec (Swagger UI)
- [ ] UI : onglet "API" dans Paramètres > Développeurs
- [ ] UI : génération clé API avec nom + permissions
- [ ] Tests : créer clé → appeler API → vérifier authentification

**Acceptance Criteria** :
- ✅ Onglet "API" dans Paramètres > Développeurs
- ✅ Génération clé API avec nom descriptif
- ✅ Permissions granulaires (read threads, write messages, etc.)
- ✅ Documentation Swagger accessible `/api/docs`
- ✅ Rate limiting appliqué (429 si dépassement)
- ✅ Révocation clé → invalidation immédiate

---

### 13. Personnalisation Complète des Agents
**Statut** : 🔴 Non implémenté
**Temps estimé** : 6 jours

**Tâches** :
- [ ] Backend : table `custom_agents` (user_id, name, system_prompt, model, temperature)
- [ ] Backend : endpoints CRUD agents personnalisés
- [ ] Backend : sélection agent custom dans chat service
- [ ] UI : onglet "Agents" dans Paramètres Avancés
- [ ] UI : éditeur agent (nom, prompt système, modèle, température, top_p)
- [ ] UI : sélecteur agent dans chat (dropdown avec agents par défaut + customs)
- [ ] Tests : créer agent → sélectionner dans chat → vérifier réponse

**Acceptance Criteria** :
- ✅ Onglet "Agents" dans Paramètres Avancés
- ✅ Création agent avec prompt système personnalisé
- ✅ Sélection modèle IA (GPT-4, Claude, Gemini)
- ✅ Paramètres avancés (temperature, top_p, max_tokens)
- ✅ Agent custom apparaît dans dropdown chat
- ✅ Conversations utilisent le prompt personnalisé

---

## 📋 RÉCAPITULATIF PAR PHASE

| Phase | Fonctionnalités | Temps Estimé | Priorité |
|-------|-----------------|--------------|----------|
| **P0** | Archivage UI, Graphe, Export CSV/PDF | 3-5 jours | 🔥 CRITIQUE |
| **P1** | Hints UI, Thème clair, Gestion concepts | 5-7 jours | ⚠️ HAUTE |
| **P2** | Dashboard admin, Multi-sessions, 2FA | 4-6 jours | 🔸 MOYENNE |
| **P3** | PWA, Webhooks, API publique, Agents custom | 8-12 jours | 🔹 BASSE |
| **TOTAL** | 13 fonctionnalités | 20-30 jours | - |

---

## 📅 PLANNING SUGGÉRÉ (Sprints de 5 jours)

### Semaine 1 (Jours 1-5) - Sprint P0
- Jour 1 : Archivage UI conversations
- Jour 2 : Graphe de connaissances intégration
- Jours 3-4 : Export CSV/PDF
- Jour 5 : Tests P0 + documentation

### Semaine 2 (Jours 6-10) - Sprint P1 (Partie 1)
- Jours 6-7 : Hints proactifs UI
- Jours 8-9 : Thème clair/sombre
- Jour 10 : Tests + début gestion concepts

### Semaine 3 (Jours 11-15) - Sprint P1 (Partie 2) + P2 (Partie 1)
- Jours 11-12 : Gestion concepts (suite + fin)
- Jours 13-15 : Dashboard admin avancé

### Semaine 4 (Jours 16-20) - Sprint P2 (Partie 2)
- Jours 16-17 : Gestion multi-sessions
- Jours 18-20 : Authentification 2FA

### Semaines 5-6 (Jours 21-30) - Sprint P3 (Optionnel)
- Jours 21-24 : Mode hors ligne (PWA)
- Jours 25-27 : Webhooks et intégrations
- Jours 28-30 : API publique ou Agents custom (selon priorités)

---

## 🎯 CRITÈRES DE SUCCÈS GLOBAUX

| Métrique | Objectif | Actuel | Cible |
|----------|----------|--------|-------|
| Fonctionnalités complètes | Toutes features tutoriel implémentées | 35% | 100% |
| Couverture tests | Tests E2E pour toutes features | ~40% | >90% |
| Documentation | Tous les guides à jour | ~60% | 100% |
| Performance | Temps chargement < 2s | Variable | <2s |
| Accessibilité | WCAG AA respecté | Partiel | Complet |

---

## 📝 NOTES IMPORTANTES

### Dépendances Techniques
- **P0** : Aucune dépendance externe majeure
- **P1** : Variables CSS pour thèmes
- **P2** : `pyotp` pour 2FA
- **P3** : Service Worker, IndexedDB pour PWA

### Points d'Attention
1. **Archivage** : Vérifier que backend ne purge pas threads archivés
2. **Graphe** : Performance avec >1000 concepts (pagination/filtres)
3. **Thème clair** : Tester TOUTES les vues (chat, mémoire, docs, admin)
4. **2FA** : Sauvegarder codes de secours utilisateur
5. **PWA** : Taille cache limitée (max 50MB recommandé)

### Tests Requis par Phase
- **P0** : 15 tests E2E minimum
- **P1** : 20 tests E2E minimum
- **P2** : 25 tests E2E minimum (sécurité critique)
- **P3** : 30 tests E2E minimum

---

## 📚 RÉFÉRENCES

### Documents Liés
- [AUDIT_COMPLET.md](docs/AUDIT_FEATURES_2025-10-15.md) - Audit détaillé des fonctionnalités
- [tutorialGuides.js](src/frontend/components/tutorial/tutorialGuides.js) - Contenu tutoriel
- [TUTORIAL_SYSTEM.md](docs/TUTORIAL_SYSTEM.md) - Documentation système tutoriel

### Anciennes Roadmaps (ARCHIVÉES)
- ~~[Roadmap Stratégique.txt](docs/archive/Roadmap_Strategique_OLD.txt)~~ → ARCHIVÉE
- ~~[memory-roadmap.md](docs/archive/memory-roadmap_OLD.md)~~ → ARCHIVÉE
- ~~[COCKPIT_ROADMAP_FIXED.md](docs/archive/COCKPIT_ROADMAP_FIXED_OLD.md)~~ → ARCHIVÉE

**⚠️ IMPORTANT** : Toute référence à une roadmap doit pointer vers `ROADMAP_OFFICIELLE.md`

---

## 🔄 VERSIONING & HISTORIQUE

### Système de Versioning Bêta

**Version actuelle** : `beta-1.0.0`

Le projet utilise le versioning sémantique (SemVer) pendant la phase bêta jusqu'à la release V1.0.0.

#### Format : `beta-X.Y.Z`
- **X (Major)** : Phases complètes (P0, P1, P2, P3) / Changements majeurs
- **Y (Minor)** : Nouvelles fonctionnalités / Features individuelles
- **Z (Patch)** : Corrections de bugs / Améliorations mineures

#### Roadmap des Versions

| Version | Phase | Fonctionnalités Principales | Date Prévue | Statut |
|---------|-------|------------------------------|-------------|--------|
| **beta-1.0.0** | Base | État initial du projet | 2025-10-15 | ✅ Actuelle |
| beta-1.1.0 | P0 | Archivage conversations (UI) | ~2025-10-20 | 🔜 Prochaine |
| beta-1.2.0 | P0 | Graphe de connaissances interactif | ~2025-10-21 | 📋 Planifiée |
| beta-1.3.0 | P0 | Export conversations (CSV/PDF) | ~2025-10-23 | 📋 Planifiée |
| **beta-2.0.0** | P1 | Phase P1 complète (UX Essentielle) | ~2025-10-30 | 📋 Planifiée |
| **beta-3.0.0** | P2 | Phase P2 complète (Admin & Sécurité) | ~2025-11-06 | 📋 Planifiée |
| **beta-4.0.0** | P3 | Phase P3 complète (Fonctionnalités Avancées) | ~2025-11-18 | 📋 Planifiée |
| **v1.0.0** | Release | Production Officielle (toutes features) | TBD | 🎯 Objectif |

#### Détail des Versions Mineures Prévues

**Phase P0 (beta-1.x.x)**
- `beta-1.1.0` : Archivage conversations - Onglet Archives, filtre Actifs/Archivés, bouton Désarchiver
- `beta-1.2.0` : Graphe interactif - Onglet Graphe, visualisation force-directed, filtres
- `beta-1.3.0` : Export avancé - CSV/PDF avec formatage markdown et métadonnées

**Phase P1 (beta-2.x.x)**
- `beta-2.0.0` : Release majeure incluant Hints proactifs UI, Thème clair/sombre, Gestion avancée concepts

**Phase P2 (beta-3.x.x)**
- `beta-3.0.0` : Release majeure incluant Dashboard admin avancé, Multi-sessions, 2FA (TOTP)

**Phase P3 (beta-4.x.x)**
- `beta-4.0.0` : Release majeure incluant PWA, Webhooks, API publique, Agents personnalisés

#### Règles de Mise à Jour

**Incrémenter Major (X)** quand :
- Une phase complète est terminée (P0 → P1 → P2 → P3)
- Changement architectural majeur
- Breaking changes dans l'API
- Migration de base de données

**Incrémenter Minor (Y)** quand :
- Nouvelle fonctionnalité ajoutée
- Feature du tutoriel implémentée
- Amélioration significative d'une feature existante

**Incrémenter Patch (Z)** quand :
- Correction de bug
- Amélioration de performance mineure
- Ajustement UI/UX mineur
- Mise à jour documentation

#### Synchronisation avec CHANGELOG

Toute modification de version doit être documentée dans [CHANGELOG.md](CHANGELOG.md) avec :
- Date de release
- Description des changements
- Liens vers commits/PR
- Métriques de progression

---

## 📜 HISTORIQUE DES MISES À JOUR ROADMAP

| Date | Version Roadmap | Changements |
|------|-----------------|-------------|
| 2025-10-15 | 1.1 | Ajout système de versioning bêta (beta-1.0.0) |
| 2025-10-15 | 1.0 | Création roadmap officielle unique basée sur audit complet |

---

## ✅ COMMENT UTILISER CETTE ROADMAP

### Pour l'équipe de développement
1. **Consulter cette roadmap** : C'est la source de vérité unique
2. **Suivre l'ordre des phases** : P0 → P1 → P2 → P3
3. **Cocher les tâches** : Remplacer `[ ]` par `[x]` au fur et à mesure
4. **Mettre à jour les statuts** : 🔴 → 🟡 → ✅
5. **Documenter les décisions** : Ajouter notes dans section appropriée

### Pour le product owner
1. **Prioriser les phases** : Valider ordre P0/P1/P2/P3
2. **Ajuster le planning** : Selon ressources disponibles
3. **Valider les AC** : Acceptance Criteria avant début sprint
4. **Suivre l'avancement** : Métriques dans section Récapitulatif

---

**Document maintenu par** : Équipe Emergence V8
**Contact** : gonzalefernando@gmail.com
**Dernière révision** : 2025-10-15
