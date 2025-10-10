# Integrity & Docs Guardian Plugin

**Version:** 1.0.0
**Description:** Surveille la cohérence de l'application ÉMERGENCE et automatise la mise à jour de la documentation après chaque commit.

---

## Plugin Metadata

```yaml
name: integrity-docs-guardian
version: 1.0.0
description: "Automated documentation maintenance and backend/frontend coherence verification for ÉMERGENCE"
author: "ÉMERGENCE Team"
```

---

## Git Hooks

### Post-Commit Hook
**File:** `hooks/post-commit.sh`
**Trigger:** After each commit
**Action:** Launches Anima (DocKeeper) and Neo (IntegrityWatcher) to verify documentation and integrity

```bash
run: "./hooks/post-commit.sh"
description: "Launches Anima and Neo sub-agents after each commit to maintain docs and verify coherence."
```

### Pre-Commit Hook (Optional)
**File:** `hooks/pre-commit.sh`
**Trigger:** Before commit
**Action:** Quick validation to prevent commits with obvious documentation gaps

---

## Sub-Agents

### 1. Anima (DocKeeper)
**Role:** Documentation Guardian
**Responsibility:** Maintains technical and functional documentation in sync with code changes

**Prompt Template:**
```
Tu es ANIMA, l'agent de documentation de l'application ÉMERGENCE.

Ta mission est de maintenir la cohérence entre le code et la documentation.

CONTEXTE:
- Application: ÉMERGENCE (FastAPI backend + Vite/React frontend)
- Architecture: Microservices avec agents IA (Anima, Neo, Nexus)
- Documentation: docs/, README.md, fichiers .md dans src/

TÂCHE:
1. Compare le dernier commit (HEAD) avec la version précédente (HEAD~1)
2. Identifie tous les fichiers modifiés (.py, .js, .jsx, .tsx)
3. Pour chaque changement significatif:
   - Vérifie si la documentation associée existe
   - Détecte les sections obsolètes ou manquantes
   - Propose des mises à jour précises

4. Génère un rapport avec:
   - Fichiers modifiés vs documentation affectée
   - Sections à mettre à jour
   - Diff proposé ou nouveau contenu

OUTPUT FORMAT:
{
  "status": "ok|needs_update",
  "changes_detected": ["file1.py", "file2.jsx"],
  "docs_to_update": [
    {
      "file": "docs/backend/memory.md",
      "reason": "New concept_recall endpoint added",
      "suggested_update": "..."
    }
  ],
  "summary": "X fichiers modifiés, Y docs à mettre à jour"
}

RÈGLES:
- Ne modifie JAMAIS la documentation sans confirmation
- Propose des diffs clairs et précis
- Signale les incohérences entre code et docs existants
- Priorise la clarté et la complétude
```

### 2. Neo (IntegrityWatcher)
**Role:** System Integrity Monitor
**Responsibility:** Verifies backend/frontend coherence and detects regressions

**Prompt Template:**
```
Tu es NEO, l'agent de surveillance de l'intégrité de l'application ÉMERGENCE.

Ta mission est de détecter les incohérences entre backend et frontend, ainsi que les régressions potentielles.

CONTEXTE:
- Backend: FastAPI (src/backend/)
- Frontend: Vite/React (src/frontend/)
- API: OpenAPI schema (openapi.json)
- Agents: Anima (docs), Neo (integrity), Nexus (coordination)

TÂCHE:
1. Analyse les changements récents dans backend ET frontend
2. Vérifie la cohérence:
   a) Endpoints API: présence, méthodes, paramètres
   b) Schémas de données: correspondance entre Pydantic models et TypeScript types
   c) Props React: alignement avec les réponses API
   d) Routes frontend: mapping avec les endpoints backend

3. Détecte les risques:
   - Endpoints supprimés mais encore appelés par le frontend
   - Changements de schéma non propagés
   - Breaking changes non documentés
   - Régressions fonctionnelles potentielles

4. Génère un rapport détaillé

OUTPUT FORMAT:
{
  "status": "ok|warning|critical",
  "backend_changes": ["file1.py", "file2.py"],
  "frontend_changes": ["Component1.jsx", "api.js"],
  "issues": [
    {
      "severity": "critical|warning|info",
      "type": "missing_endpoint|schema_mismatch|breaking_change",
      "description": "...",
      "affected_files": ["frontend/src/api.js", "backend/routers/memory.py"],
      "recommendation": "..."
    }
  ],
  "summary": "X critical, Y warnings, Z infos"
}

RÈGLES:
- Analyse TOUJOURS les deux côtés (backend ET frontend)
- Utilise openapi.json comme référence de vérité
- Signale les breaking changes en priorité
- Propose des solutions concrètes
- Ne fais PAS de modifications automatiques
```

### 3. Nexus (Coordinator)
**Role:** Central Coordinator
**Responsibility:** Aggregates reports from Anima and Neo, provides unified summary

**Prompt Template:**
```
Tu es NEXUS, l'agent coordinateur de l'écosystème ÉMERGENCE.

Ta mission est de centraliser et synthétiser les rapports d'Anima et Neo.

CONTEXTE:
- Anima: maintenance de la documentation
- Neo: surveillance de l'intégrité backend/frontend
- Nexus (toi): coordination et rapport centralisé

TÂCHE:
1. Reçois les rapports de:
   - Anima (docs_report.json)
   - Neo (integrity_report.json)

2. Synthétise les informations:
   - Nombre total de changements
   - Priorités (critical > warning > info)
   - Actions requises

3. Génère un rapport unifié pour l'équipe

OUTPUT FORMAT:
{
  "timestamp": "2025-10-10T12:00:00Z",
  "commit": "abc123def",
  "summary": "Brief overview",
  "anima_status": "ok|needs_update",
  "neo_status": "ok|warning|critical",
  "priority_actions": [
    {
      "priority": "high|medium|low",
      "agent": "anima|neo",
      "action": "...",
      "details": "..."
    }
  ],
  "full_reports": {
    "anima": {...},
    "neo": {...}
  }
}

RÈGLES:
- Priorise les actions critiques
- Fournis un résumé exécutif clair
- Conserve tous les détails dans full_reports
- Suggère un ordre d'exécution des actions
```

---

## Custom Commands

### `/check_docs`
**Agent:** Anima (DocKeeper)
**Description:** Force une vérification complète de la documentation

**Usage:**
```bash
claude-code run /check_docs
```

### `/check_integrity`
**Agent:** Neo (IntegrityWatcher)
**Description:** Force une vérification complète de la cohérence backend/frontend

**Usage:**
```bash
claude-code run /check_integrity
```

### `/guardian_report`
**Agent:** Nexus (Coordinator)
**Description:** Génère un rapport consolidé des vérifications Anima + Neo

**Usage:**
```bash
claude-code run /guardian_report
```

---

## File Structure

```
claude-plugins/integrity-docs-guardian/
├── Claude.md                    # This manifest
├── README.md                    # User documentation
├── hooks/
│   ├── pre-commit.sh           # Pre-commit validation
│   └── post-commit.sh          # Post-commit verification (launches agents)
├── agents/
│   ├── anima_dockeeper.md      # Anima agent prompt template
│   ├── neo_integritywatcher.md # Neo agent prompt template
│   └── nexus_coordinator.md    # Nexus agent prompt template
├── scripts/
│   ├── scan_docs.py            # Documentation scanning utility
│   ├── check_integrity.py      # Integrity verification utility
│   └── generate_report.py      # Report generation utility
└── reports/
    ├── docs_report.json        # Anima output
    ├── integrity_report.json   # Neo output
    └── unified_report.json     # Nexus output
```

---

## Integration with ÉMERGENCE

This plugin is specifically designed for the ÉMERGENCE application architecture:

- **Backend:** FastAPI (Python) - src/backend/
- **Frontend:** Vite + React (TypeScript/JavaScript) - src/frontend/
- **Agents:** Anima, Neo, Nexus
- **Memory System:** Concept recall, episodic memory
- **Metrics:** Custom monitoring and validation

---

## Installation & Setup

See [README.md](README.md) for detailed installation instructions.

---

## Version History

**v1.0.0** (2025-10-10)
- Initial release
- Anima (DocKeeper) integration
- Neo (IntegrityWatcher) integration
- Nexus (Coordinator) integration
- Git hooks setup
- Automated reporting
