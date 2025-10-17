# Integrity & Docs Guardian Plugin

**Version:** 2.2.0
**For:** ÉMERGENCE Application (FastAPI + Vite/React)
**Agents:** Anima (DocKeeper), Neo (IntegrityWatcher), Nexus (Coordinator), ProdGuardian, Theia (CostWatcher), Argus (LogWatcher)
**NEW:** 🤖 Automated Production Monitoring Every 30 Minutes (ProdGuardian Scheduler)

---

## 🆕 What's New in v2.2.0

### ✅ Automated Production Monitoring (ProdGuardian Scheduler)

**NEW:** Production monitoring now runs **automatically every 30 minutes**!

- ✅ **Windows Task Scheduler Integration** - Runs check_prod_logs.py every 30 minutes
- ✅ **Google Cloud Run Monitoring** - Monitors emergence-app in europe-west1
- ✅ **Automatic Anomaly Detection** - Detects OK/DEGRADED/CRITICAL states
- ✅ **Detailed Reports** - JSON reports with actionable recommendations
- ✅ **No Manual Intervention** - Fully automated once configured
- ✅ **One-Command Setup** - Simple PowerShell script for configuration

**Quick Start with Automated Monitoring:**
```powershell
# Configure automated production monitoring (Windows Task Scheduler)
.\claude-plugins\integrity-docs-guardian\scripts\setup_prod_monitoring.ps1

# Check current production status
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py

# Or via Claude Code slash command
/check_prod
```

📚 **See [PROD_MONITORING_ACTIVATED.md](PROD_MONITORING_ACTIVATED.md) for complete setup guide**

### Previous: Automatic Orchestration System (v2.0.0)

The plugin includes a **complete automatic orchestration system** that:

- ✅ **Runs all agents automatically** (Anima, Neo, ProdGuardian, Nexus)
- ✅ **Automatically updates documentation** based on verification reports
- ✅ **Integrates with Git hooks** for post-commit verification
- ✅ **Supports periodic scheduling** for continuous monitoring
- ✅ **Provides multiple execution modes** (manual, automatic, scheduled)

📚 **See [QUICKSTART_AUTO.md](QUICKSTART_AUTO.md) for orchestration details**

---

## 📋 Overview

The **Integrity & Docs Guardian** is a Claude Code plugin designed to automate documentation maintenance and ensure backend/frontend coherence in the ÉMERGENCE application. It runs automatically after each commit to detect documentation gaps, schema mismatches, and potential regressions.

### Key Features

✅ **Automated Documentation Tracking** - Detects when code changes require doc updates
✅ **Backend/Frontend Coherence** - Verifies API contracts and schema alignment
✅ **Regression Detection** - Catches breaking changes before they reach production
✅ **Multi-Agent System** - Specialized agents for different verification tasks
✅ **Git Integration** - Runs automatically via Git hooks
✅ **Actionable Reports** - Prioritized, concrete recommendations

---

## 🏗️ Architecture

### Agent Ecosystem

| Agent | Role | Responsibility |
|-------|------|----------------|
| **Anima** | DocKeeper | Monitors code changes and identifies documentation gaps |
| **Neo** | IntegrityWatcher | Verifies backend/frontend coherence and detects regressions |
| **ProdGuardian** | Production Monitor | Analyzes production logs and detects anomalies |
| **Theia** | CostWatcher | Monitors AI model costs and suggests optimizations |
| **🆕 Argus** | LogWatcher | Real-time dev log monitoring with automated error fixing |
| **Nexus** | Coordinator | Aggregates reports, prioritizes actions, provides unified view |
| **Auto-Orchestrator** | Automation Engine | Runs all agents automatically and updates documentation |

### Workflow

```
┌─────────────────┐
│  Git Commit     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Post-Commit Hook Triggered         │
└────────┬────────────────────────────┘
         │
         ├──────────────┬─────────────┐
         ▼              ▼             ▼
    ┌────────┐     ┌────────┐    ┌────────┐
    │ Anima  │     │  Neo   │    │ Nexus  │
    └────┬───┘     └────┬───┘    └────┬───┘
         │              │             │
         ▼              ▼             ▼
  docs_report.json  integrity_    unified_
                    report.json   report.json
```

---

## 📦 Installation

### Prerequisites

- **Git** repository
- **Python 3.8+**
- **Claude Code** environment (optional for slash commands)

### Step 1: Install the Plugin

The plugin is already installed at:
```
claude-plugins/integrity-docs-guardian/
```

### Step 2: Make Hooks Executable

On Unix/Linux/Mac:
```bash
chmod +x claude-plugins/integrity-docs-guardian/hooks/*.sh
```

On Windows (Git Bash):
```bash
# Run from project root
cd claude-plugins/integrity-docs-guardian/hooks
chmod +x pre-commit.sh post-commit.sh
```

### Step 3: Link Git Hooks (Optional)

To automatically run the plugin on every commit:

```bash
# From project root
ln -s ../../claude-plugins/integrity-docs-guardian/hooks/post-commit.sh .git/hooks/post-commit
ln -s ../../claude-plugins/integrity-docs-guardian/hooks/pre-commit.sh .git/hooks/pre-commit
```

Or on Windows:
```powershell
# From project root
cd .git/hooks
New-Item -ItemType SymbolicLink -Name "post-commit" -Target "..\..\claude-plugins\integrity-docs-guardian\hooks\post-commit.sh"
New-Item -ItemType SymbolicLink -Name "pre-commit" -Target "..\..\claude-plugins\integrity-docs-guardian\hooks\pre-commit.sh"
```

### Step 4: Test Installation

Run a manual check:
```bash
# Anima - Documentation check
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Neo - Integrity check
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Nexus - Unified report
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

---

## 🚀 Usage

### Automatic (Git Hooks)

Once installed, the plugin runs automatically after each commit:

```bash
git add .
git commit -m "feat: add new endpoint"

# Output:
# 🔍 ÉMERGENCE Integrity Guardian: Post-Commit Verification
# ==========================================================
# 📝 Commit: abc123def
#    Message: feat: add new endpoint
#
# 📚 [1/3] Launching Anima (DocKeeper)...
#    ✅ Anima completed successfully
#
# 🔐 [2/3] Launching Neo (IntegrityWatcher)...
#    ✅ Neo completed successfully
#
# 🎯 [3/3] Launching Nexus (Coordinator)...
#    ✅ Nexus completed successfully
#
# 📊 Reports available at:
#    - Anima:  claude-plugins/integrity-docs-guardian/reports/docs_report.json
#    - Neo:    claude-plugins/integrity-docs-guardian/reports/integrity_report.json
#    - Nexus:  claude-plugins/integrity-docs-guardian/reports/unified_report.json
```

### Manual (Slash Commands)

If using Claude Code:

```bash
# Check documentation
claude-code run /check_docs

# Check integrity
claude-code run /check_integrity

# Check production logs (Cloud Run)
claude-code run /check_prod

# Monitor development logs (local) - NEW!
claude-code run /check_logs

# Generate unified report
claude-code run /guardian_report
```

### Direct Script Execution

Run agents individually:

```bash
# Anima - Documentation verification
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Neo - Integrity verification
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Nexus - Unified reporting
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

---

## 📊 Reports

### Anima Report (`docs_report.json`)

Identifies documentation gaps:

```json
{
  "status": "needs_update",
  "changes_detected": {
    "backend": ["src/backend/routers/memory.py"],
    "frontend": ["src/frontend/components/Memory.jsx"]
  },
  "documentation_gaps": [
    {
      "severity": "high",
      "file": "src/backend/routers/memory.py",
      "issue": "New endpoint not documented",
      "affected_docs": ["docs/backend/memory.md"],
      "recommendation": "Add endpoint documentation"
    }
  ],
  "proposed_updates": [...]
}
```

### Neo Report (`integrity_report.json`)

Detects integrity issues:

```json
{
  "status": "warning",
  "backend_changes": {
    "endpoints_added": ["/api/v1/memory/concept-recall"]
  },
  "frontend_changes": {
    "api_calls_added": ["/api/v1/memory/concept-recall"]
  },
  "issues": [
    {
      "severity": "warning",
      "type": "schema_mismatch",
      "description": "Optional field mismatch",
      "recommendation": "Align schema definitions"
    }
  ]
}
```

### Nexus Report (`unified_report.json`)

Provides prioritized action plan:

```json
{
  "executive_summary": {
    "status": "warning",
    "headline": "⚠️ 2 warnings found - review recommended"
  },
  "priority_actions": [
    {
      "priority": "P1",
      "agent": "neo",
      "title": "Align ConceptRecallRequest schema",
      "affected_files": [...],
      "recommendation": "...",
      "estimated_effort": "15 minutes"
    }
  ],
  "recommendations": {
    "immediate": ["Address P1 schema alignment"],
    "short_term": ["Update documentation"],
    "long_term": ["Implement automated validation"]
  }
}
```

---

## 🎯 What Gets Checked

### Backend Monitoring

- ✅ **API Endpoints** - New/modified routes in `src/backend/routers/`
- ✅ **Data Models** - Pydantic schemas in `src/backend/models/`
- ✅ **Feature Modules** - New features in `src/backend/features/`
- ✅ **Authentication** - Auth decorators and requirements
- ✅ **OpenAPI Schema** - Alignment with code

### Frontend Monitoring

- ✅ **Components** - React components in `src/frontend/components/`
- ✅ **API Calls** - Axios/fetch calls in `src/frontend/services/`
- ✅ **Type Definitions** - TypeScript types and interfaces
- ✅ **Routes** - React Router configuration

### Documentation Monitoring

- ✅ **API Docs** - `docs/backend/`
- ✅ **Component Docs** - `docs/frontend/`
- ✅ **Architecture Docs** - `docs/architecture/`
- ✅ **README** - Main README.md
- ✅ **Integration Guides** - INTEGRATION.md, TESTING.md

---

## 🔧 Configuration

### Customizing Agent Behavior

Edit agent prompt files:

- `agents/anima_dockeeper.md` - Anima configuration
- `agents/neo_integritywatcher.md` - Neo configuration
- `agents/nexus_coordinator.md` - Nexus configuration

### Adjusting Severity Levels

Edit Python scripts to customize detection logic:

- `scripts/scan_docs.py` - Line ~95: `analyze_backend_changes()`
- `scripts/check_integrity.py` - Line ~180: `detect_integrity_issues()`

### Excluding Files

Add patterns to ignore specific files:

```python
# In scan_docs.py or check_integrity.py
EXCLUDED_PATTERNS = [
    "**/__pycache__/**",
    "**/node_modules/**",
    "**/venv/**",
    "**/*.test.js"
]
```

---

## 🔍 Troubleshooting

### Hook Not Running

**Problem:** Git hooks don't execute after commit

**Solution:**
```bash
# Verify hook exists and is executable
ls -la .git/hooks/post-commit
chmod +x .git/hooks/post-commit

# Test hook manually
.git/hooks/post-commit
```

### Python Import Errors

**Problem:** `ModuleNotFoundError` when running scripts

**Solution:**
```bash
# Ensure you're running from project root
cd /path/to/emergenceV8

# Or set PYTHONPATH
export PYTHONPATH=/path/to/emergenceV8:$PYTHONPATH
```

### No Changes Detected

**Problem:** Reports show "No changes detected" even after commit

**Solution:**
```bash
# Verify git history
git log -1 --stat

# Check if comparing correct commits
git diff --name-only HEAD~1 HEAD
```

### Reports Not Generated

**Problem:** JSON reports missing after running agents

**Solution:**
```bash
# Check reports directory exists
ls -la claude-plugins/integrity-docs-guardian/reports/

# Create if missing
mkdir -p claude-plugins/integrity-docs-guardian/reports/

# Check script permissions
chmod +x claude-plugins/integrity-docs-guardian/scripts/*.py
```

---

## 📚 Examples

### Example 1: Adding a New Backend Endpoint

**Scenario:** You add a new endpoint `POST /api/v1/memory/save`

**Anima Detects:**
- ✅ New router file modified
- ⚠️  No documentation in `docs/backend/memory.md`
- ⚠️  OpenAPI schema not updated

**Neo Detects:**
- ✅ New endpoint defined in backend
- ⚠️  No corresponding frontend API call (yet)

**Nexus Recommends:**
1. [P1] Document new endpoint in memory.md (15 min)
2. [P2] Regenerate OpenAPI schema (5 min)
3. [P3] Implement frontend integration (30 min)

### Example 2: Modifying a Data Schema

**Scenario:** You change `UserProfile` model to add `avatar_url` field

**Anima Detects:**
- ⚠️  Schema file modified
- ⚠️  No frontend type definition updated

**Neo Detects:**
- 🚨 **CRITICAL**: Schema mismatch - frontend uses old schema
- ⚠️  Frontend components may receive unexpected data

**Nexus Recommends:**
1. [P0] Update frontend TypeScript types IMMEDIATELY (10 min)
2. [P1] Update component props to handle new field (20 min)
3. [P2] Document new field in API docs (10 min)

### Example 3: Clean Refactoring

**Scenario:** You refactor internal code without changing interfaces

**Anima Detects:**
- ✅ Code changed but interfaces unchanged
- ✅ No documentation update needed

**Neo Detects:**
- ✅ No API changes
- ✅ No schema changes
- ✅ All integrity checks pass

**Nexus Reports:**
- Status: ✅ OK
- Summary: "Refactoring detected - no action required"

---

## 🤝 Contributing

### Adding New Checks

1. **For Anima** (documentation):
   - Edit `scripts/scan_docs.py`
   - Add detection logic in `analyze_backend_changes()` or `analyze_frontend_changes()`

2. **For Neo** (integrity):
   - Edit `scripts/check_integrity.py`
   - Add validation logic in `detect_integrity_issues()`

3. **For Nexus** (prioritization):
   - Edit `scripts/generate_report.py`
   - Adjust priority logic in `generate_priority_actions()`

### Testing Changes

```bash
# Test individual agents
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Test full workflow
./claude-plugins/integrity-docs-guardian/hooks/post-commit.sh
```

---

## 📖 Agent Personalities

### Anima (DocKeeper)

> "I am the guardian of knowledge. Every change in code is a story that must be told in documentation. I ensure nothing is forgotten, nothing is lost."

**Traits:**
- Thorough and meticulous
- Values clarity and completeness
- Proposes rather than imposes

### Neo (IntegrityWatcher)

> "I see the connections, the dependencies, the fragile contracts. I stand watch at the boundary between backend and frontend, ensuring they speak the same language."

**Traits:**
- Analytical and precise
- Focuses on system coherence
- Escalates critical issues immediately

### Nexus (Coordinator)

> "I synthesize, I prioritize, I guide. From chaos of multiple reports, I extract clarity and actionable wisdom."

**Traits:**
- Strategic and decisive
- Provides executive perspective
- Balances urgency with feasibility

---

## 📖 Documentation

### Complete Guide

| Document | Description |
|----------|-------------|
| **[QUICKSTART_AUTO.md](QUICKSTART_AUTO.md)** | Quick start guide for auto-orchestration |
| **[AUTO_ORCHESTRATION.md](AUTO_ORCHESTRATION.md)** | Complete documentation of the automatic system |
| **[SUMMARY_AUTO_SETUP.md](SUMMARY_AUTO_SETUP.md)** | Summary of what was installed |
| **[README.md](README.md)** | This file - main documentation |

---

## 🔮 Future Enhancements

### Planned Features

- [x] **Automatic Orchestration** - ✅ Implemented in v2.0.0
- [x] **Documentation Auto-Update** - ✅ Implemented in v2.0.0
- [x] **Periodic Scheduling** - ✅ Implemented in v2.0.0
- [x] **Real-Time Dev Log Monitoring** - ✅ Implemented in v2.1.0 (Argus)
- [ ] **AI-Powered Suggestions** - Use Claude to generate documentation updates automatically
- [ ] **Schema Auto-Sync** - Automatically propagate schema changes to frontend types
- [ ] **CI/CD Integration** - Block PRs with critical issues
- [ ] **Dashboard** - Visual reporting of trends and health metrics
- [ ] **Slack/Discord Notifications** - Real-time alerts for critical issues
- [ ] **Historical Analysis** - Track improvement over time
- [ ] **Browser Console Capture** - Capture frontend console logs via DevTools Protocol

### Advanced Checks

- [ ] **Performance Regression Detection** - Monitor for performance-impacting changes
- [ ] **Security Audit** - Detect potential security issues in endpoint changes
- [ ] **Accessibility Check** - Verify frontend components meet a11y standards
- [ ] **Dependency Tracking** - Map component dependencies to backend endpoints

---

## 📞 Support

### Getting Help

1. **Check Reports:** Review JSON reports in `reports/` directory
2. **Read Agent Docs:** See `agents/*.md` for detailed agent behavior
3. **Run Verbose Mode:** Add `--verbose` flag to scripts (if implemented)
4. **Check Logs:** Look for `reports/*.log` files

### Common Issues

| Issue | Solution |
|-------|----------|
| Hooks not running | Verify executable permissions and symlinks |
| False positives | Adjust severity thresholds in scripts |
| Missing detections | Extend detection patterns in agent scripts |
| Performance issues | Consider running agents async or in CI only |

---

## 📜 License

Part of the ÉMERGENCE project. See main repository LICENSE.

---

## 🙏 Acknowledgments

Built for the **ÉMERGENCE** AI-powered application ecosystem.

**Agents:**
- Anima - Documentation Guardian
- Neo - Integrity Watcher
- Nexus - Coordination & Synthesis

**Technology:**
- FastAPI (Backend)
- Vite + React (Frontend)
- Git Hooks (Automation)
- Python (Agent Implementation)

---

**Version:** 2.2.0
**Last Updated:** 2025-10-17
**Maintained by:** ÉMERGENCE Team

**Changelog v2.2.0:**
- ✅ Added **Automated Production Monitoring** - Windows Task Scheduler integration
- ✅ ProdGuardian now runs automatically every 30 minutes
- ✅ One-command setup script (setup_prod_monitoring.ps1)
- ✅ Advanced scheduler with logging (prod_guardian_scheduler.ps1)
- ✅ Complete documentation (PROD_MONITORING_ACTIVATED.md, PROD_AUTO_MONITOR_SETUP.md)
- ✅ Automatic report generation and cleanup
- ✅ Real-time production health monitoring on Google Cloud Run

**Changelog v2.1.0:**
- ✅ Added **Argus (LogWatcher)** - Real-time development log monitoring
- ✅ Automated error detection for backend (FastAPI) and frontend (Vite/React)
- ✅ Intelligent fix proposals with confidence scores
- ✅ Auto-fix capability with user validation
- ✅ Added `/check_logs` slash command for dev monitoring
- ✅ PowerShell and Python scripts for log analysis
- ✅ Pattern recognition for common error types (ImportError, TypeError, etc.)

**Changelog v2.0.0:**
- ✅ Added automatic orchestration system
- ✅ Added documentation auto-update capability
- ✅ Added periodic scheduler for continuous monitoring
- ✅ Enhanced Git hook with auto-update support
- ✅ Added `/auto_sync` slash command
- ✅ Comprehensive documentation (QUICKSTART_AUTO.md, AUTO_ORCHESTRATION.md)
