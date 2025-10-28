# 🤖 Configuration Claude Code Cloud - Emergence V8

**Version :** 2025-10-28
**Pour :** Claude Code (Anthropic)
**Projet :** Emergence V8

---

## 🎯 Configuration Optimale Cloud Environment

### **Nom de l'environnement**
```
EmergenceV8-Production
```

### **Accès réseau**
```
Accès réseau de confiance
```
(Permet accès API externes, WebFetch, gcloud CLI)

### **Variables d'environnement**

**Format .env (copier-coller direct dans l'interface cloud) :**

```env
PROJECT_NAME=EmergenceV8
WORKING_DIR=c:/dev/emergenceV8
PYTHON_VERSION=3.11
NODE_VERSION=18
AUTO_UPDATE_DOCS=1
AUTO_APPLY=1
ENABLE_GUARDIAN=1
BACKEND_PORT=8000
FRONTEND_PORT=3000
GCP_PROJECT=emergence-469005
GCP_REGION=europe-west1
GCP_SERVICE=emergence-app
TZ=Europe/Zurich
LANG=fr_FR.UTF-8
```

---

## 📋 Checklist Configuration

### ✅ Permissions à activer

**Outils essentiels :**
- ✅ `*` (wildcard - permet tout par défaut)
- ✅ `Bash` (commandes shell)
- ✅ `Read` (lecture fichiers)
- ✅ `Edit` (modification fichiers)
- ✅ `Write` (création fichiers)
- ✅ `Glob` (recherche patterns)
- ✅ `Grep` (recherche contenu)
- ✅ `Task` (sous-agents)
- ✅ `WebFetch` (fetch docs)
- ✅ `WebSearch` (recherche web)

**Commandes Git :**
- ✅ `Bash(git:*)` - Toutes commandes Git
- ✅ `Bash(gh:*)` - GitHub CLI (PR, issues)

**Commandes Dev :**
- ✅ `Bash(npm:*)` - Node.js/npm
- ✅ `Bash(pytest:*)` - Tests Python
- ✅ `Bash(python:*)` - Python
- ✅ `Bash(pwsh:*)` - PowerShell
- ✅ `Bash(ruff:*)` - Linter Python
- ✅ `Bash(mypy:*)` - Type checker Python

**Commandes Cloud :**
- ✅ `Bash(gcloud:*)` - Google Cloud CLI
- ✅ `Bash(docker:*)` - Docker

**Patterns fichiers (Read) :**
- ✅ `Read(**/*.py)` - Python
- ✅ `Read(**/*.js)` - JavaScript
- ✅ `Read(**/*.ts)` - TypeScript
- ✅ `Read(**/*.json)` - JSON
- ✅ `Read(**/*.md)` - Markdown
- ✅ `Read(**/*.yaml)` - YAML
- ✅ `Read(**/*.yml)` - YAML
- ✅ `Read(**/*.ps1)` - PowerShell
- ✅ `Read(**/*.sh)` - Bash
- ✅ `Read(**/*.env*)` - Env files
- ✅ `Read(**/*.txt)` - Texte
- ✅ `Read(**/*.sql)` - SQL
- ✅ `Read(**/*.css)` - CSS
- ✅ `Read(**/*.html)` - HTML

**Dossiers importants (Read) :**
- ✅ `Read(.claude/**)` - Config Claude
- ✅ `Read(docs/**)` - Documentation
- ✅ `Read(src/**)` - Code source
- ✅ `Read(scripts/**)` - Scripts
- ✅ `Read(tests/**)` - Tests
- ✅ `Read(reports/**)` - Rapports Guardian
- ✅ `Read(claude-plugins/**)` - Plugins
- ✅ `Read(.vscode/**)` - Config VSCode
- ✅ `Read(.github/**)` - GitHub Actions

**Patterns fichiers (Edit) :**
- ✅ `Edit(**/*.py)` - Python
- ✅ `Edit(**/*.js)` - JavaScript
- ✅ `Edit(**/*.ts)` - TypeScript
- ✅ `Edit(**/*.json)` - JSON
- ✅ `Edit(**/*.md)` - Markdown
- ✅ `Edit(**/*.yaml)` - YAML
- ✅ `Edit(**/*.yml)` - YAML
- ✅ `Edit(**/*.ps1)` - PowerShell
- ✅ `Edit(**/*.sh)` - Bash
- ✅ `Edit(**/*.css)` - CSS
- ✅ `Edit(**/*.html)` - HTML

**Fichiers critiques (Edit) :**
- ✅ `Edit(.claude/settings.local.json)` - Config locale
- ✅ `Edit(SYNC_STATUS.md)` - Vue d'ensemble sync
- ✅ `Edit(AGENT_SYNC_CLAUDE.md)` - État Claude
- ✅ `Edit(AGENT_SYNC_CODEX.md)` - État Codex
- ✅ `Edit(docs/passation_claude.md)` - Journal Claude
- ✅ `Edit(docs/passation_codex.md)` - Journal Codex
- ✅ `Edit(CLAUDE.md)` - Config Claude
- ✅ `Edit(CODEV_PROTOCOL.md)` - Protocole
- ✅ `Edit(CODEX_GPT_GUIDE.md)` - Guide Codex
- ✅ `Edit(package.json)` - Dépendances Node
- ✅ `Edit(requirements.txt)` - Dépendances Python
- ✅ `Edit(CHANGELOG.md)` - Changelog
- ✅ `Edit(ROADMAP.md)` - Roadmap

**Patterns fichiers (Write) :**
- ✅ `Write(**/*.py)` - Python (nouveaux)
- ✅ `Write(**/*.js)` - JavaScript (nouveaux)
- ✅ `Write(**/*.ts)` - TypeScript (nouveaux)
- ✅ `Write(**/*.md)` - Markdown (nouveaux)
- ✅ `Write(**/*.json)` - JSON (nouveaux)
- ✅ `Write(**/*.yaml)` - YAML (nouveaux)
- ✅ `Write(**/*.css)` - CSS (nouveaux)
- ✅ `Write(**/*.html)` - HTML (nouveaux)
- ✅ `Write(reports/**)` - Rapports
- ✅ `Write(docs/**)` - Documentation
- ✅ `Write(tests/**)` - Tests
- ✅ `Write(**/*.backup)` - Backups

### ❌ Permissions à REFUSER (Deny)

**Fichiers sensibles :**
- ❌ `Write(.env)` - Secrets jamais modifiés directement
- ❌ `Write(**/*secret*)` - Fichiers secrets
- ❌ `Write(**/*password*)` - Fichiers passwords
- ❌ `Write(**/*key*.json)` - Clés API/GCP

**Commandes dangereuses :**
- ❌ `Bash(rm -rf /)` - Destruction système
- ❌ `Bash(rm -rf *)` - Suppression massive
- ❌ `Bash(git push --force origin main)` - Force push main
- ❌ `Bash(gcloud run deploy --no-confirm)` - Déploiement non confirmé

---

## 🚀 Configuration Complète Cloud

### **Variables d'environnement (format .env)**

**Copier-coller dans le champ "Variables d'environnement" :**

```env
PROJECT_NAME=EmergenceV8
WORKING_DIR=c:/dev/emergenceV8
PYTHON_VERSION=3.11
NODE_VERSION=18
AUTO_UPDATE_DOCS=1
AUTO_APPLY=1
ENABLE_GUARDIAN=1
BACKEND_PORT=8000
FRONTEND_PORT=3000
GCP_PROJECT=emergence-469005
GCP_REGION=europe-west1
GCP_SERVICE=emergence-app
TZ=Europe/Zurich
LANG=fr_FR.UTF-8
```

### **Permissions - Liste complète**

**⚠️ IMPORTANT :** Dans l'interface cloud Claude Code, tu dois cocher les permissions une par une. Voici la liste complète à activer :

**Permissions générales (OBLIGATOIRES) :**
- ✅ `*` (wildcard - permet tout par défaut)
- ✅ `Bash` (toutes commandes shell)
- ✅ `Read` (lecture fichiers)
- ✅ `Edit` (modification fichiers)
- ✅ `Write` (création fichiers)
- ✅ `Glob` (recherche patterns)
- ✅ `Grep` (recherche contenu)
- ✅ `Task` (lancer sous-agents)
- ✅ `WebFetch` (fetch documentation)
- ✅ `WebSearch` (recherche web)

**Permissions spécifiques - Liste complète à activer :**

```
Bash(git:*)
Bash(gh:*)
Bash(npm:*)
Bash(pytest:*)
Bash(python:*)
Bash(pwsh:*)
Bash(docker:*)
Bash(gcloud:*)
Bash(ruff:*)
Bash(mypy:*)
Read(**/*.py)
Read(**/*.js)
Read(**/*.ts)
Read(**/*.json)
Read(**/*.md)
Read(**/*.yaml)
Read(**/*.yml)
Read(**/*.ps1)
Read(**/*.sh)
Read(**/*.env*)
Read(**/*.txt)
Read(**/*.sql)
Read(**/*.css)
Read(**/*.html)
Read(.claude/**)
Read(docs/**)
Read(src/**)
Read(scripts/**)
Read(tests/**)
Read(reports/**)
Read(claude-plugins/**)
Read(.vscode/**)
Read(.github/**)
Edit(**/*.py)
Edit(**/*.js)
Edit(**/*.ts)
Edit(**/*.json)
Edit(**/*.md)
Edit(**/*.yaml)
Edit(**/*.yml)
Edit(**/*.ps1)
Edit(**/*.sh)
Edit(**/*.css)
Edit(**/*.html)
Edit(.claude/settings.local.json)
Edit(SYNC_STATUS.md)
Edit(AGENT_SYNC_CLAUDE.md)
Edit(AGENT_SYNC_CODEX.md)
Edit(docs/passation_claude.md)
Edit(docs/passation_codex.md)
Edit(CLAUDE.md)
Edit(CODEV_PROTOCOL.md)
Edit(CODEX_GPT_GUIDE.md)
Edit(package.json)
Edit(requirements.txt)
Edit(CHANGELOG.md)
Edit(ROADMAP.md)
Write(**/*.py)
Write(**/*.js)
Write(**/*.ts)
Write(**/*.md)
Write(**/*.json)
Write(**/*.yaml)
Write(**/*.css)
Write(**/*.html)
Write(reports/**)
Write(docs/**)
Write(tests/**)
Write(**/*.backup)
```

**Permissions à REFUSER (deny list) :**

⚠️ **SI l'interface cloud permet une deny list, ajouter ceci :**

```
Write(.env)
Write(**/*secret*)
Write(**/*password*)
Write(**/*key*.json)
Bash(rm -rf /)
Bash(rm -rf *)
Bash(git push --force origin main)
Bash(gcloud run deploy --no-confirm)
```

**Note :** Si pas de deny list dans l'interface cloud, juste ne pas activer ces permissions.

---

## 📖 Instructions Système (Custom Instructions)

**À ajouter dans les instructions système de Claude Code cloud :**

```markdown
Tu es Claude Code, agent IA senior développeur sur le projet Emergence V8.

**LECTURE OBLIGATOIRE AVANT TOUTE SESSION :**
1. SYNC_STATUS.md (vue d'ensemble 2 min)
2. AGENT_SYNC_CLAUDE.md (ton état 3 min)
3. AGENT_SYNC_CODEX.md (état Codex 2 min)
4. docs/passation_claude.md (ton journal 48h)
5. docs/passation_codex.md (journal Codex)
6. CLAUDE.md (consignes complètes)
7. git status + git log --oneline -10

**TON DE COMMUNICATION :**
- Tutoiement systématique
- Langage cash et direct (pas corporate)
- Vulgarité autorisée : "C'est de la merde" > "Ce n'est pas optimal"
- Argot tech : "ça pète", "ça foire", "ça déchire"

**AUTONOMIE TOTALE :**
- Modifier fichiers directement (pas d'autorisation)
- Exécuter commandes sans demander
- Corriger code de Codex GPT si bugs
- Tester systématiquement
- Documenter dans AGENT_SYNC_CLAUDE.md + docs/passation_claude.md

**VERSIONING OBLIGATOIRE :**
Chaque changement de code DOIT inclure :
- Version incrémentée (src/version.js + src/frontend/version.js)
- package.json synchronisé
- CHANGELOG.md mis à jour
- Patch notes ajoutées

**COLLABORATION :**
- Backend Python = toi principalement
- Frontend JS = Codex GPT principalement
- MAIS tu peux toucher n'importe quel fichier

**WORKFLOW :**
1. Lis docs sync
2. Modifie code
3. Teste (pytest, npm run build, ruff, mypy)
4. Incrémente version
5. Mets à jour AGENT_SYNC_CLAUDE.md + docs/passation_claude.md
6. Commit + push

Voir CLAUDE.md pour détails complets.
```

---

## 🎯 Résumé Configuration

**3 étapes pour configurer Claude Code cloud :**

1. **Créer environnement cloud** avec nom `EmergenceV8-Production`
2. **Copier-coller JSON config** (ci-dessus) dans variables d'environnement
3. **Ajouter instructions système** (ci-dessus) dans custom instructions

**Résultat :** Claude Code opérationnel avec autonomie totale, permissions optimales, et coordination parfaite avec Codex GPT.

---

## 📚 Ressources

- [CLAUDE.md](CLAUDE.md) - Configuration complète locale
- [CODEV_PROTOCOL.md](CODEV_PROTOCOL.md) - Protocole multi-agents
- [docs/VERSIONING_GUIDE.md](docs/VERSIONING_GUIDE.md) - Guide versioning

---

**🤖 Configuration créée le 2025-10-28 par Claude Code**
