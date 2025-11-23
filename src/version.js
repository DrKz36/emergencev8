/**
 * ÉMERGENCE V8 - Version centralisée
 *
 * Ce fichier est la source unique de vérité pour le versioning de l'application.
 * Toutes les références de version doivent importer depuis ce fichier.
 *
 * Versioning sémantique : beta-MAJOR.MINOR.PATCH
 * - MAJOR : Phase complète (P0 = 1, P1 = 2, P2 = 3, etc.)
 * - MINOR : Fonctionnalité complétée dans la phase
 * - PATCH : Bugfixes et hotfixes
 *
 * Historique :
 * - beta-3.3.38 : SW cache bust (RAG/TTS styles auto-apply) [ACTUEL]
 * - beta-3.3.37 : Persist state light (quota localStorage)
 * - beta-3.3.36 : SW Deep Aura cache (RAG/TTS)
 * - beta-3.3.35 : PWA cache versionn� (RAG/TTS styles appliqu�s sans vidage cache)
 * - beta-1.0.0 : Phase P0 complétée (Quick Wins - 3/3)
 * - beta-2.0.0 : Phase P1 complétée (UX Essentielle - 3/3)
 * - beta-2.1.0 : Phase 1 & 3 Debug (Backend fixes + UI/UX improvements)
 * - beta-2.1.1 : Audit système multi-agents + versioning unifié
 * - beta-2.1.2 : Guardian automation + pre-deployment validation
 * - beta-2.1.3 : Guardian email reports automation
 * - beta-2.1.4 : Fix 404 production (reset-password, favicon)
 * - beta-2.1.5 : Fix responsive mobile admin dashboard
 * - beta-2.2.0 : Mypy 100% clean (0 errors) + monitoring router fix
 * - beta-3.0.0 : Phase P2 complétée (Admin & Sécurité - 3/3)
 * - beta-3.3.29 : Fix Document Upload Timeout - Gros documents fonctionnels en production
 * - beta-3.3.28 : TTS Mobile Autoplay Fix - Déblocage restrictions navigateurs mobiles
 * - beta-3.3.24 : RAG Phase 4 - Requêtes exhaustives + boost retrieval gros documents
 * - beta-3.3.23 : Réactivation snapshot Firestore allowlist - Persistence comptes entre déploiements
 * - beta-3.3.22 : Fix TTS mobile portrait visibility - Override CSS important
 * - beta-3.3.21 : Fix allowlist overwrite FINAL - Merge intelligent Firestore (union emails)
 * - beta-3.3.21 : Fix bouton TTS mobile disparu + Sync desktop/mobile
 * - beta-3.3.20 : Fix allowlist overwrite on redeploy - Preserve manually added accounts
 * - beta-3.3.19 : Fix modal reprise conversation - Évite affichage intempestif après choix utilisateur
 * - beta-3.3.19 : TTS toggle header + Voix par agent + Auto-play silencieux
 * - beta-3.3.18 : Fix Voice DI container leak - Réutilise app.state container
 * - beta-3.3.17 : Fix Voice TTS - Auth token + SVG icon cohérent
 * - beta-3.3.16 : Voice agents avec ElevenLabs TTS - Écouter les messages
 * - beta-3.3.15 : Fix upload gros documents - Limites strictes pour éviter timeout Cloud Run
 * - beta-3.3.14 : Production connectivity fixes - WebSocket auth & thread cleanup
 * - beta-3.3.13 : Auth token test bundler compatibility
 * - beta-3.3.12 : Auth session continuity
 * - beta-3.3.11 : Auth handshake stabilization
 * - beta-3.3.10 : Sync script compatibility fix
 * - beta-3.3.9 : Version manifest merge fix
 * - beta-3.3.8 : Document chunk throttling & warnings
 * - beta-3.3.7 : Document upload resilience & cross-agent routing
 * - beta-3.3.6 : About module metrics refresh & genesis timeline fix
 * - beta-3.3.5 : Setup Firestore Snapshot - Infrastructure Sync Allowlist Automatique
 * - beta-3.3.4 : Fix Timing Pop-up - Affichage au Démarrage App (pas au mount module)
 * - beta-3.3.3 : Fix Pop-up Reprise - Modal Systématique + Centrage Correct
 * - beta-3.3.2 : Fix Critiques Routing/Session - Pop-up Reprise + Validation Threads Archivés
 * - beta-3.3.1 : Fix Critiques BDD - Duplication Messages + Soft-Delete Archives
 * - beta-3.3.0 : PWA Mode Hors Ligne (P3.10 Complétée)
 * - beta-3.2.2 : Configuration Email Officielle - emergence.app.ch@gmail.com
 * - beta-3.2.1 : Changelog enrichi - 5 révisions détaillées avec sections complètes
 * - beta-3.2.0 : Module À Propos avec Changelog enrichi (13 versions affichées)
 * - beta-3.1.3 : Métrique nDCG@k temporelle + garde composer mobile
 * - beta-3.1.2 : Refactor docs inter-agents (fichiers séparés - zéro conflit merge)
 * - beta-3.1.1 : Dialogue - Modal reprise multi-conversations
 * - beta-3.1.0 : Webhooks + Health Check Scripts + Qualité (mypy 100%)
 */

export const CURRENT_RELEASE = {
  version: 'beta-3.3.38',
  name: 'SW cache bust (RAG/TTS styles auto-apply)',
  date: '2025-11-23',
};

export const VERSION = CURRENT_RELEASE.version;
export const VERSION_NAME = CURRENT_RELEASE.name;
export const VERSION_DATE = CURRENT_RELEASE.date;
export const BUILD_PHASE = 'P3';
export const COMPLETION_PERCENTAGE = 78; // 18/23 features (P3.11 webhooks complété)
export const TOTAL_FEATURES = 23;

/**
 * Patch notes pour la version actuelle
 * Affichées dans le module "À propos" des paramètres
 */
export const PATCH_NOTES = [
  {
    version: 'beta-3.3.38',
    tagline: 'SW cache bust (RAG/TTS styles auto-apply)',
    date: '2025-11-23',
    changes: [
      { type: 'fix', text: 'Bump version SW/pwa pour invalider les caches shell/runtime et appliquer les styles RAG/TTS sans vidage manuel.' },
      { type: 'quality', text: 'Relâche le cache service worker via /sw.js?v=beta-3.3.38 et caches emergence-shell/runtime-3.3.38.' }
    ]
  },
  {
    version: 'beta-3.3.37',
    tagline: 'Persist state light (quota localStorage)',
    date: '2025-11-20',
    changes: [
      { type: 'fix', text: 'Prune des messages et docs avant persist pour �viter QuotaExceededError dans localStorage (limite 20 messages/agent + map threads sans payloads).' },
      { type: 'quality', text: 'StateManager �crit un �tat all�g� (threads sans messages/docs) pour ne pas saturer la persist offline.' }
    ]
  },
  {
    version: 'beta-3.3.36',
    tagline: 'SW Deep Aura cache (RAG/TTS)',
    date: '2025-11-20',
    changes: [
      { type: 'fix', text: 'Le service worker precache explicitement rag-power-button.css pour appliquer les styles RAG/TTS sans hard refresh.' },
      { type: 'ops', text: "Version SW incrementee (beta-3.3.36) pour forcer l'activation du nouveau cache sur les postes existants." }
    ]
  },
  {
    version: 'beta-3.3.35',
    tagline: 'PWA cache versioning - styles RAG/TTS',
    date: '2025-11-20',
    changes: [
      { type: 'fix', text: 'Service worker versionn� par release via `/sw.js?v=<version>` pour invalider automatiquement les caches CSS sans vider manuellement le cache navigateur.' },
      { type: 'quality', text: 'Caches shell/runtime nomm�s avec la version et purge syst�matique des versions obsol�tes � l\'activation du SW.' },
      { type: 'ux', text: 'Les boutons RAG/TTS appliquent d�s le premier chargement les styles Deep Aura en local (plus besoin de hard refresh + cache clear).' }
    ]
  },
  {
    version: 'beta-3.3.34',
    tagline: 'Deep Aura UI Refresh & Desktop Fix',
    date: '2025-11-20',
    changes: [
      { type: 'fix', text: 'Restauration des imports CSS core dans index.html pour r�tablir la mise en page desktop et masquer correctement le verrou orientation.' },
      { type: 'ui', text: 'Th�me Deep Aura appliqu� avec variables, glassmorphism V3 et animations globales charg�es depuis l\'entrypoint.' },
      { type: 'quality', text: 'Alignement des versions frontend/backend sur la release Deep Aura.' }
    ]
  },
  {
    version: 'beta-3.3.33',
    tagline: 'Documents Upload Stability & Auth Guard',
    date: '2025-11-02',
    changes: [
      { type: 'fix', text: 'Fallback PyPDF2 si PyMuPDF est absent pour garder le module Documents disponible au lieu de 503.' },
      { type: 'quality', text: 'Imports PDF/DOCX lazy pour ne pas bloquer DocumentService si une dependance native manque.' },
      { type: 'quality', text: 'Module Documents emet auth:missing sur 401/403 et indique la reconnexion lors des uploads/listes.' }
    ]
  },
  {
    version: 'beta-3.3.32',
    tagline: 'ChatService Architecture - Décomposition Phase 2+3 (MemoryService + PromptService)',
    date: '2025-11-20',
    changes: [
      { type: 'quality', text: '🏗️ REFACTOR ARCHITECTURAL: Extraction de MemoryService depuis ChatService (Phase 2) - Gestion consolidée mémoire, concepts, temporal history, groupement thématique' },
      { type: 'quality', text: '🏗️ REFACTOR ARCHITECTURAL: Extraction de PromptService depuis ChatService (Phase 3) - Chargement prompts avec versioning (v3>v2>lite), résolution config agents, application style rules tutoiement' },
      { type: 'quality', text: '✨ Code plus maintenable: ChatService passé de ~2000 lignes monolithique → 3 services spécialisés avec responsabilités claires' },
      { type: 'quality', text: '🔧 Cleanup imports: Suppression import Optional inutilisé dans interfaces.py (ruff clean)' },
      { type: 'docs', text: '📚 Architecture documentée: Nouveaux services ajoutés dans docs/architecture/10-Components.md' }
    ]
  },
  {
    version: 'beta-3.3.31',
    tagline: 'Large Document Upload Resilience - Chunk fallback multi-phase',
    date: '2025-11-01',
    changes: [
      { type: 'fix', text: 'Fallback de chunking dynamique : suppression de la limite 2 paragraphes pour les documents > 10 000 sections afin d\'éviter l\'erreur 413.' },
      { type: 'performance', text: 'Augmentation adaptative du chunk_size et fusion progressive pour maintenir ≤ 5 000 chunks tout en vectorisant 100 % du document.' },
      { type: 'quality', text: 'Test d\'intégration `test_process_upload_with_massive_line_count` pour garantir l\'upload complet de 12 500 paragraphes.' }
    ]
  },
  {
    version: 'beta-3.3.30',
    tagline: 'Investigation Cross-Device Persistence - Outils de diagnostic et migration',
    date: '2025-11-01',
    changes: [
      { type: 'investigation', text: '🔍 INVESTIGATION COMPLÈTE: Analyse du système de persistance cross-device (mobile ↔ desktop)' },
      { type: 'quality', text: '✅ Code vérifié: Backend JWT contient bien `sub` constant (hash email), frontend stocke `user_id`, queries priorisent `user_id`' },
      { type: 'quality', text: '⚠️  Problème identifié: Si JWT ancien SANS `sub` OU tables DB sans colonne `user_id` → isolation par session' },
      { type: 'feature', text: '📊 Nouveau: Script diagnostic `scripts/diagnose_cross_device.py` - Vérifie schéma DB + données manquantes' },
      { type: 'feature', text: '🔧 Nouveau: Script migration `scripts/migrate_cross_device.py` - Ajoute colonnes + backfill user_id automatique' },
      { type: 'docs', text: '📝 Rapport complet: `CROSS_DEVICE_INVESTIGATION.md` - Analyse détaillée + solutions proposées' },
      { type: 'fix', text: '🎯 Action recommandée: Lancer diagnostic puis migration si nécessaire + test 2 devices (mobile + desktop)' },
      { type: 'quality', text: 'Architecture validée: Système CORRECT pour cross-device, problème vient probablement de données legacy' }
    ]
  },
  {
    version: 'beta-3.3.29',
    tagline: 'Fix Document Upload Timeout - Gros documents fonctionnels en production',
    date: '2025-11-01',
    changes: [
      { type: 'fix', text: '🔥 FIX CRITIQUE: Timeout Cloud Run augmenté 600s→1800s (10min→30min) pour supporter documents 20 000+ lignes' },
      { type: 'fix', text: 'Crash connexion en prod résolu - Documents volumineux ne font plus timeout' },
      { type: 'performance', text: '🚀 PERF: Batch sizes optimisés x4 - VECTOR_BATCH_SIZE: 64→256, CHUNK_INSERT_BATCH_SIZE: 128→512' },
      { type: 'performance', text: 'Processing 4x plus rapide - Pour 5000 chunks: 117 appels → 30 appels (20 batches vectorisation + 10 batches DB)' },
      { type: 'quality', text: 'Logs de progression ajoutés - Visibilité complète du processing (parsing, chunking, DB insert, vectorisation)' },
      { type: 'ops', text: 'stable-service.yaml: timeoutSeconds 600→1800' },
      { type: 'ops', text: 'documents/service.py: Batch sizes augmentés + logs détaillés pour debug gros uploads' }
    ]
  },
  {
    version: 'beta-3.3.28',
    tagline: 'TTS Mobile Autoplay Fix - Déblocage restrictions navigateurs mobiles',
    date: '2025-11-01',
    changes: [
      { type: 'fix', text: '🔥 FIX MOBILE: TTS autoplay bloqué sur iOS Safari / Chrome Android par politiques autoplay navigateurs' },
      { type: 'fix', text: 'Déblocage autoplay au clic du bouton TTS - Création audio element avec play() immédiat d\'un silence' },
      { type: 'quality', text: 'Réutilisation audio element débloqué pour tous les messages suivants - Contourne restrictions mobiles' },
      { type: 'quality', text: 'Desktop non affecté - Autoplay fonctionnait déjà, maintenant fonctionne aussi sur mobile' },
      { type: 'ops', text: 'chat-ui.js toggleTTS(): Création _ttsAudioElement + play silence au clic utilisateur' },
      { type: 'ops', text: 'chat-ui.js _playTTS(): Réutilisation _ttsAudioElement au lieu de créer nouveau Audio() à chaque fois' }
    ]
  },
  {
    version: 'beta-3.3.27',
    tagline: 'RAG Phase 4.2 FIX CRITIQUE - DELETE + SCOPE filters sans session_id',
    date: '2025-11-01',
    changes: [
      { type: 'fix', text: '🔥 FIX CRITIQUE delete_document(): session_id RETIRÉ du filtre delete (chunks non supprimés car filtre incompatible)' },
      { type: 'fix', text: '🔥 FIX CRITIQUE scope_filter upload: session_id RETIRÉ (cohérence metadata chunks)' },
      { type: 'quality', text: 'DELETE fonctionne maintenant: chunks scopés user_id uniquement → suppression complète' },
      { type: 'quality', text: 'Résout problème "22 chunks sur 1913" - anciens chunks mal supprimés polluaient ChromaDB' },
      { type: 'ops', text: 'documents/service.py lignes 1095-1103: delete_document() sans session_id filter' },
      { type: 'ops', text: 'documents/service.py lignes 1033-1043: scope_filter sans session_id' }
    ]
  },
  {
    version: 'beta-3.3.26',
    tagline: 'RAG Phase 4.1 FIX FINAL - Pattern sans accent + Metadata scope user',
    date: '2025-11-01',
    changes: [
      { type: 'fix', text: '🔥 FIX CRITIQUE Pattern exhaustif: Ajout mots SANS accent (resume, detail, integral, synthese) - Support clavier US/international' },
      { type: 'fix', text: '🔥 FIX CRITIQUE Metadata: session_id RETIRÉ des chunks ChromaDB - Documents accessibles à TOUTES sessions du user' },
      { type: 'quality', text: 'Requête "resume memoire.txt" détectée maintenant comme exhaustive → top_k boost 5→100' },
      { type: 'quality', text: 'Retrieval passe de 16 chunks → 1913 chunks (100% du fichier) après re-upload' },
      { type: 'ops', text: 'chat/service.py: Pattern regex enrichi avec variantes sans accent' },
      { type: 'ops', text: 'documents/service.py: _build_chunk_payloads() sans session_id dans metadata' }
    ]
  },
  {
    version: 'beta-3.3.25',
    tagline: 'RAG Phase 4 FIX CRITIQUE - Gros documents ENFIN complets',
    date: '2025-11-01',
    changes: [
      { type: 'fix', text: '🔥 FIX CRITIQUE: Limite vectorisation 1000→5000 chunks (documents >1000 chunks tronqués à 50%)' },
      { type: 'fix', text: 'Documents accessibles à toutes les sessions du user (plus de filtrage session_id restrictif)' },
      { type: 'quality', text: 'memoire.txt (1913 chunks, 21955 lignes) maintenant ENTIÈREMENT vectorisé et accessible' },
      { type: 'quality', text: 'Résout problème "fragments seulement" de Neo - retrieval passe de 16 chunks → 1913 chunks (x119)' },
      { type: 'ops', text: 'DEFAULT_MAX_VECTOR_CHUNKS: 1000 → 5000 (5x augmentation pour gros documents)' }
    ]
  },
  {
    version: 'beta-3.3.24',
    tagline: 'RAG Phase 4 - Machine de guerre pour gros documents',
    date: '2025-11-01',
    changes: [
      { type: 'feature', text: '🚀 RAG Phase 4: Détection automatique des requêtes exhaustives ("résume", "analyse", "tous les concepts", etc.)' },
      { type: 'feature', text: 'Boost dynamique top_k: 5→100 chunks pour requêtes exhaustives (x20 amélioration)' },
      { type: 'quality', text: 'Multiplicateur retrieval augmenté: x3→x10 avec limite 500 chunks max (évite timeout)' },
      { type: 'quality', text: 'Amélioration drastique pour gros documents: 15→500 chunks récupérés pour analyses complètes' },
      { type: 'fix', text: 'Fix problème "fragments seulement" signalé par utilisateur - Nexus voit maintenant le contexte complet' }
    ]
  },
  {
    version: 'beta-3.3.23',
    tagline: 'Réactivation snapshot Firestore allowlist',
    date: '2025-11-01',
    changes: [
      { type: 'fix', text: '🔥 FIX CRITIQUE: Réactivation snapshot Firestore pour persistence allowlist entre déploiements Cloud Run' },
      { type: 'fix', text: 'Les comptes ajoutés manuellement via l\'admin UI survivent maintenant aux révisions (plus d\'écrasement de l\'allowlist)' },
      { type: 'ops', text: 'Décommentées variables d\'env AUTH_ALLOWLIST_SNAPSHOT_BACKEND=firestore dans stable-service.yaml' },
      { type: 'quality', text: 'Le système de merge intelligent Firestore (beta-3.3.21) est maintenant activé en production' },
      { type: 'quality', text: 'Snapshot Firestore existant détecté avec 2 comptes (admin + membre) - sera restauré au prochain déploiement' }
    ]
  },
  {
    version: 'beta-3.3.22',
    tagline: 'Fix TTS mobile portrait visibility',
    date: '2025-10-31',
    changes: [
      { type: 'fix', text: 'Corrige la régression mobile: le bouton TTS mobile restait masqué car la règle responsive sans !important ne prenait jamais le dessus sur display:none !important.' },
      { type: 'fix', text: 'Ajout de display:flex !important dans la media query mobile pour forcer l\'affichage du bouton TTS (et RAG) lorsque l\'écran est en portrait <= 760px.' },
      { type: 'quality', text: 'Synchronise visuellement desktop/mobile : la toggle voix reste disponible même dans le PWA shell ou Safari iOS où les media queries orientation étaient ignorées.' },
      { type: 'ops', text: 'Version patch express suite QA prod mobile : assure que le mode vocal est utilisable sur tous les devices portrait.' }
    ]
  },
  {
    version: 'beta-3.3.21',
    tagline: 'Fix allowlist overwrite FINAL - Merge intelligent Firestore',
    date: '2025-10-31',
    changes: [
      { type: 'fix', text: '🔥 FIX CRITIQUE: Implémentation merge intelligent Firestore (union emails) - Les comptes manuels NE SONT PLUS JAMAIS PERDUS' },
      { type: 'fix', text: 'Réécriture complète _persist_allowlist_snapshot() - Lit Firestore existant, merge avec DB locale, écrit résultat uni' },
      { type: 'fix', text: 'Logique merge: 1) Load Firestore 2) Union emails 3) Priorité DB locale si conflit 4) Gestion réactivation/révocation' },
      { type: 'fix', text: 'Logger info détaillé du merge: nombre active/revoked après fusion Firestore + DB locale' }
    ]
  },
  {
    version: 'beta-3.3.20',
    tagline: 'Fix allowlist overwrite - Preserve manually added accounts',
    date: '2025-10-31',
    changes: [
      { type: 'fix', text: 'Fix allowlist écrasée à chaque redéploiement Cloud Run - Les comptes ajoutés manuellement en prod survivent maintenant aux révisions' },
      { type: 'fix', text: 'Inversion ordre bootstrap auth: RESTORE depuis Firestore snapshot avant SEED depuis env pour préserver les données existantes' },
      { type: 'fix', text: 'Suppression sync prématuré dans _seed_allowlist_from_env() qui écrasait Firestore avant restoration' },
      { type: 'fix', text: 'Fix duplicate key "name" dans CURRENT_RELEASE (merge Codex foireux) qui faisait planter Vite build' },
    ]
  },
  {
    version: 'beta-3.3.19',
    tagline: 'Fix modal reprise + TTS toggle header + Voix par agent',
    date: '2025-10-31',
    changes: [
      { type: 'fix', text: 'Modal de reprise ne réapparaît plus après que l\'utilisateur ait fait son choix (nouvelle conversation ou reprendre)' },
      { type: 'fix', text: 'Événements auth:restored et auth:login:success n\'affichent plus le modal si un thread actif valide existe déjà' },
      { type: 'quality', text: 'Vérification thread valide dans _prepareConversationPrompt avant de réinitialiser les flags' },
      { type: 'quality', text: 'Logs de debug améliorés pour tracer les appels de modal de reprise' },
      { type: 'feature', text: 'Bouton toggle TTS dans header - Active/désactive la synthèse vocale des réponses (plus besoin de cliquer "Écouter" sur chaque message)' },
      { type: 'feature', text: 'Voix personnalisées par agent - Anima voix féminine (Rachel), Neo voix masculine jeune (Antoni), Nexus voix masculine posée (Josh)' },
      { type: 'feature', text: 'Auto-play silencieux - Les réponses des agents sont lues automatiquement quand TTS activé (pas de player audio visible)' },
      { type: 'quality', text: 'Mapping voice_id backend - API /api/voice/tts accepte agent_id optionnel pour sélectionner la voix ElevenLabs dynamiquement' },
      { type: 'fix', text: 'Suppression player audio flottant - Le lecteur visible en bas à droite qui ne disparaissait pas a été remplacé par audio invisible' },
    ]
  },
  {
    version: 'beta-3.3.18',
    tagline: 'Fix Voice DI container leak - Réutilise app.state container',
    date: '2025-10-31',
    changes: [
      { type: 'fix', text: 'Fix memory leak critique - Endpoint /api/voice/tts créait un nouveau ServiceContainer() à chaque appel au lieu de réutiliser app.state.service_container' },
      { type: 'fix', text: 'Sockets httpx leakés - Chaque requête TTS instanciait un nouveau httpx.AsyncClient jamais fermé par shutdown hook' },
      { type: 'quality', text: 'Pattern DI unifié - _ensure_voice_service_rest() utilise maintenant request.app.state.service_container comme le WebSocket' },
      { type: 'quality', text: 'Review Codex appliquée - Correctif suite à review de Codex GPT qui a détecté le leak avant merge' },
    ]
  },
  {
    version: 'beta-3.3.17',
    tagline: 'Fix Voice TTS - Auth token + SVG icon cohérent',
    date: '2025-10-31',
    changes: [
      { type: 'fix', text: 'Fix authentification TTS - Utilisait le mauvais nom de clé localStorage (\'authToken\' au lieu de \'emergence.id_token\'), causait erreur 401 Unauthorized' },
      { type: 'fix', text: 'Utilisation de getIdToken() - Import de la fonction auth officielle qui gère correctement le token JWT (sessionStorage + localStorage)' },
      { type: 'quality', text: 'Icône speaker cohérente - SVG refait avec stroke-linecap="round", stroke-linejoin="round", fill="none" pour matcher le design des autres icônes' },
      { type: 'fix', text: 'Fix Response format - Bypass api-client (qui parse JSON) pour appeler fetch() direct et récupérer Response brute nécessaire pour .blob()' },
    ]
  },
  {
    version: 'beta-3.3.16',
    tagline: 'Voice agents with ElevenLabs TTS - Listen to agent responses',
    date: '2025-10-31',
    changes: [
      { type: 'feature', text: 'Voix des agents avec ElevenLabs - Les messages d\'agents peuvent maintenant être écoutés via TTS (Text-to-Speech) de haute qualité' },
      { type: 'feature', text: 'Bouton Écouter sur chaque message - Un bouton speaker apparaît sur tous les messages d\'agents pour générer l\'audio à la demande' },
      { type: 'feature', text: 'Player audio flottant - Le player audio apparaît en bas à droite avec contrôles (play/pause/volume) pour une UX propre' },
      { type: 'feature', text: 'API REST TTS - Endpoint POST /api/voice/tts pour générer de l\'audio à partir de n\'importe quel texte (streaming MP3)' },
      { type: 'quality', text: 'Configuration ElevenLabs centralisée - Clés API, voice ID et model ID configurés via .env (eleven_multilingual_v2)' },
    ]
  },
  {
    version: 'beta-3.3.15',
    tagline: 'Large document upload timeout fix - Strict limits to prevent Cloud Run timeout',
    date: '2025-10-31',
    changes: [
      { type: 'fix', text: 'Upload gros documents résolu - Documents avec beaucoup de lignes causaient un timeout Cloud Run (limite 10 min) pendant parsing + chunking + vectorisation' },
      { type: 'quality', text: 'Limites strictes ajoutées - 50MB max par fichier, 5000 chunks max (rejet explicite si dépassement)' },
      { type: 'quality', text: 'Vectorisation optimisée - Limite réduite de 2048 à 1000 chunks pour rester sous le timeout' },
      { type: 'fix', text: 'Messages d\'erreur clairs - Frontend affiche maintenant le détail exact de l\'erreur serveur (taille fichier, nombre de chunks, etc.)' },
      { type: 'quality', text: 'Cleanup automatique - Si document rejeté pour taille excessive, le fichier et l\'entrée DB sont supprimés proprement' },
    ]
  },
  {
    version: 'beta-3.3.14',
    tagline: 'Production connectivity fixes - WebSocket auth & thread cleanup',
    date: '2025-10-30',
    changes: [
      { type: 'fix', text: 'WebSocket race condition résolue - Supprimé appel connect() prématuré dans handler auth:login qui causait "Aucun ID token" à la connexion' },
      { type: 'fix', text: 'Cleanup automatique threads 404 - localStorage nettoyé + nouveau thread ID stocké quand un thread n\'existe plus' },
      { type: 'quality', text: 'Amélioration robustesse auth - Le WebSocket attend maintenant que le token soit stocké avant de se connecter' },
      { type: 'fix', text: 'Fix version.js - Supprimé doublons CURRENT_RELEASE introduits par merge Codex' },
    ]
  },
  {
    version: 'beta-3.3.13',
    tagline: 'Auth token test bundler compatibility',
    date: '2025-10-30',
    changes: [
      { type: 'tests', text: 'Renommé la suite auth.normalize-token en .test.mjs pour s\'aligner sur les runners Node ESM et éviter que Vite traite les tests comme modules CommonJS.' },
      { type: 'fix', text: 'Mise à jour des références documentaires et scripts pour pointer vers le nouveau chemin du test.' },
      { type: 'quality', text: 'Validation build/test pour garantir la compatibilité Guardian et pipelines CI.' },
    ]
  },
  {
    version: 'beta-3.3.12',
    tagline: 'Auth session continuity',
    date: '2025-10-30',
    changes: [
      { type: 'fix', text: 'resetForSession() préserve auth.isAuthenticated lorsqu\'on garde la session active et le client WebSocket passe ce flag pour éviter les faux prompts de reconnexion.' },
      { type: 'fix', text: 'refreshSessionRole() réaffirme auth.hasToken et auth.isAuthenticated après chaque ping backend pour empêcher les déconnexions instantanées.' },
      { type: 'tests', text: 'Nouvelle suite node:test pour valider la normalisation des tokens (Bearer/token=/padding) et la purge des valeurs invalides.' },
      { type: 'fix', text: 'Chargement dynamique de rollup-plugin-visualizer en ESM afin que l\'analyse de bundle fonctionne avec Node >= 20.' },
      { type: 'quality', text: 'Gestion d\'erreur explicite lorsque le plugin est absent ou incompatible pour éviter les builds cassés en CI.' },
      { type: 'build', text: 'Configuration Vite convertie en fonction async pour ne pas impacter les builds standard hors analyse.' },
    ]
  },
  {
    version: 'beta-3.3.11',
    tagline: 'Auth handshake stabilization',
    date: '2025-10-30',
    changes: [
      { type: 'fix', text: 'Normalisation stricte des tokens (Bearer/token=/guillemets) avant stockage + purge des entrées invalides pour éviter les WebSocket 4401.' },
      { type: 'quality', text: 'StateManager expose désormais auth.isAuthenticated pour bloquer les prompts tant que l’auth n’est pas finalisée.' },
      { type: 'quality', text: 'Listener storage multi-onglets et badge auth synchronisés avec la nouvelle normalisation de token.' },
    ]
  },
  {
    version: 'beta-3.3.10',
    tagline: 'Sync script compatibility fix',
    date: '2025-10-30',
    changes: [
      { type: 'fix', text: 'scripts/sync_version.ps1 sait lire CURRENT_RELEASE et ne casse plus quand VERSION n’est plus un littéral.' },
      { type: 'quality', text: 'Le script liste précisément les fichiers mis à jour et respecte le mode dry-run sans bruit inutile.' },
      { type: 'tests', text: 'npm run build + npm test pour vérifier que la refactorisation n’impacte pas le front.' }
    ]
  },
  {
    version: 'beta-3.3.9',
    tagline: 'Version manifest merge fix',
    date: '2025-10-29',
    changes: [
      { type: 'fix', text: 'Corrige la fusion simultanée des fichiers de version qui cassait le build Vite suite à la duplication des clefs.' },
      { type: 'quality', text: 'Synchronisation des métadonnées de version frontend/backend + changelog remis en cohérence.' },
      { type: 'tests', text: 'Le build frontend repasse et protège contre les futures régressions de merge.' }
    ]
  },
  {
    version: 'beta-3.3.8',
    tagline: 'Document chunk throttling & warnings',
    date: '2025-10-29',
    changes: [
      { type: 'fix', text: 'Les uploads massifs gèrent désormais des milliers de paragraphes : vectorisation en lots, limite de chunks configurable et warning explicite plutôt qu’un 500.' },
      { type: 'quality', text: 'L’API documents retourne le nombre de chunks indexés et remonte un avertissement même lorsque l’upload réussit.' },
      { type: 'ux', text: 'Le module Documents affiche un toast d’avertissement quand la vectorisation est partielle, y compris après ré-indexation.' },
      { type: 'test', text: 'Nouveau test backend qui valide la limitation de chunks et le découpage en batchs d’indexation.' }
    ]
  },
  {
    version: 'beta-3.3.7',
    tagline: 'Document upload resilience & cross-agent routing',
    date: '2025-10-29',
    changes: [
      { type: 'fix', text: 'Les uploads et ré-indexations de documents restent possibles même lorsque le vector store est en READ-ONLY : statut “erreur” explicite et avertissement UI.' },
      { type: 'quality', text: 'Les avertissements de vectorisation sont stockés et renvoyés côté API/Frontend pour garder la trace des indexations partielles.' },
      { type: 'fix', text: 'Les réponses d’opinion restent dans la conversation de l’agent évalué avec fallback propre si la source est absente.' },
      { type: 'tests', text: 'Suite node:test mise à jour pour vérifier le bucket source lors des réponses d’opinion.' }
    ]
  },
  {
    version: 'beta-3.3.6',
    tagline: 'About module metrics refresh & genesis timeline fix',
    date: '2025-10-29',
    changes: [
      { type: 'quality', text: 'Module À propos : statistiques projet synchronisées (139 fichiers backend, 95 JS frontend, 503 tests Pytest, 48 dépendances Python, 10 packages Node, ~88k LOC actifs).' },
      { type: 'quality', text: 'Listes frontend/backend mises à jour pour refléter Benchmarks, Usage Analytics et Guardian.' },
      { type: 'quality', text: 'featuresDisplay s’appuie désormais sur la progression réelle (18/23 • 78%) et est utilisé côté documentation.' },
      { type: 'fix', text: 'Chronologie Genèse corrigée : premières expérimentations LLM datées 2022, plus 2024.' }
    ]
  },
  {
    version: 'beta-3.3.5',
    tagline: 'Setup Firestore Snapshot - Infrastructure Sync Allowlist Automatique',
    date: '2025-10-28',
    changes: [
      { type: 'quality', text: 'Firestore activé - Mode natif région europe-west1 pour backup persistant allowlist' },
      { type: 'quality', text: 'Service account dédié - firestore-sync@emergence-469005.iam.gserviceaccount.com avec rôles datastore.user + secretAccessor' },
      { type: 'quality', text: 'Cloud Run service account - Basculé de compute@developer vers firestore-sync pour accès Firestore natif' },
      { type: 'quality', text: 'Document Firestore initialisé - Collection auth_config/allowlist avec admin entry (gonzalefernando@gmail.com)' },
      { type: 'quality', text: 'Script init_firestore_snapshot.py - Outil pour vérifier/créer document Firestore initial' }
    ]
  },
  {
    version: 'beta-3.3.4',
    tagline: 'Fix Timing Pop-up - Affichage au Démarrage App (pas au mount module)',
    date: '2025-10-28',
    changes: [
      { type: 'fix', text: 'Fix pop-up n\'apparaît qu\'après 20 secondes - Déplacé logique de init() vers listener threads:ready pour affichage immédiat au démarrage' },
      { type: 'fix', text: 'Fix pop-up absent si on reste dans module Conversations - mount() appelé uniquement au switch vers Dialogue, maintenant géré dans init()' },
      { type: 'quality', text: 'Setup listener _setupInitialConversationCheck() - Écoute threads:ready + fallback timeout 3s pour afficher modal au démarrage app' },
      { type: 'quality', text: 'Flag _initialModalChecked - Évite double affichage modal (init() + mount()) via flag de contrôle' },
      { type: 'quality', text: 'Modal s\'affiche maintenant <3s après connexion - Indépendant du module actif, garantit UX cohérente au démarrage' }
    ]
  },
  {
    version: 'beta-3.3.3',
    tagline: 'Fix Pop-up Reprise - Modal Systématique + Centrage Correct',
    date: '2025-10-28',
    changes: [
      { type: 'fix', text: 'Fix pop-up qui n\'apparaît qu\'à la première connexion - mount() vérifie maintenant si thread valide chargé (pas juste si ID existe)' },
      { type: 'fix', text: 'Fix pop-up décalé visuellement à gauche - Modal TOUJOURS appendé à document.body pour centrage flexbox correct' },
      { type: 'quality', text: 'Validation robuste mount() - Vérifie thread valide (existe + messages chargés + pas archivé) avant skip modal' },
      { type: 'quality', text: 'Modal systématique reconnexion - Affichage même après archivage conversations + création nouvelle + reconnexion' }
    ]
  },
  {
    version: 'beta-3.3.2',
    tagline: 'Fix Critiques Routing/Session - Pop-up Reprise + Validation Threads Archivés',
    date: '2025-10-28',
    changes: [
      { type: 'fix', text: 'Fix pop-up reprise conversation manquant (bug critique) - TOUJOURS attendre events backend threads:ready avant affichage modal' },
      { type: 'fix', text: 'Fix routage messages vers mauvaise conversation - Validation thread existe dans state ET n\'est pas archivé (getCurrentThreadId)' },
      { type: 'fix', text: 'Fix conversations qui fusionnent bizarrement - Ne plus utiliser localStorage seul comme indicateur threads existants' },
      { type: 'fix', text: 'Fix race condition localStorage/state/backend - _waitForThreadsBootstrap supprime early return qui skippait attente events' },
      { type: 'quality', text: 'Validation robuste threads archivés - getCurrentThreadId() clear thread ID si thread archivé ou absent du state' },
      { type: 'quality', text: 'Logs debug améliorés - Console warnings quand thread archivé/obsolète détecté avec clearing automatique' },
      { type: 'quality', text: 'Protection frontend 3 niveaux - _hasExistingConversations(), _waitForThreadsBootstrap(), getCurrentThreadId() synchronisées' }
    ]
  },
  {
    version: 'beta-3.3.1',
    tagline: 'Fix Critiques BDD - Duplication Messages + Soft-Delete Archives',
    date: '2025-10-28',
    changes: [
      { type: 'fix', text: 'Fix duplication messages (bug critique) - Supprimé double envoi REST+WebSocket dans chat.js (ligne 926) qui créait 2-4 messages en BDD' },
      { type: 'fix', text: 'Protection backend anti-duplication - Ajout vérification message_id existant avant INSERT (queries.py ligne 1177-1189)' },
      { type: 'quality', text: 'Contrainte UNIQUE SQL - Migration 20251028_unique_messages_id.sql pour empêcher doublons au niveau base' },
      { type: 'fix', text: 'Fix effacement archives (bug critique) - Soft-delete par défaut sur threads au lieu de DELETE physique (récupérable)' },
      { type: 'quality', text: 'Soft-delete threads - Nouveau param hard_delete=False par défaut dans delete_thread() avec archival_reason' },
      { type: 'quality', text: 'Index SQL optimisés - Migration 20251028_soft_delete_threads.sql avec index archived_status + archived_at' },
      { type: 'quality', text: 'Audit complet BDD - Analyse schéma messages/threads, identification root causes duplication/effacement' }
    ]
  },
  {
    version: 'beta-3.2.2',
    tagline: 'Configuration Email Officielle - emergence.app.ch@gmail.com',
    date: '2025-10-27',
    changes: [
      { type: 'quality', text: 'Configuration email officielle - Compte emergence.app.ch@gmail.com configuré avec app password Gmail' },
      { type: 'quality', text: 'SMTP Gmail - smtp.gmail.com:587 avec TLS activé pour tous les emails (password reset, Guardian reports, beta invitations)' },
      { type: 'quality', text: 'Script de test email - scripts/test/test_email_config.py créé pour valider la configuration SMTP' },
      { type: 'quality', text: 'Documentation .env.example - Mise à jour avec la nouvelle configuration email officielle' },
      { type: 'fix', text: 'Fix encoding Windows - Correction du script de test pour supporter les emojis UTF-8 sur console Windows' }
    ]
  },
  {
    version: 'beta-3.2.1',
    tagline: 'Changelog Enrichi - 5 Dernières Révisions Détaillées',
    date: '2025-10-26',
    changes: [
      { type: 'feature', text: 'Changelog enrichi - Affichage détaillé des 5 dernières versions avec toutes les sections du CHANGELOG.md' },
      { type: 'feature', text: 'Sections complètes - Fonctionnalités, Corrections, Qualité, Impact, Fichiers modifiés pour chaque version' },
      { type: 'feature', text: 'Détails techniques - Descriptions longues, fichiers touchés, contexte complet pour chaque changement' },
      { type: 'quality', text: 'Nouvelles classes CSS - Styles pour sections détaillées, badges impact/files, items enrichis' },
      { type: 'quality', text: 'Export FULL_CHANGELOG - Structure JavaScript complète depuis CHANGELOG.md pour 5 dernières versions' },
      { type: 'fix', text: 'Fix critique orientation lock - Desktop landscape ne force plus le mode portrait sur écrans < 900px hauteur' }
    ]
  },
  {
    version: 'beta-3.2.0',
    tagline: 'Module À Propos avec Changelog Enrichi',
    date: '2025-10-26',
    changes: [
      { type: 'feature', text: 'Nouveau module "À propos" dans Paramètres - Affichage complet du changelog avec 13 versions' },
      { type: 'feature', text: 'Historique des versions enrichi - Classement par type (Phase, Nouveauté, Qualité, Performance, Correction)' },
      { type: 'feature', text: 'Modules installés - Vue d\'ensemble des 15 modules actifs avec versions' },
      { type: 'feature', text: 'Crédits complets - Informations développeur, technologies, écosystème Guardian' },
      { type: 'quality', text: 'Design glassmorphism moderne avec badges colorés et animations fluides' }
    ]
  },
  {
    version: 'beta-3.1.3',
    tagline: 'Temporal nDCG Metric + Chat Composer Guard',
    date: '2025-10-26',
    changes: [
      { type: 'feature', text: 'Métrique nDCG@k temporelle - Évalue qualité ranking avec pénalisation fraîcheur exponentielle' },
      { type: 'feature', text: 'Endpoint POST /api/benchmarks/metrics/ndcg-temporal - Calcul métrique à la demande' },
      { type: 'quality', text: 'BenchmarksService.calculate_temporal_ndcg() - Méthode helper pour intégrations futures' },
      { type: 'quality', text: 'Tests complets (18 tests) - Cas edge, décroissance temporelle, trade-offs, validation params' },
      { type: 'quality', text: 'Documentation formule DCG temporelle - Mesure impact boosts fraîcheur/entropie moteur ranking' },
      { type: 'fix', text: 'Dialogue mobile – Le composer reste accessible en mode portrait (offset bottom nav + sticky guard)' },
      { type: 'quality', text: 'Messages mobile – Padding dynamique pour éviter les zones mortes sous la barre de navigation' }
    ]
  },
  {
    version: 'beta-3.1.2',
    date: '2025-10-26',
    changes: [
      { type: 'quality', text: 'Refactor complet docs inter-agents - Fichiers séparés par agent (AGENT_SYNC_CLAUDE.md / AGENT_SYNC_CODEX.md)' },
      { type: 'quality', text: 'Nouvelle structure passation - Journaux séparés (passation_claude.md / passation_codex.md) avec rotation 48h stricte' },
      { type: 'quality', text: 'SYNC_STATUS.md - Vue d\'ensemble centralisée des activités multi-agents' },
      { type: 'quality', text: 'Résultat : Zéro conflit merge sur docs de sync, meilleure coordination agents' },
      { type: 'quality', text: 'Mise à jour prompts agents (CLAUDE.md, CODEV_PROTOCOL.md, CODEX_GPT_GUIDE.md)' }
    ]
  },
  {
    version: 'beta-3.1.1',
    date: '2025-10-26',
    changes: [
      { type: 'fix', text: 'Module Dialogue - L\'option "Reprendre" réapparaît dès que des conversations existent (attente bootstrap threads)' },
      { type: 'quality', text: 'Modal d\'accueil dynamique selon la disponibilité des conversations (mise à jour live du contenu)' }
    ]
  },
  {
    version: 'beta-3.1.0',
    date: '2025-10-26',
    changes: [
      { type: 'feature', text: 'Système de webhooks complet (P3.11) - Intégrations externes avec retry automatique' },
      { type: 'feature', text: 'Scripts de monitoring production (health check avec JWT auth)' },
      { type: 'quality', text: 'Mypy 100% clean - 471 erreurs corrigées (0 erreurs restantes)' },
      { type: 'fix', text: 'Cockpit - 3 bugs SQL critiques résolus (graphiques distribution)' },
      { type: 'fix', text: 'Module Documents - Layout desktop/mobile corrigé' },
      { type: 'fix', text: 'Module Chat - 4 bugs UI/UX critiques résolus (modal, scroll, routing)' },
      { type: 'perf', text: 'Bundle optimization - Lazy loading Chart.js, jsPDF, PapaParse' },
      { type: 'fix', text: 'Tests - 5 flaky tests corrigés (ChromaDB Windows + mocks RAG)' }
    ]
  },
  {
    version: 'beta-3.0.0',
    date: '2025-10-22',
    changes: [
      { type: 'phase', text: 'Phase P2 complétée - Admin & Sécurité (3/3 features)' },
      { type: 'feature', text: 'Système de permissions avancé' },
      { type: 'feature', text: 'Audit logs et traçabilité' }
    ]
  },
  {
    version: 'beta-2.2.0',
    date: '2025-10-20',
    changes: [
      { type: 'quality', text: 'Mypy 100% clean - 0 erreurs de type restantes' },
      { type: 'fix', text: 'Correction monitoring router - endpoints /ready et /metrics' }
    ]
  },
  {
    version: 'beta-2.1.5',
    date: '2025-10-19',
    changes: [
      { type: 'fix', text: 'Dashboard admin - Responsive mobile corrigé (graphiques et layout)' }
    ]
  },
  {
    version: 'beta-2.1.4',
    date: '2025-10-18',
    changes: [
      { type: 'fix', text: 'Production - Correction 404 sur /reset-password et /favicon.ico' }
    ]
  },
  {
    version: 'beta-2.1.3',
    date: '2025-10-17',
    changes: [
      { type: 'feature', text: 'Guardian - Rapports automatiques par email (SMTP intégré)' },
      { type: 'quality', text: 'Orchestration Guardian - Envoi automatique des rapports après audit' }
    ]
  },
  {
    version: 'beta-2.1.2',
    date: '2025-10-17',
    changes: [
      { type: 'fix', text: 'Synchronisation versioning - Production affiche maintenant la bonne version' },
      { type: 'fix', text: 'Bug password_must_reset - Fin de la boucle infinie de demande de reset' },
      { type: 'fix', text: 'Thread mobile - Chargement automatique au retour sur module chat' },
      { type: 'feature', text: 'Script PowerShell - Synchronisation automatique de version entre fichiers' }
    ]
  },
  {
    version: 'beta-2.0.0',
    date: '2025-10-15',
    changes: [
      { type: 'phase', text: 'Phase P1 complétée - UX Essentielle (3/3 features)' },
      { type: 'feature', text: 'Mémoire - Feedback temps réel consolidation avec barre de progression' },
      { type: 'fix', text: 'Mémoire - Détection questions temporelles et enrichissement contexte historique' },
      { type: 'quality', text: 'Documentation - Guide utilisateur beta + Guide QA mémoire' }
    ]
  },
  {
    version: 'beta-1.1.0',
    date: '2025-10-15',
    changes: [
      { type: 'feature', text: 'Archivage conversations - Toggle Actifs/Archivés avec compteurs' },
      { type: 'feature', text: 'Fonction de désarchivage - Restauration conversations depuis archives' },
      { type: 'quality', text: 'Menu contextuel adaptatif - Actions selon mode actif/archivé' }
    ]
  },
  {
    version: 'beta-1.0.0',
    date: '2025-10-15',
    changes: [
      { type: 'phase', text: 'Version bêta de référence - État initial documenté' },
      { type: 'feature', text: 'Système d\'authentification et gestion utilisateurs' },
      { type: 'feature', text: 'Chat multi-agents - 5 agents (Analyste, Généraliste, Créatif, Technique, Éthique)' },
      { type: 'feature', text: 'Centre Mémoire avec extraction de concepts' },
      { type: 'feature', text: 'Documentation interactive intégrée' },
      { type: 'feature', text: 'Métriques Prometheus activées par défaut' }
    ]
  }
];

/**
 * Changelog complet des 5 dernières versions
 * Contenu enrichi depuis CHANGELOG.md pour affichage détaillé dans le module À propos
 */
export const FULL_CHANGELOG = [
  {
    version: 'beta-3.3.6',
    date: '2025-10-29',
    title: 'Module À Propos — métriques synchronisées & genèse corrigée',
    description: 'Actualisation du module À propos avec statistiques techniques recalculées, progression alignée sur la roadmap et chronologie LLM mise à jour (premiers prototypes en 2022).',
    sections: [
      {
        type: 'quality',
        title: '✨ Mise à jour des informations techniques',
        items: [
          {
            title: 'Cartes modules synchronisées',
            description: 'Listes frontend/backend reflétant l’architecture actuelle (Benchmarks, Usage Analytics, Guardian, Voice) avec icônes harmonisées.',
            file: 'src/frontend/features/settings/settings-about.js'
          },
          {
            title: 'Statistiques projet rafraîchies',
            description: 'Affichage des compteurs réalistes (139 fichiers backend, 95 JS frontend, 503 tests, 48 packages Python, 10 packages Node, ~88k LOC) et date de premiers prototypes LLM (2022).',
            file: 'src/frontend/features/settings/settings-about.js'
          },
          {
            title: 'Hints & responsive grid',
            description: 'Nouvelle grille (min 200px) avec hints explicatifs pour chaque métrique technique.',
            file: 'src/frontend/features/settings/settings-about.css'
          }
        ]
      },
      {
        type: 'fixes',
        title: '🔧 Corrections',
        items: [
          {
            title: 'Progression 18/23 alignée',
            description: 'Le calcul completedFeatures utilise désormais la progression réelle (78%) et alimente directement featuresDisplay.',
            file: 'src/version.js'
          },
          {
            title: 'Version display unifié',
            description: 'Les écrans documentation consomment featuresDisplay (au lieu d’un recalcul par phase) pour éviter les divergences.',
            file: 'src/frontend/core/version-display.js'
          },
          {
            title: 'Chronologie Genèse corrigée',
            description: 'La documentation précise que les premières expérimentations LLM datent de 2022, pas de 2024.',
            file: 'docs/story-genese-emergence.md'
          }
        ]
      },
      {
        type: 'impact',
        title: '🎯 Impact',
        items: [
          'Transparence accrue sur l’état réel du code et des dépendances',
          'Progression produit cohérente avec la roadmap (18/23 • 78%)',
          'Narratif du projet réaligné avec l’historique réel des expérimentations IA'
        ]
      },
      {
        type: 'files',
        title: '📁 Fichiers Modifiés',
        items: [
          'src/frontend/features/settings/settings-about.js',
          'src/frontend/features/settings/settings-about.css',
          'src/frontend/core/version-display.js',
          'src/frontend/version.js',
          'src/version.js',
          'docs/story-genese-emergence.md',
          'CHANGELOG.md'
        ]
      }
    ]
  },
  {
    version: 'beta-3.2.1',
    date: '2025-10-26',
    title: 'Changelog Enrichi - 5 Dernières Révisions Détaillées',
    description: 'Amélioration majeure du module "À propos" avec affichage complet et détaillé des 5 dernières versions du changelog incluant toutes les sections, descriptions longues et fichiers modifiés.',
    sections: [
      {
        type: 'features',
        title: '🆕 Fonctionnalités Ajoutées',
        items: [
          {
            title: 'Changelog enrichi - Affichage détaillé complet',
            description: 'Affichage des 5 dernières versions avec toutes les sections complètes du CHANGELOG.md (Fonctionnalités, Corrections, Qualité, Impact, Fichiers modifiés)',
            file: 'src/frontend/features/settings/settings-about.js'
          },
          {
            title: 'Sections techniques détaillées',
            description: 'Pour chaque version : descriptions longues de chaque changement, fichiers touchés avec chemins, contexte complet technique et business, badges colorés par type de changement',
            file: 'src/frontend/features/settings/settings-about.js'
          },
          {
            title: 'Export FULL_CHANGELOG structuré',
            description: 'Nouvelle structure JavaScript complète exportée depuis CHANGELOG.md pour les 5 dernières versions, format réutilisable dans tout le frontend',
            file: 'src/version.js'
          }
        ]
      },
      {
        type: 'quality',
        title: '🧹 Améliorations Qualité',
        items: [
          {
            title: 'Nouvelles classes CSS pour sections enrichies',
            description: 'Styles dédiés pour sections détaillées (changelog-detailed-item, changelog-item-description), badges impact/files avec couleurs différenciées, mise en page optimisée pour longues descriptions',
            file: 'src/frontend/features/settings/settings-about.css'
          },
          {
            title: 'Méthodes de rendu améliorées',
            description: 'renderChangelogSection() gère maintenant sections simples et détaillées, renderChangelogSectionItems() avec support descriptions riches, groupement automatique par type de changement',
            file: 'src/frontend/features/settings/settings-about.js'
          }
        ]
      },
      {
        type: 'fixes',
        title: '🔧 Corrections',
        items: [
          {
            title: 'Fix bouton RAG dédoublé en Dialogue (mode desktop)',
            description: 'Correction du problème d\'affichage de 2 boutons RAG en mode desktop dans le module Dialogue. Ajout de !important et media query explicite @media (min-width: 761px) pour forcer le masquage du bouton mobile en desktop',
            file: 'src/frontend/styles/components/rag-power-button.css'
          },
          {
            title: 'Fix chevauchement tutos Dashboard/Config (page À propos)',
            description: 'Grid des tutos avec minmax(320px) trop étroit causait chevauchements entre 640px-720px de largeur. Augmentation du minmax de 320px à 380px pour éviter tout chevauchement des cartes tutoriels',
            file: 'src/frontend/features/documentation/documentation.css'
          },
          {
            title: 'Fix critique orientation lock desktop',
            description: 'Desktop landscape (écrans < 900px hauteur) ne force plus le mode portrait, media query corrigé pour détecter uniquement vrais mobiles (largeur <= 960px)',
            file: 'src/frontend/styles/overrides/mobile-menu-fix.css'
          }
        ]
      },
      {
        type: 'impact',
        title: '🎯 Impact',
        items: [
          'Transparence technique maximale - Utilisateurs voient TOUT le détail des évolutions',
          'Documentation vivante - Changelog complet accessible directement dans l\'app',
          'Traçabilité complète - Fichiers modifiés et contexte pour chaque changement',
          'UX moderne - Design enrichi avec sections organisées et badges colorés'
        ]
      },
      {
        type: 'files',
        title: '📁 Fichiers Modifiés',
        items: [
          'src/version.js - Ajout FULL_CHANGELOG enrichi (6 versions) + Fixes détaillés',
          'src/frontend/version.js - Synchronisation FULL_CHANGELOG',
          'src/frontend/features/settings/settings-about.js - Méthodes rendu détaillées',
          'src/frontend/features/settings/settings-about.css - Styles sections enrichies',
          'src/frontend/styles/components/rag-power-button.css - Fix bouton RAG dédoublé',
          'src/frontend/features/documentation/documentation.css - Fix grid tutos (380px)',
          'package.json - Version beta-3.2.1',
          'CHANGELOG.md - Entrée beta-3.2.1'
        ]
      }
    ]
  },
  {
    version: 'beta-3.2.0',
    date: '2025-10-26',
    title: 'Module À Propos avec Changelog Enrichi',
    description: 'Ajout d\'un module complet dédié à l\'affichage des informations de version, du changelog enrichi et des crédits du projet.',
    sections: [
      {
        type: 'features',
        title: '🆕 Fonctionnalités Ajoutées',
        items: [
          {
            title: 'Onglet "À propos" dans Paramètres',
            description: 'Navigation dédiée avec icône et description, intégration complète dans le module Settings',
            file: 'settings-main.js'
          },
          {
            title: 'Affichage Changelog Enrichi',
            description: 'Historique de 13 versions (de beta-1.0.0 à beta-3.2.0), classement automatique par type de changement (Phase, Nouveauté, Qualité, Performance, Correction), badges colorés pour chaque type avec compteurs, mise en évidence de la version actuelle',
            file: 'settings-about.js'
          },
          {
            title: 'Section Informations Système',
            description: 'Version actuelle avec badges (Phase, Progression, Fonctionnalités), grille d\'informations (Date build, Version, Phase, Progression), logo ÉMERGENCE avec design moderne',
            file: 'settings-about.js'
          },
          {
            title: 'Section Modules Installés',
            description: 'Affichage des 15 modules actifs, grille responsive avec icônes et versions, statut actif pour chaque module',
            file: 'settings-about.js'
          },
          {
            title: 'Section Crédits & Remerciements',
            description: 'Informations développeur principal, remerciements spéciaux (Marem ❤️), technologies clés avec tags interactifs, description écosystème Guardian, footer avec contact et copyright',
            file: 'settings-about.js'
          },
          {
            title: 'Design & UX',
            description: 'Style glassmorphism cohérent avec le reste de l\'application, animations fluides et transitions, responsive mobile/desktop, badges et tags colorés par catégorie',
            file: 'settings-about.css'
          }
        ]
      },
      {
        type: 'impact',
        title: '🎯 Impact',
        items: [
          'Transparence complète - Utilisateurs voient tout l\'historique des évolutions',
          'Documentation intégrée - Changelog accessible directement dans l\'app',
          'Crédits visibles - Reconnaissance du développement et des technologies',
          'UX moderne - Design glassmorphism avec animations et badges colorés'
        ]
      },
      {
        type: 'files',
        title: '📁 Fichiers modifiés',
        items: [
          'src/frontend/features/settings/settings-about.js (créé - 350 lignes)',
          'src/frontend/features/settings/settings-about.css (créé - 550 lignes)',
          'src/frontend/features/settings/settings-main.js (import module)',
          'src/version.js (version beta-3.2.0 + 13 versions historique)',
          'src/frontend/version.js (synchronisation)',
          'package.json (version beta-3.2.0)',
          'CHANGELOG.md (entrée beta-3.2.0)'
        ]
      }
    ]
  },
  {
    version: 'beta-3.1.3',
    date: '2025-10-26',
    title: 'Temporal nDCG Metric + Chat Composer Guard',
    description: 'Implémentation d\'une métrique d\'évaluation interne pour mesurer l\'impact des boosts de fraîcheur et entropie dans le moteur de ranking ÉMERGENCE V8.',
    sections: [
      {
        type: 'features',
        title: '✨ Nouvelle Fonctionnalité',
        items: [
          {
            title: 'Métrique nDCG@k temporelle (ndcg_time_at_k)',
            description: 'Formule : DCG^time@k = Σ (2^rel_i - 1) * exp(-λ * Δt_i) / log2(i+1). Pénalisation exponentielle selon la fraîcheur des documents. Paramètres configurables : k, T_days, lambda',
            file: 'src/backend/features/benchmarks/metrics/temporal_ndcg.py'
          },
          {
            title: 'Intégration dans BenchmarksService',
            description: 'Méthode helper : BenchmarksService.calculate_temporal_ndcg(). Import de la métrique dans features/benchmarks/service.py. Exposition pour réutilisation dans d\'autres services',
            file: 'src/backend/features/benchmarks/service.py'
          },
          {
            title: 'Endpoint API',
            description: 'POST /api/benchmarks/metrics/ndcg-temporal - Calcul métrique à la demande. Pydantic models pour validation : RankedItem, TemporalNDCGRequest. Retour JSON avec score nDCG@k + métadonnées',
            file: 'src/backend/features/benchmarks/router.py'
          },
          {
            title: 'Tests complets',
            description: '18 tests unitaires. Couverture : cas edge, décroissance temporelle, trade-offs pertinence/fraîcheur. Validation paramètres (k, T_days, lambda). Scénarios réalistes (recherche documents)',
            file: 'tests/backend/features/test_benchmarks_metrics.py'
          }
        ]
      },
      {
        type: 'fixes',
        title: '🔧 Corrections',
        items: [
          {
            title: 'Chat Mobile – Composer & Scroll',
            description: 'Décale le footer du chat au-dessus de la barre de navigation portrait pour garder la zone de saisie accessible. Ajoute un padding dynamique côté messages pour éviter les zones mortes sous la bottom nav sur iOS/Android',
            file: 'chat.css'
          }
        ]
      },
      {
        type: 'impact',
        title: '🎯 Impact',
        items: [
          'Quantification boosts fraîcheur - Mesure réelle impact ranking temporel',
          'Métrique réutilisable - Accessible via service pour benchmarks futurs',
          'API externe - Endpoint pour calcul à la demande',
          'Type-safe - Type hints complets + validation Pydantic'
        ]
      }
    ]
  },
  {
    version: 'beta-3.1.2',
    date: '2025-10-26',
    title: 'Refactor Documentation Inter-Agents',
    description: 'Résolution des conflits merge récurrents sur AGENT_SYNC.md et docs/passation.md (454KB !) lors de travail parallèle des agents.',
    sections: [
      {
        type: 'quality',
        title: '✨ Amélioration Qualité',
        items: [
          {
            title: 'Fichiers de synchronisation séparés',
            description: 'AGENT_SYNC_CLAUDE.md ← Claude Code écrit ici. AGENT_SYNC_CODEX.md ← Codex GPT écrit ici. SYNC_STATUS.md ← Vue d\'ensemble centralisée (index)',
            file: 'AGENT_SYNC_*.md, SYNC_STATUS.md'
          },
          {
            title: 'Journaux de passation séparés',
            description: 'docs/passation_claude.md ← Journal Claude (48h max, auto-archivé). docs/passation_codex.md ← Journal Codex (48h max, auto-archivé). docs/archives/passation_archive_*.md ← Archives >48h',
            file: 'docs/passation_*.md'
          },
          {
            title: 'Rotation stricte 48h',
            description: 'Anciennes entrées archivées automatiquement. Fichiers toujours légers (<50KB)',
            file: 'docs/archives/'
          }
        ]
      },
      {
        type: 'impact',
        title: '🎯 Résultat',
        items: [
          'Zéro conflit merge sur docs de synchronisation (fichiers séparés)',
          'Meilleure coordination (chaque agent voit clairement ce que fait l\'autre)',
          'Lecture rapide (SYNC_STATUS.md = 2 min vs 10 min avant)',
          'Rotation auto (passation.md archivé de 454KB → <20KB)'
        ]
      },
      {
        type: 'files',
        title: '📁 Fichiers modifiés',
        items: [
          'Créés: SYNC_STATUS.md, AGENT_SYNC_CLAUDE.md, AGENT_SYNC_CODEX.md',
          'Créés: docs/passation_claude.md, docs/passation_codex.md',
          'Archivé: docs/passation.md (454KB) → docs/archives/passation_archive_2025-10-01_to_2025-10-26.md',
          'Mis à jour: CLAUDE.md, CODEV_PROTOCOL.md, CODEX_GPT_GUIDE.md'
        ]
      }
    ]
  },
  {
    version: 'beta-3.1.1',
    date: '2025-10-26',
    title: 'Fix Modal Reprise Conversation',
    description: 'Correction du modal de reprise de conversation qui ne fonctionnait pas après connexion.',
    sections: [
      {
        type: 'fixes',
        title: '🔧 Corrections',
        items: [
          {
            title: 'Module Dialogue - Modal de reprise',
            description: 'Attente automatique du chargement des threads pour proposer l\'option « Reprendre » quand des conversations existent. Mise à jour dynamique du contenu du modal si les données arrivent après affichage',
            file: 'chat.js'
          }
        ]
      }
    ]
  },
  {
    version: 'beta-3.1.0',
    date: '2025-10-26',
    title: 'Webhooks + Health Check Scripts + Qualité',
    description: 'Système de webhooks complet (P3.11), scripts de monitoring production, Mypy 100% clean, corrections critiques Cockpit/Chat/Documents',
    sections: [
      {
        type: 'features',
        title: '🆕 Fonctionnalités Ajoutées',
        items: [
          {
            title: 'Système de Webhooks Complet (P3.11)',
            description: 'Endpoints REST /api/webhooks/* (CRUD + deliveries + stats). Événements: thread.created, message.sent, analysis.completed, debate.completed, document.uploaded. Delivery HTTP POST avec HMAC SHA256 pour sécurité. Retry automatique 3x avec backoff (5s, 15s, 60s). UI complète: Settings > Webhooks (modal, liste, logs, stats). Tables BDD: webhooks + webhook_deliveries (migration 010)',
            file: 'webhooks/router.py, settings-webhooks.js'
          },
          {
            title: 'Scripts de Monitoring Production',
            description: 'Script health check avec JWT auth (résout 403). Vérification endpoint /ready avec Bearer token. Métriques Cloud Run via gcloud (optionnel). Logs récents (20 derniers, optionnel). Rapport markdown auto-généré. Détection OS automatique (python/python3)',
            file: 'scripts/check-prod-health.ps1, scripts/README_HEALTH_CHECK.md'
          },
          {
            title: 'Système de Patch Notes',
            description: 'Patch notes centralisées dans src/version.js. Affichage automatique dans module "À propos" (Paramètres). Historique des 2 dernières versions visible. Icônes par type de changement (feature, fix, quality, perf, phase). Mise en évidence de la version actuelle',
            file: 'src/version.js, settings-main.js'
          }
        ]
      },
      {
        type: 'quality',
        title: '✨ Qualité & Performance',
        items: [
          {
            title: 'Mypy 100% Clean - Type Safety Complet',
            description: '471 erreurs mypy corrigées → 0 erreurs restantes. Type hints complets sur tout le backend Python. Strict mode mypy activé. Guide de style mypy intégré',
            file: 'docs/MYPY_STYLE_GUIDE.md'
          },
          {
            title: 'Bundle Optimization Frontend',
            description: 'Lazy loading: Chart.js, jsPDF, PapaParse. Réduction taille bundle initial. Amélioration temps de chargement page',
            file: 'vite.config.js'
          }
        ]
      },
      {
        type: 'fixes',
        title: '🔧 Corrections',
        items: [
          {
            title: 'Cockpit - 3 Bugs SQL Critiques',
            description: 'Bug SQL no such column: agent → agent_id. Filtrage session_id trop restrictif → session_id=None. Agents fantômes dans Distribution → whitelist stricte. Graphiques vides → fetch données + backend metrics',
            file: 'cockpit/router.py'
          },
          {
            title: 'Module Documents - Layout Desktop/Mobile',
            description: 'Fix layout foireux desktop et mobile. Résolution problèmes d\'affichage et scroll',
            file: 'documents.css'
          },
          {
            title: 'Module Chat - 4 Bugs UI/UX Critiques',
            description: 'Modal démarrage corrigé. Scroll automatique résolu. Routing réponses agents fixé. Duplication messages éliminée',
            file: 'chat.js'
          },
          {
            title: 'Tests - 5 Flaky Tests Corrigés',
            description: 'ChromaDB Windows compatibility. Mocks RAG améliorés. Stabilité suite de tests',
            file: 'tests/'
          }
        ]
      },
      {
        type: 'impact',
        title: '🎯 Impact Global',
        items: [
          '78% features complétées (18/23) - +4% vs beta-3.0.0',
          'Phase P3 démarrée (1/4 features done - P3.11 webhooks)',
          'Qualité code maximale (mypy 100% clean)',
          'Monitoring production automatisé',
          'Intégrations externes possibles via webhooks'
        ]
      }
    ]
  }
];

export default {
  currentRelease: CURRENT_RELEASE,
  version: VERSION,
  versionName: VERSION_NAME,
  versionDate: VERSION_DATE,
  buildPhase: BUILD_PHASE,
  completionPercentage: COMPLETION_PERCENTAGE,
  totalFeatures: TOTAL_FEATURES,

  // Detailed phase breakdown
  phases: {
    P0: { status: 'completed', features: 3, completion: 100 },
    P1: { status: 'completed', features: 3, completion: 100 },
    P2: { status: 'completed', features: 3, completion: 100 },
    P3: { status: 'in_progress', features: 4, completion: 25 }, // P3.11 webhooks done
    P4: { status: 'pending', features: 10, completion: 0 },
  },

  // Patch notes (newest first)
  patchNotes: PATCH_NOTES,

  /**
   * Get patch notes for current version
   * @returns {Object|null} Current version patch notes
   */
  getCurrentPatchNotes() {
    return this.patchNotes.find(note => note.version === VERSION) || null;
  },

  /**
   * Get patch notes formatted for display
   * @param {number} limit - Maximum number of versions to show
   * @returns {Array} Formatted patch notes
   */
  getFormattedPatchNotes(limit = 2) {
    return this.patchNotes.slice(0, limit);
  },

  // Display helpers
  get fullVersion() {
    return `${VERSION} - ${VERSION_NAME}`;
  },

  get shortVersion() {
    return VERSION;
  },

  get displayVersion() {
    return VERSION.replace('beta-', 'β');
  },

  // Feature count helpers
  get completedFeatures() {
    return Math.round((this.completionPercentage / 100) * this.totalFeatures);
  },

  get featuresDisplay() {
    return `${this.completedFeatures}/${this.totalFeatures}`;
  }
};
