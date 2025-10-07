# Routine Automatique - Synchronisation Documentation

## 🔄 À EXÉCUTER après chaque session de modifications

Chaque fois que tu modifies du code (frontend, backend, config), **tu DOIS** mettre à jour la documentation collaborative pour Codex GPT.

### Checklist Documentation

```markdown
- [ ] AGENT_SYNC.md mis à jour
  - [ ] Timestamp actualisé (format: YYYY-MM-DD HH:MM CEST)
  - [ ] Section "Claude Code (moi)" complète
  - [ ] Fichiers touchés listés
  - [ ] Changements clés documentés
  - [ ] Prochaines actions définies

- [ ] docs/passation.md mis à jour
  - [ ] Nouvelle entrée avec timestamp [YYYY-MM-DD HH:MM]
  - [ ] Agent identifié (Claude Code)
  - [ ] Contexte expliqué
  - [ ] Actions réalisées détaillées
  - [ ] Tests effectués
  - [ ] Résultats obtenus
  - [ ] Prochaines actions recommandées
  - [ ] Blocages (ou "Aucun")
```

### Commande Rapide

Après tes modifications, dis simplement :

```
Mets à jour AGENT_SYNC.md et docs/passation.md avec les changements de cette session
```

### Fichiers à Mettre à Jour

1. **AGENT_SYNC.md** (racine)
   - Section "Dernière mise à jour"
   - Section "Zones de travail en cours" → "Claude Code (moi)"

2. **docs/passation.md**
   - Nouvelle entrée en haut du fichier
   - Format standardisé avec toutes les sections

### Exemple Type

```markdown
## [2025-MM-DD HH:MM] - Agent: Claude Code (Description courte)

### Fichiers modifiés
- path/to/file1.ext
- path/to/file2.ext

### Contexte
- Pourquoi ces changements
- Problème résolu

### Actions réalisées
1. Action 1 avec détails
2. Action 2 avec détails

### Tests
- ✅ Test réussi
- ⏳ Test à relancer

### Résultats
- Impact mesurable

### Prochaines actions recommandées
1. Action pour la suite
2. Tests à valider

### Blocages
- Aucun (ou détailler)
```

### Cas d'Usage

**À chaque fois que tu modifies :**
- ✅ Code frontend (src/frontend/)
- ✅ Code backend (src/backend/)
- ✅ Styles CSS
- ✅ Configuration (package.json, requirements.txt)
- ✅ Architecture
- ✅ Déploiements

**Tu peux skip si :**
- ❌ Simple lecture/analyse de code
- ❌ Réponses aux questions sans modification
- ❌ Recherche de bugs sans fix

---

**Cette routine garantit que Codex GPT peut reprendre le travail sans friction !** 🎯
