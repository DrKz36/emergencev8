#!/usr/bin/env python3
"""
ARGUS Log Analyzer
Analyzes captured logs from backend and frontend to detect errors,
generate fix proposals, and optionally apply fixes.
"""

import re
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

# Add parent directory to path for imports
script_dir = Path(__file__).parent
root_dir = script_dir.parent
project_root = root_dir.parent
sys.path.insert(0, str(project_root))

# Error pattern definitions
BACKEND_ERROR_PATTERNS = [
    {
        "type": "ImportError",
        "pattern": r"ImportError:\s+No module named ['\"]([^'\"]+)['\"]",
        "severity": "critical",
        "extract_module": 1
    },
    {
        "type": "ModuleNotFoundError",
        "pattern": r"ModuleNotFoundError:\s+No module named ['\"]([^'\"]+)['\"]",
        "severity": "critical",
        "extract_module": 1
    },
    {
        "type": "AttributeError",
        "pattern": r"AttributeError:\s+'(\w+)'\s+object has no attribute '(\w+)'",
        "severity": "critical"
    },
    {
        "type": "KeyError",
        "pattern": r"KeyError:\s+['\"]([^'\"]+)['\"]",
        "severity": "warning"
    },
    {
        "type": "TypeError",
        "pattern": r"TypeError:\s+(.+)",
        "severity": "critical"
    },
    {
        "type": "ValidationError",
        "pattern": r"ValidationError:\s+(.+)",
        "severity": "warning"
    },
    {
        "type": "DatabaseError",
        "pattern": r"(sqlalchemy\.\w+\.)?(\w*Error):\s+(.+)",
        "severity": "critical"
    },
    {
        "type": "HTTP500",
        "pattern": r"HTTP/\d\.\d\"\s+500",
        "severity": "critical"
    },
    {
        "type": "HTTP404",
        "pattern": r"HTTP/\d\.\d\"\s+404",
        "severity": "warning"
    },
    {
        "type": "Exception",
        "pattern": r"(\w+Exception):\s+(.+)",
        "severity": "warning"
    }
]

FRONTEND_ERROR_PATTERNS = [
    {
        "type": "TypeError",
        "pattern": r"TypeError:\s+(.+)",
        "severity": "critical"
    },
    {
        "type": "ReferenceError",
        "pattern": r"ReferenceError:\s+(.+)",
        "severity": "critical"
    },
    {
        "type": "SyntaxError",
        "pattern": r"SyntaxError:\s+(.+)",
        "severity": "critical"
    },
    {
        "type": "NetworkError",
        "pattern": r"(Network Error|Failed to fetch)",
        "severity": "warning"
    },
    {
        "type": "ReactWarning",
        "pattern": r"Warning:\s+(.+)",
        "severity": "info"
    },
    {
        "type": "ConsoleError",
        "pattern": r"Error:\s+(.+)",
        "severity": "warning"
    }
]


class ErrorDetector:
    """Detects errors in log files"""

    def __init__(self):
        self.backend_errors = []
        self.frontend_errors = []

    def analyze_backend_logs(self, log_file: Path) -> List[Dict[str, Any]]:
        """Analyze backend log file for errors"""
        if not log_file.exists():
            return []

        errors = []
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            for pattern_def in BACKEND_ERROR_PATTERNS:
                match = re.search(pattern_def["pattern"], line, re.IGNORECASE)
                if match:
                    error = {
                        "timestamp": datetime.now().isoformat(),
                        "severity": pattern_def["severity"],
                        "type": pattern_def["type"],
                        "message": match.group(0),
                        "line_number": i + 1,
                        "context": line.strip(),
                        "file": None,  # Extract from traceback if available
                        "stack_trace": self._extract_stack_trace(lines, i)
                    }

                    # Extract module name for import errors
                    if "extract_module" in pattern_def:
                        error["module"] = match.group(pattern_def["extract_module"])

                    errors.append(error)
                    break

        return errors

    def analyze_frontend_logs(self, log_file: Path) -> List[Dict[str, Any]]:
        """Analyze frontend log file for errors"""
        if not log_file.exists():
            return []

        errors = []
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            for pattern_def in FRONTEND_ERROR_PATTERNS:
                match = re.search(pattern_def["pattern"], line, re.IGNORECASE)
                if match:
                    error = {
                        "timestamp": datetime.now().isoformat(),
                        "severity": pattern_def["severity"],
                        "type": pattern_def["type"],
                        "message": match.group(0),
                        "line_number": i + 1,
                        "context": line.strip(),
                        "file": None,  # Extract from traceback if available
                        "stack_trace": self._extract_stack_trace(lines, i)
                    }

                    errors.append(error)
                    break

        return errors

    def _extract_stack_trace(self, lines: List[str], error_line: int, max_lines: int = 10) -> str:
        """Extract stack trace around error line"""
        start = max(0, error_line - 5)
        end = min(len(lines), error_line + max_lines)
        return ''.join(lines[start:end])


class FixGenerator:
    """Generates fix proposals for detected errors"""

    def generate_fixes(self, error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fix proposals for an error"""
        error_type = error.get("type")

        if error_type in ["ImportError", "ModuleNotFoundError"]:
            return self._fix_import_error(error)
        elif error_type == "AttributeError":
            return self._fix_attribute_error(error)
        elif error_type == "TypeError":
            return self._fix_type_error(error)
        elif error_type == "ValidationError":
            return self._fix_validation_error(error)
        elif error_type == "NetworkError":
            return self._fix_network_error(error)
        elif error_type == "ReactWarning":
            return self._fix_react_warning(error)
        else:
            return self._generic_fix(error)

    def _fix_import_error(self, error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for import errors"""
        module = error.get("module", "unknown")

        # Common module name mappings
        pip_packages = {
            "jwt": "pyjwt",
            "jose": "python-jose",
            "dotenv": "python-dotenv",
            "PIL": "pillow",
            "cv2": "opencv-python",
            "yaml": "pyyaml",
            "bs4": "beautifulsoup4",
        }

        package_name = pip_packages.get(module, module)

        return [
            {
                "confidence": 95,
                "type": "dependency_install",
                "description": f"Install missing {package_name} package",
                "actions": [
                    {
                        "type": "shell_command",
                        "command": f"pip install {package_name}",
                        "description": f"Install {package_name} via pip"
                    }
                ],
                "estimated_time": "30 seconds",
                "risk": "low"
            }
        ]

    def _fix_attribute_error(self, error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for attribute errors"""
        return [
            {
                "confidence": 80,
                "type": "code_fix",
                "description": "Add null/None check before accessing attribute",
                "actions": [
                    {
                        "type": "manual_review",
                        "description": "Review code and add null checks (e.g., if obj is not None: ...)"
                    }
                ],
                "estimated_time": "5 minutes",
                "risk": "low"
            }
        ]

    def _fix_type_error(self, error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for type errors"""
        message = error.get("message", "")

        if "NoneType" in message or "undefined" in message:
            return [
                {
                    "confidence": 85,
                    "type": "code_fix",
                    "description": "Add null/undefined check",
                    "actions": [
                        {
                            "type": "manual_review",
                            "description": "Add optional chaining (?.) or null check"
                        }
                    ],
                    "estimated_time": "2 minutes",
                    "risk": "low"
                }
            ]

        return self._generic_fix(error)

    def _fix_validation_error(self, error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for validation errors"""
        return [
            {
                "confidence": 70,
                "type": "schema_alignment",
                "description": "Review backend/frontend schema alignment",
                "actions": [
                    {
                        "type": "manual_review",
                        "description": "Check if frontend is sending all required fields"
                    }
                ],
                "estimated_time": "10 minutes",
                "risk": "medium"
            }
        ]

    def _fix_network_error(self, error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for network errors"""
        return [
            {
                "confidence": 60,
                "type": "configuration",
                "description": "Check CORS configuration and API endpoint availability",
                "actions": [
                    {
                        "type": "manual_review",
                        "description": "Verify backend is running and CORS is configured"
                    }
                ],
                "estimated_time": "5 minutes",
                "risk": "low"
            }
        ]

    def _fix_react_warning(self, error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fixes for React warnings"""
        message = error.get("message", "")

        if "key" in message.lower():
            return [
                {
                    "confidence": 90,
                    "type": "code_fix",
                    "description": "Add unique 'key' prop to list items",
                    "actions": [
                        {
                            "type": "manual_review",
                            "description": "Add key={item.id} or key={index} to mapped elements"
                        }
                    ],
                    "estimated_time": "2 minutes",
                    "risk": "low"
                }
            ]

        return self._generic_fix(error)

    def _generic_fix(self, error: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generic fix proposal"""
        return [
            {
                "confidence": 50,
                "type": "manual_review",
                "description": "Review error context and fix manually",
                "actions": [
                    {
                        "type": "manual_review",
                        "description": f"Investigate {error.get('type')} error"
                    }
                ],
                "estimated_time": "10 minutes",
                "risk": "unknown"
            }
        ]


class ReportGenerator:
    """Generates analysis reports"""

    def __init__(self):
        self.detector = ErrorDetector()
        self.fix_generator = FixGenerator()

    def generate_report(
        self,
        session_id: str,
        backend_log: Optional[Path],
        frontend_log: Optional[Path],
        start_time: datetime,
        include_fixes: bool = True
    ) -> Dict[str, Any]:
        """Generate comprehensive error report"""

        # Analyze logs
        backend_errors = []
        frontend_errors = []

        if backend_log and backend_log.exists():
            backend_errors = self.detector.analyze_backend_logs(backend_log)

        if frontend_log and frontend_log.exists():
            frontend_errors = self.detector.analyze_frontend_logs(frontend_log)

        # Generate fixes if requested
        if include_fixes:
            for error in backend_errors:
                error["fix_proposals"] = self.fix_generator.generate_fixes(error)

            for error in frontend_errors:
                error["fix_proposals"] = self.fix_generator.generate_fixes(error)

        # Calculate statistics
        total_errors = len(backend_errors) + len(frontend_errors)
        critical = sum(1 for e in backend_errors + frontend_errors if e.get("severity") == "critical")
        warnings = sum(1 for e in backend_errors + frontend_errors if e.get("severity") == "warning")
        info = sum(1 for e in backend_errors + frontend_errors if e.get("severity") == "info")

        # Determine status
        if critical > 0:
            status = "errors_detected"
        elif warnings > 0:
            status = "warnings"
        elif info > 0:
            status = "info_only"
        else:
            status = "ok"

        # Build report
        duration_minutes = (datetime.now() - start_time).total_seconds() / 60

        report = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "monitoring_duration_minutes": round(duration_minutes, 2),
            "status": status,
            "backend_errors": backend_errors,
            "frontend_errors": frontend_errors,
            "statistics": {
                "total_errors": total_errors,
                "critical": critical,
                "warnings": warnings,
                "info": info,
                "backend_errors": len(backend_errors),
                "frontend_errors": len(frontend_errors),
                "unique_errors": total_errors,  # TODO: Deduplicate
                "recurring_errors": 0  # TODO: Detect recurring
            }
        }

        return report


def main():
    parser = argparse.ArgumentParser(description="ARGUS Log Analyzer")
    parser.add_argument("--session-id", required=True, help="Monitoring session ID")
    parser.add_argument("--output", required=True, help="Output report file path")
    parser.add_argument("--backend-log", help="Backend log file path")
    parser.add_argument("--frontend-log", help="Frontend log file path")
    parser.add_argument("--final", action="store_true", help="Final analysis (not incremental)")
    parser.add_argument("--auto-fix", action="store_true", help="Auto-apply high-confidence fixes")
    parser.add_argument("--report-only", action="store_true", help="Generate report only, no fixes")

    args = parser.parse_args()

    # Determine log file paths
    reports_dir = script_dir.parent / "reports"
    backend_log = Path(args.backend_log) if args.backend_log else reports_dir / f"backend_buffer_{args.session_id}.log"
    frontend_log = Path(args.frontend_log) if args.frontend_log else reports_dir / f"frontend_buffer_{args.session_id}.log"

    # Generate report
    generator = ReportGenerator()
    start_time = datetime.now()  # TODO: Load from session file

    include_fixes = not args.report_only
    report = generator.generate_report(
        session_id=args.session_id,
        backend_log=backend_log,
        frontend_log=frontend_log,
        start_time=start_time,
        include_fixes=include_fixes
    )

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✅ Report generated: {output_path}")
    print(f"   Status: {report['status']}")
    print(f"   Total errors: {report['statistics']['total_errors']}")

    # Auto-fix if requested
    if args.auto_fix and not args.report_only:
        print("\n🤖 Auto-fix mode enabled (not yet implemented)")
        # TODO: Implement auto-fix logic

    # Exit with appropriate code
    if report['status'] == "ok":
        return 0
    elif report['status'] in ["info_only", "warnings"]:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
