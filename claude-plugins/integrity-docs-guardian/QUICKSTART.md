# Quick Start Guide - Integrity & Docs Guardian

**Version:** 1.0.0
**For:** ÉMERGENCE Application

---

## 🚀 5-Minute Setup

### Step 1: Verify Installation ✅

The plugin is already installed! Verify it:

```bash
ls -la claude-plugins/integrity-docs-guardian/
```

You should see:
- `Claude.md` - Plugin manifest
- `README.md` - Full documentation
- `hooks/` - Git hooks
- `agents/` - Agent prompt templates
- `scripts/` - Python implementation
- `reports/` - Generated reports (after first run)

### Step 2: Test the Plugin 🧪

Run a quick test:

```bash
# Test Anima (DocKeeper)
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Test Neo (IntegrityWatcher)
python claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Test Nexus (Coordinator)
python claude-plugins/integrity-docs-guardian/scripts/generate_report.py
```

**Expected Output:**
```
🔍 ANIMA (DocKeeper) - Scanning for documentation gaps...
📝 Detected X changed file(s)
✅ Report generated: .../reports/docs_report.json
📊 Summary: ...

🔐 NEO (IntegrityWatcher) - Checking system integrity...
📝 Detected X changed file(s)
✅ Report generated: .../reports/integrity_report.json
📊 Summary: ...

🎯 NEXUS (Coordinator) - Generating unified report...
✅ Unified report generated: .../reports/unified_report.json
📊 Executive Summary: ...
```

### Step 3: (Optional) Enable Git Hooks 🔗

To run automatically after each commit:

**On Linux/Mac:**
```bash
# From project root
chmod +x claude-plugins/integrity-docs-guardian/hooks/*.sh

# Link hooks
ln -sf ../../claude-plugins/integrity-docs-guardian/hooks/post-commit.sh .git/hooks/post-commit
ln -sf ../../claude-plugins/integrity-docs-guardian/hooks/pre-commit.sh .git/hooks/pre-commit
```

**On Windows (Git Bash):**
```bash
# From project root
cd .git/hooks

# Create symbolic links
cmd //c mklink post-commit ..\\..\\claude-plugins\\integrity-docs-guardian\\hooks\\post-commit.sh
cmd //c mklink pre-commit ..\\..\\claude-plugins\\integrity-docs-guardian\\hooks\\pre-commit.sh
```

**Or just copy the hooks:**
```bash
# From project root
cp claude-plugins/integrity-docs-guardian/hooks/post-commit.sh .git/hooks/post-commit
cp claude-plugins/integrity-docs-guardian/hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/post-commit .git/hooks/pre-commit
```

### Step 4: Make a Test Commit 📝

```bash
# Make a small change
echo "# Test" >> test-guardian.md

# Commit it
git add test-guardian.md
git commit -m "test: verify integrity guardian"

# Watch the magic happen! 🎉
```

You should see:
```
🔍 ÉMERGENCE Integrity Guardian: Post-Commit Verification
==========================================================
📝 Commit: abc123...
   Message: test: verify integrity guardian

📚 [1/3] Launching Anima (DocKeeper)...
   ✅ Anima completed successfully

🔐 [2/3] Launching Neo (IntegrityWatcher)...
   ✅ Neo completed successfully

🎯 [3/3] Launching Nexus (Coordinator)...
   ✅ Nexus completed successfully

📊 Reports available at:
   - Anima:  claude-plugins/integrity-docs-guardian/reports/docs_report.json
   - Neo:    claude-plugins/integrity-docs-guardian/reports/integrity_report.json
   - Nexus:  claude-plugins/integrity-docs-guardian/reports/unified_report.json
```

---

## 📊 Reading Reports

### View the Unified Report (Recommended)

```bash
# Pretty print with jq (if installed)
jq '.' claude-plugins/integrity-docs-guardian/reports/unified_report.json

# Or just open it
cat claude-plugins/integrity-docs-guardian/reports/unified_report.json
```

**Key Sections:**
- `executive_summary` - Overall status and headline
- `priority_actions` - What to do next (sorted by priority)
- `agent_status` - Individual agent results
- `recommendations` - Short/medium/long-term suggestions

### Priority Levels

| Priority | Meaning | Action Timeline |
|----------|---------|-----------------|
| **P0** | Critical - Blocks deployment | Immediate |
| **P1** | High - Should fix ASAP | Within 1 day |
| **P2** | Medium - Plan to fix | Within 1 week |
| **P3** | Low - Backlog | Within sprint |
| **P4** | Info - Nice to have | Backlog |

---

## 🎯 Common Use Cases

### Use Case 1: I Added a New API Endpoint

**What the Guardian Does:**
1. **Anima** detects router file change
2. **Anima** checks if docs exist for the endpoint
3. **Neo** verifies OpenAPI schema is updated
4. **Neo** looks for frontend integration
5. **Nexus** prioritizes documentation update

**Your Action:**
1. Check `unified_report.json`
2. Follow P1 actions (update docs)
3. Follow P2 actions (verify frontend)

### Use Case 2: I Modified a Pydantic Model

**What the Guardian Does:**
1. **Anima** flags schema file change
2. **Neo** checks for frontend type mismatches
3. **Neo** warns if breaking change detected
4. **Nexus** escalates to P0 if critical

**Your Action:**
1. Review schema alignment issues
2. Update frontend TypeScript types
3. Test both backend and frontend

### Use Case 3: I Refactored Code

**What the Guardian Does:**
1. **Anima** checks if interfaces changed
2. **Neo** verifies no breaking changes
3. **Nexus** reports "OK" if clean refactor

**Your Action:**
- If status is OK: Nothing! ✅
- If warnings: Review and address

---

## 🔧 Configuration

### Adjust Detection Sensitivity

Edit these files to customize:

**Anima (Documentation):**
```bash
# Edit detection rules
vim claude-plugins/integrity-docs-guardian/scripts/scan_docs.py

# Look for: analyze_backend_changes(), analyze_frontend_changes()
```

**Neo (Integrity):**
```bash
# Edit detection rules
vim claude-plugins/integrity-docs-guardian/scripts/check_integrity.py

# Look for: detect_integrity_issues()
```

**Nexus (Prioritization):**
```bash
# Edit priority mapping
vim claude-plugins/integrity-docs-guardian/scripts/generate_report.py

# Look for: generate_priority_actions()
```

### Exclude Files

Add to the scripts:

```python
# In scan_docs.py or check_integrity.py
EXCLUDED_PATTERNS = [
    "**/test_*.py",
    "**/__pycache__/**",
    "**/node_modules/**"
]
```

---

## 🐛 Troubleshooting

### "No changes detected" even after commit

**Solution:**
```bash
# Check git diff is working
git diff --name-only HEAD~1 HEAD

# If empty, you may need to commit something first
git log --oneline -5  # Check recent commits
```

### Scripts don't run on Windows

**Solution:**
```bash
# Ensure Python 3.8+ is installed
python --version

# Run with explicit python
python claude-plugins/integrity-docs-guardian/scripts/scan_docs.py
```

### Emoji characters not displaying

**Solution:**
- Use Windows Terminal (supports UTF-8)
- Or Git Bash with UTF-8 encoding
- Reports still work, just display issues

### Hooks not running automatically

**Solution:**
```bash
# Check hook exists
ls -la .git/hooks/post-commit

# Make executable
chmod +x .git/hooks/post-commit

# Test manually
.git/hooks/post-commit
```

---

## 📚 Next Steps

1. ✅ **Test the plugin** - Make a commit and verify reports
2. 📖 **Read full docs** - See [README.md](README.md) for details
3. 🎨 **Customize agents** - Edit `agents/*.md` to adjust behavior
4. 🔗 **Enable hooks** - Automate checks on every commit
5. 📊 **Review reports** - Check `reports/unified_report.json` regularly

---

## 🤝 Get Help

- **Full Documentation:** [README.md](README.md)
- **Agent Details:** [agents/](agents/)
- **Configuration:** [Claude.md](Claude.md)

---

## 🎉 You're All Set!

The Integrity & Docs Guardian is now protecting your ÉMERGENCE codebase!

**What happens next:**
- 🔍 Every commit is analyzed
- 📚 Documentation gaps are detected
- 🔐 Integrity issues are flagged
- 🎯 Actionable reports are generated
- ✅ You maintain a healthy codebase

**Meet your agents:**
- **Anima** 📚 - Your documentation guardian
- **Neo** 🔐 - Your integrity watcher
- **Nexus** 🎯 - Your coordination center

---

**Happy coding! 🚀**

*ÉMERGENCE - Where code and consciousness converge*
