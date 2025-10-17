# 🔗 Guardian Agents - Unified Coordination Protocol

**Version:** 3.0.0
**Date:** 2025-10-17
**Status:** ACTIVE

---

## 📋 Executive Summary

Ce document définit le **protocole de coordination unifié** pour tous les Guardian sub-agents du système ÉMERGENCE. Il établit les règles de communication, les priorités, les mécanismes de synchronisation, et les workflows automatisés pour garantir une orchestration cohérente et sans conflits.

---

## 🎯 Objectifs du Protocole

1. ✅ **Cohérence**: Tous les agents suivent les mêmes conventions
2. ✅ **Coordination**: Échanges d'information fluides entre agents
3. ✅ **Priorisation**: Gestion claire des conflits et des dépendances
4. ✅ **Automation**: Workflows automatisés avec validation humaine
5. ✅ **Traçabilité**: Toutes les actions sont loggées et vérifiables
6. ✅ **Robustesse**: Gestion d'erreur et dégradation gracieuse

---

## 🏗️ Architecture Unifiée

### Agents et Leurs Rôles

| Agent | Rôle | Déclencheur | Priorité | Temps d'exécution |
|-------|------|-------------|----------|-------------------|
| **Anima** | Documentation & Versioning | Pre-commit / Manuel | P1 | ~30s |
| **Neo** | Integrity & Schema Alignment | Pre-commit / Manuel | P0 | ~45s |
| **Argus** | Dev Log Monitoring | Interactif / Manuel | P2 | Continu |
| **ProdGuardian** | Production Health | Pre-push / Scheduled | P0 | ~60s |
| **Theia** | AI Cost Optimization | Scheduled (weekly) | P3 | ~120s |
| **Nexus** | Coordination & Reporting | Post-commit / Manuel | P1 | ~20s |
| **Orchestrateur** | Global Orchestration | Manuel / Scheduled | P0 | ~180s |

### Niveaux de Priorité

- **P0 (CRITICAL)**: Bloquant - Empêche commit/push si problème détecté
- **P1 (HIGH)**: Avertissement fort - Recommandation de correction immédiate
- **P2 (MEDIUM)**: Avertissement - Correction dans les 24h
- **P3 (LOW)**: Informatif - Correction dans le sprint
- **P4 (INFO)**: Observation - Backlog

---

## 🔄 Workflows Automatisés

### Workflow 1: Développement Local (Git Pre-Commit)

```
┌──────────────────┐
│  git commit      │
└────────┬─────────┘
         │
         ▼
╔════════════════════════════════════╗
║  PRE-COMMIT HOOK (Blocking Phase)  ║
╚════════════════════════════════════╝
         │
         ├─── [1] Anima (DocKeeper)
         │    ├─ Scan code changes
         │    ├─ Detect doc gaps
         │    └─ Propose version bump
         │
         ├─── [2] Neo (IntegrityWatcher)
         │    ├─ Check schema alignment
         │    ├─ Validate API contracts
         │    └─ Detect breaking changes
         │
         └─── Decision Point:
              │
              ├─ ✅ All PASS or WARN → CONTINUE
              │   └─ Create commit
              │
              └─ ❌ Any CRITICAL → BLOCK COMMIT
                  ├─ Display errors
                  ├─ Suggest fixes
                  └─ Exit with code 1

╔════════════════════════════════════╗
║  POST-COMMIT HOOK (Reporting)      ║
╚════════════════════════════════════╝
         │
         └─── Nexus (Coordinator)
              ├─ Merge Anima + Neo reports
              ├─ Generate unified_report.json
              ├─ Prioritize actions (P0-P4)
              └─ Display summary to user
```

**Locking Mechanism**:
- File lock: `.guardian_lock`
- Max wait: 30 seconds
- If locked: Display "Another Guardian process is running"

---

### Workflow 2: Push to Production (Git Pre-Push)

```
┌──────────────────┐
│  git push        │
└────────┬─────────┘
         │
         ▼
╔════════════════════════════════════╗
║  PRE-PUSH HOOK (Safety Check)      ║
╚════════════════════════════════════╝
         │
         └─── ProdGuardian
              ├─ Fetch Cloud Run logs (last 2h)
              ├─ Analyze production health
              └─ Decision:
                  │
                  ├─ ✅ OK → ALLOW PUSH
                  ├─ 🟡 DEGRADED → WARN + ALLOW PUSH
                  └─ 🔴 CRITICAL → BLOCK PUSH
                      ├─ Display critical issues
                      ├─ Suggest rollback/fixes
                      └─ Exit with code 1
```

**Override**:
```bash
git push --no-verify  # Skip safety check (use with caution!)
```

---

### Workflow 3: Global Orchestration (Manual/Scheduled)

```
┌──────────────────┐
│ /sync_all        │
│ OR Scheduler     │
└────────┬─────────┘
         │
         ▼
╔════════════════════════════════════╗
║  ORCHESTRATION PIPELINE            ║
╚════════════════════════════════════╝
         │
         ├─── [0] Acquire Lock
         │    └─ Create .guardian_lock
         │
         ├─── [1] Context Detection
         │    ├─ Git: current commit hash
         │    ├─ Branch: main/dev
         │    └─ Cloud Run: deployed version
         │
         ├─── [2] Execute Agents (PARALLEL)
         │    ├─ Anima → docs_report.json
         │    ├─ Neo → integrity_report.json
         │    ├─ ProdGuardian → prod_report.json
         │    ├─ Argus → dev_logs_report.json (if dev mode)
         │    └─ Theia → cost_report.json (if weekly)
         │
         ├─── [3] Cross-Agent Validation
         │    ├─ Check for conflicts
         │    ├─ Detect cascading issues
         │    └─ Resolve dependencies
         │
         ├─── [4] Nexus Coordination
         │    ├─ Merge all reports
         │    ├─ Generate unified_report.json
         │    └─ Prioritize actions
         │
         ├─── [5] Auto-Apply Fixes (if enabled)
         │    ├─ Filter: confidence > 95% + P0/P1
         │    ├─ Apply approved fixes
         │    └─ Verify success
         │
         ├─── [6] Generate Global Report
         │    └─ global_report.json
         │
         ├─── [7] User Validation
         │    ├─ Display summary
         │    ├─ Ask for approval (if needed)
         │    └─ Wait for confirmation
         │
         ├─── [8] Commit & Sync (if approved)
         │    ├─ git add .
         │    ├─ git commit -m "chore: automated guardian updates"
         │    └─ git push origin main
         │
         └─── [9] Release Lock
              └─ Remove .guardian_lock
```

**Auto-Apply Rules**:
- Only applies fixes with:
  - Confidence ≥ 95%
  - Priority P0 or P1
  - Non-breaking changes
  - User approval (unless AUTO_APPLY=1)

---

### Workflow 4: Development Monitoring (Argus Real-Time)

```
┌──────────────────┐
│ Backend Running  │
│ Frontend Running │
└────────┬─────────┘
         │
         ▼
╔════════════════════════════════════╗
║  ARGUS MONITORING (Continuous)     ║
╚════════════════════════════════════╝
         │
         └─── Every 5 seconds:
              ├─ Parse backend logs
              ├─ Parse frontend logs
              ├─ Detect error patterns
              └─ On error detected:
                  │
                  ├─ Analyze root cause
                  ├─ Generate fix proposal
                  ├─ Display to user
                  └─ Wait for approval:
                      │
                      ├─ ✅ Approved → Apply fix
                      │   ├─ Verify resolution (30s)
                      │   └─ Log to argus_fixes_history.json
                      │
                      └─ ❌ Rejected → Log only
```

**Integration with Neo**:
- If Argus detects schema mismatch → Escalate to Neo
- Neo verifies across entire codebase
- Proposes aligned fix for both backend + frontend

---

## 📊 Report Formats Unifiés

### Standard Report Structure (All Agents)

```json
{
  "metadata": {
    "agent": "anima|neo|argus|prodguardian|theia|nexus",
    "version": "X.Y.Z",
    "timestamp": "2025-10-17T14:32:15Z",
    "session_id": "unique-session-id",
    "execution_time_seconds": 30.5
  },
  "context": {
    "commit_hash": "abc123def",
    "branch": "main",
    "files_changed": ["src/backend/file.py"],
    "deployment_version": "v2.1.0" // if applicable
  },
  "status": "ok|warning|critical",
  "summary": {
    "total_issues": 3,
    "critical": 1,
    "warnings": 2,
    "info": 0,
    "headline": "One-sentence summary"
  },
  "issues": [
    {
      "id": "agent-001",
      "severity": "critical|warning|info",
      "type": "schema_mismatch|doc_gap|import_error|etc",
      "title": "Short descriptive title",
      "description": "Detailed explanation",
      "affected_files": ["file1.py", "file2.js"],
      "context": {
        "file": "src/backend/file.py",
        "line": 42,
        "code_snippet": "actual code line"
      },
      "fix_proposals": [
        {
          "confidence": 95,
          "type": "code_fix|dependency_install|config_change",
          "description": "What this fix does",
          "actions": [
            {
              "type": "edit_file|shell_command|manual_review",
              "details": "Specific action to take"
            }
          ],
          "estimated_time": "30 seconds",
          "risk": "low|medium|high"
        }
      ],
      "escalation": {
        "to_agent": "neo|anima|nexus",
        "reason": "Why escalation is needed"
      }
    }
  ],
  "statistics": {
    "files_analyzed": 42,
    "errors_found": 3,
    "fixes_proposed": 2,
    "fixes_applied": 1
  },
  "recommendations": {
    "immediate": ["Action 1", "Action 2"],
    "short_term": ["Action 3"],
    "long_term": ["Action 4"]
  }
}
```

### Unified Report (Nexus Output)

```json
{
  "metadata": {
    "timestamp": "2025-10-17T14:32:15Z",
    "orchestration_id": "orch-20251017-143215",
    "nexus_version": "1.0.0"
  },
  "executive_summary": {
    "status": "ok|warning|critical",
    "total_issues": 5,
    "critical": 1,
    "warnings": 3,
    "info": 1,
    "headline": "1 critical issue (schema mismatch), 3 warnings (doc gaps)",
    "recommendation": "Address critical issue before next deployment"
  },
  "agent_reports": {
    "anima": { /* full Anima report */ },
    "neo": { /* full Neo report */ },
    "prodguardian": { /* full ProdGuardian report */ },
    "argus": { /* full Argus report */ },
    "theia": { /* full Theia report */ }
  },
  "priority_actions": [
    {
      "priority": "P0|P1|P2|P3|P4",
      "agent": "source agent",
      "issue_id": "agent-001",
      "title": "Action title",
      "description": "What needs to be done",
      "affected_files": [],
      "estimated_effort": "15 minutes",
      "dependencies": ["P0-002"], // blocking issues
      "recommended_owner": "backend-team|frontend-team|docs-team"
    }
  ],
  "cross_agent_insights": {
    "conflicts_detected": [
      {
        "agents": ["anima", "neo"],
        "description": "Conflicting recommendations",
        "resolution": "Prioritize Neo (schema) over Anima (docs)"
      }
    ],
    "cascading_issues": [
      {
        "root_cause": "neo-001 (schema mismatch)",
        "affected_issues": ["anima-003", "argus-012"],
        "fix_order": ["neo-001", "anima-003", "argus-012"]
      }
    ]
  },
  "trends": {
    "commits_analyzed": 150,
    "average_issues_per_commit": 1.8,
    "most_common_issue_type": "documentation_gap",
    "improvement_trend": "+5% (fewer issues than last 10 commits)"
  },
  "auto_apply_summary": {
    "fixes_proposed": 5,
    "fixes_applied": 2,
    "fixes_approved_pending": 3,
    "fixes_rejected": 0
  }
}
```

---

## 🔐 Locking & Concurrency Control

### Lock File Protocol

**Location**: `claude-plugins/integrity-docs-guardian/.guardian_lock`

**Lock Structure**:
```json
{
  "locked_by": "orchestrateur|anima|neo|etc",
  "timestamp": "2025-10-17T14:32:15Z",
  "pid": 12345,
  "operation": "full_orchestration|commit_check|etc"
}
```

**Acquire Lock Logic**:
```python
def acquire_lock(agent_name, operation, timeout=30):
    """
    Tries to acquire lock for max 'timeout' seconds.
    Returns True if successful, False if timeout.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not lock_file.exists():
            create_lock(agent_name, operation)
            return True
        else:
            # Check if lock is stale (> 5 minutes old)
            lock_data = read_lock()
            if time.time() - lock_data['timestamp'] > 300:
                # Stale lock - force release
                release_lock()
                create_lock(agent_name, operation)
                return True
        time.sleep(1)
    return False  # Timeout
```

**Release Lock**:
```python
def release_lock():
    """Always release lock in finally block"""
    if lock_file.exists():
        os.remove(lock_file)
```

**Usage in Agents**:
```python
try:
    if not acquire_lock("anima", "doc_check"):
        print("❌ Another Guardian process is running. Please wait.")
        exit(1)

    # Execute agent logic
    run_anima_checks()

finally:
    release_lock()
```

---

## 🔗 Inter-Agent Communication Protocol

### Event System

**Event Types**:
- `issue_detected`: Agent found an issue
- `fix_proposed`: Agent proposed a fix
- `fix_applied`: Fix was applied successfully
- `escalation_required`: Issue needs another agent
- `conflict_detected`: Two agents have conflicting recommendations

**Event Bus** (future implementation):
```python
class GuardianEventBus:
    def publish(self, event_type, data):
        """Publish event to all subscribed agents"""
        pass

    def subscribe(self, event_type, callback):
        """Subscribe to specific event type"""
        pass
```

### Escalation Rules

**Anima → Neo**:
- Trigger: API endpoint changes detected
- Reason: Need schema validation
- Action: Neo verifies backend/frontend alignment

**Neo → Anima**:
- Trigger: Breaking change detected
- Reason: Documentation must be updated
- Action: Anima updates CHANGELOG + migration guide

**Argus → Neo**:
- Trigger: Runtime schema mismatch error
- Reason: Systematic issue in codebase
- Action: Neo performs full integrity check

**Any Agent → Nexus**:
- Trigger: Critical issue detected
- Reason: Need priority assessment
- Action: Nexus evaluates and prioritizes

**ProdGuardian → All**:
- Trigger: Production CRITICAL
- Reason: Emergency - block all other operations
- Action: All agents pause, ProdGuardian takes control

---

## ⚙️ Configuration Unifiée

### Global Configuration File

**Location**: `claude-plugins/integrity-docs-guardian/config/guardian_config.json`

```json
{
  "version": "3.0.0",
  "orchestration": {
    "enabled": true,
    "mode": "automatic|manual|scheduled",
    "lock_timeout_seconds": 30,
    "max_parallel_agents": 4
  },
  "agents": {
    "anima": {
      "enabled": true,
      "triggers": ["pre-commit", "manual", "scheduled"],
      "auto_apply_fixes": false,
      "min_confidence_threshold": 90
    },
    "neo": {
      "enabled": true,
      "triggers": ["pre-commit", "manual"],
      "block_on_critical": true,
      "auto_apply_fixes": false
    },
    "argus": {
      "enabled": true,
      "triggers": ["manual"],
      "check_interval_seconds": 5,
      "auto_apply_fixes": true,
      "min_confidence_threshold": 95
    },
    "prodguardian": {
      "enabled": true,
      "triggers": ["pre-push", "scheduled"],
      "block_on_critical": true,
      "schedule": "0 */6 * * *"  // Every 6 hours
    },
    "theia": {
      "enabled": true,
      "triggers": ["scheduled"],
      "schedule": "0 23 * * 0"  // Sundays at 23:00
    },
    "nexus": {
      "enabled": true,
      "triggers": ["post-commit", "manual", "orchestration"]
    }
  },
  "reporting": {
    "output_dir": "reports",
    "retain_days": 30,
    "formats": ["json", "markdown"],
    "slack_webhook": null,
    "email_notifications": false
  },
  "automation": {
    "auto_commit": false,
    "auto_push": false,
    "require_approval_for_p0": true,
    "require_approval_for_p1": true,
    "auto_apply_threshold_confidence": 95
  },
  "git_hooks": {
    "pre_commit": {
      "enabled": true,
      "agents": ["anima", "neo"]
    },
    "post_commit": {
      "enabled": true,
      "agents": ["nexus"]
    },
    "pre_push": {
      "enabled": true,
      "agents": ["prodguardian"]
    }
  }
}
```

---

## 🚨 Error Handling & Graceful Degradation

### Agent Failure Handling

**Rule 1**: One agent failure should NOT block others

```python
def run_all_agents():
    results = {}
    for agent in ["anima", "neo", "prodguardian"]:
        try:
            results[agent] = run_agent(agent)
        except Exception as e:
            results[agent] = {
                "status": "error",
                "error_message": str(e),
                "execution_failed": True
            }
            log_error(f"{agent} failed: {e}")
            # Continue with other agents

    return results
```

**Rule 2**: Critical agent failures → Degraded mode

```python
if results["neo"]["execution_failed"]:
    print("⚠️ NEO FAILED - Running in degraded mode")
    print("   Schema validation skipped")
    print("   Recommend manual integrity check")
```

**Rule 3**: Report partial results

```json
{
  "status": "partial_failure",
  "agents_succeeded": ["anima", "nexus"],
  "agents_failed": ["neo"],
  "summary": "2/3 agents completed successfully. Manual review recommended."
}
```

---

## 📋 Validation & Approval Workflow

### User Validation Required For:

1. **P0 Critical Fixes** (always require approval)
2. **Breaking Changes** (schema, API)
3. **Auto-Commit** (documentation updates)
4. **Production Rollback** (ProdGuardian)

### Approval Interface

```bash
╔═══════════════════════════════════════════════════════════╗
║  GUARDIAN APPROVAL REQUIRED                                ║
╚═══════════════════════════════════════════════════════════╝

🔴 Critical Issue: Schema mismatch detected (P0)

Agent: Neo (IntegrityWatcher)
Issue ID: neo-001

Description:
  Backend expects 'user_id' (snake_case)
  Frontend sends 'userId' (camelCase)

Proposed Fix (Confidence: 92%):
  Update frontend to send 'user_id'
  Files affected: src/frontend/services/userApi.js

Risk: Low
Estimated time: 5 minutes

Actions:
  [1] ✅ Approve and apply fix
  [2] ❌ Reject (manual fix)
  [3] 📝 View full diff
  [4] ⏸️  Skip for now

Your choice [1-4]:
```

### Auto-Apply Without Approval (if enabled)

**Criteria**:
- `AUTO_APPLY=1` in config
- Confidence ≥ 95%
- Risk = "low"
- Non-breaking change
- Priority ≥ P1

**Log All Auto-Applied Fixes**:
```json
{
  "timestamp": "2025-10-17T14:32:15Z",
  "fix_id": "anima-003",
  "agent": "anima",
  "type": "documentation_update",
  "confidence": 98,
  "auto_applied": true,
  "files_modified": ["docs/backend/api.md"],
  "commit_hash": "abc123def"
}
```

---

## 🔄 Version Management Chain (Critical)

### Atomic Version Update Transaction

**Problem**: 4-step version sync can fail mid-way → inconsistency

**Solution**: Atomic transaction with rollback

```python
def update_version_atomically(new_version, changelog_entry):
    """
    Updates version across all files atomically.
    If ANY step fails, rollback ALL changes.
    """
    backup = create_backup([
        "src/version.js",
        "package.json",
        "CHANGELOG.md",
        "ROADMAP_OFFICIELLE.md"
    ])

    try:
        # Step 1: Update src/version.js (source of truth)
        update_version_js(new_version)

        # Step 2: Sync package.json
        update_package_json(new_version)

        # Step 3: Add CHANGELOG entry
        update_changelog(new_version, changelog_entry)

        # Step 4: Update ROADMAP metrics
        update_roadmap(new_version)

        # Verify all files are consistent
        verify_version_consistency(new_version)

        # Success - commit
        git_add([...])
        git_commit(f"chore: bump version to {new_version}")

        return True

    except Exception as e:
        # Rollback on ANY failure
        restore_backup(backup)
        log_error(f"Version update failed: {e}")
        return False

    finally:
        cleanup_backup(backup)
```

**Verification**:
```python
def verify_version_consistency(expected_version):
    """Ensure all files have the same version"""
    version_js = read_version_from_js()
    version_pkg = read_version_from_package_json()

    if version_js != expected_version:
        raise ValueError(f"version.js mismatch: {version_js} != {expected_version}")

    if version_pkg != expected_version:
        raise ValueError(f"package.json mismatch: {version_pkg} != {expected_version}")

    return True
```

---

## 📊 Monitoring & Metrics

### Agent Performance Metrics

Track for each agent:
- Execution time (avg, p50, p95)
- Success rate (%)
- Issues detected per run
- False positive rate
- Auto-fix success rate

**Storage**: `reports/metrics/agent_metrics.json`

```json
{
  "anima": {
    "total_runs": 150,
    "avg_execution_time_seconds": 28.5,
    "success_rate": 98.7,
    "issues_detected_total": 47,
    "false_positives": 2
  },
  "neo": { /* ... */ }
}
```

### System Health Dashboard (Future)

```
╔══════════════════════════════════════════════════════════╗
║  GUARDIAN SYSTEM HEALTH                                  ║
╚══════════════════════════════════════════════════════════╝

Agent Status:
  Anima         ✅ ACTIVE    Last run: 2min ago   (P1: 2 issues)
  Neo           ✅ ACTIVE    Last run: 2min ago   (OK)
  Argus         🔵 IDLE      Last run: N/A
  ProdGuardian  ⚠️  STALE     Last run: 6 days ago ⚠️
  Theia         ✅ ACTIVE    Last run: 2 days ago (Scheduled)
  Nexus         ✅ ACTIVE    Last run: 2min ago

System Metrics:
  Commits analyzed: 150
  Issues detected: 47
  Auto-fixes applied: 23
  Manual fixes required: 24

Recent Alerts:
  🔴 ProdGuardian report is OBSOLETE (6 days old)
  🟡 2 P1 issues pending approval (from Anima)
```

---

## 🚀 Activation Checklist

### Immediate Actions (P0)

- [ ] **Reactivate ProdGuardian scheduled execution**
  ```bash
  # Add to crontab or Task Scheduler
  0 */6 * * * cd /path/to/project && python check_prod_logs.py
  ```

- [ ] **Implement orchestration locking**
  ```bash
  # Add lock acquisition to all scripts
  # See "Locking & Concurrency Control" section
  ```

- [ ] **Fix version management chain**
  ```bash
  # Implement atomic transaction for version updates
  # See "Version Management Chain" section
  ```

### Short-term Actions (P1)

- [ ] **Integrate Argus into main pipeline**
  - Add to orchestration as optional dev stage
  - Trigger on CI/CD for PR validation

- [ ] **Add Theia to Nexus coordination**
  - Include cost reports in unified report
  - Add cost trends to executive summary

- [ ] **Implement cross-agent conflict detection**
  - Validate that fixes don't contradict each other
  - Resolve conflicts before applying

### Long-term Actions (P2)

- [ ] **Build approval workflow UI**
  - Web interface for validating fixes
  - Email/Slack notifications with approve buttons

- [ ] **Add GitHub Actions integration**
  - Run Guardian on every PR
  - Block merge if critical issues

- [ ] **Create real-time dashboard**
  - Live agent status
  - Historical trends
  - Alert management

---

## 📖 Best Practices

### For Developers

1. **Always run `/sync_all` before starting work**
   - Ensures local state is synchronized
   - Catches issues early

2. **Don't ignore P0/P1 warnings**
   - They indicate real problems
   - Fix before committing

3. **Review auto-applied fixes**
   - Check git diff after auto-commits
   - Understand what changed and why

4. **Use `/check_logs` during development**
   - Real-time error detection
   - Faster debugging

### For Agents (Prompt Guidelines)

1. **Always follow standard report format**
   - Consistent structure across all agents
   - Enables automated processing

2. **Escalate when appropriate**
   - Don't try to handle everything alone
   - Pass to specialized agent when needed

3. **Log all actions**
   - Every decision must be traceable
   - Include timestamps and context

4. **Fail gracefully**
   - Don't block other agents on error
   - Report partial results

---

**Version:** 3.0.0
**Last Updated:** 2025-10-17
**Maintained by:** ÉMERGENCE Team
**Status:** ACTIVE - Ready for Implementation
