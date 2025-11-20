#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANIMA Archive Guardian - Automatic Repository Cleanup
Scans root directory for obsolete files and archives them automatically.

Usage:
    python archive_guardian.py [--auto] [--dry-run]

Options:
    --auto      Archive automatically without confirmation
    --dry-run   Show what would be done without actually doing it
"""

import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(
        sys.stdout, "reconfigure"
    ) else None

# Paths
SCRIPT_DIR = Path(__file__).parent
PLUGIN_DIR = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
ARCHIVE_BASE = REPO_ROOT / "docs" / "archive"

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Whitelist - Files that should NEVER be archived
WHITELIST = {
    # Essential documentation
    "README.md",
    "CLAUDE.md",
    "AGENT_SYNC.md",
    "AGENTS.md",
    "CODEV_PROTOCOL.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    # Active roadmaps
    "ROADMAP_OFFICIELLE.md",
    "ROADMAP_PROGRESS.md",
    "MEMORY_REFACTORING_ROADMAP.md",
    # Operational guides
    "DEPLOYMENT_SUCCESS.md",
    "FIX_PRODUCTION_DEPLOYMENT.md",
    "CANARY_DEPLOYMENT.md",
    "GUARDIAN_SETUP_COMPLETE.md",
    # Agent guides
    "CLAUDE_CODE_GUIDE.md",
    "CODEX_GPT_GUIDE.md",
    "GUIDE_INTERFACE_BETA.md",
    # Configuration
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yaml",
    "docker-compose.override.yml",
    # Entry points
    "index.html",
    # Current cleanup plan (keep until next cleanup)
    "CLEANUP_PLAN_2025-10-18.md",
}

# Obsolete patterns - Files matching these patterns will be archived
OBSOLETE_PATTERNS = {
    # Prompts and session files
    "prompt": r"PROMPT_.*\.md",
    "handoff": r"HANDOFF_.*\.(md|txt)",
    "next_session": r"NEXT_SESSION_.*\.md",
    "resume": r"RESUME_SESSION_.*\.md",
    # Phase-related (except active)
    "phase": r"PHASE\d+.*\.md",
    # Fixes and audits (> 14 days)
    "fix": r".*_FIX_.*\.md",
    "audit": r".*_AUDIT_.*\.md",
    "corrections": r"CORRECTIONS_.*\.md",
    # Deployment (except whitelisted)
    "deployment": r"DEPLOYMENT_(?!SUCCESS|QUICKSTART).*\.md",
    # Old guides
    "implementation": r".*_IMPLEMENTATION\.md",
    "summary": r".*_SUMMARY\.md",
    "state": r".*_STATE_.*\.md",
    "upgrade": r"(UPGRADE|CHANGELOG)_.*\.md",
}

# Temporary file patterns - Will be DELETED (not archived)
TEMP_PATTERNS = {
    "tmp_files": r"tmp_.*",
    "temp_files": r"temp_.*",
    "tmp_extension": r".*\.tmp",
    "logs": r"downloaded-logs-.*\.json",
    "reports": r".*_report\.json",
    "build_tags": r"(build_tag|BUILDSTAMP)\.txt",
    "log_files": r".*\.log",
}


def get_file_age_days(filepath: Path) -> int:
    """Get file age in days based on modification time."""
    if not filepath.exists():
        return 0
    mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
    age = datetime.now() - mtime
    return age.days


def is_whitelisted(filename: str) -> bool:
    """Check if file is in whitelist."""
    return filename in WHITELIST


def is_config_file(filepath: Path) -> bool:
    """Check if file is a configuration file."""
    return filepath.suffix in [".yaml", ".yml", ".json", ".toml", ".ini", ".env"]


def should_archive_markdown(filepath: Path) -> Tuple[bool, str]:
    """Determine if a markdown file should be archived."""
    filename = filepath.name

    # Whitelist check
    if is_whitelisted(filename):
        return False, "whitelisted"

    age_days = get_file_age_days(filepath)

    # Check obsolete patterns
    import re

    for pattern_name, pattern in OBSOLETE_PATTERNS.items():
        if re.match(pattern, filename):
            # Different age thresholds for different patterns
            if pattern_name in ["prompt", "handoff", "next_session", "resume"]:
                if age_days > 7:
                    return (
                        True,
                        f"obsolete pattern ({pattern_name}), {age_days} days old",
                    )
            elif pattern_name in ["fix", "audit", "corrections"]:
                if age_days > 14:
                    return (
                        True,
                        f"obsolete pattern ({pattern_name}), {age_days} days old",
                    )
            else:
                return True, f"obsolete pattern ({pattern_name})"

    # Check for dated files (YYYY-MM-DD pattern)
    date_pattern = r".*(\d{4}-\d{2}-\d{2}).*\.md"
    match = re.match(date_pattern, filename)
    if match and age_days > 30:
        return True, f"dated file, {age_days} days old"

    return False, ""


def should_archive_script(filepath: Path) -> Tuple[bool, str]:
    """Determine if a script should be archived."""
    filename = filepath.name

    # Active migration scripts - keep recent ones
    if filename.startswith("apply_migration_") and get_file_age_days(filepath) <= 7:
        return False, "recent migration script"

    # Test scripts in root
    if filename.startswith("test_") and filepath.suffix == ".py":
        return True, "test script in root"

    # Batch/shell scripts (except whitelisted)
    if filepath.suffix in [".bat", ".sh"]:
        return True, "batch/shell script in root"

    # Check specific patterns
    obsolete_script_patterns = [
        "check_db",
        "fix_",
        "fetch_",
        "send_",
        "consolidate_",
        "qa_",
        "inject_",
        "generate_",
        "deploy_",
        "cleanup",
        "revoke_",
        "disable_",
        "add_password",
    ]

    for pattern in obsolete_script_patterns:
        if filename.startswith(pattern):
            age_days = get_file_age_days(filepath)
            if age_days > 7:
                return True, f"obsolete script pattern ({pattern}), {age_days} days old"

    return False, ""


def should_delete_temp(filepath: Path) -> Tuple[bool, str]:
    """Determine if a file should be deleted (temporary files)."""
    filename = filepath.name

    import re

    for pattern_name, pattern in TEMP_PATTERNS.items():
        if re.match(pattern, filename):
            return True, f"temporary file ({pattern_name})"

    # Downloaded logs, reports, etc.
    if "downloaded" in filename.lower() or "logs-" in filename:
        return True, "downloaded/log file"

    return False, ""


def scan_root_directory() -> Dict[str, List[Dict]]:
    """Scan root directory and categorize files."""
    results = {"to_archive": [], "to_delete": [], "whitelisted": [], "kept": []}

    # Scan only files in root directory (not subdirectories)
    for item in REPO_ROOT.iterdir():
        if not item.is_file():
            continue

        filename = item.name

        # Check whitelist first
        if is_whitelisted(filename):
            results["whitelisted"].append({"file": filename, "reason": "whitelisted"})
            continue

        # Check if should be deleted (temp files)
        should_delete, delete_reason = should_delete_temp(item)
        if should_delete:
            results["to_delete"].append(
                {
                    "file": filename,
                    "reason": delete_reason,
                    "age_days": get_file_age_days(item),
                }
            )
            continue

        # Check markdown files
        if item.suffix == ".md":
            should_archive, archive_reason = should_archive_markdown(item)
            if should_archive:
                results["to_archive"].append(
                    {
                        "file": filename,
                        "type": "markdown",
                        "reason": archive_reason,
                        "age_days": get_file_age_days(item),
                    }
                )
                continue

        # Check scripts (Python, Batch, Shell)
        if item.suffix in [".py", ".bat", ".sh"]:
            should_archive, archive_reason = should_archive_script(item)
            if should_archive:
                results["to_archive"].append(
                    {
                        "file": filename,
                        "type": "script",
                        "reason": archive_reason,
                        "age_days": get_file_age_days(item),
                    }
                )
                continue

        # Check HTML files (except index.html)
        if item.suffix == ".html" and filename != "index.html":
            results["to_archive"].append(
                {
                    "file": filename,
                    "type": "html",
                    "reason": "HTML test file in root",
                    "age_days": get_file_age_days(item),
                }
            )
            continue

        # Keep everything else
        results["kept"].append({"file": filename, "reason": "no matching rule"})

    return results


def create_archive_structure(year_month: str) -> Dict[str, Path]:
    """Create archive directory structure for the given month."""
    archive_dir = ARCHIVE_BASE / year_month

    subdirs = {
        "obsolete-docs": archive_dir / "obsolete-docs",
        "temp-scripts": archive_dir / "temp-scripts",
        "test-files": archive_dir / "test-files",
    }

    # Create all subdirectories
    for subdir in subdirs.values():
        subdir.mkdir(parents=True, exist_ok=True)

    return subdirs


def archive_file(
    filepath: Path, file_type: str, year_month: str, dry_run: bool = False
) -> bool:
    """Archive a single file to appropriate location."""
    subdirs = create_archive_structure(year_month)

    # Determine destination based on file type
    if file_type == "markdown":
        dest_dir = subdirs["obsolete-docs"]
    elif file_type == "script":
        dest_dir = subdirs["temp-scripts"]
    elif file_type == "html":
        dest_dir = subdirs["test-files"]
    else:
        dest_dir = subdirs["temp-scripts"]

    dest_path = dest_dir / filepath.name

    if dry_run:
        print(
            f"[DRY-RUN] Would archive: {filepath.name} -> {dest_path.relative_to(REPO_ROOT)}"
        )
        return True

    try:
        shutil.move(str(filepath), str(dest_path))
        print(f"[ARCHIVED] {filepath.name} -> {dest_path.relative_to(REPO_ROOT)}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to archive {filepath.name}: {e}")
        return False


def delete_file(filepath: Path, dry_run: bool = False) -> bool:
    """Delete a temporary file."""
    if dry_run:
        print(f"[DRY-RUN] Would delete: {filepath.name}")
        return True

    try:
        filepath.unlink()
        print(f"[DELETED] {filepath.name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to delete {filepath.name}: {e}")
        return False


def generate_report(scan_results: Dict, actions_taken: Dict, year_month: str) -> Dict:
    """Generate cleanup report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "archive_month": year_month,
        "scan_results": {
            "to_archive": len(scan_results["to_archive"]),
            "to_delete": len(scan_results["to_delete"]),
            "whitelisted": len(scan_results["whitelisted"]),
            "kept": len(scan_results["kept"]),
        },
        "actions_taken": actions_taken,
        "files": {
            "to_archive": scan_results["to_archive"],
            "to_delete": scan_results["to_delete"],
            "whitelisted": scan_results["whitelisted"][:10],  # Limit to 10 for brevity
            "kept": scan_results["kept"][:10],  # Limit to 10 for brevity
        },
        "summary": f"{actions_taken['archived']} fichiers archivés, {actions_taken['deleted']} fichiers supprimés",
    }

    return report


def save_report(report: Dict, report_path: Path):
    """Save report to JSON file."""
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n[REPORT] Saved to: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="ANIMA Archive Guardian - Automatic repository cleanup"
    )
    parser.add_argument(
        "--auto", action="store_true", help="Archive automatically without confirmation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without doing it",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("ANIMA ARCHIVE GUARDIAN - Repository Cleanup")
    print("=" * 80)
    print()

    # Scan root directory
    print("[SCAN] Scanning root directory...")
    scan_results = scan_root_directory()

    print()
    print("[RESULTS] Scan complete:")
    print(f"  - Files to archive: {len(scan_results['to_archive'])}")
    print(f"  - Files to delete: {len(scan_results['to_delete'])}")
    print(f"  - Whitelisted files: {len(scan_results['whitelisted'])}")
    print(f"  - Files kept: {len(scan_results['kept'])}")
    print()

    # Show files to be archived
    if scan_results["to_archive"]:
        print("[TO ARCHIVE]")
        for item in scan_results["to_archive"]:
            print(f"  - {item['file']} ({item['type']}, {item['reason']})")
        print()

    # Show files to be deleted
    if scan_results["to_delete"]:
        print("[TO DELETE]")
        for item in scan_results["to_delete"]:
            print(f"  - {item['file']} ({item['reason']})")
        print()

    # Confirm if not auto mode and not dry-run
    if not args.auto and not args.dry_run:
        total_actions = len(scan_results["to_archive"]) + len(scan_results["to_delete"])
        if total_actions == 0:
            print("[OK] No actions needed. Repository is clean!")
            return

        response = input(
            f"\n[CONFIRM] Proceed with {total_actions} actions? (yes/no): "
        )
        if response.lower() != "yes":
            print("[CANCELLED] Cleanup cancelled.")
            return

    # Determine archive month
    year_month = datetime.now().strftime("%Y-%m")

    # Execute actions
    actions_taken = {"archived": 0, "deleted": 0, "errors": 0}

    print()
    print(
        f"[EXECUTE] {'DRY-RUN - ' if args.dry_run else ''}Archiving files to docs/archive/{year_month}/..."
    )
    print()

    # Archive files
    for item in scan_results["to_archive"]:
        filepath = REPO_ROOT / item["file"]
        if archive_file(filepath, item["type"], year_month, dry_run=args.dry_run):
            actions_taken["archived"] += 1
        else:
            actions_taken["errors"] += 1

    # Delete temp files
    for item in scan_results["to_delete"]:
        filepath = REPO_ROOT / item["file"]
        if delete_file(filepath, dry_run=args.dry_run):
            actions_taken["deleted"] += 1
        else:
            actions_taken["errors"] += 1

    # Generate report
    print()
    print("[REPORT] Generating cleanup report...")
    report = generate_report(scan_results, actions_taken, year_month)
    report_path = REPORTS_DIR / "archive_cleanup_report.json"
    save_report(report, report_path)

    # Summary
    print()
    print("=" * 80)
    print("[SUMMARY]")
    print("=" * 80)
    print(f"Archived: {actions_taken['archived']} files")
    print(f"Deleted: {actions_taken['deleted']} files")
    print(f"Errors: {actions_taken['errors']}")
    print()

    if args.dry_run:
        print("[DRY-RUN] No actual changes were made.")
    else:
        print("[OK] Cleanup complete!")
    print()


if __name__ == "__main__":
    main()
