# AutoSyncService – Synchronisation documentaire multi-agents

**Module** : `src/backend/features/sync/auto_sync_service.py`  
**Dernière mise à jour** : Novembre 2025 (beta-3.3.39)

## Vue d’ensemble

Le service surveille les fichiers de coordination inter-agents et génère automatiquement des rapports de consolidation. Depuis **beta-3.3.39**, la structure multi-fichiers (`SYNC_STATUS.md` + `AGENT_SYNC_*.md` + journaux par agent) remplace l’ancien `AGENT_SYNC.md` unique.

## Fichiers surveillés

- `SYNC_STATUS.md` – vue d’ensemble
- `AGENT_SYNC_CLAUDE.md`, `AGENT_SYNC_CODEX.md`, `AGENT_SYNC_GEMINI.md`
- `docs/passation_claude.md`, `docs/passation_codex.md`
- `AGENTS.md`, `CODEV_PROTOCOL.md`
- `docs/architecture/00-Overview.md`, `docs/architecture/10-Components.md`, `docs/architecture/30-Contracts.md`
- `ROADMAP.md`

Chaque fichier est hashé (MD5) toutes les 30s, et un évènement `created|modified|deleted` est enregistré lorsqu’un checksum change.

## Déclencheurs de consolidation

- **Seuil** : déclenchement au-delà de `consolidation_threshold` (défaut 5 changements).
- **Temps** : consolidation toutes les `consolidation_interval_minutes` (défaut 60 min) même si le seuil n’est pas atteint.
- **Manuel** : `POST /api/sync/consolidate`.

Chaque consolidation ajoute un rapport à `SYNC_STATUS.md` (section “🤖 Synchronisation automatique”) listant les fichiers touchés, le type de déclencheur et les agents concernés.

## API REST

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/sync/status` | Statut du service (running, pending_changes, last_consolidation, fichiers surveillés). |
| `GET` | `/api/sync/pending-changes` | Détail des évènements en attente. |
| `POST` | `/api/sync/consolidate` | Force une consolidation immédiate. |

Toutes les routes supportent l’entête `x-dev-bypass: 1` pour le debug local.

## Configuration

```bash
AUTOSYNC_ENABLED=1           # peut être forcé à 0 pour désactiver le service
AUTOSYNC_CHECK_INTERVAL=30   # secondes
AUTOSYNC_THRESHOLD=5         # nb de changements avant consolidation
AUTOSYNC_INTERVAL_MIN=60     # minutes entre consolidations temporelles
```

Le service se lance automatiquement dans `backend.main:create_app()` et peut être relancé via `scripts/run-backend.ps1`.

## Notes d’implémentation (beta-3.3.39)

- Surveiller `SYNC_STATUS.md` au lieu du legacy `AGENT_SYNC.md`.
- Rapports écrits exclusivement dans `SYNC_STATUS.md` pour éviter les conflits entre agents.
- Journalisation explicite quand le fichier cible est introuvable (permet de diagnostiquer les environnements incomplets).
