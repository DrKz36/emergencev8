# 🔄 Flux d'Exécution - Architecture Cloud Run ÉMERGENCE V8

## 📊 Flux 1 : Requête Chat Utilisateur → Réponse Agent

### Séquence complète (architecture cible)

```
┌─────────┐
│ User    │
│ Browser │
└────┬────┘
     │ 1. POST /api/chat/message {"text": "Bonjour"}
     ▼
┌─────────────────────────────────────┐
│ ORCHESTRATEUR (FastAPI Cloud Run)  │
│                                     │
│ ┌─────────────────────────────────┐│
│ │ ChatService.handle_message()    ││
│ │                                 ││
│ │ 2. Check Redis cache            ││
│ │    redis.get_session_context()  ││
│ └─────────┬───────────────────────┘│
│           │ Cache MISS             │
│           ▼                        │
│ ┌─────────────────────────────────┐│
│ │ 3. Load context from PostgreSQL ││
│ │    SELECT messages FROM ...     ││
│ │    WHERE session_id = $1        ││
│ │    LIMIT 10                     ││
│ └─────────┬───────────────────────┘│
│           │                        │
│           ▼                        │
│ ┌─────────────────────────────────┐│
│ │ 4. Store user message in DB     ││
│ │    INSERT INTO messages ...     ││
│ └─────────┬───────────────────────┘│
│           │                        │
│           ▼                        │
│ ┌─────────────────────────────────┐│
│ │ 5. RAG: Check if enabled        ││
│ │    if rag_enabled:              ││
│ │      - Check Redis cache        ││
│ │      - Or search pgvector       ││
│ └─────────┬───────────────────────┘│
│           │ RAG docs found         │
│           ▼                        │
│ ┌─────────────────────────────────┐│
│ │ 6. Build agent task payload     ││
│ │    {                            ││
│ │      "message_id": "uuid",      ││
│ │      "session_id": "uuid",      ││
│ │      "messages": [...],         ││
│ │      "rag_context": [...],      ││
│ │      "model": "claude-3-haiku"  ││
│ │    }                            ││
│ └─────────┬───────────────────────┘│
│           │                        │
│           ▼                        │
│ ┌─────────────────────────────────┐│
│ │ 7. Publish to Pub/Sub           ││
│ │    topic: "agent-anima-tasks"   ││
│ │    data: base64(json(payload))  ││
│ └─────────┬───────────────────────┘│
└───────────┼─────────────────────────┘
            │
            │ Pub/Sub message
            ▼
┌──────────────────────────────────────┐
│ PUB/SUB TOPIC                        │
│ projects/.../topics/agent-anima-tasks│
└──────────┬───────────────────────────┘
           │ Push subscription
           ▼
┌──────────────────────────────────────┐
│ WORKER: Anima (Cloud Run Service)   │
│                                      │
│ POST /process (Pub/Sub push)         │
│                                      │
│ ┌────────────────────────────────┐  │
│ │ 8. Decode Pub/Sub message      │  │
│ │    base64_decode(data)         │  │
│ │    json.loads(...)             │  │
│ └────────┬───────────────────────┘  │
│          │                          │
│          ▼                          │
│ ┌────────────────────────────────┐  │
│ │ 9. Call Anthropic API          │  │
│ │    anthropic.messages.create() │  │
│ │      model: claude-3-haiku     │  │
│ │      messages: [...]           │  │
│ │      system: [RAG context]     │  │
│ └────────┬───────────────────────┘  │
│          │ Response from Claude    │
│          ▼                          │
│ ┌────────────────────────────────┐  │
│ │ 10. Calculate cost             │  │
│ │     tokens_in * $0.25/1M       │  │
│ │     + tokens_out * $1.25/1M    │  │
│ └────────┬───────────────────────┘  │
│          │                          │
│          ▼                          │
│ ┌────────────────────────────────┐  │
│ │ 11. Store in PostgreSQL        │  │
│ │     INSERT INTO messages       │  │
│ │       (session_id, role,       │  │
│ │        content, agent_id,      │  │
│ │        tokens_input, ...)      │  │
│ │     INSERT INTO costs          │  │
│ │       (user_id, cost_usd, ...) │  │
│ └────────┬───────────────────────┘  │
│          │                          │
│          ▼                          │
│ ┌────────────────────────────────┐  │
│ │ 12. Notify orchestrator        │  │
│ │     Option A: WebSocket        │  │
│ │     Option B: Redis Pub/Sub    │  │
│ │     Option C: Poll DB          │  │
│ └────────┬───────────────────────┘  │
│          │                          │
│          ▼                          │
│ ┌────────────────────────────────┐  │
│ │ 13. Return 200 OK (ACK)        │  │
│ │     Pub/Sub marks delivered    │  │
│ └────────────────────────────────┘  │
└──────────────────────────────────────┘
            │
            │ Notification (WebSocket ou polling)
            ▼
┌─────────────────────────────────────┐
│ ORCHESTRATEUR                       │
│                                     │
│ ┌─────────────────────────────────┐│
│ │ 14. Retrieve response from DB   ││
│ │     SELECT * FROM messages      ││
│ │     WHERE id = $1               ││
│ └─────────┬───────────────────────┘│
│           │                        │
│           ▼                        │
│ ┌─────────────────────────────────┐│
│ │ 15. Send via WebSocket          ││
│ │     ws.send({                   ││
│ │       type: "chat.message",     ││
│ │       role: "assistant",        ││
│ │       content: "...",           ││
│ │       agent_id: "anima",        ││
│ │       cost_usd: 0.0012          ││
│ │     })                          ││
│ └─────────┬───────────────────────┘│
│           │                        │
│           ▼                        │
│ ┌─────────────────────────────────┐│
│ │ 16. Update Redis cache          ││
│ │     redis.store_session_context ││
│ │       (session_id, messages)    ││
│ └─────────────────────────────────┘│
└─────────────────────────────────────┘
            │
            │ WebSocket message
            ▼
┌─────────┐
│ User    │
│ Browser │ Displays response "Bonjour ! Comment puis-je vous aider ?"
└─────────┘
```

**Latences estimées** :
1. Orchestrator: 50ms (DB query + Pub/Sub publish)
2. Pub/Sub delivery: 10-50ms
3. Worker LLM call: 500-2000ms (Anthropic API)
4. Worker DB write: 20ms
5. WebSocket notification: 10ms

**Total p50** : ~1.5s
**Total p99** : ~3s (cold start worker + LLM latency)

---

## 📊 Flux 2 : RAG Document Query (pgvector)

### Recherche similaire avec embeddings

```
┌─────────┐
│ User    │ "Explique le document X"
└────┬────┘
     │
     ▼
┌─────────────────────────────────────┐
│ ORCHESTRATEUR                       │
│                                     │
│ 1. Check RAG enabled                │
│    rag_enabled = True               │
│                                     │
│ 2. Generate query embedding         │
│    embedding = sbert.encode(query)  │
│    # [0.123, -0.456, ..., 0.789]    │
│    # 384 dimensions                 │
│                                     │
│ 3. Check Redis cache                │
│    key = f"rag:query:{hash(query)}" │
│    cached = redis.get(key)          │
└─────────┬───────────────────────────┘
          │ Cache MISS
          ▼
┌─────────────────────────────────────┐
│ CLOUD SQL POSTGRESQL (pgvector)    │
│                                     │
│ 4. Vector search (cosine similarity)│
│                                     │
│ SELECT                              │
│   dc.id,                            │
│   dc.content,                       │
│   d.filename,                       │
│   (1 - (dc.embedding <=>            │
│         '[0.123,-0.456,...]'::vector│
│    ))::DECIMAL AS similarity        │
│ FROM document_chunks dc             │
│ JOIN documents d ON d.id = dc.doc_id│
│ WHERE d.user_id = 'user@example.com'│
│   AND (1 - (dc.embedding <=>        │
│            query_vector))           │
│       >= 0.7  /* threshold */       │
│ ORDER BY                            │
│   dc.embedding <=> query_vector     │
│ LIMIT 5;                            │
│                                     │
│ Uses index:                         │
│   idx_chunks_embedding_ivfflat      │
│   (IVFFLAT with 100 lists)          │
│                                     │
│ Query time: ~50ms (index scan)      │
└─────────┬───────────────────────────┘
          │ Results: 5 chunks
          ▼
┌─────────────────────────────────────┐
│ ORCHESTRATEUR                       │
│                                     │
│ 5. Cache results in Redis           │
│    redis.set(                       │
│      key,                           │
│      json.dumps(results),           │
│      ex=300  # 5 min TTL            │
│    )                                │
│                                     │
│ 6. Build context for agent          │
│    rag_context = "\n\n".join([      │
│      f"[{r['filename']}]\n"         │
│      f"{r['content']}"              │
│      for r in results               │
│    ])                               │
│                                     │
│ 7. Include in agent payload         │
│    system_prompt = f"""             │
│      Context documents:             │
│      {rag_context}                  │
│                                     │
│      User question:                 │
│      {user_query}                   │
│    """                              │
└─────────┬───────────────────────────┘
          │
          │ → Pub/Sub → Worker (see Flux 1)
          ▼
```

**Optimisations pgvector** :

1. **Index IVFFLAT** : Partitionne espace vectoriel en 100 clusters
   - Recherche approximative (trade-off vitesse/précision)
   - Idéal pour >10K vectors
   - Recommandé: `lists = sqrt(nb_rows)`

2. **Index HNSW (alternative)** : Graphe hierarchique
   - Meilleure précision que IVFFLAT
   - Plus lent à construire
   - Idéal pour >100K vectors

3. **Similarité cosine** : `<=>` operator
   - Distance : 0 = identique, 2 = opposé
   - Similarity : `1 - distance`

---

## 📊 Flux 3 : Session Cache (Redis)

### Gestion session utilisateur avec TTL

```
┌─────────┐
│ User    │ Login successful
└────┬────┘
     │ JWT issued (session_id: "uuid-123")
     ▼
┌─────────────────────────────────────┐
│ ORCHESTRATEUR                       │
│                                     │
│ 1. Create session context           │
│    context = {                      │
│      "user_id": "user@example.com", │
│      "session_id": "uuid-123",      │
│      "current_thread_id": "uuid-...",│
│      "rag_enabled": False,          │
│      "last_activity": timestamp     │
│    }                                │
│                                     │
│ 2. Store in Redis with TTL          │
│    redis.store_session_context(     │
│      session_id="uuid-123",         │
│      context=context,               │
│      ttl=1800  # 30 minutes         │
│    )                                │
│                                     │
│    Internally:                      │
│    SET session:uuid-123:context     │
│        '{"user_id":"...","..."}' EX 1800│
└─────────────────────────────────────┘
          │
          │ User sends message (10 min later)
          ▼
┌─────────────────────────────────────┐
│ ORCHESTRATEUR                       │
│                                     │
│ 3. Retrieve session context         │
│    context = redis.get_session_     │
│              context("uuid-123")    │
│                                     │
│    Redis:                           │
│    GET session:uuid-123:context     │
│    → Returns JSON (still valid)     │
│    → TTL remaining: 1200s (20 min)  │
│                                     │
│ 4. Refresh TTL on activity          │
│    redis.expire(                    │
│      "session:uuid-123:context",    │
│      1800  # Reset to 30 min        │
│    )                                │
└─────────────────────────────────────┘
          │
          │ User inactive for 30 minutes
          ▼
┌─────────────────────────────────────┐
│ REDIS (Memorystore)                 │
│                                     │
│ 5. Key expired (TTL = 0)            │
│    DEL session:uuid-123:context     │
│                                     │
│    Memory freed (LRU eviction)      │
└─────────────────────────────────────┘
          │
          │ User sends new message after expiration
          ▼
┌─────────────────────────────────────┐
│ ORCHESTRATEUR                       │
│                                     │
│ 6. Cache MISS                       │
│    context = redis.get_session_     │
│              context("uuid-123")    │
│    → Returns None                   │
│                                     │
│ 7. Reload from PostgreSQL           │
│    SELECT * FROM sessions           │
│    WHERE id = 'uuid-123'            │
│                                     │
│ 8. Re-cache in Redis                │
│    redis.store_session_context(...)  │
└─────────────────────────────────────┘
```

**TTLs recommandés** :
- **Session context** : 30 min (refresh on activity)
- **RAG results** : 5 min (queries similaires fréquentes)
- **Agent state** : 15 min (thinking, temporary data)
- **Rate limits** : 60s (sliding window)

---

## 📊 Flux 4 : Pub/Sub Dead Letter Queue (Retry Logic)

### Gestion erreurs avec retry automatique

```
┌─────────────────────────────────────┐
│ ORCHESTRATEUR                       │
│ Publish message to Pub/Sub          │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ PUB/SUB TOPIC: agent-anima-tasks    │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ SUBSCRIPTION: anima-worker-sub      │
│ ack_deadline: 600s (10 min)         │
│ retry_policy:                       │
│   min_backoff: 10s                  │
│   max_backoff: 600s                 │
│ max_delivery_attempts: 5            │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ WORKER: Anima                       │
│                                     │
│ Attempt 1: Call Anthropic API       │
│ → Error: 429 Rate Limit             │
│ → Return 500 (no ACK)               │
└─────────┬───────────────────────────┘
          │
          │ Pub/Sub retry with backoff
          ▼
┌─────────────────────────────────────┐
│ SUBSCRIPTION (retry)                │
│ Wait: 10s (min_backoff)             │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ WORKER: Anima                       │
│                                     │
│ Attempt 2: Call Anthropic API       │
│ → Error: 503 Service Unavailable    │
│ → Return 500 (no ACK)               │
└─────────┬───────────────────────────┘
          │
          │ Pub/Sub retry with backoff
          ▼
┌─────────────────────────────────────┐
│ SUBSCRIPTION (retry)                │
│ Wait: 20s (exponential backoff)     │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ WORKER: Anima                       │
│                                     │
│ Attempt 3: Call Anthropic API       │
│ → Success: 200 OK                   │
│ → Store in DB                       │
│ → Return 200 (ACK)                  │
└─────────────────────────────────────┘
          │
          │ Message acknowledged
          ▼
┌─────────────────────────────────────┐
│ SUBSCRIPTION                        │
│ Message deleted from queue          │
└─────────────────────────────────────┘

=== Alternative: Max retries exceeded ===

┌─────────────────────────────────────┐
│ WORKER: Anima                       │
│                                     │
│ Attempt 5: Call Anthropic API       │
│ → Error: 500 Internal Error         │
│ → Return 500 (no ACK)               │
└─────────┬───────────────────────────┘
          │
          │ Max delivery attempts reached (5)
          ▼
┌─────────────────────────────────────┐
│ DEAD LETTER QUEUE: agent-tasks-dlq  │
│                                     │
│ Message moved to DLQ with metadata: │
│ {                                   │
│   "original_topic": "agent-anima...",│
│   "delivery_attempts": 5,           │
│   "last_error": "500 Internal",     │
│   "first_attempt_time": timestamp,  │
│   "last_attempt_time": timestamp    │
│ }                                   │
└─────────┬───────────────────────────┘
          │
          │ Alert monitoring team
          ▼
┌─────────────────────────────────────┐
│ CLOUD MONITORING ALERT              │
│                                     │
│ Alert: DLQ messages > 10            │
│ → Send Slack notification           │
│ → Page on-call engineer             │
│                                     │
│ Manual investigation:               │
│ - Check DLQ messages                │
│ - Analyze failure pattern           │
│ - Fix root cause (API outage, etc.) │
│ - Re-publish from DLQ if needed     │
└─────────────────────────────────────┘
```

**Retry strategy** :
- Attempt 1: Immédiate
- Attempt 2: +10s
- Attempt 3: +20s (exponential)
- Attempt 4: +40s
- Attempt 5: +80s
- → DLQ after 5 échecs (total ~2.5 min)

---

## 🎯 Résumé Performance

| Opération | Latence p50 | Latence p99 | Throughput |
|-----------|-------------|-------------|------------|
| Chat message (cache hit) | 800ms | 1.5s | 500 req/s |
| Chat message (cache miss) | 1.5s | 3s | 200 req/s |
| RAG vector search | 50ms | 200ms | 1000 req/s |
| Session context (Redis) | 5ms | 20ms | 5000 req/s |
| Worker LLM call | 1s | 3s | 100 req/s/worker |

**Scalabilité** :
- Orchestrator : Auto-scale 1-10 instances (concurrent 80 req/instance)
- Workers : Auto-scale 0-10 instances (concurrent 10 req/instance)
- PostgreSQL : Connection pool 100 max, MVCC = 0 locks
- Redis : 1GB = ~10K sessions cached simultaneously

**🤖 Flux documentation généré avec CodeSmith-AI**
