# Instructions pour GPT Codex Cloud — Synchronisation GitHub

## 🎯 Tu travailles dans un environnement cloud SANS accès direct à GitHub

### Contexte Technique
- **Ton environnement** : `/workspace/emergencev8` (ou similaire)
- **Limitations** :
  - ❌ Aucun remote Git configuré
  - ❌ Pas d'accès réseau sortant
  - ❌ Impossible de push/pull vers GitHub
- **Solution** : Tu génères des patches, l'agent local les applique et push vers GitHub

---

## 📝 Procédure Standard de Synchronisation

### AVANT de commencer à coder

1. **Lire les fichiers de contexte** (OBLIGATOIRE) :
   ```bash
   # Dans l'ordre
   cat AGENT_SYNC.md              # État actuel du projet
   cat AGENTS.md                  # Consignes générales
   cat CODEV_PROTOCOL.md          # Protocole multi-agents
   tail -100 docs/passation.md    # 3 dernières entrées
   git log --oneline -10          # Historique récent
   git status                     # État working tree
   ```

2. **Vérifier que tu as la dernière version** :
   - L'agent local doit confirmer que le code dans le cloud est à jour
   - Si incertain, demander au développeur de synchroniser d'abord

---

### PENDANT le développement

1. **Travailler normalement** :
   - Modifier le code
   - Faire des commits locaux si besoin
   - Tester autant que possible

2. **Documenter en continu** :
   - Ajouter une section dans `AGENT_SYNC.md` décrivant ton travail
   - Utiliser le format :
     ```markdown
     ### 🟢 GPT Codex Cloud - Session YYYY-MM-DD HH:MM (Titre Session)
     - **Statut** : 🔄 EN COURS / ✅ TERMINÉE
     - **Priorité** : 🔴 CRITIQUE / 🟡 MOYENNE / 🟢 BASSE
     - **Fichiers touchés** :
       - `chemin/fichier.py` - description modification
       - `autre/fichier.js` - description modification
     - **Actions réalisées** : ...
     - **Tests / checks** : ...
     - **Prochaines actions** : ...
     ```

---

### APRÈS avoir fini (FIN DE SESSION)

#### Étape 1 : Générer le patch de synchronisation

```bash
# Créer un dossier pour l'export
mkdir -p /workspace/sync_export

# Générer le patch avec TOUTES tes modifications
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
git format-patch origin/main --stdout > /workspace/sync_export/changes_$TIMESTAMP.patch

# OU si tu n'as pas origin/main configuré
git diff HEAD > /workspace/sync_export/changes_$TIMESTAMP.patch

# Lister les fichiers modifiés
git status --short > /workspace/sync_export/files_$TIMESTAMP.txt

# Résumé des commits (si tu en as fait)
git log --oneline -20 > /workspace/sync_export/commits_$TIMESTAMP.txt
```

#### Étape 2 : Documenter la session

Ajouter une entrée dans `docs/passation.md` :

```markdown
## [YYYY-MM-DD HH:MM] - Agent: GPT Codex Cloud (Titre Session)

### Fichiers modifiés
- `chemin/fichier1.py` — description modification
- `chemin/fichier2.js` — description modification

### Contexte
Description du problème résolu ou de la feature ajoutée.

### Actions Complétées
1. Action 1
2. Action 2
3. ...

### Résultats Tests
- **Tests créés** : X tests
- **Résultat** : X/X PASSED ✅
- **Validation** : Ruff/Mypy/Build OK

### Patch Généré
📦 **Fichier** : `sync_export/changes_YYYYMMDD_HHMMSS.patch`

### Next Steps
1. Agent local doit appliquer le patch
2. Agent local doit tester (npm build, pytest)
3. Agent local doit push vers GitHub
4. Vérifier synchronisation complète
```

#### Étape 3 : Mettre à jour AGENT_SYNC.md

Modifier ta section dans `AGENT_SYNC.md` :
- Passer le statut à `✅ TERMINÉE`
- Ajouter le nom du patch généré
- Lister les prochaines actions pour l'agent local

#### Étape 4 : Informer le développeur

Message clair au développeur :

```
✅ Session terminée. Modifications prêtes pour synchronisation.

📦 PATCH GÉNÉRÉ : sync_export/changes_YYYYMMDD_HHMMSS.patch

📝 RÉSUMÉ :
- X fichiers modifiés
- [Description courte des changements]

📋 FICHIERS CRITIQUES :
- chemin/fichier1.py - [description]
- chemin/fichier2.js - [description]

🧪 TESTS :
- [Résultats des tests si applicable]
- [Validations effectuées]

🔄 PROCHAINES ÉTAPES POUR AGENT LOCAL :
1. Récupérer le patch : sync_export/changes_YYYYMMDD_HHMMSS.patch
2. Appliquer : git apply changes_YYYYMMDD_HHMMSS.patch
3. Tester : npm run build && pytest
4. Commit : git commit -m "sync: [description]"
5. Push : git push origin main
6. Mettre à jour AGENT_SYNC.md avec nouveau SHA

📄 DOCUMENTATION :
- AGENT_SYNC.md : Section mise à jour
- docs/passation.md : Nouvelle entrée ajoutée
```

---

## 🛠️ Commandes Utiles

### Vérifier l'état avant de générer le patch
```bash
# Fichiers modifiés
git status

# Différences non commitées
git diff

# Différences commitées localement
git log origin/main..HEAD --oneline

# Tous les changements (staged + unstaged)
git diff HEAD
```

### Générer différents types de patches

```bash
# Patch de tous les changements non commitées
git diff > unstaged_changes.patch

# Patch de tous les commits locaux
git format-patch origin/main --stdout > all_commits.patch

# Patch des N derniers commits
git format-patch -N --stdout > last_N_commits.patch

# Patch d'un fichier spécifique
git diff -- chemin/fichier.py > fichier_specific.patch
```

### Vérifier le contenu du patch avant export
```bash
# Voir ce qui sera dans le patch
git diff --stat HEAD

# Voir le détail ligne par ligne
git diff HEAD | less
```

---

## 🚨 Gestion des Cas Particuliers

### Si tu as fait plusieurs commits locaux
```bash
# Voir tes commits
git log --oneline -20

# Générer un patch pour chaque commit
git format-patch origin/main

# OU tout regrouper en un seul patch
git format-patch origin/main --stdout > all_changes.patch
```

### Si tu n'es pas sûr de la branche de base
```bash
# Voir toutes les branches
git branch -a

# Voir les différences avec main
git diff main

# Voir les différences avec la branche actuelle
git diff HEAD
```

### Si le dépôt cloud n'a pas de remote du tout
```bash
# Utiliser HEAD comme référence
git diff HEAD > all_uncommitted_changes.patch

# OU créer un patch depuis le début du projet (ATTENTION : gros fichier)
git format-patch --root --stdout > from_scratch.patch
```

---

## ✅ Checklist Avant de Terminer la Session

- [ ] Code développé et testé (autant que possible)
- [ ] Commits locaux faits (optionnel mais recommandé)
- [ ] Patch généré (`git format-patch` ou `git diff`)
- [ ] Fichiers modifiés listés (`git status --short`)
- [ ] `AGENT_SYNC.md` mis à jour avec ta section
- [ ] `docs/passation.md` mis à jour avec nouvelle entrée
- [ ] Message clair au développeur avec :
  - [ ] Nom du patch
  - [ ] Résumé des modifications
  - [ ] Fichiers critiques
  - [ ] Résultats tests (si applicable)
  - [ ] Prochaines étapes pour agent local

---

## 🎯 Points Clés à Retenir

### ❌ Tu NE PEUX PAS :
- Ajouter un remote Git (`git remote add` échouera)
- Push vers GitHub (`git push` échouera)
- Pull depuis GitHub (`git pull` échouera)
- Accéder à des URLs externes

### ✅ Tu PEUX :
- Modifier le code localement
- Faire des commits locaux
- Générer des patches
- Tester le code (si l'environnement le permet)
- Documenter dans `AGENT_SYNC.md` et `docs/passation.md`
- Lire tous les fichiers du projet

### 🔄 Le Workflow Complet est :
1. **Toi** (GPT Codex Cloud) → Développer + Générer patch
2. **Développeur** → Transférer patch cloud→local
3. **Agent Local** (Claude Code) → Appliquer patch + Tester + Push GitHub
4. **GitHub** → Code synchronisé et accessible à tous

---

## 📚 Documentation de Référence

- **[docs/CLOUD_LOCAL_SYNC_WORKFLOW.md](CLOUD_LOCAL_SYNC_WORKFLOW.md)** : Guide complet détaillé
- **[AGENT_SYNC.md](../AGENT_SYNC.md)** : État actuel du projet
- **[CODEV_PROTOCOL.md](../CODEV_PROTOCOL.md)** : Protocole collaboration multi-agents
- **[docs/passation.md](passation.md)** : Journal des sessions

---

## 💡 Exemple Complet de Fin de Session

```bash
# 1. Générer le patch
mkdir -p /workspace/sync_export
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
git format-patch origin/main --stdout > /workspace/sync_export/changes_$TIMESTAMP.patch
git status --short > /workspace/sync_export/files_$TIMESTAMP.txt

# 2. Vérifier le contenu
echo "📦 Patch généré : changes_$TIMESTAMP.patch"
echo ""
echo "📝 Fichiers modifiés :"
cat /workspace/sync_export/files_$TIMESTAMP.txt
echo ""
echo "📊 Taille du patch :"
wc -l /workspace/sync_export/changes_$TIMESTAMP.patch

# 3. Maintenant éditer AGENT_SYNC.md et docs/passation.md
# (utiliser tes outils d'édition)

# 4. Message final au développeur
echo "✅ Session terminée. Patch prêt : sync_export/changes_$TIMESTAMP.patch"
```

---

**Dernière mise à jour** : 2025-10-10
**Par** : Claude Code (Agent Local)
**Pour** : GPT Codex Cloud
