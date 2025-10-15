# Glossaire IA - ÉMERGENCE

> **Votre dictionnaire de l'intelligence artificielle**
> Ce glossaire explique les termes clés utilisés dans ÉMERGENCE et le monde de l'IA conversationnelle, avec des définitions accessibles au grand public.

---

## Table des matières

- [Agent Conversationnel](#agent-conversationnel)
- [LLM (Large Language Model)](#llm-large-language-model)
- [Prompt](#prompt)
- [RAG (Retrieval-Augmented Generation)](#rag-retrieval-augmented-generation)
- [Mémoire (STM / LTM)](#memoire-stm-ltm)
- [Vectorisation](#vectorisation)
- [Émergence](#emergence)
- [Hallucination (IA)](#hallucination-ia)
- [Token](#token)
- [Température](#temperature)
- [Contexte (fenêtre de contexte)](#contexte-fenetre-de-contexte)
- [Embedding](#embedding)
- [Fine-tuning](#fine-tuning)
- [Prompt Engineering](#prompt-engineering)
- [Zero-shot / Few-shot Learning](#zero-shot-few-shot-learning)
- [Chunking](#chunking)
- [Similarité Cosinus](#similarite-cosinus)

---

## Agent Conversationnel

### Définition
Un **agent conversationnel** (ou chatbot IA) est un programme informatique basé sur un **LLM** (voir ci-dessous), conçu pour dialoguer en langage naturel et accomplir des tâches spécifiques.

### Dans ÉMERGENCE
Anima, Neo et Nexus sont trois agents conversationnels avec des personnalités et missions distinctes :
- **Anima** : empathique et clarificatrice
- **Neo** : analytique et structurante
- **Nexus** : coordonnatrice et organisatrice

### Analogie
Imaginez trois collègues experts, chacun avec une spécialité, qui collaborent pour vous aider sur un projet.

### Pourquoi c'est important
Les agents conversationnels démocratisent l'accès à l'expertise : plus besoin d'être analyste de données pour obtenir une synthèse, ni écrivain pour rédiger une lettre.

---

## LLM (Large Language Model)

### Définition
Un **LLM** (Modèle de Langage de Grande Taille) est une intelligence artificielle entraînée sur des milliards de mots pour comprendre et générer du texte humain.

### Exemples célèbres
- **GPT-4** (OpenAI)
- **Claude** (Anthropic)
- **Mistral** (Mistral AI)
- **LLaMA** (Meta)
- **Gemini** (Google)

### Comment ça fonctionne ?
Un LLM est un réseau de neurones artificiels entraîné sur d'immenses corpus de textes (livres, articles, sites web). Il apprend à prédire le mot suivant dans une phrase, ce qui lui permet ensuite de générer du texte cohérent.

### Analogie
Imaginez une bibliothèque universelle qui a "lu" tout internet et peut discuter de n'importe quel sujet. Le LLM ne "comprend" pas vraiment, mais il reconnaît des motifs statistiques dans le langage.

### Limites
- Peut **halluciner** (inventer des faits faux)
- N'a pas de conscience ou de jugement moral
- Dépend de la qualité de ses données d'entraînement

---

## Prompt

### Définition
Le **prompt** est la consigne, la question ou l'instruction que vous donnez à un agent conversationnel.

### Exemples
- **Prompt simple** : "Explique-moi le changement climatique."
- **Prompt détaillé** : "Explique-moi les causes du changement climatique en 200 mots, avec un ton pédagogique pour des lycéens."

### Bonnes pratiques
- **Soyez précis** : Plus votre prompt est clair, meilleure sera la réponse.
- **Donnez du contexte** : "Je prépare une présentation pour mon entreprise..." aide l'IA à adapter le ton.
- **Itérez** : Si la première réponse n'est pas parfaite, reformulez ou précisez.

### Prompt Engineering
L'art d'écrire des prompts efficaces s'appelle le **prompt engineering** (voir section dédiée ci-dessous).

---

## RAG (Retrieval-Augmented Generation)

### Définition
Le **RAG** (Génération Augmentée par Recherche) est une technique où l'IA cherche d'abord des documents pertinents dans une base de données, puis génère une réponse en s'appuyant sur ces documents.

### Comment ça fonctionne ?
1. **Vous posez une question** : "Quelles sont les recommandations du rapport sur le climat ?"
2. **L'IA cherche** : Elle parcourt vos documents téléchargés et trouve les passages pertinents.
3. **L'IA génère** : Elle rédige une réponse en citant les sources trouvées.

### Avantages
- **Réduit les hallucinations** : L'IA s'appuie sur des faits réels (vos documents).
- **Permet la traçabilité** : Vous savez d'où vient l'information (page, document).
- **Personnalise** : L'IA répond avec VOS données, pas des informations génériques.

### Dans ÉMERGENCE
Activez le mode RAG depuis l'interface de chat pour interroger vos documents PDF, Word, etc. Les agents citeront automatiquement les passages pertinents.

### Analogie
C'est comme demander à un assistant de parcourir votre bibliothèque avant de répondre, au lieu de répondre de mémoire (où il pourrait se tromper).

---

## Mémoire (STM / LTM)

### Définition
La **mémoire conversationnelle** est le mécanisme par lequel un agent se souvient des échanges passés pour offrir de la continuité et de la personnalisation.

### Les deux types dans ÉMERGENCE

#### STM (Short-Term Memory - Mémoire à Court Terme)
- **Ce qu'elle fait** : Résume la session en cours.
- **Durée** : Valable uniquement pendant la conversation active.
- **Exemple** : "L'utilisateur parle aujourd'hui d'un voyage en Italie."
- **Analogie** : Comme votre mémoire immédiate quand vous discutez avec quelqu'un.

#### LTM (Long-Term Memory - Mémoire à Long Terme)
- **Ce qu'elle fait** : Base de connaissances persistante qui se souvient entre les sessions.
- **Durée** : Permanente, enrichie au fil du temps.
- **Exemple** : "L'utilisateur aime l'Italie, préfère les cuisines authentiques."
- **Analogie** : Comme vos souvenirs qui restent après avoir quitté la conversation.

### Pourquoi c'est révolutionnaire ?
Sans mémoire, chaque conversation recommence à zéro. Avec mémoire, l'agent "apprend" vos préférences et adapte ses réponses au fil du temps.

### Dans ÉMERGENCE
Vous pouvez :
- **Consulter** la mémoire (graphe de connaissances)
- **Consolider** manuellement après une session importante
- **Effacer** si nécessaire
- **Éditer** les concepts mémorisés

---

## Vectorisation

### Définition
La **vectorisation** (ou embedding) est la manière de représenter du texte sous forme de nombres (vecteurs) pour que l'IA puisse les comparer mathématiquement.

### Comment ça fonctionne ?
Chaque mot, phrase ou document est transformé en un tableau de nombres (par ex. 1536 nombres pour GPT-4).

**Exemple simplifié** :
- "Chat" → [0.2, 0.8, 0.1, ...]
- "Chien" → [0.25, 0.75, 0.15, ...] (proche de "chat")
- "Voiture" → [0.9, 0.1, 0.05, ...] (loin de "chat")

### Analogie
Imaginez que chaque concept est un point dans un espace multidimensionnel. Les concepts similaires (chat, chien) sont proches, les concepts différents (chat, voiture) sont éloignés.

### Pourquoi c'est utile ?
La vectorisation permet à l'IA de :
- **Chercher rapidement** des documents pertinents (RAG)
- **Retrouver** des souvenirs similaires (mémoire LTM)
- **Comparer** des idées (similarité cosinus - voir ci-dessous)

### Dans ÉMERGENCE
Tous vos documents et concepts mémorisés sont vectorisés pour permettre une recherche ultra-rapide.

---

## Émergence

### Définition
L'**émergence** est un concept où la collaboration de plusieurs éléments simples produit un résultat complexe, supérieur à la somme de leurs parties.

### Exemples dans la nature
- Les **fourmis** : Individuellement simples, mais en colonie elles construisent des structures complexes.
- Le **cerveau** : Des milliards de neurones simples créent la conscience.

### Dans ÉMERGENCE (le projet)
- **Anima** (empathie) + **Neo** (analyse) + **Nexus** (coordination) ensemble offrent une réponse plus riche que chacun séparément.
- La mémoire collective des agents devient plus intelligente au fil du temps.

### Philosophie
C'est le cœur du projet : l'idée que la **coopération augmente l'intelligence**. Plusieurs agents spécialisés collaborant valent mieux qu'un seul agent généraliste.

---

## Hallucination (IA)

### Définition
Une **hallucination** se produit quand un LLM invente des informations fausses mais les présente avec assurance.

### Exemples
- "Albert Einstein a découvert la pénicilline." (Faux, c'était Alexander Fleming)
- "Le sommet du Mont Blanc culmine à 5000 mètres." (Faux, c'est 4808 mètres)
- Inventer des citations ou des références bibliographiques inexistantes.

### Pourquoi ça arrive ?
Les LLM sont entraînés à prédire du texte plausible, pas forcément vrai. Si le modèle n'a pas la bonne information, il peut "combler les trous" avec des inventions.

### Comment éviter ?
- **Activez le RAG** : L'IA s'appuie sur vos documents (faits vérifiés).
- **Vérifiez les sources** : Demandez "D'où vient cette information ?"
- **Croisez les réponses** : Demandez à plusieurs agents ou sources.
- **Utilisez le mode strict** : ÉMERGENCE peut refuser de répondre si aucun document pertinent n'est trouvé.

---

## Token

### Définition
Un **token** est l'unité de texte pour un LLM. Un token peut être un mot, une partie de mot, ou un caractère.

### Exemples
- "Bonjour" → 1 token
- "Bonjour !" → 2 tokens (mot + ponctuation)
- "Intelligence artificielle" → 2-3 tokens selon le modèle

### Pourquoi c'est important ?
- **Limites de contexte** : Les LLM ont des limites (ex. 4000, 16000, 128000 tokens). Plus vous écrivez, plus vous consommez de tokens.
- **Coût** : Les LLM cloud facturent au token (ex. 0.03$ / 1000 tokens).
- **Performance** : Plus de tokens = plus de temps de calcul.

### Dans ÉMERGENCE
Le Dashboard affiche votre consommation de tokens par agent et par période.

---

## Température

### Définition
La **température** est un paramètre qui contrôle la créativité (ou imprévisibilité) d'un LLM.

### Échelle
- **Basse (0.0-0.3)** : Réponses précises, déterministes et prévisibles.
  - **Bon pour** : Faits, résumés, analyses techniques.
  - **Exemple** : "Quelle est la capitale de la France ?" → "Paris" (toujours la même réponse).

- **Moyenne (0.5-0.7)** : Équilibre créativité/précision.
  - **Bon pour** : Conversation générale, conseils.

- **Haute (0.8-1.0)** : Réponses créatives, variées et parfois surprenantes.
  - **Bon pour** : Écriture créative, brainstorming, poésie.
  - **Exemple** : "Écris-moi un poème sur l'automne" → Réponse différente à chaque fois.

### Dans ÉMERGENCE
Vous pouvez ajuster la température de chaque agent dans les Paramètres.

---

## Contexte (fenêtre de contexte)

### Définition
Le **contexte** (ou fenêtre de contexte) est la quantité de texte que l'IA peut "voir" et "se rappeler" en une seule fois.

### Exemples
- **GPT-3.5** : ~4000 tokens (~3000 mots)
- **GPT-4** : ~8000 ou 32000 tokens selon la version
- **Claude 2** : ~100 000 tokens (~75 000 mots)

### Pourquoi c'est une limite ?
Si votre conversation dépasse la fenêtre de contexte, l'IA "oublie" le début. C'est comme si vous discutiez avec quelqu'un qui ne se souvient que des 10 dernières minutes.

### Dans ÉMERGENCE
La **mémoire LTM** contourne cette limite en résumant et stockant les informations importantes même après la fin de la session.

---

## Embedding

### Définition
Un **embedding** est la représentation vectorielle d'un texte (voir **Vectorisation** ci-dessus). C'est le terme technique pour "transformer du texte en nombres".

### Modèles d'embedding populaires
- **text-embedding-ada-002** (OpenAI)
- **sentence-transformers** (Open source)
- **all-MiniLM-L6-v2** (Léger et rapide)

### Utilisation dans ÉMERGENCE
Tous vos documents et concepts sont convertis en embeddings pour permettre la recherche sémantique (chercher par sens, pas juste par mots-clés).

---

## Fine-tuning

### Définition
Le **fine-tuning** (affinage) est le processus d'entraîner un LLM existant sur des données spécifiques pour le spécialiser.

### Exemple
- Prendre GPT-4 et l'entraîner sur des dossiers médicaux pour créer un assistant médical.
- Prendre Mistral et l'entraîner sur du code Python pour améliorer ses compétences en programmation.

### Différence avec le RAG
- **Fine-tuning** : Modifie les poids du modèle (coûteux, technique).
- **RAG** : Ajoute simplement des documents dans la base de données (rapide, accessible).

---

## Prompt Engineering

### Définition
Le **prompt engineering** est l'art et la science d'écrire des prompts efficaces pour obtenir les meilleures réponses d'un LLM.

### Techniques avancées
- **Chain-of-Thought** : Demander à l'IA de raisonner étape par étape.
  - Exemple : "Explique ton raisonnement avant de répondre."
- **Role-playing** : Assigner un rôle à l'IA.
  - Exemple : "Tu es un professeur de physique. Explique la relativité."
- **Few-shot learning** : Donner des exemples avant la question.
  - Exemple : "Synonyme de 'heureux' : content. Synonyme de 'triste' : ?"

### Dans ÉMERGENCE
Les agents utilisent déjà des techniques de prompt engineering en interne pour optimiser leurs réponses.

---

## Zero-shot / Few-shot Learning

### Définition
- **Zero-shot** : L'IA répond sans aucun exemple préalable, juste avec la consigne.
- **Few-shot** : Vous donnez quelques exemples avant la question pour guider l'IA.

### Exemple

**Zero-shot** :
```
Traduis en anglais : "Bonjour"
→ "Hello"
```

**Few-shot** :
```
Traduis en anglais :
- "Bonjour" → "Hello"
- "Merci" → "Thank you"
- "Au revoir" → ?
→ "Goodbye"
```

### Pourquoi c'est utile ?
Few-shot améliore la précision sans avoir à fine-tuner le modèle.

---

## Chunking

### Définition
Le **chunking** est le processus de découper un document long en morceaux (chunks) plus petits pour faciliter l'indexation et la recherche.

### Pourquoi c'est nécessaire ?
Les LLM ont des limites de contexte. Un document de 100 pages ne peut pas être traité en une fois. On le découpe donc en chunks de ~500-1000 mots.

### Dans ÉMERGENCE
Quand vous téléchargez un PDF, le système :
1. Le découpe en chunks (~500 tokens par défaut).
2. Vectorise chaque chunk.
3. Lors d'une question, cherche les chunks pertinents (RAG).

### Paramétrage
Vous pouvez ajuster la taille des chunks dans les Paramètres :
- **Petits chunks (200 tokens)** : Réponses très précises, mais peut manquer le contexte global.
- **Grands chunks (800 tokens)** : Plus de contexte, mais moins de précision.

---

## Similarité Cosinus

### Définition
La **similarité cosinus** est une mesure mathématique pour comparer deux vecteurs (embeddings) et déterminer leur degré de similarité.

### Comment ça fonctionne ?
- **Score 1.0** : Identique
- **Score 0.8-0.99** : Très similaire
- **Score 0.5-0.79** : Moyennement similaire
- **Score 0.0** : Pas de similarité
- **Score négatif** : Opposé

### Exemple
Si vous cherchez "voyage en Italie", le système compare votre question vectorisée avec tous les chunks de documents :
- "Guide de voyage à Rome" → 0.92 (très pertinent)
- "Histoire de l'Italie" → 0.78 (pertinent)
- "Recette de pizza" → 0.65 (moyennement pertinent)
- "Mécanique automobile" → 0.12 (pas pertinent)

### Dans ÉMERGENCE
Le RAG utilise la similarité cosinus pour classer les documents par pertinence avant de générer une réponse.

---

## Ressources pour aller plus loin

### Articles pédagogiques
- [Qu'est-ce qu'un LLM ?](https://fr.wikipedia.org/wiki/Grand_mod%C3%A8le_de_langage) (Wikipedia)
- [Comprendre le RAG](https://www.anthropic.com/research/retrieval-augmented-generation) (Anthropic)
- [Guide du prompt engineering](https://www.promptingguide.ai/) (Prompting Guide)

### Tutoriels techniques
- [Documentation OpenAI](https://platform.openai.com/docs) (GPT, embeddings)
- [Documentation Anthropic](https://docs.anthropic.com) (Claude)
- [LangChain](https://python.langchain.com/) (Framework RAG)

### Chaînes YouTube vulgarisation
- [Underscore_](https://www.youtube.com/@Underscore_) (IA en français)
- [Lex Fridman](https://www.youtube.com/@lexfridman) (Interviews experts IA)
- [Two Minute Papers](https://www.youtube.com/@TwoMinutePapers) (Recherche IA vulgarisée)

---

## Contribuer au glossaire

Ce glossaire est vivant et s'enrichit régulièrement. Si vous identifiez :
- Un terme manquant
- Une définition imprécise
- Une meilleure analogie

Contactez l'équipe ÉMERGENCE ou proposez une modification via le dépôt GitHub.

---

**Version** : 1.0
**Dernière mise à jour** : Octobre 2025
**Auteur** : Équipe ÉMERGENCE
**Licence** : CC BY-SA 4.0 (Creative Commons Attribution-ShareAlike)

---

**🔗 Retour au** [Tutoriel ÉMERGENCE](EMERGENCE_TUTORIEL_VULGARISE_V2.md)
