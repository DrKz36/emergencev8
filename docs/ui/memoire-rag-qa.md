# Memoire et RAG QA

## Objectif
- Centraliser les verifications front pour le bandeau memoire et les indicateurs RAG.
- Relier chaque observation aux smokes 2025-09-27 afin d assurer la coherence avec `docs/Memoire.md` et `docs/passation.md`.

## Smokes 2025-09-27
- `scripts/smoke/smoke-ws-rag.ps1 -SessionId ragtest124 -MsgType chat.message -UserId "smoke_rag&dev_bypass=1"`
  - Resultat : OK. Flux `ws:chat_stream_end` (OpenAI gpt-4o-mini) + upload document_id=57 sans 5xx.
  - Log QA : `../assets/memoire/smoke-ws-rag.log`.
- `scripts/smoke/smoke-ws-rag.ps1 -SessionId ragtest-ws-send-20250927 -MsgType ws:chat_send -UserId "smoke_rag&dev_bypass=1"`
  - Resultat : KO. Handshake accepte mais reponse `ws:error` (`Type inconnu: ws:chat_send`).
  - Log QA : `../assets/memoire/smoke-ws-rag-ws-chat_send.log` (a surveiller jusqu au correctif backend).
- `scripts/smoke/smoke-ws-3msgs.ps1 -SessionId ragtest-3msgs-20250927 -MsgType chat.message -UserId "smoke_rag&dev_bypass=1"`
  - Resultat : OK. Trois emissions consecutives `ws:chat_stream_start` puis `ws:chat_stream_end`; aucun HTTP 5xx cote uploads/documents (controle `backend.err.log`).
  - Log QA : `../assets/memoire/smoke-ws-3msgs.log`.

## Bandeau memoire (`ws:memory_banner`)
- Evenements observes pendant `smoke-ws-3msgs` :
  - `has_stm=false`, `ltm_items=0`, `injected_into_prompt=false` sur chaque `ws:chat_stream_start` (session fraiche, aucun rappel injecte).
  - Confirmer que la UI affiche le bandeau memoire en mode "STM vide / LTM 0" sans toast d erreur.
- Actions QA recommandees :
  - Declencher manuellement une consolidation (`Analyser`) apres la serie de messages pour verifier le passage `loading -> done` et la mise a jour des compteurs.
  - Controler la console front : `window.__EMERGENCE_QA_METRICS__.memoryBanner` doit refleter les derniers payloads (`session_id`, `ltm_items`).

## Indicateurs RAG (`ws:rag_status`, toasts sources)
- `smoke-ws-rag.ps1` en mode `chat.message` envoie `use_rag=true` :
  - Attendre la sequence `ws:rag_status` (`searching` puis `found`) ainsi que les toasts sources cote UI.
  - Cross-check `meta.selected_doc_ids` dans les payloads WS pour confirmer l alignement des documents autorises.
- Tant que `ws:chat_send` reste refuse par le backend, conserver `MsgType=chat.message` pour les smokes et noter l erreur dans les rapports QA.
- Pour les tests UI prolonges, rejouer l upload doc (`POST /api/documents/upload`) et afficher le bandeau documents afin de verifier la coloration RAG (icones + badge source).

## Suivi et references
- Referencer chaque run dans `docs/Memoire.md` (section Observabilite & Journal d execution) et dans `docs/passation.md` (Backend & QA).
- Captures a produire lors de la prochaine passe UI :
  - Bandeau memoire `has_stm=false` vs `has_stm=true`.
  - Toast sources RAG lorsque `ws:rag_status=found`.
  - Console QA montrant `memoryBanner` et `ragStatus` incremente apres un smoke.

