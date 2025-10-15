# Guide Utilisateur ÉMERGENCE Beta
**Version:** V8 - Phase Beta
**Dernière mise à jour:** 2025-10-15

---

## 📚 Table des Matières

1. [Introduction](#introduction)
2. [Démarrage Rapide](#démarrage-rapide)
3. [Chat Multi-Agents](#chat-multi-agents)
4. [Centre Mémoire](#centre-mémoire) ⭐ **NOUVEAU**
5. [Gestion des Documents](#gestion-des-documents)
6. [Mode RAG](#mode-rag)
7. [Paramètres](#paramètres)
8. [Trucs et Astuces](#trucs-et-astuces)

---

## Introduction

Bienvenue dans **ÉMERGENCE V8**, la plateforme de conversation multi-agents intelligente !

### Qu'est-ce qu'ÉMERGENCE ?

ÉMERGENCE est une interface de chat qui vous connecte à **3 agents IA spécialisés** :
- 🌟 **Anima** : Empathique et clarifiante
- 🔬 **Neo** : Analytique et structurante
- 🧩 **Nexus** : Architecte systémique

### Fonctionnalités Clés

✅ **Conversations contextuelles** : Les agents se souviennent de vos préférences
✅ **Mémoire progressive** : STM (session) + LTM (persistante)
✅ **RAG avancé** : Recherche dans vos documents
✅ **Multi-agents** : Consultez plusieurs perspectives
✅ **Feedback temps réel** : Barre de progression pour consolidations

---

## Démarrage Rapide

### 1. Connexion

1. Accédez à `https://emergence-app.ch`
2. Entrez vos identifiants (email + mot de passe)
3. Vous arrivez sur l'écran d'accueil

### 2. Première Conversation

1. Cliquez sur **"Nouvelle conversation"** (icône +)
2. Tapez votre message dans la zone de saisie
3. Appuyez sur **Entrée** ou cliquez sur l'icône envoi
4. L'agent par défaut (Anima) vous répond

### 3. Explorer l'Interface

Navigation principale (barre latérale gauche) :
- 💬 **Chat** : Conversations avec les agents
- 🧠 **Mémoire** : Centre de gestion mémoire ⭐ **NOUVEAU**
- 📚 **Documents** : Gestion de vos fichiers
- ⚙️ **Paramètres** : Configuration
- 📊 **Cockpit** : Statistiques d'utilisation

---

## Chat Multi-Agents

### Les Trois Agents

#### 🌟 Anima - La Présence Empathique

**Quand la solliciter** :
- Clarifier une question complexe
- Reformuler une demande mal exprimée
- Détecter les intentions implicites
- Faciliter la collaboration

**Exemple** :
```
"Anima, j'ai du mal à exprimer ce que je recherche -
peux-tu m'aider à clarifier ma demande ?"
```

#### 🔬 Neo - L'Analyste Stratégique

**Quand la solliciter** :
- Analyse critique d'une solution
- Structuration de plans d'action
- Recherche de données factuelles (RAG)
- Identification des risques

**Exemple** :
```
"Neo, analyse les risques techniques de cette architecture
et propose un plan de migration"
```

#### 🧩 Nexus - L'Architecte Systémique

**Quand le solliciter** :
- Conception d'architecture globale
- Synthèse de multiples perspectives
- Coordination entre composants
- Vue d'ensemble stratégique

**Exemple** :
```
"Nexus, coordonne une discussion entre Anima et Neo
pour concevoir l'architecture complète"
```

### Changer d'Agent

**Méthode 1 : Sélecteur d'agent**
- Cliquez sur le nom de l'agent en haut du chat
- Sélectionnez l'agent désiré
- Continuez la conversation avec le nouvel agent

**Méthode 2 : Consultation ponctuelle**
- Survolez un message d'agent
- Cliquez sur l'icône d'un autre agent (cercle en haut du message)
- L'agent consulté donnera son point de vue sur ce message

### Mode RAG (Recherche Documentaire)

**Activation** :
1. Cliquez sur l'icône 📚 dans la zone de saisie
2. Le toggle devient actif (bleu/cyan)
3. L'agent recherchera dans vos documents uploadés

**Bénéfices** :
- Réponses basées sur VOS données
- Citations de sources précises
- Contexte enrichi

**Note** : Légèrement plus lent (~2-3s) mais beaucoup plus précis

---

## Centre Mémoire

⭐ **NOUVEAU (V3.8 - 2025-10-15)** : Feedback temps réel avec barre de progression !

### Qu'est-ce que la Consolidation Mémoire ?

La **consolidation mémoire** analyse vos conversations pour extraire automatiquement :

1. **Concepts clés** : Thématiques, sujets techniques abordés
2. **Faits structurés** : Informations explicites (mot-code, préférences)
3. **Préférences & intentions** : Vos habitudes, besoins récurrents
4. **Entités nommées** : Noms propres, outils, frameworks mentionnés

### Deux Niveaux de Mémoire

#### 📝 STM (Short-Term Memory)
- Résumé de la session en cours (2-3 phrases)
- Conservé pendant la session active
- Réduit le contexte envoyé aux LLM
- Visible dans le Centre Mémoire

#### 🧬 LTM (Long-Term Memory)
- Base de connaissances persistante
- Stockée dans ChromaDB (recherche vectorielle)
- Partagée entre sessions
- Injection automatique dans les réponses agents
- Badge 📚 indique quand la LTM est utilisée

### Utiliser le Centre Mémoire

#### Accès
1. Cliquez sur **"Mémoire"** dans le menu principal
2. Vous voyez 3 cartes résumées :
   - **STM** : État mémoire court terme (Disponible / Vide)
   - **LTM** : Nombre d'items en mémoire longue
   - **Dernière analyse** : Timestamp dernière consolidation

#### Consolider Mémoire (Manuel)

**Quand consolider ?**
- ✅ Après une discussion importante à mémoriser
- ✅ Pour forcer l'extraction de préférences
- ✅ Si l'agent "oublie" des informations précédentes

**Comment ?**
1. Cliquez sur **"Consolider mémoire"**
2. Une barre de progression apparaît :
   ```
   Extraction des concepts... (2/5 sessions)
   ```
3. Phases affichées :
   - "Extraction des concepts"
   - "Analyse des préférences"
   - "Vectorisation des connaissances"
4. Message final :
   ```
   ✓ Consolidation terminée : 5 sessions, 23 nouveaux items
   ```

**Durée estimée** : 30 secondes à 2 minutes selon le volume

**💡 Note** : La consolidation se fait aussi **automatiquement** tous les 10 messages

#### Effacer la Mémoire

**Attention** : Action irréversible !

1. Cliquez sur **"Effacer"**
2. Une modal de confirmation s'affiche
3. Choisissez :
   - Effacer STM + LTM (tout)
   - Effacer uniquement STM
   - Annuler
4. Confirmez

**Cas d'usage** :
- Commencer un nouveau projet
- Réinitialiser les préférences
- Tests / debugging

### Comprendre les Statistiques

**STM Disponible** :
- Résumé session chargé ✅
- Concepts extraits disponibles
- Les agents ont accès au contexte court terme

**LTM (X items)** :
- Nombre de concepts/préférences/faits stockés
- Base de connaissances persistante
- Recherche vectorielle active

**Dernière analyse** :
- Timestamp consolidation
- "Jamais" si aucune consolidation
- "Analyse en cours" pendant exécution

---

## Gestion des Documents

### Upload de Documents

**Formats supportés** :
- PDF (`.pdf`)
- Texte (`.txt`, `.md`)
- Code (`.py`, `.js`, `.ts`, etc.)
- Office (`.docx`, `.xlsx`) - selon configuration

**Comment uploader** :
1. Allez dans **Documents** (menu)
2. Cliquez sur **"Upload"** ou drag & drop
3. Sélectionnez vos fichiers
4. Attendez la fin du traitement (chunking + vectorisation)
5. Le document apparaît dans la liste

### Utiliser les Documents (RAG)

1. Activez le mode RAG (toggle 📚)
2. Posez votre question
3. L'agent recherche dans vos documents
4. Réponse enrichie avec citations de sources

**Exemple** :
```
User (avec RAG activé) :
"Quelle est la configuration recommandée pour FastAPI ?"

Neo :
D'après votre document "fastapi_guide.pdf", la configuration
recommandée inclut Uvicorn avec 4 workers...
[Source: fastapi_guide.pdf, page 12]
```

### Gérer les Documents

**Voir les détails** :
- Cliquez sur un document → Voir métadonnées (taille, date, chunks)

**Supprimer** :
- Cliquez sur l'icône 🗑️ → Confirmation → Supprimé

---

## Mode RAG

### Qu'est-ce que le RAG ?

**RAG** = Retrieval-Augmented Generation (Génération Augmentée par Récupération)

Au lieu de répondre uniquement avec ses connaissances pré-entraînées, l'agent :
1. **Recherche** dans vos documents uploadés
2. **Récupère** les passages pertinents
3. **Génère** une réponse basée sur VOS données

### Activer/Désactiver

**Toggle RAG** (zone de saisie) :
- Icône 📚 (gris) = Désactivé
- Icône 📚 (bleu/cyan) = Activé

**Raccourci clavier** : `Ctrl + R` (à venir)

### Mode RAG Strict

Dans **Paramètres** > **RAG** :
- **Strict Mode OFF** : Combine connaissances générales + documents
- **Strict Mode ON** : Répond UNIQUEMENT à partir de vos documents

**Cas d'usage Strict Mode** :
- Conformité réglementaire
- Données sensibles
- Éviter les hallucinations

### Recherche Hybride (BM25 + Vectorielle)

ÉMERGENCE utilise une **recherche hybride** :
- **BM25** : Recherche lexicale (mots-clés exacts)
- **Vectorielle** : Recherche sémantique (similarité de sens)
- **Alpha = 0.5** : Équilibre 50/50 (configurable dans Paramètres)

**Bénéfice** : Meilleure pertinence des résultats

---

## Paramètres

### Accéder aux Paramètres

1. Cliquez sur **⚙️ Paramètres** (menu)
2. Naviguez entre les onglets :
   - **Profil** : Informations utilisateur
   - **Modèles** : Configuration LLM par agent
   - **RAG** : Paramètres recherche documentaire
   - **UI** : Personnalisation interface
   - **Sécurité** : Mot de passe, sessions
   - **Tutoriel** : Guides interactifs

### Paramètres RAG

**Score Threshold** (Seuil de pertinence) :
- `0.0` : Pas de filtrage (tous résultats)
- `0.3` : Filtrage modéré (recommandé)
- `0.7+` : Filtrage strict (haute précision)

**Alpha** (Poids vectoriel vs BM25) :
- `0.0` : Full BM25 (lexical pur)
- `0.5` : Équilibre (recommandé)
- `1.0` : Full vectoriel (sémantique pur)

**Strict Mode** :
- OFF : Agent peut utiliser connaissances générales
- ON : Agent répond UNIQUEMENT depuis vos documents

### Paramètres Modèles

Personnalisez le modèle LLM par agent :
- Anima : `gpt-4o-mini` (défaut)
- Neo : `gemini-2.0-flash-exp` (défaut)
- Nexus : `claude-3-5-sonnet-20241022` (défaut)

**Note** : Nécessite clés API configurées

---

## Trucs et Astuces

### 💡 Consolidation Mémoire

**Truc 1 : Consolidez après les discussions importantes**
```
Après une discussion de conception architecturale de 20 messages :
→ Allez dans Mémoire
→ Cliquez "Consolider mémoire"
→ Les concepts sont sauvegardés en LTM
→ Prochaine session : l'agent s'en souvient !
```

**Truc 2 : Surveillez la barre de progression**
```
Si consolidation >5 min sans retour :
→ Vérifiez les logs backend (F12 → Console)
→ Vérifiez connexion réseau
→ Réessayez
```

**Truc 3 : Comprendre les phases**
- "Extraction concepts" : Analyse LLM (~20s par session)
- "Analyse préférences" : Classification intent/préférence (~10s)
- "Vectorisation" : Sauvegarde ChromaDB (~5s)

### 💬 Chat Multi-Agents

**Truc 1 : Combinez les perspectives**
```
1. Demandez à Neo une analyse technique
2. Cliquez sur l'icône Anima au-dessus de sa réponse
3. Obtenez la perspective empathique sur l'impact utilisateur
```

**Truc 2 : Utilisez Nexus pour la synthèse**
```
"Nexus, synthétise les points de vue de Neo et Anima
sur cette architecture et recommande la meilleure approche"
```

### 📚 Mode RAG

**Truc 1 : Nommez bien vos documents**
```
❌ doc1.pdf, doc2.pdf
✅ fastapi_config_guide.pdf, api_security_best_practices.pdf
```

**Truc 2 : Testez avec et sans RAG**
```
Question sans RAG : Réponse générale
Même question avec RAG : Réponse spécifique à vos docs
```

### ⌨️ Raccourcis Clavier (à venir)

- `Ctrl + Enter` : Envoyer message
- `Ctrl + R` : Toggle RAG
- `Ctrl + K` : Nouvelle conversation
- `Ctrl + /` : Ouvrir recherche

---

## FAQ

### La consolidation mémoire prend-elle longtemps ?

**Durée normale** : 30 secondes à 2 minutes
- Dépend du nombre de sessions à consolider
- 3 appels LLM par session (fallback cascade)
- La barre de progression affiche l'avancement

**Si >5 minutes** : Vérifier logs backend

### Puis-je annuler une consolidation ?

**Non**, pas encore implémenté (roadmap Phase 2)
- La consolidation continue en arrière-plan
- Refresh la page pour interrompre (perte partielle données)

### Quelle différence entre STM et LTM ?

| Critère | STM | LTM |
|---------|-----|-----|
| **Durée** | Session en cours | Persistant |
| **Stockage** | SQLite (table `sessions`) | ChromaDB (vectoriel) |
| **Contenu** | Résumé 2-3 phrases | Concepts/Préférences/Faits |
| **Usage** | Contexte immédiat | Recherche sémantique |
| **Reset** | Fin de session | Manuel ("Effacer") |

### Le mode RAG ralentit-il les réponses ?

**Oui, légèrement** :
- Sans RAG : ~1-2s
- Avec RAG : ~2-4s (recherche vectorielle + BM25)

**Bénéfice** : Précision ++, hallucinations --

### Puis-je voir ce qui est stocké en LTM ?

**Partiellement** :
- Centre Mémoire → Compteur LTM (nombre items)
- Pas encore d'interface visualisation détaillée (roadmap)

**Workaround** : Demandez à un agent :
```
"Anima, que sais-tu de moi d'après ta mémoire longue terme ?"
```

---

## Support & Feedback

### Signaler un Bug

**Méthode 1 : Formulaire Beta**
1. Accédez à `/beta_report.html`
2. Remplissez le formulaire
3. Soumettez (envoi par email)

**Méthode 2 : Email Direct**
- Email : `gonzalefernando@gmail.com`
- Sujet : `[ÉMERGENCE Beta] Bug - Description courte`

### Demander une Fonctionnalité

Même processus que signalement bug, en précisant :
- Cas d'usage
- Bénéfice attendu
- Priorité (haute/moyenne/basse selon vous)

### Documentation Complète

- **[Tutoriel Système](TUTORIAL_SYSTEM.md)** : Guide complet
- **[Mémoire Progressive](Memoire.md)** : Doc technique STM/LTM
- **[Architecture](architecture/)** : Détails techniques

---

## Changelog Récent

### V3.8 (2025-10-15) - Améliorations Mémoire UX

✅ **Feedback temps réel** : Barre de progression consolidation
✅ **Labels traduits** : Phases en français ("Extraction concepts...")
✅ **Message final** : Résumé sessions/items consolidés
✅ **Bouton renommé** : "Analyser" → "Consolider mémoire"
✅ **Tooltip explicatif** : Survol bouton affiche description
✅ **Documentation enrichie** : Tutoriel + guides mis à jour

### V3.7 (2025-10-11) - Extraction Préférences

✅ Extraction automatique préférences/intentions
✅ Classification par type (preference/intent/constraint)
✅ Injection contexte agents (confidence ≥0.6)

---

**Créé le** : 2025-10-15
**Version** : V8 - Beta
**Statut** : ✅ Actif

---

## Prochaines Étapes

1. Explorez le **Centre Mémoire** ⭐ **NOUVEAU**
2. Essayez la **consolidation manuelle**
3. Uploadez vos **premiers documents**
4. Testez le **mode RAG**
5. Donnez votre **feedback** !

**Bienvenue dans ÉMERGENCE !** 🚀
