# Instructions pour Codex GPT Cloud — Emergence V8

**Version:** 2025-10-28 | **Agent:** Codex GPT (OpenAI)

---

## 🎯 Environnement Cloud avec Accès GitHub Direct

### Contexte Technique
- **Ton environnement** : Cloud avec accès réseau
- **Accès GitHub** : ✅ Push/pull direct possible (si token configuré)
- **Workflow** : Travail direct sur le dépôt, comme Claude Code

### Important
**Ce fichier est OBSOLÈTE si tu as accès GitHub direct.**
Utilise plutôt **[PROMPT_CODEX_CLOUD.md](../PROMPT_CODEX_CLOUD.md)** qui contient les instructions complètes et à jour.

---

## 🔄 Redirection vers Nouveau Prompt

**✅ Pour la configuration complète et à jour, voir :**

**[PROMPT_CODEX_CLOUD.md](../PROMPT_CODEX_CLOUD.md)**

Ce nouveau fichier contient :
- ✅ Nouvelle structure fichiers séparés (SYNC_STATUS.md, AGENT_SYNC_CODEX.md, passation_codex.md)
- ✅ Versioning obligatoire (PATCH/MINOR/MAJOR)
- ✅ Rotation stricte 48h passation
- ✅ Variables environnement format .env
- ✅ Ton communication cash (pas corporate)
- ✅ Workflow autonomie totale
- ✅ Templates passation + sync

---

## 📋 Ordre de Lecture (NOUVELLE STRUCTURE)

**AVANT toute session, lire dans cet ordre :**

1. **`SYNC_STATUS.md`** ← VUE D'ENSEMBLE (qui a fait quoi - 2 min)
2. **`AGENT_SYNC_CODEX.md`** ← TON FICHIER (état détaillé - 3 min)
3. **`AGENT_SYNC_CLAUDE.md`** ← FICHIER CLAUDE (comprendre l'autre agent - 2 min)
4. **`docs/passation_codex.md`** ← TON JOURNAL (48h max - 2 min)
5. **`docs/passation_claude.md`** ← JOURNAL CLAUDE (contexte croisé - 1 min)
6. **`git status` + `git log --oneline -10`** ← État Git

**Temps total:** 10 minutes (OBLIGATOIRE)

---

## ⚠️ Fichiers Obsolètes (Ne Plus Utiliser)

- ❌ `AGENT_SYNC.md` (remplacé par `AGENT_SYNC_CODEX.md` + `AGENT_SYNC_CLAUDE.md`)
- ❌ `docs/passation.md` (remplacé par `docs/passation_codex.md` + `docs/passation_claude.md`)
- ❌ `CODEX_SYSTEM_PROMPT.md` (remplacé par `PROMPT_CODEX_CLOUD.md`)

---

## 🚀 Workflow Moderne (Avec Accès GitHub)

### AVANT de coder
1. Lis `SYNC_STATUS.md` + `AGENT_SYNC_CODEX.md` + `AGENT_SYNC_CLAUDE.md`
2. `git fetch --all --prune && git status`
3. `git log --oneline -10`

### PENDANT le développement
1. Modifie le code
2. Teste (`npm run build`, `pytest`)
3. Commit local (`git commit -m "..."`)

### APRÈS le développement
1. Incrémente version (src/version.js + src/frontend/version.js + package.json)
2. Mets à jour `AGENT_SYNC_CODEX.md` + `docs/passation_codex.md`
3. Push direct (`git push origin <branche>`)

**Voir [PROMPT_CODEX_CLOUD.md](../PROMPT_CODEX_CLOUD.md) pour détails complets.**

---

## 📚 Documentation de Référence (À Jour)

**Fichiers à utiliser :**
- ✅ **[PROMPT_CODEX_CLOUD.md](../PROMPT_CODEX_CLOUD.md)** - Prompt cloud complet (2025-10-28)
- ✅ **[SYNC_STATUS.md](../SYNC_STATUS.md)** - Vue d'ensemble projet
- ✅ **[AGENT_SYNC_CODEX.md](../AGENT_SYNC_CODEX.md)** - TON état sync
- ✅ **[AGENT_SYNC_CLAUDE.md](../AGENT_SYNC_CLAUDE.md)** - État Claude Code
- ✅ **[docs/passation_codex.md](passation_codex.md)** - TON journal (48h)
- ✅ **[docs/passation_claude.md](passation_claude.md)** - Journal Claude (48h)
- ✅ **[CODEV_PROTOCOL.md](../CODEV_PROTOCOL.md)** - Protocole multi-agents
- ✅ **[CODEX_GPT_GUIDE.md](../CODEX_GPT_GUIDE.md)** - Guide complet local

**Fichiers obsolètes (NE PLUS UTILISER) :**
- ❌ `AGENT_SYNC.md` (remplacé)
- ❌ `docs/passation.md` (remplacé)
- ❌ `CODEX_SYSTEM_PROMPT.md` (remplacé)
- ❌ `docs/CLOUD_LOCAL_SYNC_WORKFLOW.md` (workflow patches obsolète)

---

**Dernière mise à jour** : 2025-10-28
**Par** : Claude Code
**Statut** : ⚠️ FICHIER OBSOLÈTE - Utiliser [PROMPT_CODEX_CLOUD.md](../PROMPT_CODEX_CLOUD.md) à la place
