# 📦 Archive Octobre 2025 - Cleanup Docs Racine

**Date cleanup:** 2025-10-23
**Agent:** Claude Code
**Contexte:** P1.1 - Cleanup documentation racine (33 → 14 fichiers .md)

---

## 🎯 Objectif du Cleanup

Réduire le nombre de fichiers .md dans la racine du projet pour améliorer la navigation et la clarté.

**Avant cleanup:** 33 fichiers .md
**Après cleanup:** 14 fichiers .md (+ CONTRIBUTING.md)
**Réduction:** -19 fichiers (-58%)

---

## 📂 Structure Archive

```
docs/archive/2025-10/
├── audits-anciens/          # Audits remplacés par versions plus récentes
├── bugs-resolus/            # Investigations de bugs terminées
├── prompts-sessions/        # Prompts de sessions passées
├── setup/                   # Setups terminés et documentés ailleurs
├── guides-obsoletes/        # Guides remplacés par versions plus récentes
├── temporaire/              # Fichiers temporaires de test
└── benchmarks/              # READMEs de benchmarks
```

---

## 📋 Fichiers Archivés (19 total)

### 🗂️ Audits Anciens (3 fichiers)

| Fichier | Date | Raison Archivage |
|---------|------|------------------|
| `AUDIT_COMPLET_2025-10-18.md` | 2025-10-18 | Remplacé par AUDIT_COMPLET_2025-10-23.md |
| `AUDIT_COMPLET_2025-10-21.md` | 2025-10-21 | Remplacé par AUDIT_COMPLET_2025-10-23.md |
| `AUDIT_CLOUD_SETUP.md` | ? | Audit cloud setup terminé |

**Nouveaux audits:** Utiliser `AUDIT_COMPLET_2025-10-23.md` (racine)

---

### 🐛 Bugs Résolus (2 fichiers)

| Fichier | Date | Raison Archivage |
|---------|------|------------------|
| `BUG_STREAMING_CHUNKS_INVESTIGATION.md` | 2025-10-18 | ✅ Bug résolu - Streaming chunks fix implémenté |
| `FIX_PRODUCTION_DEPLOYMENT.md` | ? | ✅ Fix production deployment terminé |

**Statut:** Bugs résolus et fixes intégrés en production.

---

### 📝 Prompts Sessions (6 fichiers)

| Fichier | Date | Raison Archivage |
|---------|------|------------------|
| `NEXT_SESSION_PROMPT.md` | 2025-10-21 | Prompt Mypy batch 2 - Session dépassée |
| `PROMPT_CODEX_RAPPORTS.md` | 2025-10-21 | Dupliqué avec CODEX_GPT_GUIDE.md section 9.3 |
| `PROMPT_PHASE_2_GUARDIAN.md` | 2025-10-19 | Prompt Phase 2 Guardian Cloud - Session terminée |
| `PROMPT_RAPPORTS_GUARDIAN.md` | ? | Dupliqué avec PROMPT_CODEX_RAPPORTS.md |
| `PROMPT_SUITE_AUDIT.md` | 2025-10-18 | Prompt suite audit dashboard admin - Fait |
| `CODEX_GPT_SYSTEM_PROMPT.md` | ? | System prompt Codex - Obsolète |

**Note:** Ces prompts étaient utilisés pour des sessions spécifiques maintenant terminées.

---

### ⚙️ Setup Terminés (3 fichiers)

| Fichier | Date | Raison Archivage |
|---------|------|------------------|
| `CLAUDE_AUTO_MODE_SETUP.md` | 2025-10-18 | Setup terminé et documenté dans CLAUDE.md |
| `GUARDIAN_SETUP_COMPLETE.md` | ? | Setup Guardian terminé |
| `CODEX_CLOUD_GMAIL_SETUP.md` | ? | Setup Gmail Guardian Cloud terminé |

**Documentation actuelle:** Voir `CLAUDE.md` et `docs/GUARDIAN_COMPLETE_GUIDE.md`

---

### 📚 Guides Obsolètes (2 fichiers)

| Fichier | Date | Raison Archivage |
|---------|------|------------------|
| `CLAUDE_CODE_GUIDE.md` | 2025-10-16 | Remplacé par CLAUDE.md (2025-10-23, plus complet) |
| `GUARDIAN_AUTOMATION.md` | ? | Redondant avec docs/GUARDIAN_COMPLETE_GUIDE.md |

**Nouveaux guides:** Utiliser `CLAUDE.md` et `docs/GUARDIAN_COMPLETE_GUIDE.md`

---

### 🧪 Temporaires (1 fichier)

| Fichier | Date | Raison Archivage |
|---------|------|------------------|
| `TEST_WORKFLOWS.md` | 2025-10-21 | Fichier test temporaire (11 lignes) |

**Note:** Fichier de test GitHub Actions, quasi-vide.

---

### 📊 Benchmarks (1 fichier)

| Fichier | Date | Raison Archivage |
|---------|------|------------------|
| `MEMORY_BENCHMARK_README.md` | ? | README benchmark memory |

**Note:** À vérifier si benchmarks existent encore.

---

## ✅ Fichiers Conservés dans Racine (15 fichiers)

### Critiques (référencés dans docs architecture)

1. **AGENT_SYNC.md** - Sync inter-agents OBLIGATOIRE
2. **AGENTS.md** - Consignes générales agents
3. **CLAUDE.md** - Config Claude Code (mise à jour 2025-10-23)
4. **CODEV_PROTOCOL.md** - Protocole multi-agents
5. **CODEX_GPT_GUIDE.md** - Guide Codex GPT
6. **ROADMAP_OFFICIELLE.md** - Roadmap master P0/P1/P2/P3
7. **ROADMAP_PROGRESS.md** - Suivi progression (74%)
8. **DEPLOYMENT_MANUAL.md** - Procédure déploiement officielle
9. **DEPLOYMENT_SUCCESS.md** - État production actuel
10. **CHANGELOG.md** - Historique versions
11. **README.md** - Readme projet

### Utiles (récents/pertinents)

12. **AUDIT_COMPLET_2025-10-23.md** - Audit complet le plus récent
13. **GUIDE_INTERFACE_BETA.md** - Guide utilisateur beta
14. **CANARY_DEPLOYMENT.md** - Déploiement avancé (canary)
15. **CONTRIBUTING.md** - Guide contribution

---

## 🔄 Récupération Fichiers Archivés

Si tu as besoin d'un fichier archivé:

```bash
# Lister fichiers archive
ls docs/archive/2025-10/

# Copier un fichier archivé vers racine
cp docs/archive/2025-10/prompts-sessions/NEXT_SESSION_PROMPT.md .

# Voir contenu d'un fichier archivé
cat docs/archive/2025-10/bugs-resolus/BUG_STREAMING_CHUNKS_INVESTIGATION.md
```

---

## 📊 Statistiques Cleanup

| Métrique | Avant | Après | Delta |
|----------|-------|-------|-------|
| **Fichiers .md racine** | 33 | 14 | -19 (-58%) |
| **Audits racine** | 3 | 1 | -2 |
| **Prompts racine** | 6 | 0 | -6 |
| **Guides racine** | 4 | 2 | -2 |

**Impact:** Navigation racine beaucoup plus claire, fichiers essentiels facilement identifiables.

---

## 🔗 Références

**Documentation cleanup:**
- Analyse complète: `CLEANUP_ANALYSIS.md` (temporaire, supprimé après commit)
- Session passation: `docs/passation.md` entrée 2025-10-23
- État sync: `AGENT_SYNC.md` session 2025-10-23

**Checklist architecture:**
- Tous les fichiers critiques référencés dans `docs/architecture/AGENTS_CHECKLIST.md` ont été conservés
- Aucun fichier requis pour l'architecture n'a été archivé

---

**🤖 Archive créée par:** Claude Code
**Date:** 2025-10-23
**Commit:** (voir git log)
