# Memoire assets

## Screens a maintenir
- `centre-memoire.png` : vue Centre mémoire admin avec Conversations intégrées (placeholder actuel à remplacer par la capture UI réelle).
- `conversations-list.png` : vue Conversations par défaut (liste active + actions).
- `conversations-confirm.png` : bloc de confirmation `Supprimer ?` avec boutons `Confirmer/Annuler`.
- `conversations-empty.png` : état vide après cascade delete (sélection auto du nouveau thread).
- `memory-banner.png` : bandeau mémoire (STM/LTM) dans Conversations après analyse ou clear.

## Journaux et scripts
- `scenario-memory-clear.log` : sortie du script scénario clear.
- `smoke-ws-*.log` : smokes RAG/WS référencés dans `docs/passation.md`.
- `vector-store-reset-YYYYMMDD.log` : transcription hebdo de `tests/test_vector_store_reset.ps1` (horodatage, révision backend, dossier backup, résultat). Utiliser `tests/test_vector_store_reset.ps1 -AutoBackend` pour l'exécution automatisée (stdout conservé).
