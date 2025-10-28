#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANIMA (DocKeeper) v2.0 - Documentation Scanner
Analyzes git commits AND working directory for documentation gaps

CHANGELOG v2.0:
- Support working directory (git diff HEAD) for pre-commit checks
- Support commit history (git diff HEAD~1 HEAD) for post-commit analysis
- Mode selection via --mode flag (pre-commit | post-commit | both)
- Better severity assessment with configurable thresholds
- Verbose output with color-coded messages
"""

import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Literal

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PLUGIN_DIR = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
REPORTS_DIR = REPO_ROOT / "reports"  # UNIFIED: All reports in repo root

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Scan modes
ScanMode = Literal["pre-commit", "post-commit", "both"]


def run_git_command(cmd: List[str], cwd: Path = REPO_ROOT) -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Remplace caractères invalides au lieu de crasher
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}", file=sys.stderr)
        return ""


def get_commit_info() -> Tuple[str, str]:
    """Get current commit hash and message."""
    commit_hash = run_git_command(["git", "rev-parse", "HEAD"])
    commit_msg = run_git_command(["git", "log", "-1", "--pretty=%B"])
    return commit_hash, commit_msg


def get_changed_files(mode: ScanMode = "both") -> Dict[str, List[str]]:
    """
    Get files changed, categorized by type.

    Args:
        mode: Scan mode
            - "pre-commit": Working directory changes (git diff HEAD)
            - "post-commit": Last commit changes (git diff HEAD~1 HEAD)
            - "both": Union of both (deduplicated)

    Returns:
        Dict with categorized file lists
    """
    all_files = set()

    # Get working directory changes (unstaged + staged)
    if mode in ("pre-commit", "both"):
        # Staged changes
        staged = run_git_command(["git", "diff", "--name-only", "--cached"])
        if staged:
            all_files.update(staged.split("\n"))

        # Unstaged changes
        unstaged = run_git_command(["git", "diff", "--name-only", "HEAD"])
        if unstaged:
            all_files.update(unstaged.split("\n"))

    # Get last commit changes
    if mode in ("post-commit", "both"):
        committed = run_git_command(["git", "diff", "--name-only", "HEAD~1", "HEAD"])
        if committed:
            all_files.update(committed.split("\n"))

    # Remove empty strings
    all_files.discard("")

    if not all_files:
        return {"backend": [], "frontend": [], "docs": [], "other": []}

    # Categorize files
    categorized = {
        "backend": [],
        "frontend": [],
        "docs": [],
        "other": []
    }

    for file in sorted(all_files):
        if not file:
            continue

        # Backend files
        if file.startswith("src/backend/") and file.endswith(".py"):
            categorized["backend"].append(file)

        # Frontend files
        elif file.startswith("src/frontend/") and file.endswith((".js", ".jsx", ".ts", ".tsx")):
            categorized["frontend"].append(file)

        # Documentation files
        elif file.endswith(".md") or file.startswith("docs/"):
            categorized["docs"].append(file)

        # Other files
        else:
            categorized["other"].append(file)

    return categorized


def analyze_backend_changes(files: List[str]) -> List[Dict]:
    """Analyze backend file changes for documentation needs."""
    gaps = []

    for file in files:
        file_path = REPO_ROOT / file

        if not file_path.exists():
            # File was deleted
            gaps.append({
                "severity": "medium",
                "file": file,
                "issue": "File deleted - verify documentation updated",
                "affected_docs": ["docs/backend/"],
                "recommendation": f"Update docs to reflect removal of {file}"
            })
            continue

        # Check if it's a router file (likely contains API endpoints)
        if "routers/" in file:
            gaps.append({
                "severity": "high",
                "file": file,
                "issue": "Router file modified - check API documentation",
                "affected_docs": ["docs/backend/api.md", "openapi.json"],
                "recommendation": "Verify endpoint documentation and regenerate OpenAPI schema if needed"
            })

        # Check if it's a model file
        elif "models/" in file:
            gaps.append({
                "severity": "medium",
                "file": file,
                "issue": "Model file modified - check schema documentation",
                "affected_docs": ["docs/backend/schemas.md"],
                "recommendation": "Update schema documentation if data models changed"
            })

        # Check for new feature modules
        elif "features/" in file:
            feature_name = file.split("features/")[1].split("/")[0]
            gaps.append({
                "severity": "high",
                "file": file,
                "issue": f"Feature module '{feature_name}' modified",
                "affected_docs": [f"docs/backend/{feature_name}.md", "README.md"],
                "recommendation": f"Ensure {feature_name} feature is documented"
            })

    return gaps


def analyze_architecture_docs(changed_files: Dict[str, List[str]]) -> List[Dict]:
    """Analyze if architecture documentation needs updates based on code changes."""
    gaps = []

    # Check for significant backend changes that may affect architecture
    backend_files = changed_files.get("backend", [])

    # Check for new services or major service refactoring
    for file in backend_files:
        # New or modified service files
        if "service.py" in file and "features/" in file:
            feature_name = file.split("features/")[1].split("/")[0]
            gaps.append({
                "severity": "medium",
                "file": file,
                "issue": f"Service '{feature_name}' modified - verify architecture docs",
                "affected_docs": [
                    "docs/architecture/10-Components.md",
                    "docs/architecture/00-Overview.md"
                ],
                "recommendation": f"Update architecture docs to reflect changes in {feature_name} service"
            })

        # New or modified routers (API contracts)
        if "router.py" in file and "features/" in file:
            feature_name = file.split("features/")[1].split("/")[0]
            gaps.append({
                "severity": "high",
                "file": file,
                "issue": f"Router '{feature_name}' modified - verify API contracts",
                "affected_docs": [
                    "docs/architecture/30-Contracts.md",
                    f"docs/backend/{feature_name}.md"
                ],
                "recommendation": f"Update API contracts documentation for {feature_name} endpoints"
            })

    # Check for significant database/model changes
    if any("models.py" in f or "database/" in f for f in backend_files):
        gaps.append({
            "severity": "high",
            "file": "database/models",
            "issue": "Database schema or models modified",
            "affected_docs": [
                "docs/architecture/10-Components.md",
                "docs/architecture/30-Contracts.md"
            ],
            "recommendation": "Update architecture docs to reflect database schema changes"
        })

    return gaps


def analyze_frontend_changes(files: List[str]) -> List[Dict]:
    """Analyze frontend file changes for documentation needs."""
    gaps = []

    for file in files:
        file_path = REPO_ROOT / file

        if not file_path.exists():
            # File was deleted
            gaps.append({
                "severity": "low",
                "file": file,
                "issue": "Component/file deleted - verify documentation",
                "affected_docs": ["docs/frontend/"],
                "recommendation": f"Update docs to reflect removal of {file}"
            })
            continue

        # Check for new components
        if "components/" in file:
            component_name = Path(file).stem
            gaps.append({
                "severity": "medium",
                "file": file,
                "issue": f"Component '{component_name}' modified",
                "affected_docs": ["docs/frontend/components.md"],
                "recommendation": "Document component props and usage if interface changed"
            })

        # Check for API service changes
        elif "services/api" in file or "api.js" in file:
            gaps.append({
                "severity": "high",
                "file": file,
                "issue": "API service modified - verify backend alignment",
                "affected_docs": ["docs/frontend/api-integration.md"],
                "recommendation": "Ensure frontend API calls match backend endpoints"
            })

    return gaps


def generate_proposed_updates(gaps: List[Dict]) -> List[Dict]:
    """Generate proposed documentation updates."""
    updates = []

    # Group gaps by affected doc
    doc_gaps = {}
    for gap in gaps:
        for doc in gap["affected_docs"]:
            if doc not in doc_gaps:
                doc_gaps[doc] = []
            doc_gaps[doc].append(gap)

    # Generate update proposals
    for doc, related_gaps in doc_gaps.items():
        update = {
            "file": doc,
            "action": "update_section",
            "reason": f"{len(related_gaps)} related change(s) detected",
            "related_changes": [gap["file"] for gap in related_gaps],
            "recommendation": related_gaps[0]["recommendation"]  # Use first gap's recommendation
        }
        updates.append(update)

    return updates


def generate_report(changed_files: Dict[str, List[str]], mode: ScanMode) -> Dict:
    """Generate the main documentation report."""
    commit_hash, commit_msg = get_commit_info()

    # Analyze changes
    backend_gaps = analyze_backend_changes(changed_files["backend"])
    frontend_gaps = analyze_frontend_changes(changed_files["frontend"])
    architecture_gaps = analyze_architecture_docs(changed_files)

    all_gaps = backend_gaps + frontend_gaps + architecture_gaps

    # Determine status based on severity
    critical_count = len([g for g in all_gaps if g["severity"] == "high"])
    if critical_count > 0:
        status = "critical"
    elif all_gaps:
        status = "warning"
    else:
        status = "ok"

    # Generate proposed updates
    proposed_updates = generate_proposed_updates(all_gaps)

    # Build report
    report = {
        "timestamp": datetime.now().isoformat(),
        "scan_mode": mode,
        "commit_hash": commit_hash,
        "commit_message": commit_msg,
        "status": status,
        "changes_detected": changed_files,
        "documentation_gaps": all_gaps,
        "proposed_updates": proposed_updates,
        "statistics": {
            "files_changed": sum(len(files) for files in changed_files.values()),
            "backend_files": len(changed_files["backend"]),
            "frontend_files": len(changed_files["frontend"]),
            "docs_files": len(changed_files["docs"]),
            "gaps_found": len(all_gaps),
            "high_severity": len([g for g in all_gaps if g["severity"] == "high"]),
            "medium_severity": len([g for g in all_gaps if g["severity"] == "medium"]),
            "low_severity": len([g for g in all_gaps if g["severity"] == "low"]),
            "updates_proposed": len(proposed_updates)
        },
        "summary": f"{len(all_gaps)} documentation gap(s) found, {len(proposed_updates)} update(s) proposed"
    }

    return report


def print_summary(report: Dict, verbose: bool = False) -> None:
    """Print colored summary of the report."""
    stats = report["statistics"]
    status = report["status"]

    # Status indicator
    if status == "critical":
        print("❌ Status: CRITICAL", flush=True)
    elif status == "warning":
        print("⚠️  Status: WARNING", flush=True)
    else:
        print("✅ Status: OK", flush=True)

    # Statistics
    print(f"📊 {stats['files_changed']} file(s) changed:", flush=True)
    if stats['backend_files'] > 0:
        print(f"   • Backend: {stats['backend_files']}", flush=True)
    if stats['frontend_files'] > 0:
        print(f"   • Frontend: {stats['frontend_files']}", flush=True)
    if stats['docs_files'] > 0:
        print(f"   • Docs: {stats['docs_files']}", flush=True)

    # Gaps found
    if stats['gaps_found'] > 0:
        print(f"\n📝 {stats['gaps_found']} documentation gap(s):", flush=True)
        if stats['high_severity'] > 0:
            print(f"   • High: {stats['high_severity']}", flush=True)
        if stats['medium_severity'] > 0:
            print(f"   • Medium: {stats['medium_severity']}", flush=True)
        if stats['low_severity'] > 0:
            print(f"   • Low: {stats['low_severity']}", flush=True)

        # Show details if verbose
        if verbose:
            print("\nDetails:", flush=True)
            for gap in report["documentation_gaps"]:
                severity_icon = "🔴" if gap["severity"] == "high" else "🟡" if gap["severity"] == "medium" else "🟢"
                print(f"  {severity_icon} [{gap['severity'].upper()}] {gap['file']}", flush=True)
                print(f"      {gap['issue']}", flush=True)
                print(f"      → {gap['recommendation']}", flush=True)
    else:
        print("\n✅ No documentation gaps detected", flush=True)


def main():
    """Main entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="ANIMA (DocKeeper) - Documentation Scanner v2.0")
    parser.add_argument(
        "--mode",
        choices=["pre-commit", "post-commit", "both"],
        default="pre-commit",
        help="Scan mode (default: pre-commit)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output with gap details"
    )
    args = parser.parse_args()

    print(f"🔍 ANIMA (DocKeeper) v2.0 - Scanning for documentation gaps... (mode: {args.mode})", flush=True)

    # Get changed files
    changed_files = get_changed_files(mode=args.mode)

    total_changes = sum(len(files) for files in changed_files.values())
    print(f"📝 Detected {total_changes} changed file(s)", flush=True)

    if total_changes == 0:
        print("ℹ️  No changes detected - skipping analysis", flush=True)
        # Still generate a report for consistency
        report = {
            "timestamp": datetime.now().isoformat(),
            "scan_mode": args.mode,
            "status": "ok",
            "changes_detected": changed_files,
            "documentation_gaps": [],
            "proposed_updates": [],
            "statistics": {"files_changed": 0, "gaps_found": 0, "updates_proposed": 0, "high_severity": 0, "medium_severity": 0, "low_severity": 0},
            "summary": "No changes detected"
        }
    else:
        # Generate report
        report = generate_report(changed_files, mode=args.mode)

    # Print summary
    print("\n" + "="*60, flush=True)
    print_summary(report, verbose=args.verbose)
    print("="*60 + "\n", flush=True)

    # Save report
    report_file = REPORTS_DIR / "docs_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"💾 Report saved: {report_file}", flush=True)

    # Return exit code based on status
    # critical = exit 1 (blocks commit)
    # warning = exit 0 (allows commit but warns)
    # ok = exit 0
    if report["status"] == "critical":
        print("\n🚨 CRITICAL issues detected - commit should be blocked", flush=True)
        return 1
    elif report["status"] == "warning":
        print("\n⚠️  Warnings detected - review recommended but commit allowed", flush=True)
        return 0
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
