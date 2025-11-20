#!/usr/bin/env python3
"""
Master Guardian Orchestrator
Coordinates all Guardian sub-agents with locking, conflict detection, and unified reporting.
Version: 3.0.0
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

# Setup paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = ROOT_DIR.parent.parent  # Go up to repo root
REPORTS_DIR = PROJECT_ROOT / "reports"  # UNIFIED: All reports in repo root
LOCK_FILE = ROOT_DIR / ".guardian_lock"
CONFIG_FILE = ROOT_DIR / "config" / "guardian_config.json"

# Ensure reports directory exists
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging (with UTF-8 encoding for Windows)
import io

# Force UTF-8 for stdout/stderr on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(REPORTS_DIR / "orchestrator.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class GuardianLock:
    """Guardian orchestration lock manager"""

    def __init__(self, agent_name: str, operation: str, timeout: int = 30):
        self.agent_name = agent_name
        self.operation = operation
        self.timeout = timeout
        self.acquired = False

    def acquire(self) -> bool:
        """Try to acquire lock with timeout"""
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            if not LOCK_FILE.exists():
                self._create_lock()
                self.acquired = True
                logger.info(f"🔒 Lock acquired by {self.agent_name}")
                return True
            else:
                # Check if lock is stale (> 5 minutes old)
                try:
                    with open(LOCK_FILE, "r") as f:
                        lock_data = json.load(f)

                    lock_age = time.time() - lock_data.get("timestamp", 0)
                    if lock_age > 300:  # 5 minutes
                        logger.warning(
                            f"⚠️  Stale lock detected (age: {lock_age:.0f}s). Force releasing..."
                        )
                        self.release()
                        self._create_lock()
                        self.acquired = True
                        return True
                except:
                    # Corrupt lock file - force release
                    self.release()
                    self._create_lock()
                    self.acquired = True
                    return True

            time.sleep(1)

        logger.error(f"❌ Lock acquisition timeout ({self.timeout}s)")
        return False

    def _create_lock(self):
        """Create lock file"""
        lock_data = {
            "locked_by": self.agent_name,
            "timestamp": time.time(),
            "pid": os.getpid(),
            "operation": self.operation,
        }
        with open(LOCK_FILE, "w") as f:
            json.dump(lock_data, f, indent=2)

    def release(self):
        """Release lock"""
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            logger.info(f"🔓 Lock released by {self.agent_name}")
            self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("Failed to acquire Guardian lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class AgentExecutor:
    """Execute individual Guardian agents"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def run_agent(self, agent_name: str) -> Dict[str, Any]:
        """Run a single agent and return its report"""
        logger.info(f"🚀 Launching {agent_name}...")

        agent_config = self.config.get("agents", {}).get(agent_name, {})
        if not agent_config.get("enabled", True):
            logger.warning(f"⏸️  {agent_name} is disabled in config")
            return {"status": "skipped", "reason": "disabled_in_config"}

        # Map agent to script
        agent_scripts = {
            "anima": "scan_docs.py",
            "neo": "check_integrity.py",
            "prodguardian": "check_prod_logs.py",
            "argus": "argus_analyzer.py",
            "theia": "analyze_ai_costs.py",
            "nexus": "generate_report.py",
        }

        script_name = agent_scripts.get(agent_name)
        if not script_name:
            logger.error(f"❌ Unknown agent: {agent_name}")
            return {"status": "error", "error": f"Unknown agent: {agent_name}"}

        script_path = SCRIPT_DIR / script_name
        if not script_path.exists():
            logger.error(f"❌ Script not found: {script_path}")
            return {"status": "error", "error": f"Script not found: {script_path}"}

        # Execute agent
        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes max per agent
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                logger.info(
                    f"✅ {agent_name} completed successfully ({execution_time:.1f}s)"
                )

                # Load agent report
                report_files = {
                    "anima": "docs_report.json",
                    "neo": "integrity_report.json",
                    "prodguardian": "prod_report.json",
                    "argus": "dev_logs_report.json",
                    "theia": "cost_report.json",
                    "nexus": "unified_report.json",
                }

                report_file = REPORTS_DIR / report_files.get(
                    agent_name, f"{agent_name}_report.json"
                )
                if report_file.exists():
                    with open(report_file, "r") as f:
                        report = json.load(f)
                    return {
                        "status": "success",
                        "execution_time": execution_time,
                        "report": report,
                    }
                else:
                    logger.warning(f"⚠️  {agent_name} completed but report not found")
                    return {
                        "status": "success",
                        "execution_time": execution_time,
                        "report": None,
                    }
            else:
                logger.error(f"❌ {agent_name} failed (exit code: {result.returncode})")
                logger.error(f"   Error output: {result.stderr}")
                return {
                    "status": "error",
                    "execution_time": execution_time,
                    "error": result.stderr,
                    "stdout": result.stdout,
                }

        except subprocess.TimeoutExpired:
            logger.error(f"❌ {agent_name} timed out (120s)")
            return {
                "status": "timeout",
                "execution_time": 120,
                "error": "Agent execution timed out",
            }
        except Exception as e:
            logger.error(f"❌ {agent_name} crashed: {e}")
            return {
                "status": "crashed",
                "execution_time": time.time() - start_time,
                "error": str(e),
            }


class ConflictDetector:
    """Detect conflicts between agent recommendations"""

    def detect_conflicts(self, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze agent results for conflicts"""
        conflicts = []

        # Extract issues from each agent
        all_issues = {}
        for agent_name, result in agent_results.items():
            if result.get("status") == "success" and result.get("report"):
                issues = result["report"].get("issues", [])
                all_issues[agent_name] = issues

        # Check for conflicting recommendations
        # Example: Anima wants to update API docs, but Neo says endpoint is deprecated
        # TODO: Implement specific conflict detection logic

        logger.info(f"🔍 Conflict detection: {len(conflicts)} conflicts found")
        return conflicts


class MasterOrchestrator:
    """Main orchestrator coordinating all Guardian agents"""

    def __init__(self):
        self.config = self._load_config()
        self.executor = AgentExecutor(self.config)
        self.conflict_detector = ConflictDetector()
        self.orchestration_id = f"orch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    def _load_config(self) -> Dict[str, Any]:
        """Load guardian configuration"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        else:
            logger.warning("⚠️  Config file not found, using defaults")
            return {
                "agents": {
                    "anima": {"enabled": True},
                    "neo": {"enabled": True},
                    "prodguardian": {"enabled": True},
                    "nexus": {"enabled": True},
                },
                "orchestration": {"max_parallel_agents": 4},
            }

    def run_full_orchestration(self) -> Dict[str, Any]:
        """Run complete orchestration pipeline"""
        logger.info("=" * 60)
        logger.info("🤖 MASTER GUARDIAN ORCHESTRATION")
        logger.info(f"   Orchestration ID: {self.orchestration_id}")
        logger.info("=" * 60)

        start_time = time.time()

        # Step 1: Acquire lock
        logger.info("\n[Step 1/9] Acquiring orchestration lock...")
        with GuardianLock("master_orchestrator", "full_orchestration"):
            # Step 2: Context detection
            logger.info("\n[Step 2/9] Detecting context...")
            context = self._detect_context()

            # Step 3: Execute agents
            logger.info("\n[Step 3/9] Executing agents...")
            agent_results = self._execute_agents()

            # Step 4: Conflict detection
            logger.info("\n[Step 4/9] Detecting conflicts...")
            conflicts = self.conflict_detector.detect_conflicts(agent_results)

            # Step 5: Generate unified report
            logger.info("\n[Step 5/9] Generating unified report...")
            unified_report = self._generate_unified_report(
                context, agent_results, conflicts
            )

            # Step 6: User validation (if needed)
            logger.info("\n[Step 6/9] User validation...")
            validation_result = self._request_validation(unified_report)

            # Step 7: Apply approved fixes
            logger.info("\n[Step 7/9] Applying approved fixes...")
            if validation_result.get("approved"):
                self._apply_fixes(unified_report)

            # Step 8: Save global report
            logger.info("\n[Step 8/9] Saving global report...")
            self._save_global_report(unified_report)

            # Step 9: Send email report to admins
            logger.info("\n[Step 9/9] Sending email report to administrators...")
            self._send_email_report()

        execution_time = time.time() - start_time
        logger.info(f"\n✅ Orchestration completed in {execution_time:.1f}s")

        return unified_report

    def _detect_context(self) -> Dict[str, Any]:
        """Detect current system context"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "orchestration_id": self.orchestration_id,
        }

        # Git context
        try:
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
            ).strip()
            context["commit_hash"] = commit_hash

            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=PROJECT_ROOT,
                text=True,
            ).strip()
            context["branch"] = branch

            logger.info(f"   Git: {branch} @ {commit_hash[:8]}")
        except Exception as e:
            logger.warning(f"   Git detection failed: {e}")
            context["commit_hash"] = "unknown"
            context["branch"] = "unknown"

        return context

    def _execute_agents(self) -> Dict[str, Any]:
        """Execute all enabled agents"""
        agents_to_run = ["anima", "neo", "prodguardian", "nexus"]
        results = {}

        for agent in agents_to_run:
            result = self.executor.run_agent(agent)
            results[agent] = result

        # Summary
        succeeded = sum(1 for r in results.values() if r.get("status") == "success")
        failed = len(results) - succeeded

        logger.info("\n📊 Agent Execution Summary:")
        logger.info(f"   Succeeded: {succeeded}/{len(results)}")
        logger.info(f"   Failed: {failed}/{len(results)}")

        return results

    def _generate_unified_report(
        self,
        context: Dict[str, Any],
        agent_results: Dict[str, Any],
        conflicts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate unified report from all agents"""

        # Count issues by priority
        total_issues = 0
        critical = 0
        warnings = 0

        for agent_name, result in agent_results.items():
            if result.get("status") == "success" and result.get("report"):
                report = result["report"]
                stats = report.get("statistics", {}) or report.get("summary", {})
                total_issues += stats.get("total_issues", 0)
                critical += stats.get("critical", 0)
                warnings += stats.get("warnings", 0)

        # Determine overall status
        if critical > 0:
            status = "critical"
        elif warnings > 0:
            status = "warning"
        else:
            status = "ok"

        unified_report = {
            "metadata": {
                "timestamp": context["timestamp"],
                "orchestration_id": context["orchestration_id"],
                "commit_hash": context.get("commit_hash"),
                "branch": context.get("branch"),
                "version": "3.0.0",
            },
            "executive_summary": {
                "status": status,
                "total_issues": total_issues,
                "critical": critical,
                "warnings": warnings,
                "headline": self._generate_headline(total_issues, critical, warnings),
            },
            "agent_results": agent_results,
            "conflicts_detected": conflicts,
            "recommendations": self._generate_recommendations(agent_results),
        }

        return unified_report

    def _generate_headline(self, total: int, critical: int, warnings: int) -> str:
        """Generate executive summary headline"""
        if critical > 0:
            return (
                f"🔴 {critical} critical issue(s) detected - immediate action required"
            )
        elif warnings > 0:
            return f"🟡 {warnings} warning(s) detected - review recommended"
        elif total > 0:
            return f"🟢 {total} info item(s) detected - no action required"
        else:
            return "🎉 All checks passed - no issues detected"

    def _generate_recommendations(
        self, agent_results: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate prioritized recommendations"""
        immediate = []
        short_term = []
        long_term = []

        for agent_name, result in agent_results.items():
            if result.get("status") == "success" and result.get("report"):
                report = result["report"]
                recs = report.get("recommendations", {})

                # Handle both dict and list formats
                if isinstance(recs, dict):
                    immediate.extend(recs.get("immediate", []))
                    short_term.extend(recs.get("short_term", []))
                    long_term.extend(recs.get("long_term", []))
                elif isinstance(recs, list):
                    # If recommendations is a list, add to immediate
                    immediate.extend(recs)

        return {
            "immediate": immediate,
            "short_term": short_term,
            "long_term": long_term,
        }

    def _request_validation(self, unified_report: Dict[str, Any]) -> Dict[str, Any]:
        """Request user validation for critical actions"""
        status = unified_report["executive_summary"]["status"]

        if status == "ok":
            return {"approved": True, "reason": "no_issues"}

        # For now, auto-approve non-critical
        # TODO: Implement interactive approval
        return {"approved": True, "reason": "auto_approved"}

    def _apply_fixes(self, unified_report: Dict[str, Any]):
        """Apply approved fixes"""
        logger.info("   No auto-fixes implemented yet (placeholder)")
        # TODO: Implement fix application logic

    def _save_global_report(self, unified_report: Dict[str, Any]):
        """Save unified report to disk"""
        output_file = REPORTS_DIR / "global_report.json"
        with open(output_file, "w") as f:
            json.dump(unified_report, f, indent=2)

        logger.info(f"   Report saved: {output_file}")

        # Display summary
        self._display_summary(unified_report)

    def _display_summary(self, report: Dict[str, Any]):
        """Display orchestration summary"""
        summary = report["executive_summary"]

        print("\n" + "=" * 60)
        print("📊 GUARDIAN ORCHESTRATION SUMMARY")
        print("=" * 60)
        print(f"\nStatus: {summary['status'].upper()}")
        print(f"Headline: {summary['headline']}")
        print("\nIssues Found:")
        print(f"  Total: {summary['total_issues']}")
        print(f"  Critical: {summary['critical']}")
        print(f"  Warnings: {summary['warnings']}")

        recs = report["recommendations"]
        if recs["immediate"]:
            print("\n⚠️  Immediate Actions Required:")
            for i, rec in enumerate(recs["immediate"][:3], 1):
                print(f"  {i}. {rec}")

        print("\n" + "=" * 60)

    def _send_email_report(self):
        """Send Guardian reports via email to administrators"""
        try:
            email_script = SCRIPT_DIR / "send_guardian_reports_email.py"
            if not email_script.exists():
                logger.warning("⚠️  Email script not found, skipping email notification")
                return

            result = subprocess.run(
                [sys.executable, str(email_script)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                logger.info("✅ Email report sent successfully to administrators")
            else:
                logger.warning(f"⚠️  Email sending failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.warning("⚠️  Email sending timed out (30s)")
        except Exception as e:
            logger.warning(f"⚠️  Email sending error: {e}")


def main():
    """Main entry point"""
    try:
        orchestrator = MasterOrchestrator()
        orchestrator.run_full_orchestration()
        return 0
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Orchestration interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Orchestration failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
