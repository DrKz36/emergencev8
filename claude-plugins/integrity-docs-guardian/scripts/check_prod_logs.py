#!/usr/bin/env python3
"""
ProdGuardian - Production Log Analyzer for ÉMERGENCE
Fetches and analyzes Google Cloud Run logs for anomalies
"""

import subprocess
import json
import datetime
import sys
import os
import platform

# Configuration
SERVICE = "emergence-app"
REGION = "europe-west1"
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")  # Optional: set via env var
LIMIT = 80
FRESHNESS = "1h"  # Last hour of logs

# Thresholds
ERROR_THRESHOLD_DEGRADED = 1
ERROR_THRESHOLD_CRITICAL = 5
WARNING_THRESHOLD = 3


def get_gcloud_command():
    """
    Get the appropriate gcloud command for the current platform
    """
    if platform.system() == "Windows":
        return "gcloud.cmd"
    return "gcloud"


def fetch_logs():
    """
    Fetch recent logs from Google Cloud Run using gcloud CLI
    Returns: list of log entries (JSON objects)
    """
    gcloud_cmd = get_gcloud_command()

    cmd = [
        gcloud_cmd, "logging", "read",
        f'resource.type="cloud_run_revision" AND resource.labels.service_name="{SERVICE}"',
        f'--limit={LIMIT}',
        "--format=json",
        f"--freshness={FRESHNESS}",
    ]

    # Note: --location is not supported by gcloud logging read
    # Location filtering is done via the resource.labels.location in the query if needed

    # Add project if specified
    if PROJECT_ID:
        cmd.extend([f"--project={PROJECT_ID}"])

    try:
        print(f"🔍 Fetching logs from Cloud Run service '{SERVICE}'...", file=sys.stderr)
        print(f"   Region: {REGION}, Freshness: {FRESHNESS}, Limit: {LIMIT}", file=sys.stderr)

        # Execute with timeout to prevent hanging
        output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60  # 60 seconds timeout for gcloud logging read
        )

        if not output.strip():
            print("⚠️  No logs returned (empty response)", file=sys.stderr)
            return []

        logs = json.loads(output)
        print(f"✅ Fetched {len(logs)} log entries", file=sys.stderr)
        return logs

    except subprocess.TimeoutExpired as e:
        print("❌ Timeout fetching logs from gcloud (60s):", file=sys.stderr)
        print(f"   Command: {' '.join(cmd)}", file=sys.stderr)
        print("   Suggestion: Check network connectivity or gcloud authentication", file=sys.stderr)
        return []
    except subprocess.CalledProcessError as e:
        print("❌ Error fetching logs from gcloud:", file=sys.stderr)
        print(f"   Command: {' '.join(cmd)}", file=sys.stderr)
        print(f"   Error output: {e.output}", file=sys.stderr)
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON from gcloud output: {e}", file=sys.stderr)
        return []


def extract_message(log_entry):
    """Extract the log message from various log formats"""
    if "textPayload" in log_entry:
        return log_entry["textPayload"]
    elif "jsonPayload" in log_entry:
        payload = log_entry["jsonPayload"]
        # Try common message fields
        for field in ["message", "msg", "error", "text"]:
            if field in payload:
                return str(payload[field])
        return json.dumps(payload)[:200]
    return ""


def extract_full_context(log_entry):
    """
    Extract FULL context from log entry for actionable debugging
    Returns dict with all relevant info for Codex GPT
    """
    context = {
        "timestamp": log_entry.get("timestamp", ""),
        "severity": log_entry.get("severity", "DEFAULT"),
        "message": "",
        "stack_trace": None,
        "endpoint": None,
        "http_method": None,
        "status_code": None,
        "user_agent": None,
        "request_id": None,
        "error_type": None,
        "file_path": None,
        "line_number": None,
        "full_payload": None
    }

    # Extract message
    if "textPayload" in log_entry:
        context["message"] = log_entry["textPayload"]
    elif "jsonPayload" in log_entry:
        payload = log_entry["jsonPayload"]
        context["full_payload"] = payload  # Keep full JSON for analysis

        # Message
        for field in ["message", "msg", "error", "text"]:
            if field in payload:
                context["message"] = str(payload[field])
                break

        # Stack trace
        if "stack" in payload or "stacktrace" in payload or "traceback" in payload:
            context["stack_trace"] = payload.get("stack") or payload.get("stacktrace") or payload.get("traceback")

        # HTTP context
        if "httpRequest" in payload:
            http = payload["httpRequest"]
            context["endpoint"] = http.get("requestUrl", "")
            context["http_method"] = http.get("requestMethod", "")
            context["status_code"] = http.get("status", None)
            context["user_agent"] = http.get("userAgent", "")

        # Request ID (for tracing)
        context["request_id"] = payload.get("request_id") or payload.get("requestId") or payload.get("trace")

        # Error details
        if "error" in payload:
            error = payload["error"]
            if isinstance(error, dict):
                context["error_type"] = error.get("type") or error.get("name")
                context["file_path"] = error.get("file")
                context["line_number"] = error.get("line")
                if "stack" in error:
                    context["stack_trace"] = error["stack"]

    # Extract file/line from message if not found (Python traceback format)
    if not context["file_path"] and context["message"]:
        import re
        # Match: File "/path/to/file.py", line 123
        match = re.search(r'File "([^"]+)", line (\d+)', context["message"])
        if match:
            context["file_path"] = match.group(1)
            context["line_number"] = int(match.group(2))

        # Extract error type (e.g., "ValueError:", "KeyError:")
        match = re.search(r'(\w+Error|Exception):', context["message"])
        if match:
            context["error_type"] = match.group(1)

    return context


def analyze_patterns(errors_with_context):
    """
    Analyze patterns in errors to provide actionable insights
    Returns dict with pattern analysis
    """
    patterns = {
        "by_endpoint": {},
        "by_error_type": {},
        "by_file": {},
        "frequency_timeline": [],
        "most_common_error": None
    }

    for error in errors_with_context:
        # Count by endpoint
        endpoint = error.get("endpoint")
        if endpoint:
            patterns["by_endpoint"][endpoint] = patterns["by_endpoint"].get(endpoint, 0) + 1

        # Count by error type
        error_type = error.get("error_type")
        if error_type:
            patterns["by_error_type"][error_type] = patterns["by_error_type"].get(error_type, 0) + 1

        # Count by file
        file_path = error.get("file_path")
        if file_path:
            patterns["by_file"][file_path] = patterns["by_file"].get(file_path, 0) + 1

    # Sort by frequency
    if patterns["by_endpoint"]:
        patterns["by_endpoint"] = dict(sorted(patterns["by_endpoint"].items(), key=lambda x: x[1], reverse=True))
    if patterns["by_error_type"]:
        patterns["by_error_type"] = dict(sorted(patterns["by_error_type"].items(), key=lambda x: x[1], reverse=True))
        patterns["most_common_error"] = list(patterns["by_error_type"].keys())[0]
    if patterns["by_file"]:
        patterns["by_file"] = dict(sorted(patterns["by_file"].items(), key=lambda x: x[1], reverse=True))

    return patterns


def get_code_snippet(file_path, line_number, context_lines=5):
    """
    Extract code snippet from file for debugging context
    Returns dict with code snippet or None if file not found
    """
    if not file_path or not line_number:
        return None

    # Normalize path (remove /workspace or /app prefix from Cloud Run)
    file_path = file_path.replace("/workspace/", "").replace("/app/", "")

    # Try to find file in project
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.join(project_root, file_path)

    if not os.path.exists(full_path):
        return None

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start_line = max(0, line_number - context_lines - 1)
        end_line = min(len(lines), line_number + context_lines)

        snippet = {
            "file": file_path,
            "line": line_number,
            "code_snippet": "".join(lines[start_line:end_line]),
            "start_line": start_line + 1,
            "end_line": end_line
        }

        return snippet
    except Exception as e:
        print(f"⚠️  Could not read file {full_path}: {e}", file=sys.stderr)
        return None


def get_recent_commits(max_commits=5):
    """
    Get recent git commits to help identify potential culprits
    Returns list of commit info dicts
    """
    try:
        cmd = ["git", "log", f"-{max_commits}", "--pretty=format:%H|%an|%ar|%s"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=5)

        commits = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "time": parts[2],
                    "message": parts[3]
                })

        return commits
    except Exception as e:
        print(f"⚠️  Could not fetch git commits: {e}", file=sys.stderr)
        return []


def analyze_logs(logs):
    """
    Analyze logs for errors, warnings, performance issues, and critical signals
    Returns: analysis report dict with FULL CONTEXT for Codex GPT
    """
    errors = []
    errors_with_full_context = []  # NEW: Full context for deep analysis
    warnings = []
    warnings_with_context = []
    latency_issues = []
    critical_signals = []
    info_logs = []

    for log in logs:
        severity = log.get("severity", "DEFAULT")
        timestamp = log.get("timestamp", "")
        message = extract_message(log)

        # NEW: Extract full context
        full_context = extract_full_context(log)

        # Categorize by severity
        if severity in ["ERROR", "CRITICAL", "ALERT", "EMERGENCY"]:
            # OLD format for summary
            errors.append({
                "time": timestamp,
                "severity": severity,
                "msg": message[:300]
            })
            # NEW: Full context for analysis
            errors_with_full_context.append(full_context)

        elif severity == "WARNING":
            warnings.append({
                "time": timestamp,
                "msg": message[:300]
            })
            warnings_with_context.append(full_context)

        elif severity == "INFO":
            info_logs.append({
                "time": timestamp,
                "msg": message[:200]
            })

        # Check for specific critical patterns
        message_lower = message.lower()

        # OOMKilled or memory issues
        if any(pattern in message_lower for pattern in ["oomkilled", "out of memory", "memory limit"]):
            critical_signals.append({
                "type": "OOM",
                "time": timestamp,
                "msg": message[:300],
                "full_context": full_context
            })

        # Unhealthy revisions
        if "unhealthy" in message_lower or "health check" in message_lower:
            critical_signals.append({
                "type": "UNHEALTHY",
                "time": timestamp,
                "msg": message[:300],
                "full_context": full_context
            })

        # Container crashes
        if any(pattern in message_lower for pattern in ["crash", "terminated", "killed", "exit code"]):
            critical_signals.append({
                "type": "CRASH",
                "time": timestamp,
                "msg": message[:300],
                "full_context": full_context
            })

        # Latency issues
        if "latency" in message_lower or "slow" in message_lower:
            latency_issues.append({
                "time": timestamp,
                "msg": message[:300],
                "full_context": full_context
            })

        # 5xx errors - check for actual HTTP 5xx status codes
        import re
        if severity not in ["ERROR", "CRITICAL", "ALERT", "EMERGENCY"]:  # Avoid duplicates
            if re.search(r'(status_code["\s:]+5\d{2}|HTTP[/\s]+5\d{2}|\s5(0[0-5]|0[0-9])\s)', message):
                errors.append({
                    "time": timestamp,
                    "severity": "HTTP_5XX",
                    "msg": message[:300]
                })
                errors_with_full_context.append(full_context)

    # Determine overall status
    status = "OK"
    if len(errors) > ERROR_THRESHOLD_CRITICAL or len(critical_signals) > 0:
        status = "CRITICAL"
    elif len(errors) > ERROR_THRESHOLD_DEGRADED or len(warnings) > WARNING_THRESHOLD:
        status = "DEGRADED"

    # NEW: Analyze patterns
    error_patterns = analyze_patterns(errors_with_full_context)

    # NEW: Extract code snippets for top failing files
    code_snippets = []
    if error_patterns["by_file"]:
        top_files = list(error_patterns["by_file"].keys())[:3]  # Top 3 files
        for file_path in top_files:
            # Find first error with this file to get line number
            for error_ctx in errors_with_full_context:
                if error_ctx.get("file_path") == file_path:
                    snippet = get_code_snippet(file_path, error_ctx.get("line_number"))
                    if snippet:
                        snippet["error_count"] = error_patterns["by_file"][file_path]
                        code_snippets.append(snippet)
                    break

    # NEW: Get recent commits
    recent_commits = get_recent_commits(max_commits=5)

    # Build report (ENHANCED)
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "service": SERVICE,
        "region": REGION,
        "logs_analyzed": len(logs),
        "freshness": FRESHNESS,
        "status": status,
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "critical_signals": len(critical_signals),
            "latency_issues": len(latency_issues)
        },
        # OLD format (backward compatibility)
        "errors": errors[:5],
        "warnings": warnings[:5],
        "critical_signals": critical_signals[:3],
        "latency_issues": latency_issues[:3] if latency_issues else [],

        # NEW: Full context for Codex GPT
        "errors_detailed": errors_with_full_context[:10],  # Top 10 with full context
        "warnings_detailed": warnings_with_context[:10],
        "error_patterns": error_patterns,
        "code_snippets": code_snippets,
        "recent_commits": recent_commits,

        "recommendations": []
    }

    # Generate recommendations (ENHANCED with actionable details)
    if status == "CRITICAL":
        report["recommendations"].append({
            "priority": "HIGH",
            "action": "Investigate critical issues immediately",
            "details": "OOMKilled or container crashes detected" if critical_signals else "High error rate detected",
            "affected_files": list(error_patterns["by_file"].keys())[:3] if error_patterns["by_file"] else [],
            "affected_endpoints": list(error_patterns["by_endpoint"].keys())[:3] if error_patterns["by_endpoint"] else []
        })

        if any(sig["type"] == "OOM" for sig in critical_signals):
            report["recommendations"].append({
                "priority": "HIGH",
                "action": "Increase memory limit",
                "command": f"gcloud run services update {SERVICE} --memory=1Gi --region={REGION}",
                "details": "Current limit likely insufficient for workload"
            })

        if len(errors) > 10:
            report["recommendations"].append({
                "priority": "HIGH",
                "action": "Consider rollback to previous stable revision",
                "details": "High error rate suggests recent deployment issue",
                "recent_commits": recent_commits[:3],  # Show recent commits as potential culprits
                "rollback_command": f"gcloud run services update-traffic {SERVICE} --to-revisions=PREVIOUS=100 --region={REGION}"
            })

        # Pattern-specific recommendations
        if error_patterns["most_common_error"]:
            report["recommendations"].append({
                "priority": "HIGH",
                "action": f"Fix recurring {error_patterns['most_common_error']} error",
                "details": f"This error type accounts for most failures ({error_patterns['by_error_type'][error_patterns['most_common_error']]} occurrences)",
                "suggested_files_to_check": code_snippets[:2] if code_snippets else []
            })

        if error_patterns["by_endpoint"]:
            top_endpoint = list(error_patterns["by_endpoint"].keys())[0]
            count = error_patterns["by_endpoint"][top_endpoint]
            report["recommendations"].append({
                "priority": "HIGH",
                "action": f"Fix endpoint: {top_endpoint}",
                "details": f"This endpoint is failing repeatedly ({count} errors)",
                "suggested_fix": "Check request validation, error handling, and database queries for this endpoint"
            })

    elif status == "DEGRADED":
        report["recommendations"].append({
            "priority": "MEDIUM",
            "action": "Monitor closely and investigate warnings",
            "details": f"{len(warnings)} warnings detected",
            "affected_files": list(error_patterns["by_file"].keys())[:3] if error_patterns["by_file"] else []
        })

        if latency_issues:
            report["recommendations"].append({
                "priority": "MEDIUM",
                "action": "Investigate slow queries or endpoints",
                "details": "Performance degradation detected",
                "suggested_investigation": [
                    "Check database query performance",
                    "Review API call timeouts",
                    "Analyze memory usage patterns"
                ]
            })

    else:
        report["recommendations"].append({
            "priority": "LOW",
            "action": "No immediate action required",
            "details": "Production is healthy"
        })

    return report


def save_report(report, output_path="reports/prod_report.json"):
    """Save the report to a JSON file"""
    # Ensure reports directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"📄 Report saved to: {output_path}", file=sys.stderr)


def print_summary(report):
    """Print a human-readable summary of the report"""
    # Force UTF-8 encoding for emoji support on Windows
    if platform.system() == "Windows":
        sys.stdout.reconfigure(encoding='utf-8')

    status = report["status"]

    # Status emoji
    status_emoji = {
        "OK": "🟢",
        "DEGRADED": "🟡",
        "CRITICAL": "🔴"
    }

    print(f"\n{status_emoji.get(status, '⚪')} Production Status: {status}")
    print("\n📊 Summary:")
    print(f"   - Logs analyzed: {report['logs_analyzed']}")
    print(f"   - Errors: {report['summary']['errors']}")
    print(f"   - Warnings: {report['summary']['warnings']}")
    print(f"   - Critical signals: {report['summary']['critical_signals']}")
    print(f"   - Latency issues: {report['summary']['latency_issues']}")

    if report["critical_signals"]:
        print("\n❌ Critical Issues:")
        for sig in report["critical_signals"]:
            print(f"   [{sig['time']}] {sig['type']}")
            print(f"      {sig['msg'][:150]}")

    if report["errors"]:
        print("\n⚠️  Recent Errors:")
        for i, err in enumerate(report["errors"][:3], 1):
            print(f"   {i}. [{err['time']}] {err.get('severity', 'ERROR')}")
            print(f"      {err['msg'][:150]}")

    if report["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in report["recommendations"]:
            priority_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(rec["priority"], "⚪")
            print(f"   {priority_emoji} [{rec['priority']}] {rec['action']}")
            if "command" in rec:
                print(f"      Command: {rec['command']}")
            if "details" in rec:
                print(f"      {rec['details']}")

    print()


def main():
    """Main execution flow"""
    print("=" * 60, file=sys.stderr)
    print("ProdGuardian - ÉMERGENCE Production Monitor", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Fetch logs
    logs = fetch_logs()

    if not logs:
        print("\n⚠️  No logs retrieved. Possible reasons:", file=sys.stderr)
        print("   - gcloud CLI not authenticated", file=sys.stderr)
        print("   - No logs in the specified timeframe", file=sys.stderr)
        print("   - Service name or region incorrect", file=sys.stderr)
        print("\n💡 Try running: gcloud auth login", file=sys.stderr)
        sys.exit(1)

    # Analyze logs
    report = analyze_logs(logs)

    # Save report
    save_report(report)

    # Print summary to stdout
    print_summary(report)

    # Exit code based on status
    exit_code = 0
    if report["status"] == "CRITICAL":
        exit_code = 2
    elif report["status"] == "DEGRADED":
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
