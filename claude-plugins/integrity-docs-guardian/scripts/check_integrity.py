#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEO (IntegrityWatcher) - System Integrity Checker
Verifies backend/frontend coherence and detects potential regressions
"""

import sys
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PLUGIN_DIR = SCRIPT_DIR.parent
REPO_ROOT = PLUGIN_DIR.parent.parent
REPORTS_DIR = PLUGIN_DIR / "reports"

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


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


def get_changed_files(commit_ref: str = "HEAD~1") -> Dict[str, List[str]]:
    """Get files changed in the last commit, categorized by type."""
    changed = run_git_command(["git", "diff", "--name-only", commit_ref, "HEAD"])

    if not changed:
        return {"backend": [], "frontend": [], "config": []}

    files = changed.split("\n")

    categorized = {
        "backend": [],
        "frontend": [],
        "config": []
    }

    for file in files:
        if not file:
            continue

        if file.startswith("src/backend/") and file.endswith(".py"):
            categorized["backend"].append(file)
        elif file.startswith("src/frontend/") and file.endswith((".js", ".jsx", ".ts", ".tsx")):
            categorized["frontend"].append(file)
        elif file in ["openapi.json", "docker-compose.yaml", ".env.example"]:
            categorized["config"].append(file)

    return categorized


def extract_api_endpoints_from_file(file_path: Path) -> Set[str]:
    """Extract API endpoints from a Python router file."""
    endpoints = set()

    if not file_path.exists():
        return endpoints

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Match FastAPI route decorators
        # Pattern: @router.get("/path"), @router.post("/path"), etc.
        pattern = r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
        matches = re.finditer(pattern, content)

        for match in matches:
            method = match.group(1).upper()
            path = match.group(2)
            endpoints.add(f"{method} {path}")

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return endpoints


def extract_api_calls_from_file(file_path: Path) -> Set[str]:
    """Extract API calls from a frontend JavaScript/TypeScript file."""
    api_calls = set()

    if not file_path.exists():
        return api_calls

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Match axios/fetch calls
        # Pattern: axios.get('/path'), fetch('/api/path'), etc.
        patterns = [
            r'axios\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'api\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if len(match.groups()) >= 2:
                    # Has method
                    method = match.group(1).upper()
                    path = match.group(2)
                    api_calls.add(f"{method} {path}")
                else:
                    # Only path (fetch)
                    path = match.group(1)
                    api_calls.add(f"GET {path}")  # Assume GET for fetch without method

    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return api_calls


def analyze_backend_changes(files: List[str]) -> Dict:
    """Analyze backend changes for endpoints."""
    endpoints_added = set()
    endpoints_modified = set()
    endpoints_removed = set()
    schemas_changed = []

    for file in files:
        file_path = REPO_ROOT / file

        # Check for router files
        if "routers/" in file:
            current_endpoints = extract_api_endpoints_from_file(file_path)
            endpoints_added.update(current_endpoints)

            # In a full implementation, we'd compare with previous version
            # For now, we just report what exists
            if current_endpoints:
                endpoints_modified.update(current_endpoints)

        # Check for model files
        elif "models/" in file:
            model_name = Path(file).stem
            schemas_changed.append(model_name)

    return {
        "files": files,
        "endpoints_added": list(endpoints_added),
        "endpoints_modified": list(endpoints_modified),
        "endpoints_removed": list(endpoints_removed),
        "schemas_changed": schemas_changed
    }


def analyze_frontend_changes(files: List[str]) -> Dict:
    """Analyze frontend changes for API calls."""
    api_calls_added = set()
    api_calls_modified = set()
    api_calls_removed = set()

    for file in files:
        file_path = REPO_ROOT / file

        # Check for API service files or components making API calls
        if "services/api" in file or "api.js" in file or file_path.exists():
            current_calls = extract_api_calls_from_file(file_path)
            api_calls_added.update(current_calls)

    return {
        "files": files,
        "api_calls_added": list(api_calls_added),
        "api_calls_modified": list(api_calls_modified),
        "api_calls_removed": list(api_calls_removed)
    }


def detect_integrity_issues(backend_analysis: Dict, frontend_analysis: Dict) -> List[Dict]:
    """Detect integrity issues between backend and frontend."""
    issues = []

    # Check for frontend calls to non-existent backend endpoints
    backend_endpoints = set(backend_analysis["endpoints_added"] + backend_analysis["endpoints_modified"])
    frontend_calls = set(frontend_analysis["api_calls_added"])

    # Normalize paths for comparison (remove /api/v1 prefix variations)
    def normalize_endpoint(endpoint: str) -> str:
        method, path = endpoint.split(" ", 1) if " " in endpoint else ("GET", endpoint)
        # Remove common prefixes
        path = path.replace("/api/v1", "").replace("/api", "")
        return f"{method} {path}"

    normalized_backend = {normalize_endpoint(e) for e in backend_endpoints}

    # Find frontend calls that might not have backend endpoints
    # This is a heuristic - in production you'd check against a complete endpoint registry
    for call in frontend_calls:
        norm_call = normalize_endpoint(call)
        if norm_call not in normalized_backend and backend_endpoints:
            # Only report if we have backend data to compare
            issues.append({
                "severity": "warning",
                "type": "potential_missing_endpoint",
                "description": f"Frontend calls endpoint that may not exist in recent backend changes: {call}",
                "affected_files": frontend_analysis["files"],
                "recommendation": "Verify that backend endpoint exists and is properly registered"
            })

    # Check for schema changes without corresponding frontend updates
    if backend_analysis["schemas_changed"] and not frontend_analysis["files"]:
        issues.append({
            "severity": "warning",
            "type": "schema_change_without_frontend_update",
            "description": f"Backend schemas changed ({', '.join(backend_analysis['schemas_changed'])}) but no frontend files updated",
            "affected_files": backend_analysis["files"],
            "recommendation": "Verify frontend types/interfaces are aligned with backend schema changes"
        })

    # Check OpenAPI schema status
    openapi_path = REPO_ROOT / "openapi.json"
    if backend_analysis["endpoints_added"] and openapi_path.exists():
        # Check if openapi.json was modified in this commit
        changed_files = run_git_command(["git", "diff", "--name-only", "HEAD~1", "HEAD"])
        if "openapi.json" not in changed_files:
            issues.append({
                "severity": "warning",
                "type": "openapi_outdated",
                "description": "Backend endpoints modified but OpenAPI schema not regenerated",
                "affected_files": ["openapi.json"],
                "recommendation": "Regenerate OpenAPI schema to reflect endpoint changes"
            })

    return issues


def validate_openapi_schema() -> Dict:
    """Validate OpenAPI schema status."""
    openapi_path = REPO_ROOT / "openapi.json"

    if not openapi_path.exists():
        return {
            "status": "missing",
            "missing_endpoints": [],
            "outdated_schemas": []
        }

    # In a full implementation, we'd parse the schema and compare with actual code
    # For now, just check if it was recently updated
    try:
        with open(openapi_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # Basic validation
        has_paths = "paths" in schema and len(schema["paths"]) > 0
        has_schemas = "components" in schema and "schemas" in schema.get("components", {})

        if has_paths and has_schemas:
            return {
                "status": "ok",
                "endpoints_count": len(schema["paths"]),
                "schemas_count": len(schema.get("components", {}).get("schemas", {}))
            }
        else:
            return {
                "status": "incomplete",
                "missing_endpoints": [] if has_paths else ["paths section missing"],
                "outdated_schemas": [] if has_schemas else ["schemas section missing"]
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def generate_report(changed_files: Dict[str, List[str]]) -> Dict:
    """Generate the main integrity report."""
    commit_hash, commit_msg = get_commit_info()

    # Analyze changes
    backend_analysis = analyze_backend_changes(changed_files["backend"])
    frontend_analysis = analyze_frontend_changes(changed_files["frontend"])

    # Detect issues
    issues = detect_integrity_issues(backend_analysis, frontend_analysis)

    # Validate OpenAPI
    openapi_validation = validate_openapi_schema()

    # Determine status
    critical_count = len([i for i in issues if i["severity"] == "critical"])
    warning_count = len([i for i in issues if i["severity"] == "warning"])

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "ok"

    # Build report
    report = {
        "timestamp": datetime.now().isoformat(),
        "commit_hash": commit_hash,
        "commit_message": commit_msg,
        "status": status,
        "backend_changes": backend_analysis,
        "frontend_changes": frontend_analysis,
        "issues": issues,
        "openapi_validation": openapi_validation,
        "statistics": {
            "backend_files_changed": len(changed_files["backend"]),
            "frontend_files_changed": len(changed_files["frontend"]),
            "issues_found": len(issues),
            "critical": critical_count,
            "warnings": warning_count,
            "info": len([i for i in issues if i["severity"] == "info"])
        },
        "summary": f"{critical_count} critical, {warning_count} warning(s), {len(issues)} total issue(s) found"
    }

    return report


def main():
    """Main entry point."""
    print("🔐 NEO (IntegrityWatcher) - Checking system integrity...")

    # Get changed files
    changed_files = get_changed_files()

    total_changes = sum(len(files) for files in changed_files.values())
    print(f"📝 Detected {total_changes} changed file(s)")

    if total_changes == 0:
        print("ℹ️  No backend/frontend changes detected - skipping analysis")
        # Still generate a report for consistency
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": "ok",
            "backend_changes": {"files": [], "endpoints_added": [], "endpoints_modified": [], "endpoints_removed": [], "schemas_changed": []},
            "frontend_changes": {"files": [], "api_calls_added": [], "api_calls_modified": [], "api_calls_removed": []},
            "issues": [],
            "openapi_validation": validate_openapi_schema(),
            "statistics": {"backend_files_changed": 0, "frontend_files_changed": 0, "issues_found": 0, "critical": 0, "warnings": 0, "info": 0},
            "summary": "No changes detected"
        }
    else:
        # Generate report
        report = generate_report(changed_files)

    # Save report
    report_file = REPORTS_DIR / "integrity_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✅ Report generated: {report_file}")
    print(f"📊 Summary: {report['summary']}")

    # Return exit code based on severity
    if report["statistics"]["critical"] > 0:
        print("🚨 CRITICAL issues found - immediate action required")
        return 2
    elif report["statistics"]["warnings"] > 0:
        print("⚠️  Warnings found - review recommended")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
