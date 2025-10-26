# Journal de Passation — Codex GPT

**Archives >48h:** Voir `docs/archives/passation_archive_*.md`

**RÈGLE:** Ce fichier contient UNIQUEMENT les entrées des 48 dernières heures.
**Rotation:** Entrées >48h sont automatiquement archivées.

---

## [2025-10-26 18:10] — Agent: Codex GPT

### Version
- **Ancienne:** beta-3.1.0
- **Nouvelle:** beta-3.1.1 (PATCH - fix modal reprise conversation)

### Fichiers modifiés
- `src/frontend/features/chat/chat.js`
- `src/version.js`
- `src/frontend/version.js`
- `package.json`
- `CHANGELOG.md`
- `docs/passation_codex.md`
- `AGENT_SYNC_CODEX.md`

### Contexte
Fix bug modal reprise conversation qui ne fonctionnait pas après connexion.
Ajout attente explicite sur événements `threads:*` avant affichage modal.
Reconstruction du modal quand conversations arrivent pour garantir wiring bouton "Reprendre".

### Tests
- ✅ `npm run build`

### Versioning
- ✅ Version incrémentée (PATCH car bugfix)
- ✅ CHANGELOG.md mis à jour
- ✅ Patch notes ajoutées

### Prochaines actions recommandées
1. Vérifier côté backend que `threads.currentId` reste cohérent avec reprise utilisateur
2. QA UI sur l'app pour valider flux complet (connexion → modal → reprise thread)
3. Finir tests PWA offline/online (P3.10 - reste 20%)

### Blocages
Aucun.

---

## [2025-10-26 18:05] — Agent: Codex GPT

### Version
- **Ancienne:** beta-3.0.0
- **Nouvelle:** beta-3.1.0 (MINOR - lock portrait mobile + composer spacing)

### Fichiers modifiés
- `manifest.webmanifest`
- `src/frontend/main.js`
- `src/frontend/features/chat/chat.css`
- `src/frontend/styles/overrides/mobile-menu-fix.css`

### Contexte
Verrouillage orientation portrait pour PWA mobile avec overlay avertissement en mode paysage.
Ajustement zone de saisie chat pour intégrer safe-area iOS et assurer accès au composer sur mobile.
Amélioration affichage métadonnées conversation et sélecteurs agents en mode portrait.

### Tests
- ✅ `npm run build`

### Versioning
- ✅ Version incrémentée (MINOR car nouvelle feature UX)
- ✅ CHANGELOG.md mis à jour
- ✅ Patch notes ajoutées

### Prochaines actions recommandées
1. QA sur device iOS/Android pour valider overlay orientation et padding composer
2. Vérifier que guard portrait n'interfère pas avec mode desktop (résolution > 900px)
3. Ajuster UX de l'overlay selon retours utilisateur

### Blocages
Aucun.

---

**Note:** Pour historique complet, voir `docs/archives/passation_archive_2025-10-01_to_2025-10-26.md`
