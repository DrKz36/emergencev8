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


def analyze_logs(logs):
    """
    Analyze logs for errors, warnings, performance issues, and critical signals
    Returns: analysis report dict
    """
    errors = []
    warnings = []
    latency_issues = []
    critical_signals = []
    info_logs = []

    for log in logs:
        severity = log.get("severity", "DEFAULT")
        timestamp = log.get("timestamp", "")
        message = extract_message(log)

        # Categorize by severity
        if severity in ["ERROR", "CRITICAL", "ALERT", "EMERGENCY"]:
            errors.append({
                "time": timestamp,
                "severity": severity,
                "msg": message[:300]
            })
        elif severity == "WARNING":
            warnings.append({
                "time": timestamp,
                "msg": message[:300]
            })
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
                "msg": message[:300]
            })

        # Unhealthy revisions
        if "unhealthy" in message_lower or "health check" in message_lower:
            critical_signals.append({
                "type": "UNHEALTHY",
                "time": timestamp,
                "msg": message[:300]
            })

        # Container crashes
        if any(pattern in message_lower for pattern in ["crash", "terminated", "killed", "exit code"]):
            critical_signals.append({
                "type": "CRASH",
                "time": timestamp,
                "msg": message[:300]
            })

        # Latency issues
        if "latency" in message_lower or "slow" in message_lower:
            # Try to extract latency value
            latency_issues.append({
                "time": timestamp,
                "msg": message[:300]
            })

        # 5xx errors - check for actual HTTP 5xx status codes
        # Look for patterns like "status_code": 500 or "500 Internal" or " 502 " (with spaces)
        import re
        if severity not in ["ERROR", "CRITICAL", "ALERT", "EMERGENCY"]:  # Avoid duplicates
            if re.search(r'(status_code["\s:]+5\d{2}|HTTP[/\s]+5\d{2}|\s5(0[0-5]|0[0-9])\s)', message):
                errors.append({
                    "time": timestamp,
                    "severity": "HTTP_5XX",
                    "msg": message[:300]
                })

    # Determine overall status
    status = "OK"
    if len(errors) > ERROR_THRESHOLD_CRITICAL or len(critical_signals) > 0:
        status = "CRITICAL"
    elif len(errors) > ERROR_THRESHOLD_DEGRADED or len(warnings) > WARNING_THRESHOLD:
        status = "DEGRADED"

    # Build report
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
        "errors": errors[:5],  # Top 5 errors
        "warnings": warnings[:5],  # Top 5 warnings
        "critical_signals": critical_signals[:3],  # Top 3 critical signals
        "latency_issues": latency_issues[:3] if latency_issues else [],
        "recommendations": []
    }

    # Generate recommendations
    if status == "CRITICAL":
        report["recommendations"].append({
            "priority": "HIGH",
            "action": "Investigate critical issues immediately",
            "details": "OOMKilled or container crashes detected" if critical_signals else "High error rate detected"
        })

        if any(sig["type"] == "OOM" for sig in critical_signals):
            report["recommendations"].append({
                "priority": "HIGH",
                "action": "Increase memory limit",
                "command": f"gcloud run services update {SERVICE} --memory=1Gi --region={REGION}"
            })

        if len(errors) > 10:
            report["recommendations"].append({
                "priority": "HIGH",
                "action": "Consider rollback to previous stable revision",
                "details": "High error rate suggests recent deployment issue"
            })

    elif status == "DEGRADED":
        report["recommendations"].append({
            "priority": "MEDIUM",
            "action": "Monitor closely and investigate warnings",
            "details": f"{len(warnings)} warnings detected"
        })

        if latency_issues:
            report["recommendations"].append({
                "priority": "MEDIUM",
                "action": "Investigate slow queries or endpoints",
                "details": "Performance degradation detected"
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
