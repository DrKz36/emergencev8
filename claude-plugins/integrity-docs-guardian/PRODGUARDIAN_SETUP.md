# ProdGuardian - Setup Guide

## ✅ Implementation Complete

Le sous-agent **ProdGuardian** a été implémenté avec succès dans le plugin Integrity & Docs Guardian.

---

## 📦 What Was Implemented

### 1. **Agent Definition**
- ✅ `agents/prodguardian.md` - Complete agent prompt template
- ✅ Integrated into `Claude.md` as sub-agent #4

### 2. **Production Log Analyzer**
- ✅ `scripts/check_prod_logs.py` - Python script for Cloud Run log analysis
  - Fetches logs from Google Cloud Run (service: emergence-app)
  - Analyzes errors, warnings, performance issues
  - Detects OOMKilled, crashes, 5xx errors, latency spikes
  - Generates structured JSON reports
  - Provides severity-based status (OK / DEGRADED / CRITICAL)

### 3. **Slash Command**
- ✅ `.claude/commands/check_prod.md` - Custom command definition
- ✅ Usage: `claude-code run /check_prod`

### 4. **Git Hook Integration (Optional)**
- ✅ Updated `hooks/post-commit.sh`
- ✅ ProdGuardian runs after commit when `ENABLE_PROD_CHECK=1`

### 5. **Documentation**
- ✅ `PRODGUARDIAN_README.md` - Comprehensive user guide
- ✅ `PRODGUARDIAN_SETUP.md` - This setup guide

---

## 🚀 How to Use

### Method 1: Claude Code Command (Recommended)

```bash
claude-code run /check_prod
```

This will:
1. Execute `scripts/check_prod_logs.py`
2. Analyze Cloud Run logs from the last hour
3. Generate `reports/prod_report.json`
4. Display a human-readable diagnostic

### Method 2: Direct Script Execution

```bash
cd claude-plugins/integrity-docs-guardian
python scripts/check_prod_logs.py
```

### Method 3: Automated via Git Hook

Enable production checks after every commit:

```bash
export ENABLE_PROD_CHECK=1
git commit -m "Your message"
```

---

## 📋 Prerequisites

### Required Tools

1. **Python 3.11+**
   ```bash
   python --version
   ```

2. **gcloud CLI** (Google Cloud SDK)
   ```bash
   # Install
   curl https://sdk.cloud.google.com | bash

   # Authenticate
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Access to Cloud Run Service**
   ```bash
   # Verify access
   gcloud run services describe emergence-app --region=europe-west1

   # Test log reading
   gcloud logging read 'resource.type="cloud_run_revision"' --limit=5
   ```

### Optional Tools

- **jq** - For prettier JSON parsing in hooks
  ```bash
  # Ubuntu/Debian
  sudo apt-get install jq

  # macOS
  brew install jq
  ```

---

## 🔧 Configuration

### Service Configuration

Edit `scripts/check_prod_logs.py` to customize:

```python
# Cloud Run service details
SERVICE = "emergence-app"
REGION = "europe-west1"
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")  # Optional

# Log fetch parameters
LIMIT = 80          # Number of log entries
FRESHNESS = "1h"    # Time window (1h, 6h, 1d, etc.)

# Severity thresholds
ERROR_THRESHOLD_DEGRADED = 1
ERROR_THRESHOLD_CRITICAL = 5
WARNING_THRESHOLD = 3
```

### Environment Variables

```bash
# Set GCP project explicitly (optional)
export GCP_PROJECT_ID="your-project-id"

# Enable production check in post-commit hook
export ENABLE_PROD_CHECK=1
```

---

## 📊 Output Examples

### Healthy Production (OK)

```
🟢 Production Status: OK

📊 Summary:
   - Logs analyzed: 78
   - Errors: 0
   - Warnings: 0
   - Critical signals: 0
   - Latency issues: 0

💡 Recommendations:
   🟢 [LOW] No immediate action required
      Production is healthy
```

### Degraded Production

```
🟡 Production Status: DEGRADED

📊 Summary:
   - Logs analyzed: 80
   - Errors: 2
   - Warnings: 4
   - Critical signals: 0
   - Latency issues: 1

⚠️  Recent Errors:
   1. [2025-10-10T14:32:15Z] WARNING
      Slow query detected: GET /api/memory/search (872ms)

💡 Recommendations:
   🟡 [MEDIUM] Monitor closely and investigate warnings
      4 warnings detected
   🟡 [MEDIUM] Investigate slow queries or endpoints
      Performance degradation detected
```

### Critical Production

```
🔴 Production Status: CRITICAL

📊 Summary:
   - Logs analyzed: 80
   - Errors: 12
   - Warnings: 5
   - Critical signals: 2
   - Latency issues: 0

❌ Critical Issues:
   [2025-10-10T15:47:23Z] OOM
      Container exceeded memory limit (OOMKilled)

⚠️  Recent Errors:
   1. [2025-10-10T15:47:23Z] CRITICAL
      OOMKilled: Container terminated
   2. [2025-10-10T15:45:12Z] HTTP_5XX
      500 Internal Server Error on POST /api/chat/message

💡 Recommendations:
   🔴 [HIGH] Investigate critical issues immediately
      OOMKilled or container crashes detected
   🔴 [HIGH] Increase memory limit
      Command: gcloud run services update emergence-app --memory=1Gi --region=europe-west1
   🔴 [HIGH] Consider rollback to previous stable revision
      High error rate suggests recent deployment issue
```

---

## 🧪 Testing the Setup

### Step 1: Verify Python Syntax

```bash
python -m py_compile claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
echo "✅ Syntax valid"
```

### Step 2: Check gcloud Authentication

```bash
gcloud auth list
# Should show your authenticated account
```

### Step 3: Test Log Access

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="emergence-app"' \
  --limit=5 \
  --region=europe-west1
```

### Step 4: Run ProdGuardian

```bash
# Via Claude Code (recommended)
claude-code run /check_prod

# Or directly
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
```

### Step 5: Verify Report Generated

```bash
cat claude-plugins/integrity-docs-guardian/reports/prod_report.json
```

Expected structure:
```json
{
  "timestamp": "2025-10-10T...",
  "service": "emergence-app",
  "region": "europe-west1",
  "status": "OK|DEGRADED|CRITICAL",
  "summary": { ... },
  "errors": [ ... ],
  "recommendations": [ ... ]
}
```

---

## 🔗 Integration Points

### With Anima & Neo

ProdGuardian works alongside the existing agents:

- **Anima** (DocKeeper) - Maintains documentation
- **Neo** (IntegrityWatcher) - Verifies backend/frontend coherence
- **Nexus** (Coordinator) - Aggregates Anima + Neo reports
- **ProdGuardian** (NEW) - Monitors production health

### With CI/CD Pipeline

Add to `.github/workflows/deploy.yml`:

```yaml
- name: Deploy to Cloud Run
  run: gcloud run deploy emergence-app ...

- name: Verify Production Health
  run: |
    python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
    if [ $? -eq 2 ]; then
      echo "::error::Production CRITICAL after deployment"
      exit 1
    fi
```

### With Monitoring Alerts

When Cloud Monitoring alerts fire:

```bash
# Triggered by webhook or alert policy
claude-code run /check_prod
# Provides detailed diagnostic context
```

---

## 📁 File Structure Overview

```
claude-plugins/integrity-docs-guardian/
├── Claude.md                          # ✅ Updated with ProdGuardian
├── PRODGUARDIAN_README.md             # ✅ User documentation
├── PRODGUARDIAN_SETUP.md              # ✅ This setup guide
│
├── agents/
│   ├── anima_dockeeper.md
│   ├── neo_integritywatcher.md
│   ├── nexus_coordinator.md
│   └── prodguardian.md                # ✅ NEW: Agent prompt template
│
├── scripts/
│   ├── scan_docs.py
│   ├── check_integrity.py
│   ├── generate_report.py
│   └── check_prod_logs.py             # ✅ NEW: Log analyzer
│
├── reports/
│   ├── docs_report.json
│   ├── integrity_report.json
│   ├── unified_report.json
│   └── prod_report.json               # ✅ NEW: Generated by ProdGuardian
│
├── hooks/
│   ├── pre-commit.sh
│   └── post-commit.sh                 # ✅ Updated with ProdGuardian
│
└── .claude/commands/
    └── check_prod.md                  # ✅ NEW: Slash command
```

---

## 🛠️ Troubleshooting

### Issue: "gcloud: command not found"

**Solution:**
```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### Issue: "Permission denied" errors

**Solution:**
```bash
# Re-authenticate
gcloud auth login

# Grant logging viewer role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/logging.viewer"
```

### Issue: "No logs returned"

**Possible Causes:**
1. Service name incorrect (verify: `gcloud run services list`)
2. Region incorrect (should be `europe-west1`)
3. No logs in last hour (adjust `FRESHNESS` in script)
4. Service not receiving traffic

**Debug:**
```bash
# List all Cloud Run services
gcloud run services list

# Check recent logs manually
gcloud logging read 'resource.type="cloud_run_revision"' --limit=1

# Increase time window in script
# Edit check_prod_logs.py: FRESHNESS = "6h"
```

### Issue: Script runs but no critical issues detected

**Expected Behavior:**
- If production is healthy, status will be "OK"
- Only real anomalies trigger DEGRADED/CRITICAL status

**To Test Alert Logic:**
- Trigger an error in production (carefully!)
- Or modify thresholds in script to be more sensitive

---

## 🔮 Next Steps

### Immediate Actions

1. **Test with Real Production:**
   ```bash
   # After gcloud setup
   claude-code run /check_prod
   ```

2. **Enable Post-Commit Checks (Optional):**
   ```bash
   echo 'export ENABLE_PROD_CHECK=1' >> ~/.bashrc
   source ~/.bashrc
   ```

3. **Add to Deployment Pipeline:**
   - Update CI/CD workflow to run ProdGuardian after deploy

### Future Enhancements

- [ ] Slack/Discord webhook integration for alerts
- [ ] Trend analysis (compare with historical data)
- [ ] Auto-remediation with approval workflow
- [ ] Cost monitoring and optimization suggestions
- [ ] User impact estimation (correlate errors with sessions)
- [ ] SLO tracking (99.9% uptime, p95 latency, etc.)

---

## 📚 Additional Resources

- [Main Plugin README](README.md)
- [ProdGuardian User Guide](PRODGUARDIAN_README.md)
- [Agent Prompt Template](agents/prodguardian.md)
- [Cloud Run Logging Docs](https://cloud.google.com/run/docs/logging)
- [gcloud Logging Commands](https://cloud.google.com/sdk/gcloud/reference/logging)

---

## ✅ Verification Checklist

- [x] Agent prompt template created (`prodguardian.md`)
- [x] Log analyzer script implemented (`check_prod_logs.py`)
- [x] Slash command defined (`.claude/commands/check_prod.md`)
- [x] Claude.md manifest updated
- [x] Post-commit hook updated (optional integration)
- [x] Documentation written (README + SETUP)
- [x] Python syntax validated
- [ ] gcloud CLI installed and authenticated (user action required)
- [ ] Successfully fetched production logs (user action required)
- [ ] Tested with real production data (user action required)

---

**Status:** ✅ Implementation Complete - Ready for Testing

**Next Action:** Install and authenticate gcloud CLI, then run `/check_prod`

---

**Last Updated:** 2025-10-10
**Implemented By:** Claude Code Agent
**Version:** 1.0.0
