
# Conversations Module Refactor - Pass 3 Delivery

The conversations list now lives in its own feature module and no longer injects DOM directly into the sidebar. Navigation, state events, and styling have been updated so the thread management experience happens in the main content area with full-width layout and delete support.

## Implemented Changes
- Added a dedicated `ConversationsModule` (`src/frontend/features/conversations/conversations.js`) and linked it from `App.moduleConfig` via the new `conversations` tab.
- Refactored `ThreadsPanel` to accept an injected host element, render its own shell, and expose destructive actions (archive/delete) without touching the sidebar.
- Introduced `EVENTS.THREADS_DELETED` plus `threads-service.deleteThread` to orchestrate the backend cascade (`DELETE /api/threads/{id}`) and keep the chat state in sync.
- Updated global styles: `threads.css` now targets the central layout (header, actions, confirm prompts) and `conversations.css` positions the module inside the content pane.
- Added node-based tests (`threads-panel.delete.test.js`) covering the deletion flow, fallback selection, and event emission.

## Module Architecture Snapshot
- **ConversationsModule**
  - Imports `ThreadsPanel`, sets it up with `keepMarkup`, and subscribes to `THREADS_DELETED` / `THREADS_LIST_UPDATED` to toggle empty-state styling.
  - Loaded dynamically through `moduleLoaders.conversations`; the nav shows after `Dialogue` and before `Documents`.
- **ThreadsPanel**
  - Constructor now receives options (`hostElement`, `keepMarkup`) and exposes `setHostElement()`.
  - `ensureContainer()` renders a structured shell (`threads-panel__inner`) and drops the old `#app-sidebar` coupling.
  - `handleDelete()` calls `apiDeleteThread`, removes the entry from state, emits `THREADS_DELETED`, then selects the next thread or creates a fresh one when the list becomes empty.
  - `renderList()` drives the new UI (action row + confirm block) with disabled states for archive/delete while operations are pending.
- **Events & State**
  - `EVENTS.THREADS_DELETED` added to `shared/constants.js` and used in panel + module.
  - `removeThreadFromState()` keeps `threads.currentId` / `chat.threadId` aligned, letting chat recover automatically when the active thread disappears.

## UX Notes
- Delete now triggers an inline confirm block: `Supprimer ?` + `Confirmer/Annuler` buttons; destructive buttons are highlighted with the new red palette.
- The new layout offers a short subtitle and larger hitboxes so the list can stretch across desktop width. Buttons collapse to full-width on small screens.
- Empty states remain handled by `renderList()` placeholders; the module wraps the panel with `conversations-module--empty` to allow future illustration blocks if desired.

## Follow-up & QA (Pass 4)
1. Capture updated screenshots for the Conversations view (default list, delete confirm, empty state) under `docs/assets/ui/`.
2. Run the full frontend build + smoke flows to validate navigation (ensure no regressions on mobile sidebar).
3. Confirm the new `DELETE /api/threads/{id}` endpoint is exercised end-to-end in manual QA (including message/doc cleanup) and document test notes in `passation.md`.
