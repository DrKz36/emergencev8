// FICHIER TEMPORAIRE - PATCH DEBUG pour handleStreamChunk
// À insérer dans chat.js ligne 800 pour debugger

handleStreamChunk(payload = {}) {
  console.log('[Chat] 🔍 handleStreamChunk called with payload:', JSON.stringify(payload, null, 2));
  const agentId = String(payload && typeof payload === 'object' ? (payload.agent_id ?? payload.agentId) : '').trim();
  const messageId = payload && typeof payload === 'object' ? payload.id : null;
  console.log('[Chat] 🔍 Chunk agentId:', agentId, 'messageId:', messageId);
  if (!agentId || !messageId) {
    console.warn('[Chat] ❌ Chunk ignored: missing agentId or messageId');
    return;
  }
  const rawChunk = payload && typeof payload.chunk !== 'undefined' ? payload.chunk : '';
  const chunkText = typeof rawChunk === 'string' ? rawChunk : String(rawChunk ?? '');
  console.log('[Chat] 🔍 Chunk text:', JSON.stringify(chunkText));
  const meta = (payload && typeof payload.meta === 'object') ? payload.meta : null;

  const lastChunk = this._lastChunkByMessage.get(String(messageId));
  if (chunkText && lastChunk === chunkText) {
    console.log('[Chat] ⏭️ Chunk ignored: duplicate');
    return;
  }

  const bucketId = this._resolveBucketFromCache(messageId, agentId, meta);
  console.log('[Chat] 🔍 Bucket ID:', bucketId);
  const list = this.state.get(`chat.messages.${bucketId}`) || [];
  const idx = list.findIndex((m) => m.id === messageId);
  console.log('[Chat] 🔍 Message index in bucket:', idx, 'list length:', list.length);
  if (idx >= 0) {
    const msg = { ...list[idx] };
    const oldContent = msg.content || '';
    msg.content = oldContent + chunkText;
    list[idx] = msg;
    this.state.set(`chat.messages.${bucketId}`, [...list]);
    this._lastChunkByMessage.set(String(messageId), chunkText);
    this._updateThreadCacheFromBuckets();
    console.log('[Chat] ✅ Chunk applied! Old length:', oldContent.length, 'New length:', msg.content.length);
  } else {
    console.warn('[Chat] ❌ Message not found in bucket for chunk, messageId:', messageId, 'bucketId:', bucketId);
    console.warn('[Chat] Available messages in bucket:', list.map(m => ({ id: m.id, role: m.role, contentLength: (m.content || '').length })));
  }
}
