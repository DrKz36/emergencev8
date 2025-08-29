# ÉMERGENCE — Contrats d’API internes

## WebSocket Frames
### Outbound (client → serveur)
```json
{ "type": "chat.message", "payload": { "text": "…", "agent_id": "anima|neo|nexus", "thread_id": "optional" } }
