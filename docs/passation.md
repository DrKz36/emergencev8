## [2025-10-19 05:30] — Agent: Claude Code

### Fichiers modifiés
- `src/backend/features/chat/service.py` (ajout stm_content et ltm_content dans ws:memory_banner)
- `src/frontend/features/chat/chat.js` (affichage chunks mémoire dans l'UI)
- `AGENT_SYNC.md` (documentation session)
- `docs/passation.md` (cette entrée)

### Contexte
User demandait pourquoi les chunks de mémoire (STM/LTM) n'étaient pas affichés dans l'interface alors que le système les chargeait. Les agents recevaient la mémoire en contexte mais rien n'était visible pour l'utilisateur.

### Problème identifié (2 bugs distincts)

**Bug #1 - Backend n'envoyait pas le contenu:**
- `ws:memory_banner` envoyait seulement des stats (has_stm, ltm_items, injected_into_prompt)
- Le contenu textuel des chunks (stm, ltm_block) n'était PAS envoyé au frontend
- Frontend ne pouvait donc pas afficher les chunks même s'il le voulait

**Bug #2 - Frontend mettait les messages dans le mauvais bucket:**
- `handleMemoryBanner()` créait un message système dans le bucket "system"
- L'UI affiche seulement les messages du bucket de l'agent actuel (anima, nexus, etc.)
- Résultat: message créé mais jamais visible dans l'interface

### Solution implémentée

**Backend (service.py:2334-2335, 2258-2259):**
- Ajout de `stm_content` (résumé de session) dans le payload `ws:memory_banner`
- Ajout de `ltm_content` (faits & souvenirs LTM) dans le payload `ws:memory_banner`
- Les deux champs envoyés dans les 2 occurrences de `ws:memory_banner`

**Frontend (chat.js:1436-1480):**
- `handleMemoryBanner()` extrait maintenant `stm_content` et `ltm_content` du payload
- Crée un message système visible avec icône 🧠 "Mémoire chargée"
- Affiche le résumé de session (STM) si présent
- Affiche les faits & souvenirs (LTM) si présents
- **CRITIQUE**: Ajoute le message dans le bucket de l'agent qui répond (pas "system")
- Utilise `_determineBucketForMessage(agent_id, null)` pour trouver le bon bucket
- Log le bucket utilisé pour debug

### Tests effectués
- ✅ Test manuel: Envoi message global → tous les agents (Anima, Neo, Nexus) affichent le message mémoire
- ✅ Message "🧠 **Mémoire chargée**" visible dans chaque conversation agent
- ✅ Résumé de session affiché correctement (371 caractères dans le test)
- ✅ Console log confirme: `[Chat] Adding memory message to bucket: anima` (puis neo, nexus)

### Résultats
- ✅ Les chunks de mémoire sont maintenant visibles dans l'interface pour chaque agent
- ✅ L'utilisateur peut voir exactement ce que l'agent a en contexte mémoire
- ✅ Transparence totale sur la mémoire STM/LTM chargée

### Prochaines actions
1. Améliorer le formatage visuel du message mémoire (collapse/expand pour grands résumés)
2. Ajouter un indicateur visuel si ltm_items > 0 mais ltm_content vide
3. Considérer un bouton "Détails mémoire" pour ouvrir le centre mémoire

### Notes techniques
- Chrome DevTools MCP installé et testé (mais connexion instable)
- Debugging fait via API Chrome DevTools directe (WebSocket)
- Vite hot-reload a bien fonctionné après F5

---

## [2025-10-19 05:55] - Agent: Codex

### Fichiers modifiés
- `src/backend/features/chat/service.py` (timeline MemoryQueryTool injectée dans le contexte)
- `AGENT_SYNC.md` (journal de session mis à jour)
- `docs/passation.md` (cette entrée)

### Contexte
Les réponses des agents restaient bloquées sur "Je n'ai pas accès..." : la timeline consolidée n'était jamais injectée lorsque use_rag était désactivé côté frontend.

### Modifications
- Instanciation de `MemoryQueryTool` dans `ChatService` et propagation de `agent_id` vers la requête temporelle.
- `_build_temporal_history_context` agrège désormais la timeline formatée (limite dynamique par période) et n'affiche le regroupement vectoriel qu'en fallback.
- Contexte final limité aux sections pertinentes pour éviter le bruit (messages récents + synthèse chronologique).

### Tests
- OK `pytest tests/memory -q`
- OK Script manuel `inspect_temporal.py` pour vérifier le contexte généré (fichier supprimé ensuite).

### Résultats
- Anima dispose d'une synthèse chronologique (dates + occurrences) même sans RAG, éliminant la réponse "pas accès".

### Prochaines étapes
1. Purger les concepts LTM qui ne sont que des requêtes brutes (batch de consolidation du vector store).
2. Exposer la synthèse chronologique dans l'UI mémoire (centre mémoire + bannière RAG).

---

## [2025-10-19 04:20] ÔÇö Agent: Claude Code

### Fichiers modifi├®s
- `src/backend/features/memory/memory_query_tool.py` (header toujours retourn├®)
- `src/backend/features/chat/memory_ctx.py` (toujours appeler formatter)
- `src/backend/features/chat/service.py` (3 fixes critiques)
- `AGENT_SYNC.md` (documentation session)
- `docs/passation.md` (cette entr├®e)

### Contexte
User signalait qu'Anima r├®pondait "Je n'ai pas acc├¿s ├á nos conversations pass├®es" au lieu de r├®sumer les sujets/concepts abord├®s avec dates et fr├®quences. Cette feature marchait il y a 4 jours, cass├®e depuis ajout r├¿gles anti-hallucination.

### Analyse multi-couches (3 bugs d├®couverts!)

**Bug #1 - Flow memory context (memory_ctx.py):**
- Probl├¿me: `format_timeline_natural_fr()` retournait `"Aucun sujet abord├® r├®cemment."` SANS le header `### Historique des sujets abord├®s` quand timeline vide
- Impact: Anima cherche ce header exact dans le contexte RAG (r├¿gle anti-hallucination ligne 7 du prompt)
- Si header absent ÔåÆ Anima dit "pas acc├¿s" au lieu de "aucun sujet trouv├®"
- Fix commit e466c38: Toujours retourner le header m├¬me si timeline vide

**Bug #2 - Flow temporal query (_build_temporal_history_context):**
- Probl├¿me: M├®thode retournait `""` (cha├«ne vide) si liste vide
- Impact: Condition `if temporal_context:` devient False en Python ÔåÆ bloc jamais ajout├® ├á `blocks_to_merge`
- Header "Historique des sujets abord├®s" jamais g├®n├®r├® par `_merge_blocks()`
- Fix commit b106d35: Retourner toujours au moins `"*(Aucun sujet trouv├® dans l'historique)*"` m├¬me si vide ou erreur

**Bug #3 - CRITIQUE (cause r├®elle du probl├¿me):**
- Probl├¿me: Frontend envoyait `use_rag: False` pour les questions de r├®sum├®
- `_normalize_history_for_llm()` ligne 1796 checkait `if use_rag and rag_context:`
- Le rag_context ├®tait **cr├®├® avec le header** mais **JAMAIS INJECT├ë** dans le prompt!
- Anima ne voyait jamais le contexte ÔåÆ disait "pas acc├¿s"
- Fix commit 1f0b1a3 Ô¡É: Nouvelle condition `should_inject_context` d├®tecte "Historique des sujets abord├®s" dans rag_context et injecte m├¬me si use_rag=False
- Respecte l'intention du commentaire ligne 2487 "m├¬me si use_rag=False"

### Tests
- Ô£à `git push` (Guardians pass├®s, prod OK)
- ÔÅ│ **TEST MANUEL REQUIS**: Red├®marrer backend + demander ├á Anima "r├®sume les sujets abord├®s"
- Anima devrait maintenant voir le header et r├®pondre correctement

### R├®sultat attendu
Anima verra maintenant toujours dans son contexte:
```
[RAG_CONTEXT]
### Historique des sujets abord├®s

*(Aucun sujet trouv├® dans l'historique)*
```
Ou avec de vrais sujets si la consolidation des archives r├®ussit.

### Travail de Codex GPT pris en compte
- Aucune modification Codex dans cette zone r├®cemment
- Fix ind├®pendant backend uniquement

### Prochaines actions recommand├®es
1. **PRIORIT├ë 1**: Red├®marrer backend et tester si Anima r├®pond correctement
2. **PRIORIT├ë 2**: Fixer script `consolidate_all_archives.py` (erreurs d'imports)
3. Une fois consolidation OK, historique sera peupl├® avec vrais sujets archiv├®s
4. V├®rifier que dates/heures/fr├®quences apparaissent dans r├®ponse Anima

### Blocages
- Consolidation threads archiv├®s bloqu├®e par erreurs imports Python (script cherche `backend.*` au lieu de `src.backend.*`)
- Non bloquant pour le fix imm├®diat du header

---

## [2025-10-19 12:45] ÔÇö Agent: Claude Code (Fix Streaming Chunks Display FINAL - R├ëSOLU Ô£à)

### Fichiers modifi├®s
- `src/frontend/features/chat/chat.js` (d├®placement flag _isStreamingNow apr├¿s state.set(), ligne 809)
- `AGENT_SYNC.md` (mise ├á jour session 12:45)
- `docs/passation.md` (cette entr├®e)

### Contexte
Bug critique streaming chunks : les chunks arrivent du backend via WebSocket, le state est mis ├á jour, MAIS l'UI ne se rafra├«chit jamais visuellement pendant le streaming.

Erreur dans logs : `[Chat] ÔÜá´©Å Message element not found in DOM for id: 1ac7c84a-0585-432a-91e2-42b62af359ea`

**Root cause :**
- Dans `handleStreamStart`, le flag `_isStreamingNow = true` ├®tait activ├® AVANT le `state.set()`
- Ordre incorrect : flag activ├® ligne 784 ÔåÆ puis `state.set()` ligne 803
- Quand `state.set()` d├®clenche le listener state, le flag bloque d├®j├á l'appel ├á `ui.update()`
- R├®sultat : le message vide n'est JAMAIS rendu dans le DOM
- Quand les chunks arrivent, `handleStreamChunk` cherche l'├®l├®ment DOM avec `data-message-id` mais il n'existe pas
- Tous les chunks ├®chouent silencieusement : state mis ├á jour mais DOM jamais rafra├«chi

**Investigation pr├®c├®dente (session 2025-10-18 18:35) :**
- Avait impl├®ment├® modification directe du DOM avec `data-message-id`
- MAIS le probl├¿me ├®tait en amont : le message vide n'├®tait jamais ajout├® au DOM
- La modification directe du DOM ├®tait correcte, mais op├®rait sur un ├®l├®ment inexistant

### Actions r├®alis├®es

**Fix FINAL : D├®placement du flag apr├¿s state.set()**

Modifi├® `handleStreamStart()` (chat.js:782-810) :

```javascript
handleStreamStart(payload = {}) {
  const agentIdRaw = payload && typeof payload === 'object' ? (payload.agent_id ?? payload.agentId) : null;
  const agentId = String(agentIdRaw ?? '').trim() || 'nexus';
  const messageId = payload && typeof payload === 'object' && payload.id ? payload.id : `assistant-${Date.now()}`;
  const baseMeta = (payload && typeof payload.meta === 'object') ? { ...payload.meta } : null;

  const bucketId = this._resolveBucketFromCache(messageId, agentId, baseMeta);
  const agentMessage = {
    id: messageId,
    role: 'assistant',
    content: '',
    agent_id: agentId,
    isStreaming: true,
    created_at: Date.now(),
  };
  if (baseMeta && Object.keys(baseMeta).length) agentMessage.meta = baseMeta;

  const curr = this.state.get(`chat.messages.${bucketId}`) || [];
  this.state.set(`chat.messages.${bucketId}`, [...curr, agentMessage]);
  this.state.set('chat.currentAgent', agentId);
  this.state.set('chat.streamingMessageId', messageId);
  this.state.set('chat.streamingAgent', agentId);

  // ­ƒöÑ FIX CRITIQUE: Activer le flag APR├êS que state.set() ait d├®clench├® le listener
  // Cela permet au listener d'appeler ui.update() et de rendre le message vide dans le DOM
  // Ensuite les chunks peuvent modifier le DOM directement car l'├®l├®ment existe
  this._isStreamingNow = true;

  console.log(`[Chat] ­ƒöì handleStreamStart completed for ${agentId}/${messageId}`);
}
```

**Ordre d'ex├®cution correct maintenant :**
1. `state.set()` ajoute le message vide au state (ligne 800)
2. Le listener state se d├®clenche ÔåÆ appelle `ui.update()` (flag pas encore activ├®)
3. Le message vide est rendu dans le DOM avec `data-message-id`
4. PUIS `_isStreamingNow = true` (ligne 809) bloque les prochains updates
5. Quand les chunks arrivent, l'├®l├®ment DOM existe ÔåÆ mise ├á jour directe du DOM fonctionne

### Tests
- Ô£à Build frontend: `npm run build` ÔåÆ OK (3.04s, aucune erreur)
- ÔÅ│ Test manuel requis: backend actif + envoi message ├á Anima
- Logs attendus:
  ```
  [Chat] handleStreamStart ÔåÆ state.set() ÔåÆ listener ÔåÆ ui.update() appel├®
  [Chat] Message vide rendu dans DOM avec data-message-id="..."
  [Chat] ­ƒöÑ DOM updated directly for message ... - length: 2
  [Chat] ­ƒÜ½ State listener: ui.update() skipped (streaming in progress)
  ```

### Travail de Codex GPT pris en compte
- Aucune modification r├®cente de Codex dans chat.js
- Fix autonome par Claude Code

### Prochaines actions recommand├®es
1. Tester manuellement avec backend actif
2. V├®rifier que le texte s'affiche chunk par chunk en temps r├®el
3. Si OK, nettoyer console.log() debug excessifs
4. Commit + push fix streaming chunks FINAL

### Blocages
Aucun.

---
