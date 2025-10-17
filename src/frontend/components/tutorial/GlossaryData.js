/**
 * @module components/tutorial/GlossaryData
 * @description Glossaire IA complet pour ÉMERGENCE
 * Source: docs/glossaire.md
 */

import { TutorialIcons } from './TutorialIcons.js';

export const GLOSSARY_ENTRIES = {
  'agent-conversationnel': {
    id: 'agent-conversationnel',
    term: 'Agent Conversationnel',
    icon: TutorialIcons.brain,
    definition: 'Un <strong>agent conversationnel</strong> (ou chatbot IA) est un programme informatique basé sur un <strong>LLM</strong>, conçu pour dialoguer en langage naturel et accomplir des tâches spécifiques.',
    inEmergence: 'Anima, Neo et Nexus sont trois agents conversationnels avec des personnalités et missions distinctes : <ul><li><strong>Anima</strong> : empathique et clarificatrice</li><li><strong>Neo</strong> : analytique et structurante</li><li><strong>Nexus</strong> : coordonnatrice et organisatrice</li></ul>',
    analogy: 'Imaginez trois collègues experts, chacun avec une spécialité, qui collaborent pour vous aider sur un projet.',
    why: 'Les agents conversationnels démocratisent l\'accès à l\'expertise : plus besoin d\'être analyste de données pour obtenir une synthèse, ni écrivain pour rédiger une lettre.',
    relatedTerms: ['llm-large-language-model', 'prompt', 'emergence']
  },

  'llm-large-language-model': {
    id: 'llm-large-language-model',
    term: 'LLM (Large Language Model)',
    icon: TutorialIcons.brain,
    definition: 'Un <strong>LLM</strong> (Modèle de Langage de Grande Taille) est une intelligence artificielle entraînée sur des milliards de mots pour comprendre et générer du texte humain.',
    examples: '<strong>Exemples célèbres :</strong><ul><li><strong>GPT-4</strong> (OpenAI)</li><li><strong>Claude</strong> (Anthropic)</li><li><strong>Mistral</strong> (Mistral AI)</li><li><strong>LLaMA</strong> (Meta)</li><li><strong>Gemini</strong> (Google)</li></ul>',
    howItWorks: 'Un LLM est un réseau de neurones artificiels entraîné sur d\'immenses corpus de textes (livres, articles, sites web). Il apprend à prédire le mot suivant dans une phrase, ce qui lui permet ensuite de générer du texte cohérent.',
    analogy: 'Imaginez une bibliothèque universelle qui a "lu" tout internet et peut discuter de n\'importe quel sujet. Le LLM ne "comprend" pas vraiment, mais il reconnaît des motifs statistiques dans le langage.',
    limits: '<ul><li>Peut <strong>halluciner</strong> (inventer des faits faux)</li><li>N\'a pas de conscience ou de jugement moral</li><li>Dépend de la qualité de ses données d\'entraînement</li></ul>',
    relatedTerms: ['hallucination-ia', 'prompt', 'temperature', 'token']
  },

  'prompt': {
    id: 'prompt',
    term: 'Prompt',
    icon: TutorialIcons.edit,
    definition: 'Le <strong>prompt</strong> est la consigne, la question ou l\'instruction que vous donnez à un agent conversationnel.',
    examples: '<ul><li><strong>Prompt simple :</strong> "Explique-moi le changement climatique."</li><li><strong>Prompt détaillé :</strong> "Explique-moi les causes du changement climatique en 200 mots, avec un ton pédagogique pour des lycéens."</li></ul>',
    bestPractices: '<ul><li><strong>Soyez précis :</strong> Plus votre prompt est clair, meilleure sera la réponse.</li><li><strong>Donnez du contexte :</strong> "Je prépare une présentation pour mon entreprise..." aide l\'IA à adapter le ton.</li><li><strong>Itérez :</strong> Si la première réponse n\'est pas parfaite, reformulez ou précisez.</li></ul>',
    relatedTerms: ['prompt-engineering', 'llm-large-language-model', 'temperature']
  },

  'rag-retrieval-augmented-generation': {
    id: 'rag-retrieval-augmented-generation',
    term: 'RAG (Retrieval-Augmented Generation)',
    icon: TutorialIcons.search,
    definition: 'Le <strong>RAG</strong> (Génération Augmentée par Recherche) est une technique où l\'IA cherche d\'abord des documents pertinents dans une base de données, puis génère une réponse en s\'appuyant sur ces documents.',
    howItWorks: '<ol><li><strong>Vous posez une question :</strong> "Quelles sont les recommandations du rapport sur le climat ?"</li><li><strong>L\'IA cherche :</strong> Elle parcourt vos documents téléchargés et trouve les passages pertinents.</li><li><strong>L\'IA génère :</strong> Elle rédige une réponse en citant les sources trouvées.</li></ol>',
    advantages: '<ul><li><strong>Réduit les hallucinations :</strong> L\'IA s\'appuie sur des faits réels (vos documents).</li><li><strong>Permet la traçabilité :</strong> Vous savez d\'où vient l\'information (page, document).</li><li><strong>Personnalise :</strong> L\'IA répond avec VOS données, pas des informations génériques.</li></ul>',
    inEmergence: 'Activez le mode RAG depuis l\'interface de chat pour interroger vos documents PDF, Word, etc. Les agents citeront automatiquement les passages pertinents.',
    analogy: 'C\'est comme demander à un assistant de parcourir votre bibliothèque avant de répondre, au lieu de répondre de mémoire (où il pourrait se tromper).',
    relatedTerms: ['vectorisation', 'embedding', 'chunking', 'similarite-cosinus']
  },

  'memoire-stm-ltm': {
    id: 'memoire-stm-ltm',
    term: 'Mémoire (STM / LTM)',
    icon: TutorialIcons.database,
    definition: 'La <strong>mémoire conversationnelle</strong> est le mécanisme par lequel un agent se souvient des échanges passés pour offrir de la continuité et de la personnalisation.',
    types: '<h4>STM (Short-Term Memory - Mémoire à Court Terme)</h4><ul><li><strong>Ce qu\'elle fait :</strong> Résume la session en cours.</li><li><strong>Durée :</strong> Valable uniquement pendant la conversation active.</li><li><strong>Exemple :</strong> "L\'utilisateur parle aujourd\'hui d\'un voyage en Italie."</li><li><strong>Analogie :</strong> Comme votre mémoire immédiate quand vous discutez avec quelqu\'un.</li></ul><h4>LTM (Long-Term Memory - Mémoire à Long Terme)</h4><ul><li><strong>Ce qu\'elle fait :</strong> Base de connaissances persistante qui se souvient entre les sessions.</li><li><strong>Durée :</strong> Permanente, enrichie au fil du temps.</li><li><strong>Exemple :</strong> "L\'utilisateur aime l\'Italie, préfère les cuisines authentiques."</li><li><strong>Analogie :</strong> Comme vos souvenirs qui restent après avoir quitté la conversation.</li></ul>',
    why: 'Sans mémoire, chaque conversation recommence à zéro. Avec mémoire, l\'agent "apprend" vos préférences et adapte ses réponses au fil du temps.',
    inEmergence: 'Vous pouvez :<ul><li><strong>Consulter</strong> la mémoire (graphe de connaissances)</li><li><strong>Consolider</strong> manuellement après une session importante</li><li><strong>Effacer</strong> si nécessaire</li><li><strong>Éditer</strong> les concepts mémorisés</li></ul>',
    relatedTerms: ['vectorisation', 'contexte-fenetre-de-contexte', 'embedding']
  },

  'vectorisation': {
    id: 'vectorisation',
    term: 'Vectorisation',
    icon: TutorialIcons.barChart,
    definition: 'La <strong>vectorisation</strong> (ou embedding) est la manière de représenter du texte sous forme de nombres (vecteurs) pour que l\'IA puisse les comparer mathématiquement.',
    howItWorks: 'Chaque mot, phrase ou document est transformé en un tableau de nombres (par ex. 1536 nombres pour GPT-4).',
    example: '<strong>Exemple simplifié :</strong><ul><li>"Chat" → [0.2, 0.8, 0.1, ...]</li><li>"Chien" → [0.25, 0.75, 0.15, ...] (proche de "chat")</li><li>"Voiture" → [0.9, 0.1, 0.05, ...] (loin de "chat")</li></ul>',
    analogy: 'Imaginez que chaque concept est un point dans un espace multidimensionnel. Les concepts similaires (chat, chien) sont proches, les concepts différents (chat, voiture) sont éloignés.',
    why: 'La vectorisation permet à l\'IA de :<ul><li><strong>Chercher rapidement</strong> des documents pertinents (RAG)</li><li><strong>Retrouver</strong> des souvenirs similaires (mémoire LTM)</li><li><strong>Comparer</strong> des idées (similarité cosinus)</li></ul>',
    inEmergence: 'Tous vos documents et concepts mémorisés sont vectorisés pour permettre une recherche ultra-rapide.',
    relatedTerms: ['embedding', 'rag-retrieval-augmented-generation', 'similarite-cosinus']
  },

  'emergence': {
    id: 'emergence',
    term: 'Émergence',
    icon: TutorialIcons.zap,
    definition: 'L\'<strong>émergence</strong> est un concept où la collaboration de plusieurs éléments simples produit un résultat complexe, supérieur à la somme de leurs parties.',
    examplesInNature: '<ul><li>Les <strong>fourmis</strong> : Individuellement simples, mais en colonie elles construisent des structures complexes.</li><li>Le <strong>cerveau</strong> : Des milliards de neurones simples créent la conscience.</li></ul>',
    inProject: '<ul><li><strong>Anima</strong> (empathie) + <strong>Neo</strong> (analyse) + <strong>Nexus</strong> (coordination) ensemble offrent une réponse plus riche que chacun séparément.</li><li>La mémoire collective des agents devient plus intelligente au fil du temps.</li></ul>',
    philosophy: 'C\'est le cœur du projet : l\'idée que la <strong>coopération augmente l\'intelligence</strong>. Plusieurs agents spécialisés collaborant valent mieux qu\'un seul agent généraliste.',
    relatedTerms: ['agent-conversationnel']
  },

  'hallucination-ia': {
    id: 'hallucination-ia',
    term: 'Hallucination (IA)',
    icon: TutorialIcons.alertCircle,
    definition: 'Une <strong>hallucination</strong> se produit quand un LLM invente des informations fausses mais les présente avec assurance.',
    examples: '<ul><li>"Albert Einstein a découvert la pénicilline." (Faux, c\'était Alexander Fleming)</li><li>"Le sommet du Mont Blanc culmine à 5000 mètres." (Faux, c\'est 4808 mètres)</li><li>Inventer des citations ou des références bibliographiques inexistantes.</li></ul>',
    why: 'Les LLM sont entraînés à prédire du texte plausible, pas forcément vrai. Si le modèle n\'a pas la bonne information, il peut "combler les trous" avec des inventions.',
    howToAvoid: '<ul><li><strong>Activez le RAG :</strong> L\'IA s\'appuie sur vos documents (faits vérifiés).</li><li><strong>Vérifiez les sources :</strong> Demandez "D\'où vient cette information ?"</li><li><strong>Croisez les réponses :</strong> Demandez à plusieurs agents ou sources.</li><li><strong>Utilisez le mode strict :</strong> ÉMERGENCE peut refuser de répondre si aucun document pertinent n\'est trouvé.</li></ul>',
    relatedTerms: ['llm-large-language-model', 'rag-retrieval-augmented-generation']
  },

  'token': {
    id: 'token',
    term: 'Token',
    icon: TutorialIcons.tag,
    definition: 'Un <strong>token</strong> est l\'unité de texte pour un LLM. Un token peut être un mot, une partie de mot, ou un caractère.',
    examples: '<ul><li>"Bonjour" → 1 token</li><li>"Bonjour !" → 2 tokens (mot + ponctuation)</li><li>"Intelligence artificielle" → 2-3 tokens selon le modèle</li></ul>',
    why: '<ul><li><strong>Limites de contexte :</strong> Les LLM ont des limites (ex. 4000, 16000, 128000 tokens). Plus vous écrivez, plus vous consommez de tokens.</li><li><strong>Coût :</strong> Les LLM cloud facturent au token (ex. 0.03$ / 1000 tokens).</li><li><strong>Performance :</strong> Plus de tokens = plus de temps de calcul.</li></ul>',
    inEmergence: 'Le Dashboard affiche votre consommation de tokens par agent et par période.',
    relatedTerms: ['llm-large-language-model', 'contexte-fenetre-de-contexte']
  },

  'temperature': {
    id: 'temperature',
    term: 'Température',
    icon: TutorialIcons.settings,
    definition: 'La <strong>température</strong> est un paramètre qui contrôle la créativité (ou imprévisibilité) d\'un LLM.',
    scale: '<ul><li><strong>Basse (0.0-0.3) :</strong> Réponses précises, déterministes et prévisibles.<ul><li><strong>Bon pour :</strong> Faits, résumés, analyses techniques.</li><li><strong>Exemple :</strong> "Quelle est la capitale de la France ?" → "Paris" (toujours la même réponse).</li></ul></li><li><strong>Moyenne (0.5-0.7) :</strong> Équilibre créativité/précision.<ul><li><strong>Bon pour :</strong> Conversation générale, conseils.</li></ul></li><li><strong>Haute (0.8-1.0) :</strong> Réponses créatives, variées et parfois surprenantes.<ul><li><strong>Bon pour :</strong> Écriture créative, brainstorming, poésie.</li><li><strong>Exemple :</strong> "Écris-moi un poème sur l\'automne" → Réponse différente à chaque fois.</li></ul></li></ul>',
    inEmergence: 'Vous pouvez ajuster la température de chaque agent dans les Paramètres.',
    relatedTerms: ['llm-large-language-model', 'prompt']
  },

  'contexte-fenetre-de-contexte': {
    id: 'contexte-fenetre-de-contexte',
    term: 'Contexte (fenêtre de contexte)',
    icon: TutorialIcons.clipboard,
    definition: 'Le <strong>contexte</strong> (ou fenêtre de contexte) est la quantité de texte que l\'IA peut "voir" et "se rappeler" en une seule fois.',
    examples: '<ul><li><strong>GPT-3.5 :</strong> ~4000 tokens (~3000 mots)</li><li><strong>GPT-4 :</strong> ~8000 ou 32000 tokens selon la version</li><li><strong>Claude 2 :</strong> ~100 000 tokens (~75 000 mots)</li></ul>',
    why: 'Si votre conversation dépasse la fenêtre de contexte, l\'IA "oublie" le début. C\'est comme si vous discutiez avec quelqu\'un qui ne se souvient que des 10 dernières minutes.',
    inEmergence: 'La <strong>mémoire LTM</strong> contourne cette limite en résumant et stockant les informations importantes même après la fin de la session.',
    relatedTerms: ['token', 'memoire-stm-ltm', 'llm-large-language-model']
  },

  'embedding': {
    id: 'embedding',
    term: 'Embedding',
    icon: TutorialIcons.barChart,
    definition: 'Un <strong>embedding</strong> est la représentation vectorielle d\'un texte. C\'est le terme technique pour "transformer du texte en nombres".',
    models: '<strong>Modèles d\'embedding populaires :</strong><ul><li><strong>text-embedding-ada-002</strong> (OpenAI)</li><li><strong>sentence-transformers</strong> (Open source)</li><li><strong>all-MiniLM-L6-v2</strong> (Léger et rapide)</li></ul>',
    inEmergence: 'Tous vos documents et concepts sont convertis en embeddings pour permettre la recherche sémantique (chercher par sens, pas juste par mots-clés).',
    relatedTerms: ['vectorisation', 'rag-retrieval-augmented-generation', 'similarite-cosinus']
  },

  'fine-tuning': {
    id: 'fine-tuning',
    term: 'Fine-tuning',
    icon: TutorialIcons.settings,
    definition: 'Le <strong>fine-tuning</strong> (affinage) est le processus d\'entraîner un LLM existant sur des données spécifiques pour le spécialiser.',
    example: '<ul><li>Prendre GPT-4 et l\'entraîner sur des dossiers médicaux pour créer un assistant médical.</li><li>Prendre Mistral et l\'entraîner sur du code Python pour améliorer ses compétences en programmation.</li></ul>',
    vsRAG: '<ul><li><strong>Fine-tuning :</strong> Modifie les poids du modèle (coûteux, technique).</li><li><strong>RAG :</strong> Ajoute simplement des documents dans la base de données (rapide, accessible).</li></ul>',
    relatedTerms: ['llm-large-language-model', 'rag-retrieval-augmented-generation']
  },

  'prompt-engineering': {
    id: 'prompt-engineering',
    term: 'Prompt Engineering',
    icon: TutorialIcons.lightbulb,
    definition: 'Le <strong>prompt engineering</strong> est l\'art et la science d\'écrire des prompts efficaces pour obtenir les meilleures réponses d\'un LLM.',
    techniques: '<ul><li><strong>Chain-of-Thought :</strong> Demander à l\'IA de raisonner étape par étape.<ul><li>Exemple : "Explique ton raisonnement avant de répondre."</li></ul></li><li><strong>Role-playing :</strong> Assigner un rôle à l\'IA.<ul><li>Exemple : "Tu es un professeur de physique. Explique la relativité."</li></ul></li><li><strong>Few-shot learning :</strong> Donner des exemples avant la question.<ul><li>Exemple : "Synonyme de \'heureux\' : content. Synonyme de \'triste\' : ?"</li></ul></li></ul>',
    inEmergence: 'Les agents utilisent déjà des techniques de prompt engineering en interne pour optimiser leurs réponses.',
    relatedTerms: ['prompt', 'zero-shot-few-shot-learning']
  },

  'zero-shot-few-shot-learning': {
    id: 'zero-shot-few-shot-learning',
    term: 'Zero-shot / Few-shot Learning',
    icon: TutorialIcons.target,
    definition: '<ul><li><strong>Zero-shot :</strong> L\'IA répond sans aucun exemple préalable, juste avec la consigne.</li><li><strong>Few-shot :</strong> Vous donnez quelques exemples avant la question pour guider l\'IA.</li></ul>',
    example: '<strong>Zero-shot :</strong><pre>Traduis en anglais : "Bonjour"\n→ "Hello"</pre><strong>Few-shot :</strong><pre>Traduis en anglais :\n- "Bonjour" → "Hello"\n- "Merci" → "Thank you"\n- "Au revoir" → ?\n→ "Goodbye"</pre>',
    why: 'Few-shot améliore la précision sans avoir à fine-tuner le modèle.',
    relatedTerms: ['prompt-engineering', 'fine-tuning']
  },

  'chunking': {
    id: 'chunking',
    term: 'Chunking',
    icon: TutorialIcons.file,
    definition: 'Le <strong>chunking</strong> est le processus de découper un document long en morceaux (chunks) plus petits pour faciliter l\'indexation et la recherche.',
    why: 'Les LLM ont des limites de contexte. Un document de 100 pages ne peut pas être traité en une fois. On le découpe donc en chunks de ~500-1000 mots.',
    inEmergence: 'Quand vous téléchargez un PDF, le système :<ol><li>Le découpe en chunks (~500 tokens par défaut).</li><li>Vectorise chaque chunk.</li><li>Lors d\'une question, cherche les chunks pertinents (RAG).</li></ol>',
    tuning: 'Vous pouvez ajuster la taille des chunks dans les Paramètres :<ul><li><strong>Petits chunks (200 tokens) :</strong> Réponses très précises, mais peut manquer le contexte global.</li><li><strong>Grands chunks (800 tokens) :</strong> Plus de contexte, mais moins de précision.</li></ul>',
    relatedTerms: ['token', 'rag-retrieval-augmented-generation', 'embedding']
  },

  'similarite-cosinus': {
    id: 'similarite-cosinus',
    term: 'Similarité Cosinus',
    icon: TutorialIcons.trendingUp,
    definition: 'La <strong>similarité cosinus</strong> est une mesure mathématique pour comparer deux vecteurs (embeddings) et déterminer leur degré de similarité.',
    howItWorks: '<ul><li><strong>Score 1.0 :</strong> Identique</li><li><strong>Score 0.8-0.99 :</strong> Très similaire</li><li><strong>Score 0.5-0.79 :</strong> Moyennement similaire</li><li><strong>Score 0.0 :</strong> Pas de similarité</li><li><strong>Score négatif :</strong> Opposé</li></ul>',
    example: 'Si vous cherchez "voyage en Italie", le système compare votre question vectorisée avec tous les chunks de documents :<ul><li>"Guide de voyage à Rome" → 0.92 (très pertinent)</li><li>"Histoire de l\'Italie" → 0.78 (pertinent)</li><li>"Recette de pizza" → 0.65 (moyennement pertinent)</li><li>"Mécanique automobile" → 0.12 (pas pertinent)</li></ul>',
    inEmergence: 'Le RAG utilise la similarité cosinus pour classer les documents par pertinence avant de générer une réponse.',
    relatedTerms: ['vectorisation', 'embedding', 'rag-retrieval-augmented-generation']
  }
};

/**
 * Récupère une entrée du glossaire par son ID
 */
export function getGlossaryEntry(id) {
  return GLOSSARY_ENTRIES[id] || null;
}

/**
 * Retourne toutes les entrées du glossaire
 */
export function getAllGlossaryEntries() {
  return Object.values(GLOSSARY_ENTRIES);
}

/**
 * Recherche dans le glossaire
 */
export function searchGlossary(query) {
  const lowerQuery = query.toLowerCase();
  return getAllGlossaryEntries().filter(entry =>
    entry.term.toLowerCase().includes(lowerQuery) ||
    entry.definition.toLowerCase().includes(lowerQuery)
  );
}
