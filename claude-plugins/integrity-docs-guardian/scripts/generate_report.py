#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEXUS (Coordinator) - Unified Report Generator
Aggregates reports from Anima and Neo, provides synthesis and prioritization
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(
        sys.stdout, "reconfigure"
    ) else None

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PLUGIN_DIR = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
REPORTS_DIR = REPO_ROOT / "reports"  # UNIFIED: All reports in repo root

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_json_report(file_path: Path) -> Dict:
    """Load a JSON report file."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error loading {file_path}: {e}", file=sys.stderr)
        return {}


def determine_overall_status(anima_report: Dict, neo_report: Dict) -> str:
    """Determine overall system status based on both reports."""
    anima_status = anima_report.get("status", "unknown")
    neo_status = neo_report.get("status", "unknown")

    # Critical from Neo takes precedence
    if neo_status == "critical":
        return "critical"

    # Warning from either agent
    if neo_status == "warning" or anima_status == "needs_update":
        return "warning"

    # If both are OK
    if anima_status == "ok" and neo_status == "ok":
        return "ok"

    # Default
    return "unknown"


def generate_priority_actions(anima_report: Dict, neo_report: Dict) -> List[Dict]:
    """Generate prioritized action items from both reports."""
    actions = []

    # Process Neo issues (integrity)
    neo_issues = neo_report.get("issues", [])
    for issue in neo_issues:
        severity = issue.get("severity", "info")

        # Map severity to priority
        priority_map = {"critical": "P0", "warning": "P1", "info": "P3"}
        priority = priority_map.get(severity, "P3")

        action = {
            "priority": priority,
            "agent": "neo",
            "category": issue.get("type", "unknown"),
            "title": issue.get("description", "No description"),
            "description": issue.get("description", ""),
            "affected_files": issue.get("affected_files", []),
            "recommendation": issue.get("recommendation", ""),
            "estimated_effort": estimate_effort(issue),
            "owner": suggest_owner(issue),
        }
        actions.append(action)

    # Process Anima gaps (documentation)
    anima_gaps = anima_report.get("documentation_gaps", [])
    for gap in anima_gaps:
        severity = gap.get("severity", "low")

        # Map severity to priority
        priority_map = {"high": "P1", "medium": "P2", "low": "P3"}
        priority = priority_map.get(severity, "P3")

        action = {
            "priority": priority,
            "agent": "anima",
            "category": "documentation",
            "title": gap.get("issue", "Documentation gap"),
            "description": gap.get("issue", ""),
            "affected_files": gap.get("affected_docs", []),
            "recommendation": gap.get("recommendation", ""),
            "estimated_effort": estimate_effort(gap),
            "owner": "docs-team",
        }
        actions.append(action)

    # Sort by priority (P0 > P1 > P2 > P3)
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    actions.sort(key=lambda x: priority_order.get(x["priority"], 99))

    return actions


def estimate_effort(issue: Dict) -> str:
    """Estimate effort for an issue (simple heuristic)."""
    # This is a simple heuristic - can be enhanced with ML
    affected_files = len(issue.get("affected_files", []))

    if affected_files == 0:
        return "5 minutes"
    elif affected_files == 1:
        return "15 minutes"
    elif affected_files <= 3:
        return "30 minutes"
    else:
        return "1 hour"


def suggest_owner(issue: Dict) -> str:
    """Suggest owner team based on issue type."""
    issue_type = issue.get("type", "")

    if "schema" in issue_type or "endpoint" in issue_type:
        return "backend-team"
    elif "frontend" in issue_type:
        return "frontend-team"
    elif "documentation" in issue_type:
        return "docs-team"
    else:
        return "triage"


def generate_executive_summary(
    overall_status: str,
    anima_report: Dict,
    neo_report: Dict,
    priority_actions: List[Dict],
) -> Dict:
    """Generate executive summary."""
    total_issues = len(priority_actions)
    critical = len([a for a in priority_actions if a["priority"] == "P0"])
    warnings = len([a for a in priority_actions if a["priority"] in ["P1", "P2"]])
    info = len([a for a in priority_actions if a["priority"] in ["P3", "P4"]])

    # Generate headline
    if overall_status == "critical":
        headline = f"🚨 CRITICAL: {critical} blocking issue(s) detected"
    elif overall_status == "warning":
        headline = f"⚠️  {warnings} warning(s) found - review recommended"
    else:
        headline = "✅ All checks passed - no issues detected"

    return {
        "status": overall_status,
        "total_issues": total_issues,
        "critical": critical,
        "warnings": warnings,
        "info": info,
        "headline": headline,
    }


def generate_statistics(anima_report: Dict, neo_report: Dict) -> Dict:
    """Generate comprehensive statistics."""
    anima_stats = anima_report.get("statistics", {})
    neo_stats = neo_report.get("statistics", {})

    return {
        "total_files_changed": anima_stats.get("files_changed", 0),
        "backend_files": neo_stats.get("backend_files_changed", 0),
        "frontend_files": neo_stats.get("frontend_files_changed", 0),
        "docs_files": anima_stats.get("docs_files", 0),
        "issues_by_severity": {
            "critical": neo_stats.get("critical", 0),
            "warning": neo_stats.get("warnings", 0)
            + anima_stats.get("high_severity", 0),
            "info": neo_stats.get("info", 0) + anima_stats.get("low_severity", 0),
        },
        "issues_by_category": {
            "integrity": neo_stats.get("issues_found", 0),
            "documentation": anima_stats.get("gaps_found", 0),
        },
    }


def generate_recommendations(priority_actions: List[Dict]) -> Dict:
    """Generate recommendations based on priority actions."""
    immediate = [a["title"] for a in priority_actions if a["priority"] == "P0"]
    short_term = [a["title"] for a in priority_actions if a["priority"] == "P1"]
    long_term = []

    # Add generic long-term recommendations
    if any("documentation" in a["category"] for a in priority_actions):
        long_term.append("Consider implementing documentation-first workflow")

    if any("schema" in a["category"] for a in priority_actions):
        long_term.append("Implement automated schema validation in CI/CD")

    return {
        "immediate": immediate or ["None - all checks passed"],
        "short_term": short_term or ["Continue monitoring"],
        "long_term": long_term or ["Maintain current practices"],
    }


def generate_unified_report(anima_report: Dict, neo_report: Dict) -> Dict:
    """Generate the unified Nexus report."""
    # Get commit info from either report
    commit_hash = anima_report.get("commit_hash") or neo_report.get(
        "commit_hash", "unknown"
    )
    commit_msg = anima_report.get("commit_message") or neo_report.get(
        "commit_message", "unknown"
    )

    # Determine overall status
    overall_status = determine_overall_status(anima_report, neo_report)

    # Generate priority actions
    priority_actions = generate_priority_actions(anima_report, neo_report)

    # Generate executive summary
    exec_summary = generate_executive_summary(
        overall_status, anima_report, neo_report, priority_actions
    )

    # Generate statistics
    statistics = generate_statistics(anima_report, neo_report)

    # Generate recommendations
    recommendations = generate_recommendations(priority_actions)

    # Build unified report
    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "commit_hash": commit_hash,
            "commit_message": commit_msg,
            "nexus_version": "1.0.0",
        },
        "executive_summary": exec_summary,
        "agent_status": {
            "anima": {
                "status": anima_report.get("status", "unknown"),
                "issues_found": anima_report.get("statistics", {}).get("gaps_found", 0),
                "updates_proposed": anima_report.get("statistics", {}).get(
                    "updates_proposed", 0
                ),
                "summary": anima_report.get("summary", "No data"),
            },
            "neo": {
                "status": neo_report.get("status", "unknown"),
                "issues_found": neo_report.get("statistics", {}).get("issues_found", 0),
                "critical": neo_report.get("statistics", {}).get("critical", 0),
                "warnings": neo_report.get("statistics", {}).get("warnings", 0),
                "summary": neo_report.get("summary", "No data"),
            },
        },
        "priority_actions": priority_actions,
        "full_reports": {"anima": anima_report, "neo": neo_report},
        "statistics": statistics,
        "recommendations": recommendations,
    }

    return report


def main():
    """Main entry point."""
    print("🎯 NEXUS (Coordinator) - Generating unified report...")

    # Load reports
    anima_report = load_json_report(REPORTS_DIR / "docs_report.json")
    neo_report = load_json_report(REPORTS_DIR / "integrity_report.json")

    if not anima_report and not neo_report:
        print("⚠️  No reports found - run Anima and Neo first")
        return 1

    if not anima_report:
        print("⚠️  Anima report missing - using Neo data only")

    if not neo_report:
        print("⚠️  Neo report missing - using Anima data only")

    # Generate unified report
    report = generate_unified_report(anima_report, neo_report)

    # Save report
    report_file = REPORTS_DIR / "unified_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✅ Unified report generated: {report_file}")
    print("\n📊 Executive Summary:")
    print(f"   Status: {report['executive_summary']['status'].upper()}")
    print(f"   {report['executive_summary']['headline']}")
    print(f"\n📋 Priority Actions: {len(report['priority_actions'])}")

    for action in report["priority_actions"][:3]:  # Show top 3
        print(f"   [{action['priority']}] {action['title']}")

    if len(report["priority_actions"]) > 3:
        print(f"   ... and {len(report['priority_actions']) - 3} more")

    # Return exit code based on status
    # Only fail on critical (exit 2), warnings are informational (exit 0)
    status = report["executive_summary"]["status"]
    if status == "critical":
        return 2

    # Warnings and OK both return 0 (non-blocking)
    return 0


if __name__ == "__main__":
    sys.exit(main())
