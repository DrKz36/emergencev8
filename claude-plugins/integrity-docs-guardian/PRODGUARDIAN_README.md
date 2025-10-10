# ProdGuardian - Production Monitoring Agent

**Version:** 1.0.0
**Agent Type:** Production Monitor
**Part of:** ÉMERGENCE Integrity & Docs Guardian Plugin

---

## 📋 Overview

**ProdGuardian** est un agent autonome qui surveille la santé de l'application ÉMERGENCE en production sur Google Cloud Run. Il analyse les logs récents, détecte les anomalies critiques, et fournit des recommandations d'actions correctives.

### Capabilities

✅ **Anomaly Detection:**
- Erreurs 5xx et exceptions Python
- OOMKilled et container crashes
- Unhealthy revisions et health check failures
- Latency spikes et slow queries
- Failed authentication attempts

✅ **Smart Analysis:**
- Categorizes issues by severity (CRITICAL / DEGRADED / OK)
- Provides probable root cause analysis
- Suggests immediate remediation actions
- Generates ready-to-use gcloud commands

✅ **Actionable Reports:**
- JSON report for programmatic processing
- Human-readable console output
- Integration with existing Guardian ecosystem

---

## 🚀 Quick Start

### Prerequisites

1. **gcloud CLI installed and authenticated:**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

2. **Access to Cloud Run service:**
   ```bash
   gcloud run services describe emergence-app --region=europe-west1
   ```

3. **Python 3.11+ available**

### Usage

#### Via Claude Code Command (Recommended)

```bash
claude-code run /check_prod
```

This will:
1. Execute the log analyzer script
2. Generate a report in `reports/prod_report.json`
3. Display a human-readable diagnostic

#### Via Direct Script Execution

```bash
python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
```

#### Via Git Hook (Optional)

To automatically check production after every commit:

```bash
export ENABLE_PROD_CHECK=1
git commit -m "Your commit message"
```

---

## 📊 Status Levels

### 🟢 OK
- No errors detected in the last hour
- Latency within normal range
- No unhealthy revisions
- Memory usage < 70%

**Example Output:**
```
🟢 Production Status: OK

✅ No anomalies detected in the last hour
✅ Latency stable (~230 ms avg)
✅ No 5xx errors or unhealthy revisions
✅ Memory usage normal (< 70% of limit)

Next check recommended in 1 hour
```

### 🟡 DEGRADED
- 1-5 errors detected
- 3+ warnings present
- Elevated latency (but < 3s)
- Memory usage 70-90%

**Example Output:**
```
🟡 Production Status: DEGRADED

⚠️ Warnings detected (non-critical):

1. [2025-10-10T14:32:15Z] Slow query detected (872 ms)
   - Endpoint: GET /api/memory/search
   - Suggestion: Add index on embeddings table

2. [2025-10-10T14:18:42Z] High memory usage (85% of 512 Mi)
   - Suggestion: Consider increasing memory limit to 768 Mi

Actions recommandées:
- Monitor memory usage over next 24h
- Optimize concept_recall query
```

### 🔴 CRITICAL
- 5+ errors detected
- OOMKilled or container crashes
- Unhealthy revisions
- Health check failures
- Severe latency issues (> 3s)

**Example Output:**
```
🔴 Production Status: CRITICAL

❌ Critical issues detected:

1. [2025-10-10T15:47:23Z] OOMKilled - Container terminated
   - Revision: emergence-app-00271-boh
   - Memory limit: 512 Mi
   - Cause probable: Memory leak in session cleanup

2. [2025-10-10T15:45:12Z] Multiple 5xx errors (18 occurrences)
   - Endpoint: POST /api/chat/message
   - Error: "NoneType object has no attribute 'id'"

ACTIONS IMMÉDIATES:

1. Rollback to previous stable revision:
   gcloud run services update-traffic emergence-app \
     --to-revisions=emergence-app-00270-abc=100 \
     --region=europe-west1

2. Increase memory limit:
   gcloud run services update emergence-app \
     --memory=1Gi --region=europe-west1
```

---

## 📁 Files & Structure

```
claude-plugins/integrity-docs-guardian/
├── agents/
│   └── prodguardian.md              # Agent prompt template
├── scripts/
│   └── check_prod_logs.py           # Log analyzer script
├── reports/
│   └── prod_report.json             # Generated analysis report
└── .claude/commands/
    └── check_prod.md                # Slash command definition
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Optional: Set GCP project ID explicitly
export GCP_PROJECT_ID="your-project-id"

# Enable production check in post-commit hook
export ENABLE_PROD_CHECK=1
```

### Script Parameters

Edit `scripts/check_prod_logs.py` to customize:

```python
SERVICE = "emergence-app"      # Cloud Run service name
REGION = "europe-west1"        # GCP region
LIMIT = 80                     # Number of log entries to fetch
FRESHNESS = "1h"               # Time window for logs

# Thresholds
ERROR_THRESHOLD_DEGRADED = 1   # Errors for DEGRADED status
ERROR_THRESHOLD_CRITICAL = 5   # Errors for CRITICAL status
WARNING_THRESHOLD = 3          # Warnings threshold
```

---

## 📈 Integration Scenarios

### 1. Post-Deployment Verification

After deploying a new version:

```bash
gcloud run deploy emergence-app --image=... --region=europe-west1
claude-code run /check_prod
```

ProdGuardian will verify the new deployment is healthy.

### 2. Scheduled Monitoring

Add to CI/CD pipeline (GitHub Actions, Cloud Scheduler):

```yaml
- name: Check Production Health
  run: |
    python claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py
    if [ $? -eq 2 ]; then
      echo "CRITICAL: Production issues detected!"
      # Send alert to Slack/PagerDuty
    fi
```

### 3. Alert-Based Triggering

When monitoring alerts fire, run ProdGuardian for detailed diagnostics:

```bash
# Triggered by alert webhook
/check_prod
```

### 4. Manual Investigation

When users report issues:

```bash
claude-code run /check_prod
# Provides instant diagnostic of recent production logs
```

---

## 🧪 Testing

### Test with Mock Logs (Development)

Since fetching real Cloud Run logs requires authentication, you can test the analysis logic:

1. Create a mock log file:
   ```json
   [
     {
       "severity": "ERROR",
       "timestamp": "2025-10-10T15:47:23Z",
       "textPayload": "OOMKilled: Container exceeded memory limit"
     }
   ]
   ```

2. Modify script to read from file instead of gcloud

### Verify gcloud Access

```bash
# Test gcloud authentication
gcloud auth list

# Test Cloud Run access
gcloud run services list --region=europe-west1

# Test log reading (manual)
gcloud logging read 'resource.type="cloud_run_revision"' --limit=10
```

---

## 🛠️ Troubleshooting

### Issue: "gcloud command not found"

**Solution:**
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### Issue: "Permission denied" when fetching logs

**Solution:**
```bash
# Authenticate with appropriate permissions
gcloud auth login
gcloud auth application-default login

# Ensure you have logging.viewer role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/logging.viewer"
```

### Issue: "No logs returned"

**Possible causes:**
1. Service name or region incorrect
2. No logs in the specified timeframe (last 1h)
3. Service not deployed or no traffic

**Solution:**
```bash
# Verify service exists
gcloud run services describe emergence-app --region=europe-west1

# Check if service has recent traffic
gcloud logging read 'resource.type="cloud_run_revision"' --limit=1

# Adjust FRESHNESS in script (e.g., "6h" for last 6 hours)
```

### Issue: Script exits with error code but no output

**Debug mode:**
```bash
# Run with verbose output
python -u claude-plugins/integrity-docs-guardian/scripts/check_prod_logs.py 2>&1 | tee debug.log
```

---

## 🔮 Future Enhancements

### Planned Features

1. **Trend Analysis:**
   - Compare current metrics with historical baseline
   - Detect gradual degradation patterns

2. **Slack/Discord Integration:**
   - Auto-notify team on CRITICAL status
   - Post daily health summaries

3. **Auto-Remediation (with approval):**
   - Suggest rollback and execute with user confirmation
   - Auto-scale resources based on patterns

4. **Cost Monitoring:**
   - Track Cloud Run costs
   - Suggest optimizations (min instances, CPU allocation)

5. **User Impact Estimation:**
   - Correlate errors with active user sessions
   - Estimate % of users affected

6. **SLO Tracking:**
   - Monitor against defined SLOs (99.9% uptime)
   - Alert when approaching SLO violation

---

## 📚 Related Documentation

- [Main Plugin README](README.md)
- [Agent Prompt Template](agents/prodguardian.md)
- [Anima (DocKeeper) Agent](agents/anima_dockeeper.md)
- [Neo (IntegrityWatcher) Agent](agents/neo_integritywatcher.md)
- [Nexus (Coordinator) Agent](agents/nexus_coordinator.md)

---

## 🤝 Contributing

To improve ProdGuardian:

1. **Add new anomaly patterns:**
   - Edit `scripts/check_prod_logs.py`
   - Add pattern matching in `analyze_logs()` function

2. **Enhance diagnostics:**
   - Update `agents/prodguardian.md` prompt template
   - Add new recommendation logic

3. **Extend integrations:**
   - Add webhook support for Slack/Discord
   - Create GitHub Action workflow

---

## 📝 License

Part of the ÉMERGENCE project - Internal use only

---

**Last Updated:** 2025-10-10
**Maintainer:** ÉMERGENCE Team
**Contact:** Via GitHub Issues or internal Slack
