#!/usr/bin/env python3
"""
QA P1 Preference Extraction Validation Script

Teste l'extraction de préférences/intentions/contraintes et valide les métriques P1.

Usage:
    python scripts/qa/qa_p1_validation.py --base-url https://emergence-app-486095406755.europe-west1.run.app --login-email <email> --login-password <password>

    # Ou avec dev bypass (local)
    python scripts/qa/qa_p1_validation.py --dev-bypass
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOGGER = logging.getLogger("qa.p1")

# Default URLs
DEFAULT_BASE_URL = os.environ.get(
    "EMERGENCE_QA_BASE_URL", "https://emergence-app-486095406755.europe-west1.run.app"
)
DEFAULT_LOGIN_EMAIL = os.environ.get("EMERGENCE_SMOKE_EMAIL", "")
DEFAULT_LOGIN_PASSWORD = os.environ.get("EMERGENCE_SMOKE_PASSWORD", "")

# Test messages containing explicit preferences/intents/constraints
P1_TEST_MESSAGES = [
    "Bonjour, je voudrais te parler de mes préférences de développement.",
    "Je préfère utiliser Python pour mes projets backend, surtout avec FastAPI.",
    "J'évite d'utiliser jQuery dans mes nouvelles applications web, c'est trop ancien.",
    "Je vais apprendre TypeScript la semaine prochaine pour améliorer mon code frontend.",
    "J'aime beaucoup travailler avec Claude Code pour automatiser mes tâches répétitives.",
    "Je planifie de migrer mon projet principal vers Docker d'ici la fin du mois.",
]

# Expected metrics after extraction
P1_METRICS_EXPECTED = {
    "memory_preferences_extracted_total{type=\"preference\"}": 3.0,
    "memory_preferences_extracted_total{type=\"intent\"}": 2.0,
    "memory_preferences_confidence_count": 5.0,
    "memory_preferences_extraction_duration_seconds_count": 1.0,
}


@dataclass
class P1MetricsSnapshot:
    """Snapshot des métriques P1"""

    extracted_preference: float = 0.0
    extracted_intent: float = 0.0
    extracted_constraint: float = 0.0
    confidence_count: float = 0.0
    confidence_sum: float = 0.0
    extraction_count: float = 0.0
    extraction_sum: float = 0.0
    lexical_filtered: float = 0.0
    llm_calls: float = 0.0

    def delta(self, other: "P1MetricsSnapshot") -> "P1MetricsSnapshot":
        """Calculate delta between two snapshots"""
        return P1MetricsSnapshot(
            extracted_preference=other.extracted_preference - self.extracted_preference,
            extracted_intent=other.extracted_intent - self.extracted_intent,
            extracted_constraint=other.extracted_constraint - self.extracted_constraint,
            confidence_count=other.confidence_count - self.confidence_count,
            confidence_sum=other.confidence_sum - self.confidence_sum,
            extraction_count=other.extraction_count - self.extraction_count,
            extraction_sum=other.extraction_sum - self.extraction_sum,
            lexical_filtered=other.lexical_filtered - self.lexical_filtered,
            llm_calls=other.llm_calls - self.llm_calls,
        )

    @property
    def average_confidence(self) -> float:
        """Calculate average confidence score"""
        if self.confidence_count > 0:
            return self.confidence_sum / self.confidence_count
        return 0.0

    @property
    def average_extraction_duration(self) -> float:
        """Calculate average extraction duration in seconds"""
        if self.extraction_count > 0:
            return self.extraction_sum / self.extraction_count
        return 0.0

    @property
    def filtering_rate(self) -> float:
        """Calculate lexical filtering rate (0-1)"""
        total = self.lexical_filtered + self.llm_calls
        if total > 0:
            return self.lexical_filtered / total
        return 0.0


@dataclass
class P1ValidationReport:
    """Rapport de validation P1"""

    timestamp: str
    base_url: str
    thread_id: Optional[str]
    user_sub: Optional[str]
    metrics_before: P1MetricsSnapshot
    metrics_after: P1MetricsSnapshot
    metrics_delta: P1MetricsSnapshot
    success: bool
    errors: List[str]
    messages_sent: int
    consolidation_triggered: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "base_url": self.base_url,
            "thread_id": self.thread_id,
            "user_sub": self.user_sub,
            "metrics_before": asdict(self.metrics_before),
            "metrics_after": asdict(self.metrics_after),
            "metrics_delta": asdict(self.metrics_delta),
            "success": self.success,
            "errors": self.errors,
            "messages_sent": self.messages_sent,
            "consolidation_triggered": self.consolidation_triggered,
            "validation": {
                "extracted_total": self.metrics_delta.extracted_preference
                + self.metrics_delta.extracted_intent
                + self.metrics_delta.extracted_constraint,
                "average_confidence": self.metrics_delta.average_confidence,
                "average_duration_seconds": self.metrics_delta.average_extraction_duration,
                "filtering_rate_percent": self.metrics_delta.filtering_rate * 100,
            },
        }


def _parse_prometheus_line(line: str) -> tuple[str, float] | None:
    """Parse une ligne Prometheus (format: metric_name{labels} value)"""
    if line.startswith("#") or not line.strip():
        return None
    parts = line.split()
    if len(parts) < 2:
        return None
    try:
        value = float(parts[-1])
        # Extract metric name with labels
        metric = " ".join(parts[:-1])
        return metric, value
    except ValueError:
        return None


async def fetch_p1_metrics(base_url: str) -> P1MetricsSnapshot:
    """Fetch current P1 metrics from /api/metrics endpoint"""
    LOGGER.info("Fetching P1 metrics from %s/api/metrics", base_url)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{base_url}/api/metrics")
        response.raise_for_status()
        text = response.text

    snapshot = P1MetricsSnapshot()

    for line in text.splitlines():
        parsed = _parse_prometheus_line(line)
        if not parsed:
            continue
        metric, value = parsed

        if 'memory_preferences_extracted_total{type="preference"}' in metric:
            snapshot.extracted_preference = value
        elif 'memory_preferences_extracted_total{type="intent"}' in metric:
            snapshot.extracted_intent = value
        elif 'memory_preferences_extracted_total{type="constraint"}' in metric:
            snapshot.extracted_constraint = value
        elif "memory_preferences_confidence_count" in metric:
            snapshot.confidence_count = value
        elif "memory_preferences_confidence_sum" in metric:
            snapshot.confidence_sum = value
        elif "memory_preferences_extraction_duration_seconds_count" in metric:
            snapshot.extraction_count = value
        elif "memory_preferences_extraction_duration_seconds_sum" in metric:
            snapshot.extraction_sum = value
        elif (
            "memory_preferences_lexical_filtered_total" in metric
            and "_created" not in metric
        ):
            snapshot.lexical_filtered = value
        elif (
            "memory_preferences_llm_calls_total" in metric and "_created" not in metric
        ):
            snapshot.llm_calls = value

    LOGGER.info(
        "P1 metrics: %d prefs, %d intents, %d constraints, %.2f avg conf, %.3fs avg dur",
        snapshot.extracted_preference,
        snapshot.extracted_intent,
        snapshot.extracted_constraint,
        snapshot.average_confidence,
        snapshot.average_extraction_duration,
    )

    return snapshot


async def authenticate(
    base_url: str, email: str, password: str, dev_bypass: bool = False
) -> tuple[str, str]:
    """Authenticate and return (token, user_sub)"""
    if dev_bypass:
        LOGGER.info("Using dev bypass mode (no authentication)")
        return "dev-bypass-token", "qa-dev-user"

    LOGGER.info("Authenticating with email: %s", email)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/api/auth/login",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        user_sub = data.get("user", {}).get("sub")
        if not token or not user_sub:
            raise ValueError("Authentication failed: missing token or user_sub")
        LOGGER.info("Authenticated as user: %s", user_sub)
        return token, user_sub


async def send_test_conversation(
    base_url: str, token: str, dev_bypass: bool = False
) -> str:
    """Send test messages and return thread_id"""
    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")
    ws_url = f"{ws_url}/api/ws"

    headers = {}
    if dev_bypass:
        headers = {"x-dev-bypass": "1", "x-user-id": "qa-dev-user"}
    else:
        headers = {"Authorization": f"Bearer {token}"}

    LOGGER.info("Connecting to WebSocket: %s", ws_url)

    thread_id = None
    messages_sent = 0

    async with websockets.connect(ws_url, additional_headers=headers) as websocket:
        # Handshake
        handshake = await websocket.recv()
        LOGGER.debug("Handshake received: %s", handshake)
        handshake_data = json.loads(handshake)
        thread_id = handshake_data.get("thread_id")
        LOGGER.info("Thread ID: %s", thread_id)

        # Send test messages
        for i, message in enumerate(P1_TEST_MESSAGES, 1):
            LOGGER.info("Sending message %d/%d: %s", i, len(P1_TEST_MESSAGES), message)
            await websocket.send(
                json.dumps(
                    {
                        "type": "chat_message",
                        "content": message,
                        "agent": "anima",
                        "sessionId": thread_id,
                    }
                )
            )
            messages_sent += 1

            # Wait for responses (skip reading all messages for speed)
            try:
                # Just wait a bit for processing
                await asyncio.sleep(2)
            except Exception as e:
                LOGGER.warning("Error waiting for response: %s", e)

    LOGGER.info("Sent %d messages to thread %s", messages_sent, thread_id)
    return thread_id


async def trigger_consolidation(
    base_url: str, token: str, thread_id: str, user_sub: str, dev_bypass: bool = False
) -> bool:
    """Trigger memory consolidation via /api/memory/tend-garden"""
    LOGGER.info("Triggering consolidation for thread %s", thread_id)

    headers = {}
    if dev_bypass:
        headers = {"x-dev-bypass": "1", "x-user-id": user_sub}
    else:
        headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/api/memory/tend-garden",
            json={"thread_id": thread_id, "user_sub": user_sub},
            headers=headers,
        )
        if response.status_code == 200:
            LOGGER.info("Consolidation triggered successfully")
            return True
        else:
            LOGGER.error(
                "Consolidation failed: %s %s", response.status_code, response.text
            )
            return False


async def run_p1_validation(
    base_url: str,
    email: str,
    password: str,
    dev_bypass: bool = False,
    skip_conversation: bool = False,
) -> P1ValidationReport:
    """Run full P1 validation flow"""
    errors = []
    thread_id = None
    user_sub = None
    consolidation_triggered = False
    messages_sent = 0

    try:
        # 1. Fetch baseline metrics
        LOGGER.info("Step 1: Fetching baseline P1 metrics...")
        metrics_before = await fetch_p1_metrics(base_url)

        if not skip_conversation:
            # 2. Authenticate
            LOGGER.info("Step 2: Authenticating...")
            token, user_sub = await authenticate(base_url, email, password, dev_bypass)

            # 3. Send test conversation
            LOGGER.info("Step 3: Sending test conversation with preferences...")
            thread_id = await send_test_conversation(base_url, token, dev_bypass)
            messages_sent = len(P1_TEST_MESSAGES)

            # 4. Trigger consolidation
            LOGGER.info("Step 4: Triggering memory consolidation...")
            consolidation_triggered = await trigger_consolidation(
                base_url, token, thread_id, user_sub, dev_bypass
            )

            if consolidation_triggered:
                # Wait for consolidation to complete
                LOGGER.info("Waiting 30 seconds for consolidation to complete...")
                await asyncio.sleep(30)

        # 5. Fetch final metrics
        LOGGER.info("Step 5: Fetching final P1 metrics...")
        metrics_after = await fetch_p1_metrics(base_url)

        # 6. Calculate delta
        metrics_delta = metrics_before.delta(metrics_after)

        # 7. Validate results
        success = True
        if not skip_conversation:
            if metrics_delta.extracted_preference < 1:
                errors.append("No preferences extracted (expected ≥1)")
                success = False
            if metrics_delta.extracted_intent < 1:
                errors.append("No intents extracted (expected ≥1)")
                success = False
            if metrics_delta.confidence_count < 1:
                errors.append("No confidence scores recorded (expected ≥1)")
                success = False
            if metrics_delta.average_confidence < 0.6:
                errors.append(
                    f"Low average confidence: {metrics_delta.average_confidence:.2f} (expected >0.6)"
                )
                success = False

        LOGGER.info("Validation complete: %s", "SUCCESS" if success else "FAILED")
        if errors:
            for error in errors:
                LOGGER.error("Validation error: %s", error)

    except Exception as e:
        LOGGER.exception("Validation failed with exception")
        errors.append(f"Exception: {str(e)}")
        metrics_before = P1MetricsSnapshot()
        metrics_after = P1MetricsSnapshot()
        metrics_delta = P1MetricsSnapshot()
        success = False

    return P1ValidationReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        base_url=base_url,
        thread_id=thread_id,
        user_sub=user_sub,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
        metrics_delta=metrics_delta,
        success=success,
        errors=errors,
        messages_sent=messages_sent,
        consolidation_triggered=consolidation_triggered,
    )


def main():
    parser = argparse.ArgumentParser(
        description="QA P1 Preference Extraction Validation"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the Emergence API (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--login-email",
        default=DEFAULT_LOGIN_EMAIL,
        help="Login email for authentication",
    )
    parser.add_argument(
        "--login-password",
        default=DEFAULT_LOGIN_PASSWORD,
        help="Login password for authentication",
    )
    parser.add_argument(
        "--dev-bypass",
        action="store_true",
        help="Use dev bypass mode (skip authentication)",
    )
    parser.add_argument(
        "--skip-conversation",
        action="store_true",
        help="Skip conversation (only fetch metrics)",
    )
    parser.add_argument(
        "--output",
        default="qa-p1-report.json",
        help="Output JSON file path (default: qa-p1-report.json)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate credentials if not dev bypass
    if not args.dev_bypass and not args.skip_conversation:
        if not args.login_email or not args.login_password:
            LOGGER.error(
                "Missing credentials. Provide --login-email and --login-password or use --dev-bypass"
            )
            sys.exit(1)

    # Run validation
    report = asyncio.run(
        run_p1_validation(
            base_url=args.base_url,
            email=args.login_email,
            password=args.login_password,
            dev_bypass=args.dev_bypass,
            skip_conversation=args.skip_conversation,
        )
    )

    # Print summary
    print("\n" + "=" * 60)
    print("P1 VALIDATION REPORT")
    print("=" * 60)
    print(f"Timestamp:    {report.timestamp}")
    print(f"Base URL:     {report.base_url}")
    print(f"Thread ID:    {report.thread_id or 'N/A'}")
    print(f"User Sub:     {report.user_sub or 'N/A'}")
    print(f"Messages:     {report.messages_sent}")
    print(f"Consolidation: {'Triggered' if report.consolidation_triggered else 'Skipped'}")
    print(f"\nStatus:       {'[OK] SUCCESS' if report.success else '[FAILED] FAILED'}")
    print("\nMetrics Delta:")
    print(f"  Preferences:  {report.metrics_delta.extracted_preference:+.0f}")
    print(f"  Intents:      {report.metrics_delta.extracted_intent:+.0f}")
    print(f"  Constraints:  {report.metrics_delta.extracted_constraint:+.0f}")
    print(
        f"  Avg Confidence: {report.metrics_delta.average_confidence:.2f}" if report.metrics_delta.confidence_count > 0 else "  Avg Confidence: N/A"
    )
    print(
        f"  Avg Duration: {report.metrics_delta.average_extraction_duration:.3f}s" if report.metrics_delta.extraction_count > 0 else "  Avg Duration: N/A"
    )
    print(f"  Filtering Rate: {report.metrics_delta.filtering_rate*100:.1f}%")
    print(f"  LLM Calls:    {report.metrics_delta.llm_calls:+.0f}")

    if report.errors:
        print("\nErrors:")
        for error in report.errors:
            print(f"  - {error}")

    print("=" * 60)

    # Save to JSON
    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)
    print(f"\nReport saved to: {output_path}")

    sys.exit(0 if report.success else 1)


if __name__ == "__main__":
    main()
