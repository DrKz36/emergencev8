# Architecture Prompts Agents - Emergence V8

**Date :** 2025-10-24
**Dernière MAJ :** Harmonisation complète protocole multi-agents

---

## 📁 Structure Prompts (après nettoyage)

### Prompts Système ACTIFS (racine)

| Fichier | Agent | Rôle | Statut |
|---------|-------|------|--------|
| **CLAUDE.md** | Claude Code | Prompt système complet | ✅ ACTIF |
| **CODEX_SYSTEM_PROMPT.md** | Codex GPT (local & cloud) | Prompt système complet | ✅ ACTIF |
| **PROMPT_CODEX_ALTER_EGO.md** | Alter ego Codex (backup) | Prise de relai + feedback blocages | ✅ ACTIF |
| **AGENTS.md** | Tous agents | Consignes générales dépôt | ✅ ACTIF |
| **CODEV_PROTOCOL.md** | Tous agents | Protocole co-développement | ✅ ACTIF |

### Guides Complémentaires (racine)

| Fichier | Rôle | Statut |
|---------|------|--------|
| **CODEX_GPT_GUIDE.md** | Guide détaillé Codex (référence) | ⚠️ À SUPPRIMER (redondant) |
| **CODEX_CLOUD_QUICKSTART.txt** | Quickstart Codex cloud | ⚠️ À MIGRER dans docs/ |

### Archives (docs/archive/)

Tous les anciens prompts sont dans `docs/archive/2025-10/prompts-sessions/` et `docs/archive/prompts/`.

**Ne JAMAIS utiliser les prompts archivés !**

---

## 🔄 Ordre de Lecture Harmonisé (TOUS agents)

**Identique pour Claude Code, Codex GPT, et tous futurs agents :**

1. **Docs Architecture** : `docs/architecture/AGENTS_CHECKLIST.md`, `00-Overview.md`, `10-Components.md`, `30-Contracts.md`
2. **`AGENT_SYNC.md`** : État sync inter-agents
3. **`CODEV_PROTOCOL.md`** : Protocole co-développement (sections 2.1, 4, 6)
4. **`docs/passation.md`** : Journal inter-agents (3 dernières entrées)
5. **`git status` + `git log --oneline -10`** : État Git

**Temps lecture : 10-15 minutes** (investissement obligatoire pour éviter erreurs/conflits)

---

## 📊 Matrice Cohérence Prompts

| Aspect | CLAUDE.md | CODEX_SYSTEM_PROMPT.md | AGENTS.md | CODEV_PROTOCOL.md |
|--------|-----------|------------------------|-----------|-------------------|
| **Ordre lecture** | ✅ Archi → AGENT_SYNC → CODEV → passation → git | ✅ Identique | ✅ Identique | ✅ Identique |
| **Docs Architecture** | ✅ Section 1 (détaillée) | ✅ Point 1 (avec checklist) | ✅ Point 1 (sections 10 & 13) | ✅ Point 1 |
| **Ton communication** | ✅ Mode vrai (vulgarité OK) | ✅ Mode vrai (vulgarité OK) | ❌ Professionnel | ❌ Professionnel |
| **Autonomie** | ✅ Totale (pas de demande permission) | ✅ Totale (pas de demande permission) | ✅ Autonomie | ✅ Autonomie |
| **Template passation** | ✅ Référence vers CODEV | ✅ Template détaillé (CODEV 2.1) | ✅ Référence vers CODEV | ✅ Section 2.1 (source) |
| **Guardian hooks** | ✅ Documenté | ✅ Documenté | ✅ Documenté (détaillé) | ✅ Documenté (détaillé) |

---

## 🎯 Workflow Utilisation

### Pour Claude Code

1. IDE charge automatiquement `CLAUDE.md` comme contexte système
2. Claude Code lit `CLAUDE.md` qui référence `CODEV_PROTOCOL.md`
3. Ordre lecture respecté : Archi → AGENT_SYNC → CODEV → passation → git

### Pour Codex GPT Local

1. Copier/coller manuellement `CODEX_SYSTEM_PROMPT.md` dans le chat **OU**
2. Référencer `CODEX_SYSTEM_PROMPT.md` dans la configuration IDE (Windsurf/VS Code)
3. Ordre lecture respecté : Archi → AGENT_SYNC → CODEV → passation → git

### Pour Codex GPT Cloud (ChatGPT Custom GPT)

1. Configurer Instructions GPT avec contenu de `CODEX_SYSTEM_PROMPT.md`
2. Codex cloud lit automatiquement le prompt système au démarrage
3. Ordre lecture respecté : Archi → AGENT_SYNC → CODEV → passation → git

---

## 🔥 Différences Spécifiques Agents

### Claude Code (CLAUDE.md)

**Spécificités :**
- Ton "Mode vrai" avec vulgarité autorisée (demande explicite utilisateur)
- Workflow intégré IDE (read/edit/write tools)
- Permissions auto dans `.claude/settings.local.json`
- Focus backend Python, architecture, tests

### Codex GPT (CODEX_SYSTEM_PROMPT.md)

**Spécificités :**
- Ton "Mode vrai" avec vulgarité autorisée (même que Claude Code)
- Accès rapports Guardian (`reports/codex_summary.md`)
- Focus frontend JavaScript, scripts PowerShell, UI/UX
- Instructions Python pour lire rapports locaux

### Alter Ego Codex (PROMPT_CODEX_ALTER_EGO.md)

**Spécificités :**
- Destiné à un backup/alter ego qui reprend Codex en cas d'indisponibilité
- Redemande l'ordre de lecture complet avant toute action
- Met l'accent sur le feedback immédiat : blocages consignés dans AGENT_SYNC_CODEX.md + docs/passation_codex.md, ping explicite @Codex GPT -> feedback needed
- Implique les mêmes obligations de tests, doc et ton que le prompt principal

### Consignes Générales (AGENTS.md)

**Spécificités :**
- Ton professionnel (pas de vulgarité)
- Sections détaillées : env, Git, tests, CI/CD
- Hooks Guardian détaillés
- Workflow cloud ↔ local

### Protocole Co-Dev (CODEV_PROTOCOL.md)

**Spécificités :**
- Ton professionnel (pas de vulgarité)
- Source de vérité pour :
  - Template passation (section 2.1)
  - Checklist avant soumission (section 4)
  - Anti-patterns (section 6)
  - Exemples collaboration (section 5)

---

## 🚨 Règles ABSOLUES

1. **NE JAMAIS utiliser prompts archivés** (`docs/archive/prompts/` ou `docs/archive/2025-10/prompts-sessions/`)
2. **Ordre lecture identique** pour TOUS les agents (Archi → AGENT_SYNC → CODEV → passation → git)
3. **Template passation unique** : Source = CODEV_PROTOCOL.md section 2.1 (autres fichiers référencent)
4. **Pas de duplication** : Si info dans CODEV_PROTOCOL.md, référencer (ne pas dupliquer)
5. **Mise à jour synchronisée** : Modifier un aspect = vérifier cohérence dans les 4 prompts actifs

---

## 📝 Maintenance

### Ajouter une nouvelle règle

1. Identifier portée : Tous agents (CODEV) vs spécifique Claude/Codex
2. Si TOUS agents → Ajouter dans `CODEV_PROTOCOL.md` (source)
3. Référencer dans `CLAUDE.md` et `CODEX_SYSTEM_PROMPT.md`
4. Tester cohérence : Grep références croisées

### Modifier ordre lecture

1. Modifier dans `CODEV_PROTOCOL.md` section 2.2
2. Répercuter dans `CLAUDE.md` section 2
3. Répercuter dans `CODEX_SYSTEM_PROMPT.md` section ordre lecture
4. Répercuter dans `AGENTS.md` sections 10 & 13
5. Commit atomique : "docs(protocol): Harmoniser ordre lecture"

### Archiver ancien prompt

1. Déplacer vers `docs/archive/2025-10/prompts-sessions/`
2. Ajouter note `[OBSOLÈTE - 2025-XX-XX]` en haut du fichier
3. Documenter raison archivage dans commit message
4. Mettre à jour `PROMPTS_AGENTS_ARCHITECTURE.md` (ce fichier)

---

## 🔍 Diagnostic Cohérence

```bash
# Vérifier ordre lecture partout
grep -n "AGENT_SYNC.md" CLAUDE.md CODEX_SYSTEM_PROMPT.md AGENTS.md CODEV_PROTOCOL.md

# Vérifier docs architecture
grep -n "docs/architecture" CLAUDE.md CODEX_SYSTEM_PROMPT.md AGENTS.md CODEV_PROTOCOL.md

# Vérifier références CODEV_PROTOCOL.md
grep -n "CODEV_PROTOCOL" CLAUDE.md CODEX_SYSTEM_PROMPT.md AGENTS.md

# Vérifier template passation
grep -n "passation" CODEV_PROTOCOL.md
```

---

## ✅ Checklist Harmonisation (2025-10-24)

- [x] ARBO-LOCK supprimé (6 fichiers)
- [x] Ordre lecture unifié (4 fichiers prompts)
- [x] Docs Architecture en premier partout
- [x] CODEV_PROTOCOL.md référencé partout
- [x] Template passation unique (CODEV source)
- [x] Roadmap Strategique.txt → ROADMAP.md
- [x] CODEX_SYSTEM_PROMPT.md créé (unifié racine)
- [x] PROMPTS_AGENTS_ARCHITECTURE.md créé (doc architecture)
- [ ] CODEX_GPT_GUIDE.md à supprimer (redondant)
- [ ] CODEX_CLOUD_QUICKSTART.txt à migrer docs/
- [ ] Tester avec Codex local/cloud

---

**🤖 Tous les prompts agents sont maintenant harmonisés. Un seul protocole, zéro confusion. 🚀**
