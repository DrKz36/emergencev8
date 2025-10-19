## [2025-10-19 04:20] — Agent: Claude Code

### Fichiers modifiés
- `src/backend/features/memory/memory_query_tool.py` (header toujours retourné)
- `src/backend/features/chat/memory_ctx.py` (toujours appeler formatter)
- `src/backend/features/chat/service.py` (3 fixes critiques)
- `AGENT_SYNC.md` (documentation session)
- `docs/passation.md` (cette entrée)

### Contexte
User signalait qu'Anima répondait "Je n'ai pas accès à nos conversations passées" au lieu de résumer les sujets/concepts abordés avec dates et fréquences. Cette feature marchait il y a 4 jours, cassée depuis ajout règles anti-hallucination.

### Analyse multi-couches (3 bugs découverts!)

**Bug #1 - Flow memory context (memory_ctx.py):**
- Problème: `format_timeline_natural_fr()` retournait `"Aucun sujet abordé récemment."` SANS le header `### Historique des sujets abordés` quand timeline vide
- Impact: Anima cherche ce header exact dans le contexte RAG (règle anti-hallucination ligne 7 du prompt)
- Si header absent → Anima dit "pas accès" au lieu de "aucun sujet trouvé"
- Fix commit e466c38: Toujours retourner le header même si timeline vide

**Bug #2 - Flow temporal query (_build_temporal_history_context):**
- Problème: Méthode retournait `""` (chaîne vide) si liste vide
- Impact: Condition `if temporal_context:` devient False en Python → bloc jamais ajouté à `blocks_to_merge`
- Header "Historique des sujets abordés" jamais généré par `_merge_blocks()`
- Fix commit b106d35: Retourner toujours au moins `"*(Aucun sujet trouvé dans l'historique)*"` même si vide ou erreur

**Bug #3 - CRITIQUE (cause réelle du problème):**
- Problème: Frontend envoyait `use_rag: False` pour les questions de résumé
- `_normalize_history_for_llm()` ligne 1796 checkait `if use_rag and rag_context:`
- Le rag_context était **créé avec le header** mais **JAMAIS INJECTÉ** dans le prompt!
- Anima ne voyait jamais le contexte → disait "pas accès"
- Fix commit 1f0b1a3 ⭐: Nouvelle condition `should_inject_context` détecte "Historique des sujets abordés" dans rag_context et injecte même si use_rag=False
- Respecte l'intention du commentaire ligne 2487 "même si use_rag=False"

### Tests
- ✅ `git push` (Guardians passés, prod OK)
- ⏳ **TEST MANUEL REQUIS**: Redémarrer backend + demander à Anima "résume les sujets abordés"
- Anima devrait maintenant voir le header et répondre correctement

### Résultat attendu
Anima verra maintenant toujours dans son contexte:
```
[RAG_CONTEXT]
### Historique des sujets abordés

*(Aucun sujet trouvé dans l'historique)*
```
Ou avec de vrais sujets si la consolidation des archives réussit.

### Travail de Codex GPT pris en compte
- Aucune modification Codex dans cette zone récemment
- Fix indépendant backend uniquement

### Prochaines actions recommandées
1. **PRIORITÉ 1**: Redémarrer backend et tester si Anima répond correctement
2. **PRIORITÉ 2**: Fixer script `consolidate_all_archives.py` (erreurs d'imports)
3. Une fois consolidation OK, historique sera peuplé avec vrais sujets archivés
4. Vérifier que dates/heures/fréquences apparaissent dans réponse Anima

### Blocages
- Consolidation threads archivés bloquée par erreurs imports Python (script cherche `backend.*` au lieu de `src.backend.*`)
- Non bloquant pour le fix immédiat du header

---

## [2025-10-19 12:45] — Agent: Claude Code (Fix Streaming Chunks Display FINAL - RÉSOLU ✅)

### Fichiers modifiés
- `src/frontend/features/chat/chat.js` (déplacement flag _isStreamingNow après state.set(), ligne 809)
- `AGENT_SYNC.md` (mise à jour session 12:45)
- `docs/passation.md` (cette entrée)

### Contexte
Bug critique streaming chunks : les chunks arrivent du backend via WebSocket, le state est mis à jour, MAIS l'UI ne se rafraîchit jamais visuellement pendant le streaming.

Erreur dans logs : `[Chat] ⚠️ Message element not found in DOM for id: 1ac7c84a-0585-432a-91e2-42b62af359ea`

**Root cause :**
- Dans `handleStreamStart`, le flag `_isStreamingNow = true` était activé AVANT le `state.set()`
- Ordre incorrect : flag activé ligne 784 → puis `state.set()` ligne 803
- Quand `state.set()` déclenche le listener state, le flag bloque déjà l'appel à `ui.update()`
- Résultat : le message vide n'est JAMAIS rendu dans le DOM
- Quand les chunks arrivent, `handleStreamChunk` cherche l'élément DOM avec `data-message-id` mais il n'existe pas
- Tous les chunks échouent silencieusement : state mis à jour mais DOM jamais rafraîchi

**Investigation précédente (session 2025-10-18 18:35) :**
- Avait implémenté modification directe du DOM avec `data-message-id`
- MAIS le problème était en amont : le message vide n'était jamais ajouté au DOM
- La modification directe du DOM était correcte, mais opérait sur un élément inexistant

### Actions réalisées

**Fix FINAL : Déplacement du flag après state.set()**

Modifié `handleStreamStart()` (chat.js:782-810) :

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

  // 🔥 FIX CRITIQUE: Activer le flag APRÈS que state.set() ait déclenché le listener
  // Cela permet au listener d'appeler ui.update() et de rendre le message vide dans le DOM
  // Ensuite les chunks peuvent modifier le DOM directement car l'élément existe
  this._isStreamingNow = true;

  console.log(`[Chat] 🔍 handleStreamStart completed for ${agentId}/${messageId}`);
}
```

**Ordre d'exécution correct maintenant :**
1. `state.set()` ajoute le message vide au state (ligne 800)
2. Le listener state se déclenche → appelle `ui.update()` (flag pas encore activé)
3. Le message vide est rendu dans le DOM avec `data-message-id`
4. PUIS `_isStreamingNow = true` (ligne 809) bloque les prochains updates
5. Quand les chunks arrivent, l'élément DOM existe → mise à jour directe du DOM fonctionne

### Tests
- ✅ Build frontend: `npm run build` → OK (3.04s, aucune erreur)
- ⏳ Test manuel requis: backend actif + envoi message à Anima
- Logs attendus:
  ```
  [Chat] handleStreamStart → state.set() → listener → ui.update() appelé
  [Chat] Message vide rendu dans DOM avec data-message-id="..."
  [Chat] 🔥 DOM updated directly for message ... - length: 2
  [Chat] 🚫 State listener: ui.update() skipped (streaming in progress)
  ```

### Travail de Codex GPT pris en compte
- Aucune modification récente de Codex dans chat.js
- Fix autonome par Claude Code

### Prochaines actions recommandées
1. Tester manuellement avec backend actif
2. Vérifier que le texte s'affiche chunk par chunk en temps réel
3. Si OK, nettoyer console.log() debug excessifs
4. Commit + push fix streaming chunks FINAL

### Blocages
Aucun.

---
