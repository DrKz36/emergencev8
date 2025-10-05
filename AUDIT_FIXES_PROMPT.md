# Prompt pour Prochaine Instance : Corrections Audit ÉMERGENCE V8

**Date création** : 2025-10-05
**Audit source** : Audit complet Claude Code (Score: 87.5/100)
**Objectif** : Corriger les problèmes identifiés par priorité
**Durée estimée** : 4-6 heures

---

## 🎯 CONTEXTE

Un audit complet de l'application ÉMERGENCE V8 a identifié **13 problèmes** répartis en 3 niveaux de priorité :
- 🔴 **3 critiques** (bloquants production)
- 🟠 **6 majeurs** (qualité/maintenance)
- 🟢 **4 mineurs** (amélioration continue)

**Branche actuelle** : `main` (commit 8b8a182)
**Git remotes** : `origin` (HTTPS) + `codex` (SSH)
**Environnement** : Python 3.11 + Node 18+ + Windows/Linux

---

## 📋 LECTURE OBLIGATOIRE AVANT DE COMMENCER

**IMPORTANT** : Respecter le protocole multi-agents !

1. ✅ **Lire [AGENT_SYNC.md](AGENT_SYNC.md)** - État sync inter-agents
2. ✅ **Lire [docs/passation.md](docs/passation.md)** - 3 dernières entrées minimum
3. ✅ **Lire [AGENTS.md](AGENTS.md)** - Consignes générales (section 13 : codev)
4. ✅ **Lire [CODEV_PROTOCOL.md](CODEV_PROTOCOL.md)** - Protocole collaboration
5. ✅ **Vérifier `git status`** - Working tree propre avant modifications

---

## 🔴 PHASE 1 : CORRECTIONS CRITIQUES (Priorité Urgente - 2h)

### Problème 1.1 : Dépendance `httpx` Manquante ⚠️

**Fichier** : `requirements.txt`
**Ligne** : À ajouter après ligne 52 (section Monitoring)

**Diagnostic** :
- `httpx` utilisé dans `src/backend/core/containers.py:18` (import)
- `httpx` utilisé dans `src/backend/core/containers.py:395-398` (AsyncClient)
- **Absent** de `requirements.txt`
- Impact : Crash au démarrage backend en production

**Actions** :

```bash
# 1. Vérifier l'utilisation exacte
grep -r "import httpx" src/backend/
grep -r "httpx\." src/backend/

# 2. Éditer requirements.txt
```

**Modification** (`requirements.txt` ligne ~53) :

```diff
 # --- Monitoring ---
 prometheus-client>=0.20,<1
+httpx>=0.24,<1                   # Required by VoiceService (containers.py)
```

**Validation** :

```bash
# 3. Installer localement
pip install httpx

# 4. Vérifier import
python -c "import httpx; print(httpx.__version__)"

# 5. Relancer backend
pwsh -File scripts/run-backend.ps1

# 6. Vérifier logs startup (aucune erreur httpx)
```

**Tests** :

```bash
# 7. Tests backend complets
pytest tests/backend/ -v

# 8. Vérifier endpoints voice (si accessibles)
curl http://127.0.0.1:8000/api/health
```

---

### Problème 1.2 : Route API Fantôme `POST /api/debates/export` ⚠️

**Fichier doc** : `docs/architecture/30-Contracts.md:117`
**Fichier code** : `src/backend/features/debate/router.py`

**Diagnostic** :
- Route documentée dans contrats API
- **Non implémentée** dans le router debate
- Impact : Cassure du contrat API, confusion développeurs

**Décision requise** : Choisir Option A ou B

#### Option A : Implémenter la Route (Recommandé si feature nécessaire)

**Actions** :

```bash
# 1. Lire le router actuel
cat src/backend/features/debate/router.py

# 2. Identifier le service debate
cat src/backend/features/debate/service.py | grep "export\|to_json\|serialize"

# 3. Vérifier modèles
cat src/backend/features/debate/models.py
```

**Implémentation** (`src/backend/features/debate/router.py`) :

```python
# Ajouter après les routes existantes (ligne ~150+)

@router.post("/export")
async def export_debate(
    debate_id: str = Body(..., embed=True),
    format: str = Body("json", embed=True),  # json, markdown, pdf
    user_id: str = Depends(get_user_id),
    session_id: str = Depends(get_session_id),
    debate_service: DebateService = Depends(get_debate_service)
) -> Dict[str, Any]:
    """
    Export a debate in various formats.

    Args:
        debate_id: The debate ID to export
        format: Export format (json, markdown, pdf)
        user_id: User ID from auth
        session_id: Session ID from headers

    Returns:
        Exported debate data with download_url or inline content
    """
    try:
        # Récupérer le débat
        debate = await debate_service.get_debate(debate_id)
        if not debate:
            raise HTTPException(status_code=404, detail="Debate not found")

        # Export selon format
        if format == "json":
            export_data = debate.model_dump(mode="json")
            return {
                "format": "json",
                "debate_id": debate_id,
                "data": export_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        elif format == "markdown":
            # TODO: Implémenter formatage Markdown
            md_content = _format_debate_as_markdown(debate)
            return {
                "format": "markdown",
                "debate_id": debate_id,
                "content": md_content,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    except Exception as e:
        logger.error(f"Error exporting debate {debate_id}: {e}")
        raise HTTPException(status_code=500, detail="Export failed")

def _format_debate_as_markdown(debate) -> str:
    """Helper to format debate as markdown."""
    lines = [
        f"# Débat : {debate.topic}",
        f"\n**Date** : {debate.created_at}",
        f"\n**Participants** : {', '.join(debate.participants)}",
        f"\n## Tours de Débat\n"
    ]

    for turn in debate.turns:
        lines.append(f"### Tour {turn.turn_number} - {turn.agent}")
        lines.append(f"\n{turn.content}\n")

    if debate.synthesis:
        lines.append(f"\n## Synthèse Finale\n\n{debate.synthesis}\n")

    return "\n".join(lines)
```

**Tests** :

```bash
# 4. Créer test d'intégration
cat > tests/backend/features/test_debate_export.py << 'EOF'
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_export_debate_json(client: AsyncClient, mock_debate):
    """Test JSON export of debate."""
    response = await client.post(
        "/api/debates/export",
        json={"debate_id": "test-debate-123", "format": "json"},
        headers={"X-User-Id": "test-user", "X-Session-Id": "test-session"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "json"
    assert "data" in data
    assert data["debate_id"] == "test-debate-123"

@pytest.mark.asyncio
async def test_export_debate_markdown(client: AsyncClient, mock_debate):
    """Test Markdown export of debate."""
    response = await client.post(
        "/api/debates/export",
        json={"debate_id": "test-debate-123", "format": "markdown"},
        headers={"X-User-Id": "test-user", "X-Session-Id": "test-session"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "markdown"
    assert "content" in data
    assert "# Débat" in data["content"]
EOF

# 5. Lancer les tests
pytest tests/backend/features/test_debate_export.py -v
```

**Documentation** (`docs/architecture/30-Contracts.md:117`) :

```diff
 #### `POST /api/debates/export`

-**Description** : Exporte un débat (JSON, Markdown, PDF).
+**Description** : Exporte un débat dans différents formats.
+
+**Auth** : Requis (JWT)
+
+**Body** :
+```json
+{
+  "debate_id": "debate-uuid",
+  "format": "json"  // "json" | "markdown" | "pdf" (future)
+}
+```

 **Response 200** :
 ```json
 {
   "format": "json",
   "debate_id": "debate-uuid",
-  "download_url": "https://..."
+  "data": { /* debate object */ },
+  "timestamp": "2025-10-05T12:00:00Z"
 }
 ```
+
+**Response 404** : Debate not found
+**Response 400** : Invalid format
+**Response 500** : Export failed
```

#### Option B : Retirer de la Documentation (Si feature non nécessaire)

**Plus simple si l'export n'est pas planifié.**

**Actions** :

```bash
# 1. Éditer la doc
nano docs/architecture/30-Contracts.md
```

**Modification** (`docs/architecture/30-Contracts.md`) :

```diff
-#### `POST /api/debates/export`
-
-**Description** : Exporte un débat (JSON, Markdown, PDF).
-
-**Response 200** :
-```json
-{
-  "format": "json",
-  "debate_id": "debate-uuid",
-  "download_url": "https://..."
-}
-```
-
-**Response 404** : Debate not found.
```

**Ajouter note** :

```markdown
<!-- Feature export débats : reportée à Phase P3+ selon roadmap -->
```

**Validation** :

```bash
# 2. Grep pour s'assurer qu'aucune autre référence existe
grep -r "debates/export" docs/
grep -r "export.*debate" src/frontend/
```

---

### Problème 1.3 : Module Conversations Orphelin ⚠️

**Fichiers** :
- Module : `src/frontend/features/conversations/conversations.js` ✅ Existe
- Config : `src/frontend/core/app.js` ❌ Pas de référence

**Diagnostic** :
- Module complet documenté dans `docs/ui/conversations-module-refactor.md`
- Fichier source présent et fonctionnel
- **Non référencé** dans `app.js` (moduleLoaders + baseModules)
- Impact : Feature inaccessible par les utilisateurs

**Actions** :

```bash
# 1. Vérifier le module conversations
cat src/frontend/features/conversations/conversations.js | head -50

# 2. Identifier l'icône à utiliser
grep -A5 "baseModules" src/frontend/core/app.js

# 3. Lire la doc du module
cat docs/ui/conversations-module-refactor.md
```

**Modification 1** : `src/frontend/core/app.js` (ligne ~60, section moduleLoaders)

```diff
 const moduleLoaders = {
     chat: () => import('../features/chat/chat.js'),
+    conversations: () => import('../features/conversations/conversations.js'),
     documents: () => import('../features/documents/documents.js'),
     debate: () => import('../features/debate/debate.js'),
```

**Modification 2** : `src/frontend/core/app.js` (ligne ~96, section baseModules)

```diff
 const baseModules = [
     {
         id: 'chat',
         name: 'Dialogue',
         icon: '<svg>...</svg>'
     },
+    {
+        id: 'conversations',
+        name: 'Conversations',
+        icon: '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>'
+    },
     {
         id: 'documents',
         name: 'Documents',
         icon: '<svg>...</svg>'
     },
```

**Note icône** : SVG message-square de Lucide icons (cohérent avec le design)

**Validation** :

```bash
# 4. Build frontend
npm run build

# 5. Vérifier bundle
ls -lh dist/assets/conversations-*.js

# 6. Test manuel (lancer app)
npm run dev
# Ouvrir http://localhost:5173
# Vérifier sidebar : "Conversations" doit apparaître
# Cliquer dessus : module doit se charger
```

**Vérification fonctionnelle** :

- [ ] Module "Conversations" visible dans sidebar
- [ ] Clic charge le module (pas d'erreur console)
- [ ] Liste des threads s'affiche
- [ ] Bouton "Supprimer" fonctionne (avec confirmation)
- [ ] Sélection thread met à jour le chat

**Tests** :

```bash
# 7. Tests Node (si présents)
node --test src/frontend/features/conversations/__tests__/*.test.js
```

---

## 🟠 PHASE 2 : CORRECTIONS MAJEURES (Priorité Importante - 4h)

### Problème 2.1 : Constantes WebSocket Manquantes

**Fichier** : `src/frontend/shared/constants.js`
**Documentation** : `docs/architecture/30-Contracts.md` (lignes 36-57)

**Diagnostic** :
- 5 événements WebSocket documentés mais **absents** de constants.js
- Impact : Pas de typage/autocomplétion, handlers non implémentés

**Événements manquants** :

| Événement | Doc Ligne | Usage Attendu |
|-----------|-----------|---------------|
| `ws:auth_required` | 36 | Session révoquée/expirée |
| `ws:model_info` | 49 | Info modèle IA utilisé |
| `ws:model_fallback` | 50 | Notification fallback provider |
| `ws:memory_banner` | 51 | Banner mémoire enrichi |
| `ws:analysis_status` | 56 | Statut analyse mémoire temps réel |

**Actions** :

```bash
# 1. Lire constants actuels
cat src/frontend/shared/constants.js | grep "WS_"

# 2. Identifier pattern de nommage
```

**Modification** (`src/frontend/shared/constants.js`) :

```diff
 // WebSocket Events - Server → Client
 export const WS_SESSION_ESTABLISHED = 'ws:session_established';
 export const WS_SESSION_RESTORED = 'ws:session_restored';
+export const WS_AUTH_REQUIRED = 'ws:auth_required';
 export const WS_CHAT_STREAM_START = 'ws:chat_stream_start';
 export const WS_CHAT_STREAM_CHUNK = 'ws:chat_stream_chunk';
 export const WS_CHAT_STREAM_END = 'ws:chat_stream_end';
 export const WS_ERROR = 'ws:error';
+export const WS_MODEL_INFO = 'ws:model_info';
+export const WS_MODEL_FALLBACK = 'ws:model_fallback';
+export const WS_MEMORY_BANNER = 'ws:memory_banner';
+export const WS_ANALYSIS_STATUS = 'ws:analysis_status';
 export const WS_RAG_STATUS = 'ws:rag_status';
 export const WS_DEBATE_STATUS_UPDATE = 'ws:debate_status_update';
 export const WS_DEBATE_TURN_UPDATE = 'ws:debate_turn_update';
 export const WS_DEBATE_RESULT = 'ws:debate_result';
 export const WS_DEBATE_ENDED = 'ws:debate_ended';
```

**Implémentation Handlers** (`src/frontend/core/websocket.js`) :

```bash
# 3. Localiser les handlers actuels
grep -n "case WS_" src/frontend/core/websocket.js
```

**Ajouter handlers** (après ligne ~150+, dans `handleMessage`) :

```javascript
// Ajouter dans src/frontend/core/websocket.js

import {
    WS_AUTH_REQUIRED,
    WS_MODEL_INFO,
    WS_MODEL_FALLBACK,
    WS_MEMORY_BANNER,
    WS_ANALYSIS_STATUS
} from '../shared/constants.js';

// Dans handleMessage(event):

case WS_AUTH_REQUIRED:
    console.warn('[WebSocket] Auth required:', data);
    EventBus.emit(EVENTS.AUTH_REQUIRED, {
        reason: data.reason || 'session_expired',
        message: data.message
    });
    this.disconnect();
    break;

case WS_MODEL_INFO:
    console.log('[WebSocket] Model info:', data);
    EventBus.emit(EVENTS.MODEL_INFO_RECEIVED, {
        provider: data.provider,
        model: data.model,
        agent: data.agent
    });
    break;

case WS_MODEL_FALLBACK:
    console.warn('[WebSocket] Model fallback:', data);
    EventBus.emit(EVENTS.MODEL_FALLBACK, {
        from: data.from_provider,
        to: data.to_provider,
        reason: data.reason
    });
    // Toast notification
    if (window.showToast) {
        window.showToast(
            `Basculement vers ${data.to_provider} (${data.reason})`,
            'warning'
        );
    }
    break;

case WS_MEMORY_BANNER:
    console.log('[WebSocket] Memory banner:', data);
    EventBus.emit(EVENTS.MEMORY_BANNER_UPDATE, {
        type: data.type,  // 'concept_recall', 'topic_shift', etc.
        content: data.content,
        metadata: data.metadata
    });
    break;

case WS_ANALYSIS_STATUS:
    console.log('[WebSocket] Analysis status:', data);
    EventBus.emit(EVENTS.MEMORY_ANALYSIS_STATUS, {
        status: data.status,  // 'started', 'processing', 'completed'
        progress: data.progress,
        message: data.message
    });
    break;
```

**Ajouter événements EventBus** (`src/frontend/shared/constants.js`, section EVENTS) :

```diff
 export const EVENTS = {
     // Auth
     AUTH_REQUIRED: 'auth:required',
+    MODEL_INFO_RECEIVED: 'model:info',
+    MODEL_FALLBACK: 'model:fallback',

     // Chat
     CHAT_MESSAGE_SENT: 'chat:message:sent',

     // Memory
     MEMORY_BANNER_UPDATE: 'memory:banner:update',
+    MEMORY_ANALYSIS_STATUS: 'memory:analysis:status',
```

**Tests** :

```bash
# 4. Tests unitaires WebSocket
node --test src/frontend/core/__tests__/websocket.test.js

# 5. Test manuel : simuler événement WS
# Dans console navigateur :
window.simulateWsEvent = (type, data) => {
    const event = new MessageEvent('message', {
        data: JSON.stringify({ type, ...data })
    });
    // Déclencher handler
};

window.simulateWsEvent('ws:model_info', {
    provider: 'openai',
    model: 'gpt-4o-mini',
    agent: 'neo'
});
```

**Validation** :

- [ ] Build frontend passe (`npm run build`)
- [ ] Aucune erreur console au démarrage
- [ ] Événements WS loggés dans console
- [ ] Toast s'affiche pour fallback
- [ ] EventBus émet bien les événements

---

### Problème 2.2 : Services Backend Non Documentés

**Fichier** : `docs/architecture/10-Components.md`
**Services concernés** :
1. TimelineService (`src/backend/features/timeline/`)
2. VoiceService (`src/backend/features/voice/`)
3. MetricsRouter (`src/backend/features/metrics/`)

**Actions** :

```bash
# 1. Analyser chaque service
cat src/backend/features/timeline/service.py | head -100
cat src/backend/features/voice/service.py | head -100
cat src/backend/features/metrics/router.py

# 2. Vérifier README locaux
cat src/backend/features/voice/README.md
```

**Modification** (`docs/architecture/10-Components.md`) :

Ajouter section après les services existants (ligne ~200+) :

```markdown
### TimelineService

**Fichier** : `src/backend/features/timeline/service.py`
**Router** : `src/backend/features/timeline/router.py`
**Modèles** : `src/backend/features/timeline/models.py`

**Responsabilité** : Gestion de la chronologie des événements système.

**Fonctionnalités** :
- Enregistrement événements horodatés
- Filtrage par type/période
- Agrégation statistiques temporelles

**Endpoints** :
- `GET /api/timeline` - Liste événements
- `POST /api/timeline/event` - Enregistrer événement
- `GET /api/timeline/stats` - Statistiques

**État** : ⚠️ Service présent mais peu documenté, à auditer.

---

### VoiceService

**Fichier** : `src/backend/features/voice/service.py`
**Router** : `src/backend/features/voice/router.py`
**README** : `src/backend/features/voice/README.md`

**Responsabilité** : Interface audio (Speech-to-Text, Text-to-Speech).

**Fonctionnalités** :
- STT : Transcription audio → texte
- TTS : Synthèse texte → audio
- Intégration providers externes (OpenAI Whisper, Google Cloud Speech)

**Dépendances** :
- `httpx` (requêtes async vers APIs externes)
- `aiofiles` (gestion fichiers audio)

**Endpoints** :
- `POST /api/voice/transcribe` - Transcription audio
- `POST /api/voice/synthesize` - Génération audio

**État** : ✅ Service optionnel, activé si clés API configurées.

---

### MetricsRouter (Prometheus)

**Fichier** : `src/backend/features/metrics/router.py`

**Responsabilité** : Exposition métriques Prometheus pour observabilité.

**Fonctionnalités** :
- Endpoint `/api/metrics` (format Prometheus)
- Métriques applicatives (requêtes, latence, erreurs)
- Métriques métier (coûts LLM, tokens, débats)

**Dépendances** :
- `prometheus-client` (instrumentation)

**Endpoints** :
- `GET /api/metrics` - Export métriques Prometheus

**Intégration** :
```yaml
# Prometheus config
scrape_configs:
  - job_name: 'emergence-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
```

**État** : ✅ Activé en production Cloud Run.
```

**Validation** :

```bash
# 3. Vérifier liens internes
grep -n "TimelineService\|VoiceService\|MetricsRouter" docs/architecture/*.md

# 4. Rebuild docs (si générateur auto)
# (non applicable ici, docs markdown statiques)
```

---

### Problème 2.3 : Modules Frontend Non Documentés

**Fichier** : `docs/architecture/10-Components.md`
**Modules concernés** :
1. Timeline (`src/frontend/features/timeline/timeline.js`)
2. Costs (`src/frontend/features/costs/costs.js`)
3. Voice (`src/frontend/features/voice/voice.js`)
4. Preferences (`src/frontend/features/preferences/preferences.js`)

**Actions** :

```bash
# 1. Analyser chaque module
cat src/frontend/features/timeline/timeline.js | head -100
cat src/frontend/features/costs/costs.js | head -100
cat src/frontend/features/voice/voice.js | head -100
cat src/frontend/features/preferences/preferences.js | head -100

# 2. Vérifier README locaux
cat src/frontend/features/voice/README.md
```

**Modification** (`docs/architecture/10-Components.md`) :

Ajouter section "Modules Frontend Additionnels" (ligne ~400+) :

```markdown
## Modules Frontend Additionnels

### Timeline Module

**Fichier** : `src/frontend/features/timeline/timeline.js`
**Styles** : `src/frontend/features/timeline/timeline.css`

**Responsabilité** : Visualisation chronologique des événements.

**Fonctionnalités** :
- Affichage timeline interactive
- Filtrage par type/agent/période
- Liens vers conversations/documents

**Événements consommés** :
- `EVENTS.TIMELINE_UPDATE`

**État** : ⚠️ Module présent, intégration partielle.

---

### Costs Module

**Fichier** : `src/frontend/features/costs/costs.js`
**UI** : `src/frontend/features/costs/costs-ui.js`
**Styles** : `src/frontend/features/costs/costs.css`

**Responsabilité** : Visualisation détaillée des coûts LLM.

**Fonctionnalités** :
- Graphiques coûts par agent/provider
- Export CSV/JSON
- Filtrage temporel

**API** :
- `GET /api/dashboard/costs/summary`
- `GET /api/dashboard/costs/details`

**État** : ✅ Module autonome, complément au Cockpit.

---

### Voice Module

**Fichier** : `src/frontend/features/voice/voice.js`
**README** : `src/frontend/features/voice/README.md`

**Responsabilité** : Interface audio (micro, lecture).

**Fonctionnalités** :
- Enregistrement audio navigateur (MediaRecorder API)
- Upload → transcription STT
- Lecture synthèse TTS

**Dépendances backend** :
- `POST /api/voice/transcribe`
- `POST /api/voice/synthesize`

**État** : ✅ Module optionnel, activé si VoiceService configuré.

---

### Preferences Module

**Fichier** : `src/frontend/features/preferences/preferences.js`
**Styles** : `src/frontend/features/preferences/preferences.css`

**Responsabilité** : Configuration utilisateur (modèles, UI, notifications).

**Fonctionnalités** :
- Sélection modèles IA par agent
- Thème clair/sombre (future)
- Préférences RAG (seuils, nb docs)
- Notifications push

**Stockage** :
- LocalStorage (clé `emergence_preferences`)
- Sync backend (future, endpoint `/api/users/preferences`)

**État** : ✅ Module actif, référencé dans navigation.
```

**Validation** :

```bash
# 3. Vérifier cohérence avec app.js
grep -n "timeline\|costs\|voice\|preferences" src/frontend/core/app.js

# 4. Build frontend
npm run build
```

---

## 🟢 PHASE 3 : AMÉLIORATIONS MINEURES (Priorité Maintenance - 2h)

### Problème 3.1 : Doublons Tutorial.js / Tutorial.jsx

**Fichiers** :
- `src/frontend/components/tutorial/Tutorial.js` ✅ Utilisé
- `src/frontend/components/tutorial/Tutorial.jsx` ⚠️ Doublon ?

**Actions** :

```bash
# 1. Comparer les fichiers
diff src/frontend/components/tutorial/Tutorial.js src/frontend/components/tutorial/Tutorial.jsx

# 2. Rechercher imports
grep -r "Tutorial\.jsx" src/frontend/
grep -r "Tutorial\.js" src/frontend/

# 3. Vérifier package.json scripts
cat package.json | grep -A5 "scripts"
```

**Si Tutorial.jsx est obsolète** (aucune référence) :

```bash
# 4. Supprimer fichier obsolète
git rm src/frontend/components/tutorial/Tutorial.jsx

# 5. Commit
git add .
git commit -m "chore: remove obsolete Tutorial.jsx duplicate

- Tutorial.js is the active implementation
- Tutorial.jsx was legacy React attempt, no longer used
- No imports found in codebase"
```

**Si Tutorial.jsx est utilisé** (React port en cours) :

```bash
# 4. Documenter dans README
echo "## Migration React (en cours)

Tutorial.jsx : Port React du système tutoriel
Tutorial.js : Version vanilla JS (active)

Basculer vers React : mettre à jour imports dans settings-tutorial.js
" >> src/frontend/components/tutorial/README.md

# 5. Ajouter TODO
echo "- [ ] Finaliser migration Tutorial.js → Tutorial.jsx" >> TODO.md
```

---

### Problème 3.2 : Dépendance `marked` Sous-Utilisée

**Fichier** : `package.json`
**Usage** : 1 seul fichier (`src/frontend/features/debate/debate-ui.js`)

**Actions** :

```bash
# 1. Rechercher tous les usages
grep -r "import.*marked" src/frontend/
grep -r "marked\(" src/frontend/

# 2. Analyser le fichier concerné
cat src/frontend/features/debate/debate-ui.js | grep -A10 "marked"
```

**Si peu utilisé (1-2 fichiers)** :

**Option A** : Garder en dependencies (si critique pour débats)

```bash
# Rien à faire, conserver tel quel
```

**Option B** : Déplacer en devDependencies (si usage non-critique)

```diff
 {
   "dependencies": {
-    "marked": "^12.0.2"
   },
   "devDependencies": {
+    "marked": "^12.0.2",
     "concurrently": "^9.2.0",
```

**Option C** : Supprimer et remplacer par alternative native

```javascript
// Remplacer marked par solution native/inline dans debate-ui.js

// Avant :
import { marked } from 'marked';
const html = marked(markdownText);

// Après (si Markdown simple) :
const simpleMarkdownToHtml = (md) => {
    return md
        .replace(/^### (.*$)/gim, '<h3>$1</h3>')
        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
        .replace(/\*(.*)\*/gim, '<em>$1</em>')
        .replace(/\n/gim, '<br>');
};
```

**Recommandation** : Garder `marked` si débats utilisent Markdown riche, sinon déplacer en dev.

---

### Problème 3.3 : Documentation Tutorial Obsolète

**Fichier** : `docs/TUTORIAL_SYSTEM.md`
**Problème** : Numéros de lignes mentionnés ne correspondent plus au code

**Ligne 150** :
> `settings-main.js` - Intégration (lignes 9, 19, 89-96, 121-125, 905-907)

**Actions** :

```bash
# 1. Lire settings-main.js actuel
cat src/frontend/features/settings/settings-main.js | wc -l
# Vérifier nombre total de lignes

# 2. Rechercher références tutorial
grep -n "tutorial\|Tutorial" src/frontend/features/settings/settings-main.js
```

**Modification** (`docs/TUTORIAL_SYSTEM.md:150`) :

```diff
 ### Settings Module

-- `src/frontend/features/settings/settings-main.js` - Intégration (lignes 9, 19, 89-96, 121-125, 905-907)
+- `src/frontend/features/settings/settings-main.js` - Intégration module tutoriel
+  - Import : ligne ~9
+  - Loader : ligne ~19
+  - Navigation : lignes ~89-96
+  - Render : lignes ~121-125
+  - Init : lignes ~905-907
+  - **Note** : Numéros de lignes approximatifs, code sujet à évolution
```

**Validation** :

```bash
# 3. Vérifier autres références obsolètes
grep -n "ligne [0-9]" docs/TUTORIAL_SYSTEM.md
```

**Amélioration future** :

```bash
# 4. Ajouter note en en-tête du fichier
```

Ajouter en haut de `docs/TUTORIAL_SYSTEM.md` :

```markdown
> **Note** : Les numéros de lignes mentionnés dans ce document sont **approximatifs** et peuvent varier selon les évolutions du code. Utilisez-les comme repères, pas comme références exactes. Privilégiez la recherche par mot-clé (`grep`, Ctrl+F).
```

---

### Problème 3.4 : Fichier `docs/git-workflow.md` Manquant

**Référence** : `CODEX_SYNC_UPDATE_PROMPT.md` suggère de créer ce fichier
**Statut** : Non créé

**Actions** :

```bash
# 1. Vérifier si existe
ls -la docs/git-workflow.md

# 2. Lire le prompt Codex
cat CODEX_SYNC_UPDATE_PROMPT.md | grep -A50 "git-workflow.md"
```

**Création** (`docs/git-workflow.md`) :

Reprendre le contenu suggéré dans `CODEX_SYNC_UPDATE_PROMPT.md` (lignes 162-350) :

```bash
# 3. Copier template depuis prompt
cat > docs/git-workflow.md << 'EOF'
# Git Workflow - Émergence V8

## Vue d'Ensemble

Ce projet utilise un workflow **feature branch + squash merge** :
1. Créer une branche feature depuis `main`
2. Développer + commits atomiques
3. Push + créer PR sur GitHub
4. Review + merge squash dans `main`
5. Nettoyer la branche feature

## 1. Créer une Feature Branch

```bash
# Toujours partir de main à jour
git checkout main
git pull origin main

# Créer et basculer sur la nouvelle branche
git checkout -b fix/descriptive-name-YYYYMMDD-HHMM
# Exemple: fix/debate-chat-ws-events-20250915-1808
```

**Convention de nommage** :
- `fix/` : corrections de bugs
- `feat/` : nouvelles fonctionnalités
- `docs/` : documentation uniquement
- `chore/` : maintenance, refactoring

[... copier le reste du template depuis CODEX_SYNC_UPDATE_PROMPT.md ...]
EOF
```

**Validation** :

```bash
# 4. Vérifier création
cat docs/git-workflow.md | head -20

# 5. Ajouter référence dans README
grep -n "Git" README.md
```

**Modification** (`README.md`, section workflow) :

```diff
 ## Git workflow and branch hygiene

+**Documentation complète** : [Git Workflow](docs/git-workflow.md)
+
 1. Start on a clean tree: `git status` should report no changes.
```

---

## 📦 VALIDATION FINALE & TESTS

### Checklist Avant Commit

Après avoir appliqué **toutes** les corrections :

**Backend** :

```bash
# 1. Installer dépendances mises à jour
pip install -r requirements.txt

# 2. Tests backend
pytest tests/backend/ -v --tb=short

# 3. Linters
ruff check src/backend/
mypy src/backend/ --ignore-missing-imports

# 4. Démarrer backend
pwsh -File scripts/run-backend.ps1
# Vérifier logs : aucune erreur httpx, imports OK
```

**Frontend** :

```bash
# 5. Build frontend
npm run build
# ✓ built in XXXms

# 6. Vérifier bundles
ls -lh dist/assets/*.js | grep conversations

# 7. Tests frontend
node --test src/frontend/**/__tests__/*.test.js
```

**Documentation** :

```bash
# 8. Vérifier liens internes
grep -n "](.*\.md)" docs/*.md | grep -v "http"
# Tous les liens doivent pointer vers fichiers existants

# 9. Vérifier TODO
cat TODO.md
```

**Smoke Tests** :

```bash
# 10. Lancer app localement
npm run dev
# Ouvrir http://localhost:5173

# 11. Vérifier manuellement :
# - Module Conversations visible et fonctionnel
# - Événements WS loggés dans console
# - Aucune erreur 404/500 côté backend
# - Endpoints documentés répondent (ou 404 si retirés)
```

---

## 📝 COMMIT & PASSATION

### Template Commit

**Si toutes corrections Phase 1-3 appliquées** :

```bash
git add -A
git commit -m "fix: apply audit corrections (critical + major + minor)

**Phase 1 - Critical**
- Add missing httpx dependency (VoiceService requirement)
- Implement POST /api/debates/export endpoint (OR remove from docs)
- Reference conversations module in app.js navigation

**Phase 2 - Major**
- Add 5 missing WebSocket event constants + handlers
- Document TimelineService, VoiceService, MetricsRouter in architecture
- Document Timeline, Costs, Voice, Preferences frontend modules

**Phase 3 - Minor**
- Remove Tutorial.jsx duplicate (or document React migration)
- Audit marked dependency usage (keep/move/remove decision)
- Update TUTORIAL_SYSTEM.md with approximate line numbers
- Create docs/git-workflow.md (from CODEX_SYNC_UPDATE_PROMPT template)

**Tests**
- ✅ Backend tests pass (pytest)
- ✅ Frontend build succeeds (npm run build)
- ✅ Conversations module accessible
- ✅ WS events handlers functional
- ✅ Documentation links valid

**Audit Score** : 87.5/100 → 95+/100 (estimated)

Resolves audit findings from 2025-10-05 Claude Code session.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Si corrections partielles** :

Adapter le message en listant uniquement les phases complétées.

### Passation dans `docs/passation.md`

**Ajouter entrée** :

```markdown
## [YYYY-MM-DD HH:MM] — Agent: Claude Code

### Fichiers modifiés
- `requirements.txt` (ajout httpx)
- `src/backend/features/debate/router.py` (implement export OU aucun si retiré de doc)
- `docs/architecture/30-Contracts.md` (update debates/export)
- `src/frontend/core/app.js` (add conversations module)
- `src/frontend/shared/constants.js` (add 5 WS event constants)
- `src/frontend/core/websocket.js` (add WS event handlers)
- `docs/architecture/10-Components.md` (document 3 backend services + 4 frontend modules)
- `src/frontend/components/tutorial/Tutorial.jsx` (removed duplicate)
- `docs/TUTORIAL_SYSTEM.md` (update line references)
- `docs/git-workflow.md` (created from template)
- `docs/passation.md` (cette entrée)

### Contexte
Application des corrections identifiées lors de l'audit complet du 2025-10-05.
Score audit initial : 87.5/100 (3 critiques, 6 majeurs, 4 mineurs).
Objectif : Corriger priorités P1-P3 pour atteindre ~95/100.

### Actions réalisées

**Phase 1 - Corrections Critiques** :
1. ✅ Ajout `httpx>=0.24,<1` dans requirements.txt (ligne 53)
2. ✅ Implémentation `POST /api/debates/export` (JSON + Markdown) OU retrait de la doc
3. ✅ Référencement module conversations (app.js moduleLoaders + baseModules)

**Phase 2 - Corrections Majeures** :
4. ✅ Ajout 5 constantes WS (auth_required, model_info, model_fallback, memory_banner, analysis_status)
5. ✅ Implémentation handlers WebSocket correspondants (websocket.js)
6. ✅ Documentation TimelineService, VoiceService, MetricsRouter (10-Components.md)
7. ✅ Documentation modules frontend (Timeline, Costs, Voice, Preferences)

**Phase 3 - Améliorations Mineures** :
8. ✅ Nettoyage Tutorial.jsx (supprimé OU documenté migration React)
9. ✅ Audit dépendance `marked` (décision : conservé/déplacé/remplacé)
10. ✅ Mise à jour doc tutoriel (ligne numbers → approximatifs)
11. ✅ Création docs/git-workflow.md (template workflow complet)

### Tests
- ✅ `pytest tests/backend/ -v` (tous tests passent)
- ✅ `npm run build` (build succès, bundle conversations présent)
- ✅ Smoke test backend : endpoints répondent, aucune erreur httpx
- ✅ Smoke test frontend : module conversations accessible, WS events loggés
- ✅ `ruff check` + `mypy` (backend propre)

### Prochaines actions recommandées
1. **QA manuelle approfondie** : Tester tous les modules ajoutés/corrigés en conditions réelles
2. **Tests intégration WS** : Valider handlers model_info/fallback/memory_banner avec backend réel
3. **Export débats** : Tester endpoint `/api/debates/export` avec débats réels (si implémenté)
4. **Documentation visuelle** : Ajouter captures d'écran module Conversations
5. **Monitoring** : Vérifier métriques Prometheus exposées correctement
6. **Déploiement Cloud Run** : Rebuild image Docker + déploiement révision test
7. **Audit de suivi** : Re-run audit dans 1 semaine pour valider score ~95/100

### Blocages
Aucun.

### Notes
- Décision export débats : [SPÉCIFIER ICI : implémenté OU retiré de doc]
- Décision marked : [SPÉCIFIER ICI : conservé/déplacé/remplacé]
- Décision Tutorial.jsx : [SPÉCIFIER ICI : supprimé OU migration React en cours]
```

### Mise à Jour AGENT_SYNC.md

**Modifier section "Zones de travail en cours"** :

```diff
 ### Claude Code (moi)
-- **Statut** : Setup config collaboration + tone casual
+- **Statut** : Corrections audit complet (Phase 1-3 terminées)
 - **Fichiers touchés** :
-  - `.claude/settings.local.json` (permissions all + env vars)
-  - `AGENT_SYNC.md` (ce fichier)
-- **Prochain chantier** : Intégration instructions + update AGENTS.md
+  - `requirements.txt` (httpx)
+  - `src/backend/features/debate/router.py` (export)
+  - `src/frontend/core/app.js` (conversations)
+  - `src/frontend/shared/constants.js` + `websocket.js` (WS events)
+  - `docs/architecture/10-Components.md` (services/modules)
+  - `docs/git-workflow.md` (création)
+- **Prochain chantier** : QA manuelle + déploiement Cloud Run
```

---

## 🎯 RÉSUMÉ EXÉCUTIF

### Ce qui doit être fait

**Phase 1 (Critique - 2h)** :
1. Ajouter `httpx` à requirements.txt
2. Implémenter `POST /api/debates/export` OU retirer de la doc
3. Référencer module conversations dans app.js

**Phase 2 (Majeur - 4h)** :
4. Ajouter 5 constantes WebSocket + handlers
5. Documenter 3 services backend manquants
6. Documenter 4 modules frontend manquants

**Phase 3 (Mineur - 2h)** :
7. Nettoyer Tutorial.jsx
8. Auditer `marked`
9. Mettre à jour doc tutoriel
10. Créer docs/git-workflow.md

### Livrables attendus

- ✅ Code fonctionnel (backend + frontend)
- ✅ Tests passants (pytest + npm test)
- ✅ Build succès (npm run build)
- ✅ Documentation à jour
- ✅ Commit atomique avec message détaillé
- ✅ Entrée passation complète
- ✅ AGENT_SYNC.md mis à jour

### Score cible

**Avant** : 87.5/100 (3 critiques, 6 majeurs, 4 mineurs)
**Après** : ~95/100 (tous problèmes P1-P3 résolus)

---

**Prompt créé** : 2025-10-05
**Audit source** : Claude Code audit complet
**Durée estimée** : 4-6 heures
**Difficulté** : Moyenne (suivre instructions détaillées)

🚀 Bon courage pour les corrections !
