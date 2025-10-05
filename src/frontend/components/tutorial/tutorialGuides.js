/**
 * @module components/tutorial/tutorialGuides
 * @description Guides détaillés pour chaque fonctionnalité d'Emergence
 */

export const TUTORIAL_GUIDES = [
  {
    id: 'chat',
    icon: '💬',
    title: 'Chat Multi-Agents',
    summary: 'Maîtrisez les conversations avec les agents IA spécialisés',
    content: `
      <section class="guide-section">
        <h3>🎯 Vue d'ensemble</h3>
        <p>Le système de chat d'Emergence utilise une architecture <strong>multi-agents</strong> pour vous offrir des réponses riches et variées. Chaque agent possède une personnalité et des compétences uniques.</p>
      </section>

      <section class="guide-section">
        <h3>🤖 Les Trois Agents</h3>

        <div class="guide-card">
          <h4>🌟 Anima - L'Agent Créatif</h4>
          <p><strong>Spécialités :</strong> Créativité, brainstorming, exploration d'idées, innovation</p>
          <p><strong>Quand l'utiliser :</strong></p>
          <ul>
            <li>Génération d'idées créatives</li>
            <li>Exploration de concepts innovants</li>
            <li>Réflexion divergente et brainstorming</li>
            <li>Approches non-conventionnelles</li>
          </ul>
          <p><strong>Exemple :</strong> "Anima, propose-moi 10 idées innovantes pour améliorer l'engagement utilisateur de mon application"</p>
        </div>

        <div class="guide-card">
          <h4>🔬 Neo - L'Analyste Rationnel</h4>
          <p><strong>Spécialités :</strong> Analyse logique, données, résolution de problèmes, structuration</p>
          <p><strong>Quand l'utiliser :</strong></p>
          <ul>
            <li>Analyse de données et statistiques</li>
            <li>Résolution de problèmes complexes</li>
            <li>Validation d'hypothèses</li>
            <li>Structuration d'informations</li>
          </ul>
          <p><strong>Exemple :</strong> "Neo, analyse les avantages et inconvénients de l'architecture microservices pour mon projet"</p>
        </div>

        <div class="guide-card">
          <h4>🧩 Nexus - Le Synthétiseur</h4>
          <p><strong>Spécialités :</strong> Synthèse, coordination, vue d'ensemble, intégration</p>
          <p><strong>Quand l'utiliser :</strong></p>
          <ul>
            <li>Synthèse d'informations multiples</li>
            <li>Vue d'ensemble d'un sujet complexe</li>
            <li>Coordination de perspectives différentes</li>
            <li>Résumés et conclusions</li>
          </ul>
          <p><strong>Exemple :</strong> "Nexus, résume-moi les points clés de notre discussion sur l'architecture du projet"</p>
        </div>
      </section>

      <section class="guide-section">
        <h3>⚡ Fonctionnalités Avancées</h3>

        <h4>🔄 Mode RAG (Retrieval-Augmented Generation)</h4>
        <p>Le toggle RAG permet d'enrichir les réponses avec le contenu de vos documents.</p>
        <ul>
          <li><strong>Activer :</strong> Cliquez sur l'icône 📚 dans la zone de saisie</li>
          <li><strong>Utilisation :</strong> L'IA recherchera dans vos documents pour des réponses contextualisées</li>
          <li><strong>Performance :</strong> Légèrement plus lent mais beaucoup plus précis avec vos données</li>
        </ul>

        <h4>💬 Consultation Ponctuelle d'Autres Agents</h4>
        <p>Vous pouvez demander l'avis d'un autre agent ponctuellement :</p>
        <ul>
          <li>Dans votre message, mentionnez l'agent : "@Anima", "@Neo", ou "@Nexus"</li>
          <li>L'agent actuel consultera l'agent mentionné pour obtenir son point de vue</li>
          <li>Utile pour combiner différentes perspectives (créativité + analyse)</li>
          <li>Exemple : "Analyse ce problème, et @Anima propose des solutions innovantes"</li>
        </ul>

        <h4>🧠 Mémoire Conversationnelle</h4>
        <p>Emergence garde en mémoire vos conversations :</p>
        <ul>
          <li>Contexte maintenu sur plusieurs messages</li>
          <li>Références aux échanges précédents</li>
          <li>Personnalisation progressive des réponses</li>
          <li>Continuité entre sessions (via conversations)</li>
        </ul>

        <h4>⌨️ Raccourcis Clavier</h4>
        <ul>
          <li><kbd>Entrée</kbd> : Envoyer le message</li>
          <li><kbd>Maj + Entrée</kbd> : Nouvelle ligne</li>
          <li><kbd>Ctrl/Cmd + K</kbd> : Focus sur la zone de saisie</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>💡 Astuces et Bonnes Pratiques</h3>
        <ul>
          <li>✅ <strong>Soyez précis :</strong> Plus votre question est claire, meilleure sera la réponse</li>
          <li>✅ <strong>Utilisez le contexte :</strong> Référencez des éléments de la conversation précédente</li>
          <li>✅ <strong>Combinez les agents :</strong> Demandez une vue créative ET analytique</li>
          <li>✅ <strong>Activez RAG pour vos docs :</strong> Obtenez des réponses basées sur vos propres données</li>
          <li>✅ <strong>Formatez avec Markdown :</strong> Utilisez **gras**, *italique*, \`code\`, etc.</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🎓 Exemples de Prompts Efficaces</h3>

        <div class="guide-example">
          <strong>Brainstorming créatif :</strong>
          <code>"Anima, j'ai besoin de 5 approches innovantes pour réduire le temps de chargement de mon site web, pense outside the box"</code>
        </div>

        <div class="guide-example">
          <strong>Analyse technique :</strong>
          <code>"Neo, compare PostgreSQL et MongoDB pour une application de gestion de tickets avec 100k utilisateurs actifs"</code>
        </div>

        <div class="guide-example">
          <strong>Synthèse multi-sources :</strong>
          <code>"Nexus, en te basant sur mes documents uploadés, résume les tendances principales du marché SaaS en 2024"</code>
        </div>
      </section>
    `
  },
  {
    id: 'threads',
    icon: '📂',
    title: 'Gestion des Conversations',
    summary: 'Organisez et retrouvez toutes vos conversations',
    content: `
      <section class="guide-section">
        <h3>🎯 Qu'est-ce qu'une Conversation ?</h3>
        <p>Une <strong>conversation</strong> (aussi appelée thread dans l'onglet Mémoire) est un fil de discussion isolé avec un contexte propre. Chaque conversation maintient son propre historique et sa propre mémoire contextuelle.</p>
        <p><strong>Note :</strong> Les conversations apparaissent sous le nom "Threads" dans l'interface Mémoire - c'est la même chose.</p>
      </section>

      <section class="guide-section">
        <h3>📝 Créer et Gérer des Conversations</h3>

        <h4>Créer une nouvelle conversation</h4>
        <ol>
          <li>Cliquez sur le bouton <strong>"+"</strong> ou <strong>"Nouvelle Conversation"</strong></li>
          <li>La nouvelle conversation démarre avec un contexte vierge</li>
          <li>Donnez-lui un nom descriptif pour la retrouver facilement</li>
        </ol>

        <h4>Ouvrir une conversation</h4>
        <p>Lorsque vous ouvrez une conversation :</p>
        <ul>
          <li>L'historique complet des messages est chargé</li>
          <li>Le contexte de la conversation devient actif</li>
          <li>Les agents se souviennent des échanges précédents de cette conversation</li>
          <li>Les concepts mémorisés spécifiques à cette conversation sont accessibles</li>
        </ul>

        <h4>Archiver une conversation</h4>
        <p>L'archivage permet de ranger les conversations terminées :</p>
        <ul>
          <li>La conversation est retirée de la vue principale</li>
          <li>Les données restent sauvegardées et accessibles via les archives</li>
          <li>Vous pouvez désarchiver à tout moment</li>
          <li>Utile pour garder votre liste organisée</li>
        </ul>

        <h4>Supprimer une conversation</h4>
        <p><strong>Attention :</strong> La suppression est définitive !</p>
        <ul>
          <li>Tous les messages de la conversation sont effacés</li>
          <li>Les concepts extraits spécifiques à cette conversation sont perdus</li>
          <li>Cette action est <strong>irréversible</strong></li>
          <li>Préférez l'archivage si vous n'êtes pas certain</li>
        </ul>

        <h4>Renommer une conversation</h4>
        <ol>
          <li>Survolez la conversation dans la liste</li>
          <li>Cliquez sur l'icône ✏️ ou faites un clic droit</li>
          <li>Saisissez le nouveau nom</li>
          <li>Validez avec <kbd>Entrée</kbd></li>
        </ol>
      </section>

      <section class="guide-section">
        <h3>🔍 Navigation</h3>

        <h4>Trier les conversations</h4>
        <p>Les conversations sont triées par :</p>
        <ul>
          <li><strong>Date de modification</strong> (défaut) : Les plus récentes en premier</li>
          <li><strong>Date de création :</strong> Les plus anciennes ou nouvelles</li>
          <li><strong>Alphabétique :</strong> Par nom de conversation</li>
        </ul>

        <h4>Navigation rapide</h4>
        <ul>
          <li>Double-clic sur une conversation pour l'ouvrir</li>
          <li>Utilisez les flèches haut/bas pour naviguer dans la liste</li>
          <li>La conversation active est mise en évidence</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>💡 Bonnes Pratiques</h3>

        <div class="guide-tip">
          <h4>🏷️ Nommage des Conversations</h4>
          <ul>
            <li>✅ <strong>Descriptif :</strong> "Analyse architecture projet X"</li>
            <li>✅ <strong>Date si pertinent :</strong> "Sprint planning 2024-01"</li>
            <li>✅ <strong>Catégorie :</strong> "[Dev] Optimisation base de données"</li>
            <li>❌ <strong>Éviter :</strong> "Conversation 1", "Discussion", "Notes"</li>
          </ul>
        </div>

        <div class="guide-tip">
          <h4>📁 Organisation</h4>
          <ul>
            <li>Une conversation par projet ou sujet majeur</li>
            <li>Nouvelle conversation pour changer radicalement de sujet</li>
            <li>Gardez les conversations focalisées sur un thème</li>
            <li>Archivez ou supprimez les conversations obsolètes</li>
          </ul>
        </div>
      </section>

      <section class="guide-section">
        <h3>🧠 Contexte et Mémoire</h3>
        <p>Chaque conversation maintient son propre contexte :</p>
        <ul>
          <li>✅ Historique des messages indépendant</li>
          <li>✅ Concepts mémorisés spécifiques à la conversation</li>
          <li>✅ Documents liés à la conversation</li>
          <li>✅ Continuité entre sessions (sauvegarde auto)</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>⚡ Raccourcis et Astuces</h3>
        <ul>
          <li><kbd>Ctrl/Cmd + N</kbd> : Nouvelle conversation (si configuré)</li>
          <li>Double-clic sur une conversation pour l'ouvrir</li>
          <li>Glisser-déposer pour réorganiser (si activé)</li>
          <li>Export possible via menu contextuel (clic droit)</li>
        </ul>
      </section>
    `
  },
  {
    id: 'concepts',
    icon: '🧠',
    title: 'Base de Connaissances',
    summary: 'Exploitez la mémoire sémantique d\'Emergence',
    content: `
      <section class="guide-section">
        <h3>🎯 Qu'est-ce que la Base de Connaissances ?</h3>
        <p>La <strong>base de connaissances</strong> est un système intelligent qui extrait, stocke et relie automatiquement les concepts importants de vos conversations. C'est la mémoire à long terme d'Emergence.</p>
      </section>

      <section class="guide-section">
        <h3>✨ Extraction Automatique de Concepts</h3>

        <h4>Comment ça fonctionne ?</h4>
        <ol>
          <li><strong>Analyse en temps réel :</strong> Pendant vos conversations, l'IA identifie les concepts clés</li>
          <li><strong>Extraction sémantique :</strong> Les concepts sont extraits avec leur contexte et leurs attributs</li>
          <li><strong>Stockage vectoriel :</strong> Sauvegarde dans une base vectorielle (ChromaDB)</li>
          <li><strong>Relations :</strong> Les liens entre concepts sont automatiquement établis</li>
        </ol>

        <h4>Types de concepts extraits</h4>
        <ul>
          <li>🏷️ <strong>Entités :</strong> Noms, lieux, organisations, technologies</li>
          <li>💡 <strong>Idées :</strong> Concepts abstraits, théories, approches</li>
          <li>📊 <strong>Données :</strong> Chiffres clés, statistiques, métriques</li>
          <li>🔗 <strong>Relations :</strong> Liens causaux, hiérarchiques, temporels</li>
          <li>🎯 <strong>Objectifs :</strong> Buts, intentions, projets</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔍 Consultation des Concepts</h3>

        <h4>Accéder à vos concepts</h4>
        <ol>
          <li>Cliquez sur <strong>"Concepts"</strong> dans la sidebar</li>
          <li>Parcourez la liste des concepts mémorisés</li>
          <li>Cliquez sur un concept pour voir ses détails</li>
        </ol>

        <h4>Visualisation</h4>
        <p>Les concepts sont affichés avec :</p>
        <ul>
          <li>Leur nom et description</li>
          <li>La date d'extraction</li>
          <li>Les conversations où ils apparaissent</li>
          <li>Les relations avec d'autres concepts</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔗 Graphe de Connaissances</h3>

        <h4>Visualisation des relations</h4>
        <p>Le graphe montre les liens entre vos concepts :</p>
        <ul>
          <li>📍 <strong>Nœuds :</strong> Chaque concept est un point</li>
          <li>🔗 <strong>Liens :</strong> Les relations entre concepts</li>
          <li>🎨 <strong>Couleurs :</strong> Types de concepts (entités, idées, etc.)</li>
          <li>📏 <strong>Taille :</strong> Importance du concept (fréquence)</li>
        </ul>

        <h4>Navigation interactive</h4>
        <ul>
          <li>Cliquez sur un nœud pour voir ses détails</li>
          <li>Survolez pour voir les connexions</li>
          <li>Zoom et déplacement pour explorer</li>
          <li>Filtres par type, date, importance</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🎯 Rappel Contextuel (Concept Recall)</h3>

        <h4>Utilisation automatique</h4>
        <p>L'IA utilise vos concepts pour enrichir ses réponses :</p>
        <ul>
          <li>Détection des concepts pertinents dans votre question</li>
          <li>Récupération des concepts similaires de la base</li>
          <li>Injection du contexte dans la réponse</li>
          <li>Personnalisation basée sur votre historique</li>
        </ul>

        <div class="guide-example">
          <strong>Exemple concret :</strong>
          <p><strong>Vous :</strong> "Comment optimiser les performances ?"</p>
          <p><strong>IA (avec concept recall) :</strong> "Basé sur nos discussions précédentes sur PostgreSQL et Redis, voici comment optimiser..."</p>
        </div>

        <h4>Historique</h4>
        <p>Consultez l'historique du concept recall :</p>
        <ul>
          <li>📊 Nombre de concepts récupérés par requête</li>
          <li>📈 Fréquence d'utilisation du concept recall</li>
          <li>📝 Historique des concepts rappelés</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>⚙️ Gestion des Concepts</h3>

        <h4>Édition manuelle</h4>
        <ul>
          <li>✏️ <strong>Modifier :</strong> Affinez la description d'un concept</li>
          <li>🏷️ <strong>Étiqueter :</strong> Ajoutez des tags personnalisés</li>
          <li>🔗 <strong>Lier :</strong> Créez des relations manuelles</li>
          <li>🗑️ <strong>Supprimer :</strong> Retirez les concepts non pertinents</li>
        </ul>

        <h4>Export et Sauvegarde</h4>
        <ul>
          <li>Export JSON de toute la base</li>
          <li>Export sélectif par catégorie</li>
          <li>Import depuis un fichier</li>
          <li>Sauvegarde automatique continue</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>💡 Bonnes Pratiques</h3>

        <div class="guide-tip">
          <h4>✅ Pour de meilleurs résultats</h4>
          <ul>
            <li>Soyez précis dans vos formulations</li>
            <li>Mentionnez explicitement les concepts importants</li>
            <li>Revoyez et validez les concepts extraits régulièrement</li>
            <li>Créez des liens manuels entre concepts connexes</li>
            <li>Utilisez des tags cohérents pour l'organisation</li>
          </ul>
        </div>

        <div class="guide-tip">
          <h4>⚠️ À éviter</h4>
          <ul>
            <li>Ne pas surcharger avec trop de concepts triviaux</li>
            <li>Éviter les doublons (fusionnez-les)</li>
            <li>Ne pas négliger l'entretien de la base</li>
          </ul>
        </div>
      </section>
    `
  },
  {
    id: 'documents',
    icon: '📚',
    title: 'Gestion des Documents',
    summary: 'Uploadez et exploitez vos documents avec le RAG',
    content: `
      <section class="guide-section">
        <h3>🎯 Vue d'ensemble</h3>
        <p>Le système de <strong>gestion documentaire</strong> d'Emergence vous permet d'uploader, indexer et interroger vos documents. Combiné au RAG, vos documents deviennent une source de connaissance exploitable par l'IA.</p>
      </section>

      <section class="guide-section">
        <h3>📤 Upload de Documents</h3>

        <h4>Formats supportés</h4>
        <ul>
          <li>📄 <strong>Texte :</strong> .txt, .md, .csv</li>
          <li>📝 <strong>Documents :</strong> .pdf, .docx, .odt</li>
          <li>💻 <strong>Code :</strong> .py, .js, .java, .cpp, etc.</li>
          <li>📊 <strong>Données :</strong> .json, .xml, .yaml</li>
        </ul>

        <h4>Procédure d'upload</h4>
        <ol>
          <li>Allez dans la section <strong>"Documents"</strong></li>
          <li>Cliquez sur <strong>"Uploader"</strong> ou glissez-déposez</li>
          <li>Sélectionnez un ou plusieurs fichiers</li>
          <li>Attendez le traitement (chunking et indexation)</li>
          <li>Le document est maintenant interrogeable</li>
        </ol>

        <h4>Limites</h4>
        <ul>
          <li>Taille max par fichier : 10 MB (configurable)</li>
          <li>Nombre de fichiers : Illimité (dans les limites du stockage)</li>
          <li>Encodage : UTF-8 recommandé</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔍 Traitement et Indexation</h3>

        <h4>Chunking intelligent</h4>
        <p>Les documents sont découpés en <strong>chunks</strong> (morceaux) :</p>
        <ul>
          <li>Taille optimale : ~500 tokens par chunk</li>
          <li>Overlap : 50 tokens entre chunks (continuité)</li>
          <li>Respect de la structure (paragraphes, sections)</li>
          <li>Préservation du contexte</li>
        </ul>

        <h4>Embeddings vectoriels</h4>
        <p>Chaque chunk est converti en vecteur :</p>
        <ul>
          <li>Modèle : <code>all-MiniLM-L6-v2</code> (sentence-transformers)</li>
          <li>Dimension : 384</li>
          <li>Stockage : ChromaDB (base vectorielle locale)</li>
          <li>Recherche : Similarité cosinus</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔗 Utilisation avec le RAG</h3>

        <h4>Activer le RAG</h4>
        <ol>
          <li>Dans le chat, activez le toggle <strong>📚 RAG</strong></li>
          <li>Posez votre question normalement</li>
          <li>L'IA recherche dans vos documents</li>
          <li>La réponse est enrichie avec le contenu pertinent</li>
        </ol>

        <h4>Fonctionnement du RAG</h4>
        <ol>
          <li><strong>Vectorisation de la question :</strong> Votre question devient un vecteur</li>
          <li><strong>Recherche de similarité :</strong> Trouve les chunks les plus proches</li>
          <li><strong>Top-k retrieval :</strong> Récupère les 5 meilleurs chunks</li>
          <li><strong>Injection de contexte :</strong> Les chunks sont ajoutés au prompt</li>
          <li><strong>Génération :</strong> L'IA répond avec ce contexte enrichi</li>
        </ol>

        <div class="guide-example">
          <strong>Exemple :</strong>
          <p><strong>Documents :</strong> Manuel technique de votre API</p>
          <p><strong>Question :</strong> "Comment authentifier un utilisateur ?"</p>
          <p><strong>RAG :</strong> Retrouve la section sur l'auth dans votre doc</p>
          <p><strong>Réponse :</strong> Basée sur VOTRE doc, pas sur des infos génériques</p>
        </div>
      </section>

      <section class="guide-section">
        <h3>📊 Gestion et Organisation</h3>

        <h4>Liste des documents</h4>
        <p>Consultez tous vos documents uploadés :</p>
        <ul>
          <li>📄 Nom du fichier</li>
          <li>📅 Date d'upload</li>
          <li>📏 Taille</li>
          <li>🔢 Nombre de chunks créés</li>
          <li>📊 Statut de l'indexation</li>
        </ul>

        <h4>Actions disponibles</h4>
        <ul>
          <li>👁️ <strong>Prévisualiser :</strong> Voir le contenu</li>
          <li>⬇️ <strong>Télécharger :</strong> Récupérer le fichier original</li>
          <li>🔄 <strong>Ré-indexer :</strong> Reconstruire les chunks et embeddings</li>
          <li>🗑️ <strong>Supprimer :</strong> Retirer le document et ses chunks</li>
        </ul>

      </section>

      <section class="guide-section">
        <h3>⚙️ Configuration Avancée</h3>

        <h4>Paramètres de chunking</h4>
        <ul>
          <li><strong>Taille des chunks :</strong> 200-1000 tokens</li>
          <li><strong>Overlap :</strong> 0-100 tokens</li>
          <li><strong>Stratégie :</strong> Par paragraphe, par ligne, fixe</li>
        </ul>

        <h4>Paramètres de retrieval</h4>
        <ul>
          <li><strong>Top-k :</strong> Nombre de chunks à récupérer (1-10)</li>
          <li><strong>Seuil de similarité :</strong> Score minimum (0.0-1.0)</li>
          <li><strong>Filtres :</strong> Par document, par date, par type</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>💡 Bonnes Pratiques</h3>

        <div class="guide-tip">
          <h4>✅ Pour de meilleurs résultats</h4>
          <ul>
            <li>Uploadez des documents <strong>bien structurés</strong> (titres, sections)</li>
            <li>Utilisez des <strong>formats texte</strong> quand possible (meilleure extraction)</li>
            <li>Donnez des <strong>noms descriptifs</strong> à vos fichiers</li>
            <li>Organisez par <strong>dossiers/tags</strong> si vous avez beaucoup de docs</li>
            <li>Testez vos questions RAG sur quelques docs avant d'uploader massivement</li>
          </ul>
        </div>

        <div class="guide-tip">
          <h4>🎯 Optimisation des requêtes RAG</h4>
          <ul>
            <li>Questions <strong>précises</strong> > questions vagues</li>
            <li>Mentionnez le <strong>nom du document</strong> si vous le connaissez</li>
            <li>Utilisez les <strong>mots-clés</strong> présents dans vos docs</li>
            <li>Combinez RAG et mémoire conceptuelle pour de meilleurs résultats</li>
          </ul>
        </div>
      </section>

      <section class="guide-section">
        <h3>🔧 Dépannage</h3>

        <h4>Le RAG ne trouve pas mon document</h4>
        <ul>
          <li>✅ Vérifiez que le document est bien indexé</li>
          <li>✅ Reformulez votre question avec d'autres mots</li>
          <li>✅ Augmentez le top-k dans les paramètres</li>
          <li>✅ Vérifiez le seuil de similarité</li>
        </ul>

        <h4>L'upload échoue</h4>
        <ul>
          <li>✅ Vérifiez la taille du fichier</li>
          <li>✅ Vérifiez le format (supporté ?)</li>
          <li>✅ Essayez de convertir en .txt ou .pdf</li>
          <li>✅ Consultez les logs pour plus de détails</li>
        </ul>
      </section>
    `
  },
  {
    id: 'dashboard',
    icon: '📊',
    title: 'Dashboard & Métriques',
    summary: 'Suivez vos statistiques et l\'utilisation d\'Emergence',
    content: `
      <section class="guide-section">
        <h3>🎯 Vue d'ensemble</h3>
        <p>Le <strong>Dashboard</strong> (Cockpit) vous donne une vue d'ensemble de votre utilisation d'Emergence : statistiques, coûts, performances et insights.</p>
      </section>

      <section class="guide-section">
        <h3>📊 Métriques Principales</h3>

        <h4>📈 Utilisation Globale</h4>
        <ul>
          <li><strong>Messages envoyés :</strong> Total et par période</li>
          <li><strong>Threads créés :</strong> Nombre de conversations</li>
          <li><strong>Documents uploadés :</strong> Volume de données</li>
          <li><strong>Concepts mémorisés :</strong> Taille de la base de connaissances</li>
        </ul>

        <h4>💰 Coûts et Tokens</h4>
        <ul>
          <li><strong>Tokens consommés :</strong> Input + Output</li>
          <li><strong>Coût estimé :</strong> Par modèle, par jour, par mois</li>
          <li><strong>Répartition :</strong> Par agent, par feature</li>
          <li><strong>Tendances :</strong> Évolution dans le temps</li>
        </ul>

        <h4>⚡ Performance</h4>
        <ul>
          <li><strong>Latence moyenne :</strong> Temps de réponse</li>
          <li><strong>Temps de recherche RAG :</strong> Vitesse des requêtes vectorielles</li>
          <li><strong>Taux de succès :</strong> Requêtes réussies vs erreurs</li>
          <li><strong>Uptime :</strong> Disponibilité du système</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>📉 Graphiques et Visualisations</h3>

        <h4>Timeline d'activité</h4>
        <p>Visualisez votre activité au fil du temps :</p>
        <ul>
          <li>Messages par jour/semaine/mois</li>
          <li>Pics d'utilisation</li>
          <li>Comparaison entre périodes</li>
        </ul>

        <h4>Répartition par agent</h4>
        <p>Camembert montrant l'utilisation de chaque agent :</p>
        <ul>
          <li>Anima : % des requêtes créatives</li>
          <li>Neo : % des requêtes analytiques</li>
          <li>Nexus : % des synthèses</li>
        </ul>

        <h4>Coûts cumulés</h4>
        <p>Graphique linéaire de l'évolution des coûts :</p>
        <ul>
          <li>Par jour : Détection des anomalies</li>
          <li>Par semaine : Tendances</li>
          <li>Par mois : Budget et prévisions</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔍 Insights et Analyses</h3>

        <h4>Top Concepts</h4>
        <ul>
          <li>Concepts les plus fréquents</li>
          <li>Concepts les plus récents</li>
          <li>Concepts les plus connectés</li>
        </ul>

        <h4>Top Threads</h4>
        <ul>
          <li>Threads les plus actifs</li>
          <li>Threads les plus longs</li>
          <li>Threads récents</li>
        </ul>

        <h4>Documents populaires</h4>
        <ul>
          <li>Documents les plus interrogés (RAG)</li>
          <li>Documents les plus volumineux</li>
          <li>Documents récemment uploadés</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>⚙️ Configuration et Alertes</h3>

        <h4>Limites et quotas</h4>
        <ul>
          <li>Définissez un <strong>budget mensuel</strong></li>
          <li>Alerte à X% du quota</li>
          <li>Pause automatique si dépassement</li>
        </ul>

        <h4>Notifications</h4>
        <ul>
          <li>Email si coût > seuil</li>
          <li>Rapport hebdomadaire/mensuel</li>
          <li>Alerte si erreur système</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>📤 Export et Rapports</h3>

        <h4>Formats d'export</h4>
        <ul>
          <li><strong>CSV :</strong> Données brutes pour analyse</li>
          <li><strong>JSON :</strong> Format structuré</li>
          <li><strong>PDF :</strong> Rapport formaté</li>
        </ul>

        <h4>Rapports automatiques</h4>
        <ul>
          <li>Rapport mensuel d'utilisation</li>
          <li>Facture détaillée</li>
          <li>Audit de sécurité</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>💡 Utilisation Optimale</h3>

        <div class="guide-tip">
          <h4>📊 Surveillez vos métriques</h4>
          <ul>
            <li>Consultez le dashboard <strong>hebdomadairement</strong></li>
            <li>Identifiez les <strong>pics de coûts</strong> anormaux</li>
            <li>Optimisez l'utilisation des modèles coûteux</li>
            <li>Utilisez les alertes pour le monitoring</li>
          </ul>
        </div>
      </section>
    `
  },
  {
    id: 'settings',
    icon: '⚙️',
    title: 'Paramètres et Configuration',
    summary: 'Personnalisez Emergence selon vos besoins',
    content: `
      <section class="guide-section">
        <h3>🎯 Vue d'ensemble</h3>
        <p>La section <strong>Paramètres</strong> vous permet de configurer tous les aspects d'Emergence : modèles IA, interface, sécurité, intégrations, etc.</p>
      </section>

      <section class="guide-section">
        <h3>🤖 Configuration des Modèles IA</h3>

        <h4>Choix du modèle principal</h4>
        <p>Sélectionnez le modèle utilisé par défaut :</p>
        <ul>
          <li><strong>GPT-4 Turbo :</strong> Meilleur raisonnement, plus coûteux</li>
          <li><strong>GPT-3.5 Turbo :</strong> Rapide et économique</li>
          <li><strong>Claude 3 (Sonnet/Opus) :</strong> Excellent pour l'analyse</li>
          <li><strong>Modèles locaux :</strong> Llama, Mistral (si configuré)</li>
        </ul>

        <h4>Configuration par agent</h4>
        <p>Assignez un modèle différent à chaque agent :</p>
        <ul>
          <li><strong>Anima :</strong> GPT-4 (créativité max)</li>
          <li><strong>Neo :</strong> Claude 3 (analyse rigoureuse)</li>
          <li><strong>Nexus :</strong> GPT-3.5 (synthèse rapide)</li>
        </ul>

        <h4>Paramètres de génération</h4>
        <ul>
          <li><strong>Température :</strong> 0.0 (déterministe) à 1.0 (créatif)</li>
          <li><strong>Max tokens :</strong> Limite de longueur de réponse</li>
          <li><strong>Top-p :</strong> Sampling nucléaire (0.0-1.0)</li>
          <li><strong>Presence penalty :</strong> Éviter les répétitions</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🎨 Personnalisation de l'Interface</h3>

        <h4>Thème</h4>
        <ul>
          <li><strong>Sombre</strong> (défaut) : Repose les yeux</li>
          <li><strong>Clair :</strong> Meilleure lisibilité en plein jour</li>
          <li><strong>Auto :</strong> Suit le système</li>
        </ul>

        <h4>Disposition</h4>
        <ul>
          <li>Largeur de la sidebar</li>
          <li>Taille de police</li>
          <li>Espacement des messages</li>
          <li>Affichage des avatars agents</li>
        </ul>

        <h4>Comportement</h4>
        <ul>
          <li><strong>Envoi auto :</strong> Entrée envoie (vs Ctrl+Entrée)</li>
          <li><strong>Markdown :</strong> Activer le rendu Markdown</li>
          <li><strong>Syntax highlighting :</strong> Coloration code</li>
          <li><strong>Streaming :</strong> Afficher la réponse en temps réel</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔐 Sécurité et Confidentialité</h3>

        <h4>Gestion des clés API</h4>
        <ul>
          <li>Ajoutez vos clés OpenAI, Anthropic, etc.</li>
          <li>Stockage sécurisé (chiffré)</li>
          <li>Rotation des clés</li>
          <li>Révocation instantanée</li>
        </ul>

        <h4>Authentification</h4>
        <ul>
          <li><strong>Mot de passe :</strong> Changement régulier recommandé</li>
          <li><strong>2FA :</strong> Authentification à deux facteurs</li>
          <li><strong>Sessions :</strong> Gestion des sessions actives</li>
          <li><strong>Logs :</strong> Historique des connexions</li>
        </ul>

        <h4>Données et vie privée</h4>
        <ul>
          <li><strong>Stockage local :</strong> Vos données restent sur votre machine</li>
          <li><strong>Chiffrement :</strong> Base de données chiffrée</li>
          <li><strong>Export :</strong> Exportez toutes vos données</li>
          <li><strong>Suppression :</strong> Effacement complet possible</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔗 Intégrations</h3>

        <h4>Webhooks</h4>
        <ul>
          <li>Configurez des webhooks pour être notifié</li>
          <li>Événements : Nouveau message, concept extrait, etc.</li>
          <li>Format : JSON</li>
          <li>Signature HMAC pour sécurité</li>
        </ul>

        <h4>API externe</h4>
        <ul>
          <li>Intégration Notion, Obsidian, etc.</li>
          <li>Synchronisation bidirectionnelle</li>
          <li>Export automatique</li>
        </ul>

        <h4>Extensions</h4>
        <ul>
          <li>Plugins communautaires</li>
          <li>Développez vos propres extensions</li>
          <li>API JavaScript pour personnalisation</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🗄️ Base de Données et Stockage</h3>

        <h4>Emplacement des données</h4>
        <ul>
          <li><strong>SQLite :</strong> <code>src/backend/data/db/</code></li>
          <li><strong>ChromaDB :</strong> <code>src/backend/data/vector_store/</code></li>
          <li><strong>Documents :</strong> <code>src/backend/data/uploads/</code></li>
        </ul>

        <h4>Maintenance</h4>
        <ul>
          <li><strong>Vacuum :</strong> Optimiser la base SQLite</li>
          <li><strong>Ré-indexation :</strong> Reconstruire les vecteurs</li>
          <li><strong>Nettoyage :</strong> Supprimer les données obsolètes</li>
          <li><strong>Backup :</strong> Sauvegarde automatique</li>
        </ul>

        <h4>Limites de stockage</h4>
        <ul>
          <li>Définissez un quota de stockage</li>
          <li>Alerte si proche de la limite</li>
          <li>Auto-archivage des vieux threads</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>⚡ Performance</h3>

        <h4>Cache</h4>
        <ul>
          <li><strong>Embeddings :</strong> Cache des vecteurs calculés</li>
          <li><strong>Réponses :</strong> Cache LLM (questions identiques)</li>
          <li><strong>TTL :</strong> Durée de vie du cache</li>
        </ul>

        <h4>Optimisations</h4>
        <ul>
          <li>Chunking parallel pour gros documents</li>
          <li>Batch processing des embeddings</li>
          <li>Lazy loading des threads anciens</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔧 Avancé</h3>

        <h4>Logs et Debug</h4>
        <ul>
          <li><strong>Niveau de log :</strong> DEBUG, INFO, WARNING, ERROR</li>
          <li><strong>Fichiers de log :</strong> Localisation et rotation</li>
          <li><strong>Monitoring :</strong> Prometheus, Grafana</li>
        </ul>

        <h4>Développeur</h4>
        <ul>
          <li><strong>Mode debug :</strong> Afficher les prompts complets</li>
          <li><strong>API REST :</strong> Documentation interactive (Swagger)</li>
          <li><strong>Webhooks test :</strong> Tester vos intégrations</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>💡 Recommandations</h3>

        <div class="guide-tip">
          <h4>🔒 Sécurité</h4>
          <ul>
            <li>Activez <strong>2FA</strong> immédiatement</li>
            <li>Changez votre <strong>mot de passe</strong> régulièrement</li>
            <li>Sauvegardez vos <strong>clés API</strong> en lieu sûr</li>
            <li>Vérifiez les <strong>sessions actives</strong> mensuellement</li>
          </ul>
        </div>

        <div class="guide-tip">
          <h4>⚡ Performance</h4>
          <ul>
            <li>Activez le <strong>cache</strong> pour réduire les coûts</li>
            <li>Utilisez <strong>GPT-3.5</strong> pour les tâches simples</li>
            <li>Limitez le <strong>max tokens</strong> si nécessaire</li>
            <li>Nettoyez régulièrement les <strong>vieux threads</strong></li>
          </ul>
        </div>
      </section>
    `
  }
];
