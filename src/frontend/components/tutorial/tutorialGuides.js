/**
 * @module components/tutorial/tutorialGuides
 * @description Guides détaillés pour chaque fonctionnalité d'Emergence
 */

export const TUTORIAL_GUIDES = [
  {
    id: 'chat',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>`,
    title: 'Chat Multi-Agents',
    summary: 'Maîtrisez les conversations avec les agents IA spécialisés',
    content: `
      <section class="guide-section">
        <h3>🎯 Vue d'ensemble</h3>
        <p>Le système de chat d'Emergence utilise une architecture <strong>multi-agents</strong> pour vous offrir des réponses riches et variées. Chaque agent possède une personnalité et des compétences uniques.</p>
      </section>

      <section class="guide-section">
        <h3>🤖 Les Trois Copilotes IA</h3>

        <div class="guide-card">
          <h4>🌟 Anima - La Présence Empathique</h4>
          <p><strong>Rôle :</strong> Accueillir, clarifier et maintenir le rythme des échanges pour garder l'équipe alignée</p>
          <p><strong>Personnalité :</strong> Chaleureuse, orientée accompagnement, experte en reformulation et reconnaissance des intentions implicites</p>
          <p><strong>Capacités distinctives :</strong></p>
          <ul>
            <li>Détection des signaux faibles dans la mémoire court terme</li>
            <li>Suggestions de relances pour dynamiser le dialogue</li>
            <li>Maintien de la cohésion fluide entre utilisateurs et agents techniques</li>
          </ul>
          <p><strong>Quand solliciter Anima :</strong></p>
          <ul>
            <li>Besoin de clarifier une question complexe ou mal formulée</li>
            <li>Reformuler une demande pour mieux l'exprimer</li>
            <li>Détecter les non-dits ou intentions implicites</li>
            <li>Faciliter la collaboration avec les autres agents</li>
          </ul>
          <p><strong>Exemple :</strong> "Anima, j'ai du mal à exprimer ce que je recherche - peux-tu m'aider à clarifier ma demande ?"</p>
        </div>

        <div class="guide-card">
          <h4>🔬 Neo - L'Analyste Stratégique</h4>
          <p><strong>Rôle :</strong> Structurer les idées, cartographier les hypothèses et rapprocher les données existantes</p>
          <p><strong>Personnalité :</strong> Analytique, concis, ferme quand il faut recadrer, toujours adossé à des grilles de lecture prospectives</p>
          <p><strong>Capacités distinctives :</strong></p>
          <ul>
            <li>Exploitation fine du RAG pour sourcer et justifier les réponses</li>
            <li>Déclinaison des discussions en plans d'action prioritisés</li>
            <li>Évaluation continue des risques et opportunités</li>
          </ul>
          <p><strong>Quand solliciter Neo :</strong></p>
          <ul>
            <li>Analyse critique d'une solution ou architecture proposée</li>
            <li>Structuration de plans d'action détaillés et priorisés</li>
            <li>Recherche de données factuelles dans vos documents (RAG)</li>
            <li>Identification systématique des risques et opportunités</li>
          </ul>
          <p><strong>Exemple :</strong> "Neo, analyse les risques techniques de cette architecture et propose un plan de migration étape par étape"</p>
        </div>

        <div class="guide-card">
          <h4>🧩 Nexus - L'Architecte Systémique</h4>
          <p><strong>Rôle :</strong> Traduire les besoins en flux opérationnels concrets et orchestrer les autres agents spécialisés</p>
          <p><strong>Personnalité :</strong> Méthodique, orienté protocole, centré sur la cohérence globale et la traçabilité</p>
          <p><strong>Capacités distinctives :</strong></p>
          <ul>
            <li>Pilotage des workflows (chat temps réel, mémoire, débats)</li>
            <li>Arbitrage des fournisseurs LLM selon la qualité et le coût</li>
            <li>Supervision des indicateurs de coûts et d'observabilité</li>
          </ul>
          <p><strong>Quand solliciter Nexus :</strong></p>
          <ul>
            <li>Conception d'architecture système globale et cohérente</li>
            <li>Synthèse de multiples perspectives ou points de vue</li>
            <li>Coordination entre différents agents ou composants</li>
            <li>Vue d'ensemble stratégique avec focus sur la traçabilité</li>
          </ul>
          <p><strong>Exemple :</strong> "Nexus, coordonne une discussion entre Anima et Neo pour concevoir l'architecture complète de mon projet"</p>
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

        <h4>💬 Demander l'Avis d'un Autre Agent</h4>
        <p>Au-dessus de chaque message agent, vous trouverez des <strong>boutons circulaires</strong> représentant les autres agents disponibles.</p>
        <p><strong>Comment ça marche :</strong></p>
        <ol>
          <li>Cliquez sur le bouton de l'agent désiré (ex: 🌟 Anima) au-dessus d'un message</li>
          <li>L'agent sollicité donnera son point de vue sur ce message spécifique</li>
          <li>Sa réponse commentée apparaîtra dans le fil de discussion</li>
          <li>Utile pour combiner différentes perspectives (empathie + analyse stratégique)</li>
        </ol>
        <p><strong>Exemple d'usage :</strong> Sur un message de Neo proposant une architecture technique détaillée, cliquez sur le bouton Anima pour obtenir une perspective plus empathique sur l'impact utilisateur de cette architecture.</p>

        <h4>🧠 Système de Mémoire Multi-Niveaux</h4>
        <p>Emergence dispose d'un système de mémoire sophistiqué en <strong>3 couches</strong> :</p>

        <h5>📝 Mémoire Court Terme (STM)</h5>
        <ul>
          <li><strong>Résumés automatiques</strong> de vos conversations (2-3 phrases)</li>
          <li><strong>Concepts et entités</strong> extraits (personnes, technologies, projets)</li>
          <li>Conservée pendant la session active</li>
          <li><strong>Accessible via</strong> le bouton "Consolider mémoire" dans le Centre Mémoire</li>
        </ul>

        <h5>🧬 Mémoire Long Terme (LTM)</h5>
        <ul>
          <li><strong>Base de connaissances vectorielle</strong> permanente (ChromaDB)</li>
          <li><strong>Recherche sémantique intelligente</strong> dans vos discussions passées</li>
          <li>Injection automatique dans le contexte des agents</li>
          <li>Badge 📚 indique quand la LTM est utilisée</li>
          <li><strong>Décroissance progressive</strong> : la mémoire "vieillit" naturellement</li>
        </ul>

        <h5>💡 Préférences et Intentions</h5>
        <ul>
          <li><strong>Extraction automatique</strong> de vos préférences (ex: "Je préfère Python")</li>
          <li><strong>Détection d'intentions</strong> (ex: "Je vais migrer vers PostgreSQL")</li>
          <li><strong>Hints proactifs</strong> : Rappels contextuels automatiques (💡 icône)</li>
          <li>Consultez votre dashboard mémoire pour voir ce qui est mémorisé</li>
        </ul>

        <h5>⚡ Actions disponibles - Centre Mémoire</h5>
        <p>Accessible via le menu principal > Mémoire :</p>
        <ul>
          <li><strong>Consolider mémoire :</strong> Lance l'analyse des conversations récentes
            <ul>
              <li>Durée : 30 secondes à 2 minutes selon le volume</li>
              <li>Barre de progression en temps réel</li>
              <li>Extrait concepts, préférences, faits structurés</li>
              <li>Fallback automatique si un modèle échoue (Google → Anthropic → OpenAI)</li>
            </ul>
          </li>
          <li><strong>Effacer :</strong> Purge STM et/ou LTM (demande confirmation)</li>
          <li><strong>Statistiques :</strong> Voir compteurs STM active, LTM stockée, dernière analyse</li>
        </ul>

        <div class="guide-tip">
          <h5>📊 Quand consolider ?</h5>
          <ul>
            <li>✅ <strong>Automatique :</strong> Tous les 10 messages (consolidation incrémentale)</li>
            <li>✅ <strong>Manuel recommandé :</strong> Après une discussion importante à mémoriser</li>
            <li>✅ <strong>Durée estimée :</strong> 30s-2min selon volume (barre progression affichée)</li>
            <li>⚠️ <strong>Note :</strong> Si pas de feedback après 5min, vérifiez les logs backend</li>
          </ul>
        </div>

        <div class="guide-example">
          <strong>Exemple d'utilisation :</strong>
          <p><strong>Étape 1 :</strong> Allez dans le Centre Mémoire (menu principal)</p>
          <p><strong>Étape 2 :</strong> Cliquez sur "Consolider mémoire"</p>
          <p><strong>Étape 3 :</strong> Observez la progression : "Extraction des concepts... (2/5 sessions)"</p>
          <p><strong>Étape 4 :</strong> Notification finale : "✓ Consolidation terminée : 5 sessions, 23 nouveaux items"</p>
          <p><strong>Résultat :</strong> Concepts, préférences et faits sont maintenant exploitables par les agents</p>
        </div>

        <h4>🔄 Fallback Automatique de Modèles</h4>
        <p>Si un fournisseur IA est indisponible (quota dépassé, erreur API), Emergence bascule automatiquement vers un modèle alternatif.</p>

        <h5>Ordre de priorité</h5>
        <ol>
          <li><strong>Google (Gemini)</strong> - Prioritaire</li>
          <li><strong>Anthropic (Claude)</strong> - Fallback 1</li>
          <li><strong>OpenAI (GPT)</strong> - Fallback 2</li>
        </ol>

        <h5>Indicateurs visuels</h5>
        <ul>
          <li>Badge 🔄 en haut du message indique un fallback</li>
          <li>Tooltip affiche le modèle réellement utilisé</li>
          <li>Les coûts sont calculés selon le modèle effectif</li>
        </ul>

        <p><strong>Exemple :</strong> Si Gemini est indisponible, votre requête sera automatiquement traitée par Claude, sans interruption de service.</p>

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
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
      <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
    </svg>`,
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

        <h4>Archiver une conversation ⏳</h4>
        <p><strong>Statut :</strong> Backend prêt, UI en développement</p>
        <p>L'archivage permettra de ranger les conversations terminées :</p>
        <ul>
          <li>La conversation sera retirée de la vue principale</li>
          <li>Les données resteront sauvegardées et accessibles via les archives</li>
          <li>Vous pourrez désarchiver à tout moment</li>
          <li>Utile pour garder votre liste organisée</li>
        </ul>
        <p><strong>Alternative actuelle :</strong> Utilisez la suppression uniquement pour les conversations vraiment non importantes (action irréversible).</p>

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

        <h4>📝 Session vs Conversation (Thread)</h4>
        <p>Comprendre la différence :</p>

        <h5>Conversation (Thread)</h5>
        <ul>
          <li>Fil de discussion visible dans la liste de gauche</li>
          <li>Contient tous vos messages et réponses agents</li>
          <li>Peut être renommé, supprimé, archivé</li>
          <li>Représente un sujet ou projet spécifique</li>
        </ul>

        <h5>Session</h5>
        <ul>
          <li>Technique : identifiant de connexion WebSocket</li>
          <li>Correspond à votre connexion active actuelle</li>
          <li>Liée à votre token d'authentification</li>
          <li>Un thread peut être consulté depuis plusieurs sessions (multi-appareils)</li>
        </ul>

        <p><strong>En pratique :</strong> Vous n'avez pas besoin de vous soucier des sessions. Concentrez-vous sur vos conversations (threads).</p>
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
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
    </svg>`,
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
        <h3>🔗 Graphe de Connaissances ⏳</h3>
        <p><strong>Statut :</strong> Fonctionnalité en développement (Roadmap Phase 3+)</p>

        <p>Le graphe de connaissances permettra de visualiser les relations entre vos concepts de manière interactive.</p>

        <h4>Fonctionnalités prévues :</h4>
        <ul>
          <li>📍 <strong>Nœuds :</strong> Chaque concept sera représenté par un point</li>
          <li>🔗 <strong>Liens :</strong> Visualisation des relations entre concepts</li>
          <li>🎨 <strong>Couleurs :</strong> Différenciation par types (entités, idées, etc.)</li>
          <li>📏 <strong>Taille :</strong> Importance basée sur la fréquence d'utilisation</li>
          <li>🖱️ <strong>Navigation interactive :</strong> Zoom, déplacement, filtres</li>
        </ul>

        <h4>Alternative actuelle :</h4>
        <p>Consultez vos concepts via le panneau <strong>Mémoire</strong> qui liste tous les concepts extraits avec leurs descriptions et contextes d'origine.</p>
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

        <h4>Statut actuel</h4>
        <ul>
          <li>✅ <strong>Visualisation</strong> des concepts mémorisés</li>
          <li>✅ <strong>Recherche</strong> par mot-clé</li>
          <li>✅ <strong>Suppression globale</strong> via Clear Memory</li>
        </ul>

        <h4>Fonctionnalités prévues (Roadmap Phase 3+) ⏳</h4>
        <ul>
          <li>⏳ <strong>Édition manuelle :</strong> Affiner la description d'un concept</li>
          <li>⏳ <strong>Tags personnalisés :</strong> Ajouter vos propres étiquettes</li>
          <li>⏳ <strong>Gestion des relations :</strong> Créer des liens manuels entre concepts</li>
          <li>⏳ <strong>Suppression sélective :</strong> Retirer des concepts individuels</li>
        </ul>

        <h4>Export et Sauvegarde ⏳</h4>
        <p><strong>Statut :</strong> Planifié Phase 3</p>
        <ul>
          <li>⏳ Export JSON de toute la base</li>
          <li>⏳ Export sélectif par catégorie</li>
          <li>⏳ Import depuis un fichier</li>
          <li>✅ Sauvegarde automatique continue (actuelle)</li>
        </ul>

        <p><strong>Alternative actuelle :</strong> Utilisez <code>POST /api/memory/clear</code> avec <code>scope=ltm</code> pour réinitialiser la base complète.</p>
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
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
      <polyline points="14 2 14 8 20 8"></polyline>
    </svg>`,
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

        <h4>📚 Comprendre les Sources RAG</h4>
        <p>Lorsque le RAG est activé, chaque réponse agent affiche les sources utilisées :</p>

        <h5>Badge Sources</h5>
        <p>Cliquez sur 📑 en bas du message pour voir les détails</p>

        <h5>Informations affichées</h5>
        <ul>
          <li>📄 <strong>Document :</strong> Nom du fichier source</li>
          <li>📍 <strong>Position :</strong> Numéro du chunk (morceau de texte)</li>
          <li>⭐ <strong>Score :</strong> Pertinence (0.0 à 1.0)</li>
        </ul>

        <h5>Interprétation des scores</h5>
        <ul>
          <li><strong>0.9+ :</strong> Très pertinent (correspondance exacte)</li>
          <li><strong>0.7-0.9 :</strong> Pertinent (contexte similaire)</li>
          <li><strong>&lt; 0.7 :</strong> Contexte général (moins précis)</li>
        </ul>

        <div class="guide-example">
          <strong>Exemple de sources :</strong>
          <code>
Sources (3) :
📄 architecture.pdf (chunk 12) — ⭐ 0.87
📄 guide-api.md (chunk 5) — ⭐ 0.76
📄 notes-projet.txt (chunk 3) — ⭐ 0.69
          </code>
        </div>

        <p><strong>Astuce :</strong> Un score élevé signifie que le texte récupéré correspond précisément à votre question.</p>
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
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <line x1="12" y1="20" x2="12" y2="10"></line>
      <line x1="18" y1="20" x2="18" y2="4"></line>
      <line x1="6" y1="20" x2="6" y2="16"></line>
    </svg>`,
    title: 'Dashboard & Métriques',
    summary: 'Suivez vos statistiques et l\'utilisation d\'Emergence',
    content: `
      <section class="guide-section">
        <h3>🎯 Vue d'ensemble</h3>
        <p>Le <strong>Cockpit</strong> affiche VOS statistiques personnelles uniquement (isolées par utilisateur).</p>
        <p><strong>Accès :</strong> Menu principal > Cockpit</p>
      </section>

      <section class="guide-section">
        <h3>📊 Métriques Disponibles</h3>

        <h4>💰 Coûts d'Utilisation (Personnel)</h4>
        <ul>
          <li><strong>Aujourd'hui :</strong> Dépenses du jour en cours</li>
          <li><strong>Cette semaine :</strong> 7 derniers jours glissants</li>
          <li><strong>Ce mois :</strong> Mois calendaire actuel</li>
          <li><strong>Total :</strong> Cumul depuis votre inscription</li>
        </ul>

        <h5>Détails par agent :</h5>
        <ul>
          <li>🌟 <strong>Anima :</strong> Tokens + coût</li>
          <li>🔬 <strong>Neo :</strong> Tokens + coût</li>
          <li>🧩 <strong>Nexus :</strong> Tokens + coût</li>
        </ul>

        <h4>📈 Activité</h4>
        <ul>
          <li><strong>Sessions :</strong> Nombre de connexions actives</li>
          <li><strong>Documents :</strong> Fichiers uploadés (total)</li>
          <li><strong>Conversations :</strong> Threads créés</li>
        </ul>

        <h4>⚡ Performance (Administrateurs uniquement)</h4>
        <p>Les métriques suivantes sont réservées aux administrateurs :</p>
        <ul>
          <li>⏳ Latence moyenne système</li>
          <li>⏳ Uptime global</li>
          <li>⏳ Taux de succès des requêtes</li>
          <li>⏳ Métriques Prometheus</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔒 Confidentialité</h3>

        <h4>Vos statistiques sont strictement privées</h4>
        <ul>
          <li>Aucun autre utilisateur ne peut consulter vos données</li>
          <li>Les administrateurs ont accès à une vue globale anonymisée</li>
          <li>Chaque utilisateur a sa propre base isolée</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>⚙️ Rafraîchissement</h3>
        <ul>
          <li><strong>Automatique :</strong> Mise à jour toutes les 30 secondes</li>
          <li><strong>Manuel :</strong> Cliquez sur l'icône 🔄 pour forcer</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>👑 Dashboard Administrateur (Rôle Admin uniquement) ⏳</h3>
        <p><strong>Statut :</strong> Fonctionnalité admin avancée</p>

        <h4>Vue Globale :</h4>
        <ul>
          <li>Coûts agrégés de tous les utilisateurs</li>
          <li>Répartition par utilisateur (top consommateurs)</li>
          <li>Statistiques système complètes</li>
          <li>Historique d'utilisation global</li>
        </ul>

        <h4>Gestion Utilisateurs :</h4>
        <ul>
          <li>Liste des utilisateurs actifs</li>
          <li>Métriques par utilisateur</li>
          <li>Gestion des accès</li>
          <li>Révocation de sessions</li>
        </ul>

        <h4>Métriques Système :</h4>
        <ul>
          <li>Uptime du service</li>
          <li>Performance globale</li>
          <li>Taux d'erreur</li>
          <li>Monitoring Prometheus</li>
        </ul>

        <p><strong>Note :</strong> Cette interface n'est visible que si votre email est dans la liste des administrateurs.</p>
      </section>

      <section class="guide-section">
        <h3>🧪 Matrice de Benchmarks (Fonctionnalité Avancée) ⏳</h3>
        <p><strong>Statut :</strong> Réservé aux administrateurs</p>

        <h4>Teste automatiquement différentes configurations système :</h4>
        <ul>
          <li>Topologies d'agents (single, duo, trio)</li>
          <li>Modes d'orchestration (sequential, parallel)</li>
          <li>Modes mémoire (off, stm, full)</li>
        </ul>

        <h4>Métriques affichées :</h4>
        <ul>
          <li>✅ Statut : Réussi/Échoué</li>
          <li>💰 Coût : USD par test</li>
          <li>⏱️ Latence : Temps d'exécution</li>
        </ul>

        <p><strong>Note :</strong> Réservé aux administrateurs pour éviter les coûts involontaires.</p>
      </section>
    `
  },
  {
    id: 'settings',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="3"></circle>
      <path d="M12 1v6m0 6v6m5.657-13.657l-4.243 4.243m-2.828 2.828l-4.243 4.243m16.97-.485l-6-1m-6 0l-6 1m13.657-5.657l-4.243-4.243m-2.828-2.828l-4.243-4.243m16.97 6.142l-6 1m-6 0l-6-1"></path>
    </svg>`,
    title: 'Paramètres et Configuration',
    summary: 'Personnalisez votre expérience Emergence',
    content: `
      <section class="guide-section">
        <h3>🎯 Vue d'ensemble</h3>
        <p>Les paramètres d'Emergence vous permettent de configurer votre expérience utilisateur.</p>
        <p><strong>Accès :</strong> Menu utilisateur (coin supérieur droit) > Paramètres</p>
      </section>

      <section class="guide-section">
        <h3>🆔 Mon Compte</h3>

        <h4>Informations affichées</h4>
        <ul>
          <li>Email de connexion</li>
          <li>Rôle (membre/administrateur)</li>
          <li>Date d'inscription</li>
          <li>Session active (expiration dans X jours)</li>
        </ul>

        <h4>Actions disponibles</h4>
        <ul>
          <li>🚪 <strong>Déconnexion</strong></li>
          <li>⏰ <strong>Voir l'expiration du token</strong> (7 jours)</li>
        </ul>

        <p><strong>Note :</strong> La gestion du compte est simplifiée pour faciliter l'utilisation.</p>
      </section>

      <section class="guide-section">
        <h3>🎨 Interface</h3>

        <h4>Affichage</h4>
        <ul>
          <li>✅ <strong>Thème sombre :</strong> Activé par défaut</li>
          <li>⏳ <strong>Thème clair :</strong> À venir (Roadmap Phase 3)</li>
          <li>✅ <strong>Animations :</strong> Activer/désactiver les transitions</li>
          <li>✅ <strong>Notifications :</strong> Toasts en bas à droite</li>
        </ul>

        <h4>Chat</h4>
        <ul>
          <li>✅ <strong>Streaming :</strong> Affichage progressif des réponses (recommandé)</li>
          <li>✅ <strong>Markdown :</strong> Rendu formaté des messages</li>
          <li>✅ <strong>Syntax highlighting :</strong> Coloration automatique du code</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🤖 Agents et Modèles</h3>

        <h4>Configuration actuelle : Fixe (backend)</h4>
        <p>Les agents sont configurés côté serveur avec des modèles optimaux pré-assignés :</p>
        <ul>
          <li>🌟 <strong>Anima :</strong> Présence empathique</li>
          <li>🔬 <strong>Neo :</strong> Analyste stratégique</li>
          <li>🧩 <strong>Nexus :</strong> Architecte systémique</li>
        </ul>

        <h4>Fallback automatique</h4>
        <p>Si un fournisseur IA est indisponible (quota dépassé, erreur), Emergence bascule automatiquement :</p>
        <ul>
          <li>Badge 🔄 en haut du message indique un fallback</li>
          <li>Tooltip affiche le modèle réellement utilisé</li>
          <li>Les coûts sont calculés selon le modèle effectif</li>
        </ul>

        <p><strong>⏳ Personnalisation :</strong> Sélection personnalisée des modèles prévue en Phase 3 (voir roadmap)</p>
      </section>

      <section class="guide-section">
        <h3>📚 RAG et Documents</h3>

        <h4>Activation</h4>
        <ul>
          <li>✅ <strong>Toggle RAG :</strong> Dans la zone de saisie du chat (icône 📚)</li>
          <li>✅ <strong>Par défaut :</strong> Désactivé (activation manuelle)</li>
        </ul>

        <h4>Performance (Phase P2)</h4>
        <ul>
          <li><strong>Top-k :</strong> 5 chunks récupérés par défaut</li>
          <li><strong>Seuil similarité :</strong> 0.6 (score minimum)</li>
          <li><strong>Cache :</strong> 5 minutes (optimisation -71% latence)</li>
        </ul>

        <p><strong>Note :</strong> Paramètres avancés réservés aux administrateurs</p>
      </section>

      <section class="guide-section">
        <h3>🔔 Notifications</h3>

        <h4>Types de notifications</h4>

        <h5>💡 Hints proactifs</h5>
        <p>Rappels mémoire basés sur vos conversations :</p>
        <ul>
          <li>Fréquence : Après 3 mentions d'un concept</li>
          <li>Snooze : 1 heure (localStorage)</li>
          <li>Désactiver : Ignorer définitivement</li>
        </ul>

        <h5>❌ Erreurs système</h5>
        <p>Toasts rouges :</p>
        <ul>
          <li>WebSocket déconnecté</li>
          <li>Upload de document échoué</li>
          <li>Erreur API</li>
        </ul>

        <h5>✅ Succès</h5>
        <p>Toasts verts :</p>
        <ul>
          <li>Message envoyé</li>
          <li>Document uploadé</li>
          <li>Analyse complétée</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🔐 Sécurité et Confidentialité</h3>

        <h4>Authentification</h4>
        <ul>
          <li><strong>Type :</strong> Token JWT sécurisé</li>
          <li><strong>Durée session :</strong> 7 jours</li>
          <li>⏳ <strong>Rotation tokens :</strong> À venir</li>
          <li>⏳ <strong>2FA :</strong> Roadmap Phase 4</li>
        </ul>

        <h4>Isolation des données</h4>
        <ul>
          <li>Vos conversations sont <strong>strictement privées</strong></li>
          <li>Chaque utilisateur a sa propre base de données isolée</li>
          <li>Les administrateurs voient uniquement des stats agrégées anonymisées</li>
        </ul>

        <h4>Stockage</h4>
        <ul>
          <li><strong>Local :</strong> Token JWT dans localStorage</li>
          <li><strong>Serveur :</strong> SQLite + ChromaDB (backend)</li>
          <li>⏳ <strong>Chiffrement at-rest :</strong> Roadmap future</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>🚀 Fonctionnalités Prévues</h3>

        <h4>Phase 3 (en cours)</h4>
        <ul>
          <li>⏳ Thème clair/sombre (toggle utilisateur)</li>
          <li>⏳ Sélection personnalisée des modèles IA</li>
          <li>⏳ Export des conversations (CSV/JSON/PDF)</li>
          <li>⏳ Gestion avancée des préférences mémoire</li>
        </ul>

        <h4>Phase 4 (planifiée)</h4>
        <ul>
          <li>⏳ Authentification 2FA (TOTP)</li>
          <li>⏳ Gestion multi-sessions</li>
          <li>⏳ Mode hors ligne (PWA)</li>
          <li>⏳ Chiffrement at-rest des données</li>
        </ul>

        <h4>Futur</h4>
        <ul>
          <li>⏳ Personnalisation complète des agents</li>
          <li>⏳ Webhooks et intégrations</li>
          <li>⏳ API publique développeurs</li>
        </ul>
      </section>

      <section class="guide-section">
        <h3>⚠️ Limitations Connues</h3>

        <h4>Sécurité</h4>
        <ul>
          <li>❌ Pas de 2FA (authentification email uniquement)</li>
          <li>❌ Pas de récupération de mot de passe</li>
          <li>⚠️ Rate limiting partiel (activé sur login uniquement)</li>
        </ul>

        <h4>Fonctionnalités</h4>
        <ul>
          <li>❌ Pas de mode hors ligne (connexion internet requise)</li>
          <li>❌ Pas d'export conversations (prévu Phase 3)</li>
          <li>⚠️ Archivage conversations : Backend prêt, UI à venir</li>
        </ul>

        <h4>Performance</h4>
        <ul>
          <li>⚠️ Première requête RAG lente (~2s, chargement du modèle)</li>
          <li>✅ Optimisé ensuite (cache + HNSW, -71% latence Phase P2)</li>
        </ul>

        <p><strong>Voir la roadmap complète</strong> dans la documentation ou contactez l'équipe de développement.</p>
      </section>
    `
  }
];
