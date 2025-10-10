# Prompt pour GPT Codex Cloud — Workflow de Synchronisation

## ✅ RÉSOLUTION : Le problème est diagnostiqué et résolu

### État Actuel (2025-10-10)
- ✅ **Remotes configurés sur machine locale** :
  - `origin` (HTTPS) : `https://github.com/DrKz36/emergencev8.git`
  - `codex` (SSH) : `git@github.com:DrKz36/emergencev8.git`
- ⚠️ **Environnement cloud** : Aucun remote configuré (attendu et normal)
- ✅ **Solution** : Workflow de synchronisation via patches documenté

## 🔄 Workflow de Synchronisation Cloud → Local → GitHub

### Pour Toi (GPT Codex Cloud) - SANS accès GitHub

**À la fin de chaque session de développement :**

1. **Générer un patch de tes modifications** :
   ```bash
   # Dans /workspace/emergencev8
   git format-patch origin/main --stdout > /workspace/sync_$(date +%Y%m%d_%H%M%S).patch
   ```

2. **Lister les fichiers modifiés** :
   ```bash
   git status --short > /workspace/files_changed.txt
   git log origin/main..HEAD --oneline > /workspace/commits.txt
   ```

3. **Documenter dans AGENT_SYNC.md** :
   - Résumer les modifications effectuées
   - Indiquer le nom du fichier patch généré
   - Lister les fichiers critiques modifiés
   - Ajouter une entrée dans `docs/passation.md`

4. **Informer le développeur** :
   - Indiquer clairement : "Patch généré : `sync_YYYYMMDD_HHMMSS.patch`"
   - Donner le résumé des modifications
   - Préciser si des tests sont nécessaires

### Pour l'Agent Local (Claude Code) - AVEC accès GitHub

**Réception et application du patch :**

1. **Récupérer le patch** depuis l'environnement cloud
2. **Appliquer les modifications** :
   ```bash
   cd C:\dev\emergenceV8
   git apply --check sync_*.patch  # Vérifier d'abord
   git apply sync_*.patch
   ```
3. **Tester et valider** :
   ```bash
   npm run build
   pytest
   ```
4. **Commit et push vers GitHub** :
   ```bash
   git add -A
   git commit -m "sync: intégration modifications GPT Codex cloud - [description]"
   git push origin main
   ```
5. **Confirmer dans AGENT_SYNC.md** la synchronisation complète

## 📚 Documentation Complète

Voir [docs/CLOUD_LOCAL_SYNC_WORKFLOW.md](../docs/CLOUD_LOCAL_SYNC_WORKFLOW.md) pour :
- 3 méthodes de synchronisation (patch, fichiers, bundle)
- Scripts d'automatisation
- Gestion des conflits
- Checklist complète
- Bonnes pratiques

## 🚨 Règles Importantes

### ❌ Ne JAMAIS faire
- Tenter d'ajouter un remote dans l'environnement cloud (impossible)
- Tenter de push/pull depuis le cloud (pas d'accès réseau)
- Travailler simultanément sur cloud ET local (risque de conflits)

### ✅ TOUJOURS faire
- Lire `AGENT_SYNC.md` et `docs/passation.md` avant de coder
- Documenter toutes modifications dans `AGENT_SYNC.md`
- Générer un patch à la fin de session
- Informer clairement le développeur des modifications

## 🎯 Résumé : Qui Fait Quoi ?

| Qui ? | Responsabilité |
|-------|----------------|
| **GPT Codex Cloud** (toi) | - Développer le code<br>- Générer patches<br>- Documenter dans AGENT_SYNC.md |
| **Agent Local** | - Appliquer patches<br>- Tester et valider<br>- Push vers GitHub |
| **Développeur** | - Transférer patches cloud→local<br>- Arbitrer si conflits |

**Dernière mise à jour** : 2025-10-10 par Claude Code (Agent Local)
