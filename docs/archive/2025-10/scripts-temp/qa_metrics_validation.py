#!/usr/bin/env python3
"""
QA cockpit helper: combines Prometheus metric validation and timeline scenario
in a single report.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import httpx
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

LOGGER = logging.getLogger("qa.metrics")

DEFAULT_BASE_URL = os.environ.get(
    "EMERGENCE_QA_BASE_URL", "https://emergence-app-47nct44nma-ew.a.run.app"
)
DEFAULT_LOGIN_EMAIL = os.environ.get("EMERGENCE_SMOKE_EMAIL", "")
DEFAULT_LOGIN_PASSWORD = os.environ.get("EMERGENCE_SMOKE_PASSWORD", "")
DEFAULT_AGENT = "anima"
DEFAULT_PERIOD = "7d"
DEFAULT_TIMELINE_MESSAGE = "Salut Anima ! Ce message QA verifie que les timelines cockpit remontent bien des donnees."
DEFAULT_PROMPTS: Sequence[str] = (
    "Quelle est l'architecture d'Emergence?",
    "Explique-moi le système de métriques Prometheus",
    "Comment fonctionne le concept recall?",
)

PROMETHEUS_METRICS = (
    "memory_analysis_success_total",
    "concept_recall_detections_total",
    "memory_analysis_cache_hits_total",
)

DEV_BYPASS_USER = os.environ.get("QA_DEV_USER_ID", "codex")
DEV_BYPASS_HEADERS = {
    "x-dev-bypass": "1",
    "x-user-id": DEV_BYPASS_USER,
}


class TimelineScenarioError(RuntimeError):
    """Raised when the timeline scenario fails."""


@dataclass
class AuthResult:
    token: str
    session_id: str
    user_id: str
    email: str
    mode: str = "password"
    expires_at: Optional[str] = None


@dataclass
class MetricsSnapshot:
    values: Dict[str, float] = field(default_factory=dict)

    def delta(self, other: "MetricsSnapshot") -> Dict[str, float]:
        diff: Dict[str, float] = {}
        for key in set(self.values.keys()).union(other.values.keys()):
            diff[key] = other.values.get(key, 0.0) - self.values.get(key, 0.0)
        return diff


@dataclass
class MetricsReport:
    before: MetricsSnapshot
    after: MetricsSnapshot

    @property
    def deltas(self) -> Dict[str, float]:
        return self.before.delta(self.after)


@dataclass
class TimelineSnapshot:
    activity: List[Dict[str, Any]]
    tokens: List[Dict[str, Any]]
    costs: List[Dict[str, Any]]


@dataclass
class TimelineDelta:
    messages: int
    threads: int
    tokens: int
    costs: float


@dataclass
class TimelineReport:
    before: TimelineSnapshot
    after: TimelineSnapshot
    delta: TimelineDelta
    activity_today: Dict[str, Any]
    tokens_today: Dict[str, Any]
    costs_today: Dict[str, Any]
    ws_completions: Dict[str, Any]


@dataclass
class ReadOnlyReport:
    dashboard_status: int
    timeline_status: int
    summary_sample: Optional[Dict[str, Any]] = None
    timeline_sample: Optional[Dict[str, Any]] = None


@dataclass
class QAReport:
    timestamp: str
    base_url: str
    login_mode: str
    metrics: Optional[MetricsReport] = None
    timeline: Optional[TimelineReport] = None
    read_only: Optional[ReadOnlyReport] = None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "base_url": self.base_url,
            "login_mode": self.login_mode,
        }
        if self.metrics:
            data["metrics"] = {
                "before": self.metrics.before.values,
                "after": self.metrics.after.values,
                "delta": self.metrics.deltas,
            }
        if self.timeline:
            data["timeline"] = {
                "delta": asdict(self.timeline.delta),
                "activity_today": self.timeline.activity_today,
                "tokens_today": self.timeline.tokens_today,
                "costs_today": self.timeline.costs_today,
                "ws_completions": self.timeline.ws_completions,
            }
        if self.read_only:
            data["read_only_probe"] = asdict(self.read_only)
        return data


def _normalize_base_url(raw: str) -> str:
    candidate = (raw or "").strip()
    if not candidate:
        candidate = DEFAULT_BASE_URL
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or parsed.path
    path = parsed.path if parsed.netloc else ""
    normalized = f"{scheme}://{netloc}"
    if path and path != "/":
        normalized = f"{normalized}{path.rstrip('/')}"
    return normalized.rstrip("/")


def _ws_base_from_http(base_url: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc or parsed.path}".rstrip("/")


def _sum_field(entries: Iterable[Dict[str, Any]], field: str) -> float:
    total = 0.0
    for item in entries or []:
        try:
            total += float(item.get(field, 0) or 0)
        except (TypeError, ValueError):
            continue
    return total


def _sum_activity(entries: Iterable[Dict[str, Any]]) -> Tuple[int, int]:
    messages = int(_sum_field(entries, "messages"))
    threads = int(_sum_field(entries, "threads"))
    return messages, threads


def _sum_tokens(entries: Iterable[Dict[str, Any]]) -> int:
    total = 0
    for key in ("total", "tokens", "value"):
        if any(key in (item or {}) for item in entries or []):
            total = int(_sum_field(entries, key))
            break
    if not total:
        total = int(_sum_field(entries, "input") + _sum_field(entries, "output"))
    return total


def _sum_costs(entries: Iterable[Dict[str, Any]]) -> float:
    return _sum_field(entries, "cost")


async def fetch_metrics_snapshot(
    client: httpx.AsyncClient, metric_names: Sequence[str]
) -> MetricsSnapshot:
    response = await client.get("/api/metrics")
    response.raise_for_status()
    values: Dict[str, float] = {}
    lines = response.text.splitlines()
    for metric in metric_names:
        for line in lines:
            if line.startswith(metric) and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        values[metric] = float(parts[-1])
                    except ValueError:
                        LOGGER.warning(
                            "Metric %s value not numeric in %s", metric, line
                        )
                        values[metric] = 0.0
                break
        else:
            values[metric] = 0.0
    return MetricsSnapshot(values=values)


async def attempt_password_login(
    client: httpx.AsyncClient, email: str, password: str
) -> Optional[AuthResult]:
    if not email or not password:
        return None
    payload = {
        "email": email,
        "password": password,
        "meta": {
            "source": "qa_metrics_validation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    resp = await client.post("/api/auth/login", json=payload)
    if resp.status_code != 200:
        LOGGER.warning(
            "Password login failed (%s): %s", resp.status_code, resp.text[:200]
        )
        return None
    data = resp.json()
    try:
        return AuthResult(
            token=str(data["token"]),
            session_id=str(data["session_id"]),
            user_id=str(data["user_id"]),
            email=str(data.get("email") or email),
            mode="password",
            expires_at=data.get("expires_at"),
        )
    except KeyError as exc:
        LOGGER.error("Invalid login payload: missing %s", exc)
        return None


async def attempt_dev_login(client: httpx.AsyncClient) -> Optional[AuthResult]:
    resp = await client.post("/api/auth/dev/login")
    if resp.status_code != 200:
        LOGGER.warning(
            "Dev login unavailable (%s): %s", resp.status_code, resp.text[:160]
        )
        return None
    payload = resp.json()
    if "token" not in payload:
        LOGGER.warning("Dev login payload incomplete: %s", payload)
        return None
    return AuthResult(
        token=str(payload["token"]),
        session_id=str(payload.get("session_id", "")),
        user_id=str(payload.get("user_id", "")),
        email=str(payload.get("email", "dev@local")),
        mode="dev",
        expires_at=payload.get("expires_at"),
    )


async def send_chat_prompt(
    client: httpx.AsyncClient, auth: AuthResult, message: str
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {auth.token}"}
    body = {"message": message, "session_id": auth.session_id}
    resp = await client.post("/api/chat/send", headers=headers, json=body)
    if resp.status_code != 200:
        LOGGER.warning("Chat prompt failed (%s): %s", resp.status_code, resp.text[:200])
        return {}
    return resp.json()


async def trigger_memory_analysis(client: httpx.AsyncClient, auth: AuthResult) -> bool:
    headers = {"Authorization": f"Bearer {auth.token}"}
    try:
        resp = await client.post(
            "/api/memory/analyze",
            headers=headers,
            json={"session_id": auth.session_id},
        )
    except httpx.HTTPError as exc:
        LOGGER.warning("Memory analysis request error: %s", exc)
        return False
    if resp.status_code != 200:
        LOGGER.warning(
            "Memory analysis failed (%s): %s", resp.status_code, resp.text[:200]
        )
        return False
    return True


async def fetch_dashboard_summary(
    client: httpx.AsyncClient, auth: AuthResult
) -> Optional[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {auth.token}",
        "X-Session-Id": auth.session_id,
    }
    resp = await client.get("/api/dashboard/costs/summary", headers=headers)
    if resp.status_code != 200:
        LOGGER.warning("Dashboard summary fetch failed (%s)", resp.status_code)
        return None
    try:
        return resp.json()
    except json.JSONDecodeError:
        LOGGER.warning("Dashboard summary returned non JSON payload")
        return None


async def fetch_timeline_snapshot(
    client: httpx.AsyncClient, auth: AuthResult, *, period: str
) -> TimelineSnapshot:
    headers = {
        "Authorization": f"Bearer {auth.token}",
        "X-Session-Id": auth.session_id,
    }
    params = {"period": period}

    async def _get(path: str) -> List[Dict[str, Any]]:
        resp = await client.get(path, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        raise TimelineScenarioError(f"Unexpected response for {path}: {data}")

    activity = await _get("/api/dashboard/timeline/activity")
    tokens = await _get("/api/dashboard/timeline/tokens")
    costs = await _get("/api/dashboard/timeline/costs")
    return TimelineSnapshot(activity=activity, tokens=tokens, costs=costs)


async def ensure_thread(
    client: httpx.AsyncClient, auth: AuthResult, *, title: str = "QA Timeline Scenario"
) -> str:
    headers = {
        "Authorization": f"Bearer {auth.token}",
        "X-Session-Id": auth.session_id,
    }
    params = {"type": "chat", "limit": 1}
    resp = await client.get("/api/threads", headers=headers, params=params)
    resp.raise_for_status()
    payload = resp.json()
    items = payload.get("items") if isinstance(payload, dict) else None
    if isinstance(items, list) and items:
        thread_id = str(items[0].get("id") or "").strip()
        if thread_id:
            return thread_id

    create_resp = await client.post(
        "/api/threads", headers=headers, json={"type": "chat", "title": title}
    )
    create_resp.raise_for_status()
    data = create_resp.json()
    thread_id = str(
        data.get("id") or (data.get("thread") or {}).get("id") or ""
    ).strip()
    if not thread_id:
        raise TimelineScenarioError("Thread QA introuvable après création.")
    return thread_id


async def send_ws_message(
    base_url: str,
    auth: AuthResult,
    thread_id: str,
    *,
    agent_id: str,
    text: str,
    use_rag: bool,
    ws_timeout: int,
) -> Dict[str, Any]:
    ws_base = _ws_base_from_http(base_url)
    ws_url = f"{ws_base}/ws/{auth.session_id}?thread_id={thread_id}"
    headers = {
        "Authorization": f"Bearer {auth.token}",
        "X-Session-Id": auth.session_id,
    }
    payload = {
        "type": "chat.message",
        "payload": {
            "text": text,
            "agent_id": agent_id,
            "use_rag": use_rag,
            "doc_ids": [],
        },
    }
    pending_agents = {agent_id.lower()}
    completions: Dict[str, Any] = {}

    async with websockets.connect(
        ws_url,
        subprotocols=["jwt", auth.token],
        additional_headers=headers,
        ping_interval=20,
        ping_timeout=20,
        max_size=8 * 1024 * 1024,
    ) as websocket:
        await websocket.send(json.dumps(payload))
        while pending_agents:
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=ws_timeout)
            except asyncio.TimeoutError as exc:
                raise TimelineScenarioError(
                    f"Timeout WebSocket ({ws_timeout}s) agents restants: {sorted(pending_agents)}"
                ) from exc
            except ConnectionClosed as exc:
                raise TimelineScenarioError(f"Connexion WS fermee: {exc}") from exc
            except WebSocketException as exc:
                raise TimelineScenarioError(f"Erreur WebSocket: {exc}") from exc

            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                LOGGER.warning("Frame non JSON ignoree: %s", raw)
                continue

            ftype = (frame.get("type") or "").strip()
            if ftype == "ws:error":
                raise TimelineScenarioError(f"Erreur backend: {frame.get('payload')}")
            if ftype == "ws:chat_stream_end":
                payload = frame.get("payload") or {}
                agent = (
                    str(payload.get("agent") or payload.get("agent_id") or "")
                    .strip()
                    .lower()
                )
                if agent and agent in pending_agents:
                    pending_agents.remove(agent)
                    completions[agent] = payload

        await asyncio.sleep(3.0)
    return completions


def compute_timeline_delta(
    before: TimelineSnapshot, after: TimelineSnapshot
) -> TimelineDelta:
    before_messages, before_threads = _sum_activity(before.activity)
    after_messages, after_threads = _sum_activity(after.activity)
    before_tokens = _sum_tokens(before.tokens)
    after_tokens = _sum_tokens(after.tokens)
    before_costs = _sum_costs(before.costs)
    after_costs = _sum_costs(after.costs)
    return TimelineDelta(
        messages=after_messages - before_messages,
        threads=after_threads - before_threads,
        tokens=after_tokens - before_tokens,
        costs=after_costs - before_costs,
    )


def _today_entry(entries: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for item in entries or []:
        if item.get("date") == today:
            return item
    return entries[-1] if entries else {}


async def run_timeline_scenario(
    client: httpx.AsyncClient,
    auth: AuthResult,
    *,
    base_url: str,
    agent: str,
    message: str,
    period: str,
    use_rag: bool,
    ws_timeout: int,
) -> TimelineReport:
    before = await fetch_timeline_snapshot(client, auth, period=period)
    thread_id = await ensure_thread(client, auth)
    completions = await send_ws_message(
        base_url,
        auth,
        thread_id,
        agent_id=agent,
        text=message,
        use_rag=use_rag,
        ws_timeout=ws_timeout,
    )
    after = await fetch_timeline_snapshot(client, auth, period=period)
    delta = compute_timeline_delta(before, after)
    if delta.messages <= 0:
        raise TimelineScenarioError(
            "Timeline activité n'a pas progressé (messages delta <= 0)."
        )
    if delta.tokens <= 0:
        raise TimelineScenarioError("Timeline tokens n'a pas progressé (delta <= 0).")
    activity_today = _today_entry(after.activity)
    tokens_today = _today_entry(after.tokens)
    costs_today = _today_entry(after.costs)
    return TimelineReport(
        before=before,
        after=after,
        delta=delta,
        activity_today=activity_today,
        tokens_today=tokens_today,
        costs_today=costs_today,
        ws_completions=completions,
    )


async def run_metrics_flow(
    client: httpx.AsyncClient,
    auth: AuthResult,
    prompts: Sequence[str],
    *,
    trigger_memory: bool,
) -> None:
    for prompt in prompts:
        await send_chat_prompt(client, auth, prompt)
        await asyncio.sleep(2)
    if trigger_memory:
        await trigger_memory_analysis(client, auth)


async def run_read_only_probe(base_url: str) -> ReadOnlyReport:
    async with httpx.AsyncClient(
        base_url=base_url, timeout=httpx.Timeout(30.0)
    ) as client:
        summary_resp = await client.get(
            "/api/dashboard/costs/summary", headers=DEV_BYPASS_HEADERS
        )
        timeline_resp = await client.get(
            "/api/dashboard/timeline/activity",
            headers=DEV_BYPASS_HEADERS,
            params={"period": DEFAULT_PERIOD},
        )
    summary_sample = None
    if summary_resp.status_code == 200:
        try:
            summary_data = summary_resp.json()
            summary_sample = {
                "sessions": summary_data.get("monitoring", {}).get("total_sessions"),
                "documents": summary_data.get("monitoring", {}).get("total_documents"),
            }
        except json.JSONDecodeError:
            summary_sample = None
    timeline_sample = None
    if timeline_resp.status_code == 200:
        try:
            timeline_data = timeline_resp.json()
            if isinstance(timeline_data, list) and timeline_data:
                timeline_sample = timeline_data[0]
        except json.JSONDecodeError:
            timeline_sample = None
    return ReadOnlyReport(
        dashboard_status=summary_resp.status_code,
        timeline_status=timeline_resp.status_code,
        summary_sample=summary_sample,
        timeline_sample=timeline_sample,
    )


async def run_cli(args: argparse.Namespace) -> QAReport:
    base_url = _normalize_base_url(args.base_url)
    timestamp = datetime.now(timezone.utc).isoformat()
    timeout = httpx.Timeout(args.http_timeout)
    metrics_before = None
    metrics_after = None
    metrics_report = None
    timeline_report = None
    read_only_report = None
    login_mode = "none"

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        if not args.skip_metrics:
            metrics_before = await fetch_metrics_snapshot(client, PROMETHEUS_METRICS)

        auth: Optional[AuthResult] = None
        if not args.skip_timeline or not args.skip_metrics or args.dashboard_probe:
            auth = await attempt_password_login(
                client, args.login_email, args.login_password
            )
            login_mode = "password" if auth else "password_failed"
            if auth is None and not args.no_dev_login:
                auth = await attempt_dev_login(client)
                if auth:
                    login_mode = "dev"

        if auth:
            if not args.skip_metrics:
                await run_metrics_flow(
                    client,
                    auth,
                    args.chat_prompts or DEFAULT_PROMPTS,
                    trigger_memory=args.trigger_memory,
                )
                metrics_after = await fetch_metrics_snapshot(client, PROMETHEUS_METRICS)
                metrics_report = MetricsReport(
                    before=metrics_before, after=metrics_after
                )  # type: ignore[arg-type]
            elif metrics_before:
                metrics_after = metrics_before
                metrics_report = MetricsReport(
                    before=metrics_before, after=metrics_before
                )

            if not args.skip_timeline:
                timeline_report = await run_timeline_scenario(
                    client,
                    auth,
                    base_url=base_url,
                    agent=args.agent,
                    message=args.timeline_message,
                    period=args.timeline_period,
                    use_rag=args.use_rag,
                    ws_timeout=args.ws_timeout,
                )

            if args.dashboard_probe and not read_only_report:
                summary = await fetch_dashboard_summary(client, auth)
                if summary:
                    read_only_report = ReadOnlyReport(
                        dashboard_status=200,
                        timeline_status=0,
                        summary_sample={
                            "sessions": summary.get("monitoring", {}).get(
                                "total_sessions"
                            ),
                            "documents": summary.get("monitoring", {}).get(
                                "total_documents"
                            ),
                        },
                        timeline_sample=None,
                    )
        else:
            if not args.skip_metrics:
                metrics_after = await fetch_metrics_snapshot(client, PROMETHEUS_METRICS)
                metrics_report = MetricsReport(
                    before=metrics_before, after=metrics_after
                )  # type: ignore[arg-type]

    if metrics_report is None and metrics_before and metrics_after:
        metrics_report = MetricsReport(before=metrics_before, after=metrics_after)

    if (
        not timeline_report or args.force_read_only_probe
    ) and args.enable_read_only_fallback:
        read_only_report = await run_read_only_probe(base_url)

    return QAReport(
        timestamp=timestamp,
        base_url=base_url,
        login_mode=login_mode,
        metrics=metrics_report,
        timeline=timeline_report,
        read_only=read_only_report,
    )


def format_report(report: QAReport) -> str:
    lines = [
        "=" * 60,
        "QA VALIDATION - MÉTRIQUES & TIMELINE",
        "=" * 60,
        f"Timestamp: {report.timestamp}",
        f"Base URL: {report.base_url}",
        f"Login mode: {report.login_mode}",
    ]
    if report.metrics:
        lines.append("\n[METRICS]")
        for name, delta in report.metrics.deltas.items():
            before = report.metrics.before.values.get(name, 0.0)
            after = report.metrics.after.values.get(name, 0.0)
            lines.append(f"  - {name}: {after} (Δ {delta:+}) [before={before}]")
    if report.timeline:
        lines.append("\n[TIMELINE]")
        lines.append(
            f"  - Messages delta: {report.timeline.delta.messages}, tokens delta: {report.timeline.delta.tokens}"
        )
        lines.append(f"  - Activity today: {report.timeline.activity_today}")
        lines.append(f"  - Tokens today: {report.timeline.tokens_today}")
        lines.append(f"  - Costs today: {report.timeline.costs_today}")
    if report.read_only:
        lines.append("\n[READ-ONLY PROBE]")
        lines.append(f"  - Dashboard status: {report.read_only.dashboard_status}")
        lines.append(f"  - Timeline status: {report.read_only.timeline_status}")
        if report.read_only.summary_sample:
            lines.append(f"  - Summary sample: {report.read_only.summary_sample}")
        if report.read_only.timeline_sample:
            lines.append(f"  - Timeline sample: {report.read_only.timeline_sample}")
    lines.append("=" * 60)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valide les métriques Prometheus et les timelines cockpit via un seul script."
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="URL de base de l'API Emergence."
    )
    parser.add_argument(
        "--login-email", default=DEFAULT_LOGIN_EMAIL, help="Email pour /api/auth/login."
    )
    parser.add_argument(
        "--login-password",
        default=DEFAULT_LOGIN_PASSWORD,
        help="Mot de passe pour /api/auth/login.",
    )
    parser.add_argument(
        "--no-dev-login",
        action="store_true",
        help="Désactive le fallback /api/auth/dev/login si l'auth standard échoue.",
    )
    parser.add_argument(
        "--skip-metrics",
        action="store_true",
        help="Ignore la validation d'incrémentation des métriques.",
    )
    parser.add_argument(
        "--skip-timeline",
        action="store_true",
        help="Ignore le scénario timeline cockpit.",
    )
    parser.add_argument(
        "--chat-prompts",
        nargs="*",
        default=list(DEFAULT_PROMPTS),
        help="Prompts envoyés sur /api/chat/send pour stimuler les métriques.",
    )
    parser.add_argument(
        "--trigger-memory",
        action="store_true",
        help="Force un POST /api/memory/analyze après les prompts.",
    )
    parser.add_argument(
        "--timeline-message",
        default=DEFAULT_TIMELINE_MESSAGE,
        help="Message envoyé via WebSocket pour le scénario timeline.",
    )
    parser.add_argument(
        "--agent",
        default=DEFAULT_AGENT,
        help="Agent sollicité pour le scénario timeline.",
    )
    parser.add_argument(
        "--timeline-period",
        default=DEFAULT_PERIOD,
        help="Période timeline (7d, 30d, 90d, 1y).",
    )
    parser.add_argument(
        "--use-rag", action="store_true", help="Active use_rag lors de l'envoi WS."
    )
    parser.add_argument(
        "--ws-timeout", type=int, default=180, help="Timeout WebSocket (secondes)."
    )
    parser.add_argument(
        "--http-timeout", type=float, default=60.0, help="Timeout HTTPX global."
    )
    parser.add_argument(
        "--json-output", help="Chemin de fichier pour exporter le rapport JSON."
    )
    parser.add_argument(
        "--dashboard-probe",
        action="store_true",
        help="Récupère /api/dashboard/costs/summary avec le token authentifié.",
    )
    parser.add_argument(
        "--force-read-only-probe",
        action="store_true",
        help="Force l'exécution du fallback bypass même si l'auth est réussie.",
    )
    parser.add_argument(
        "--enable-read-only-fallback",
        action="store_true",
        help="Active la sonde bypass quand l'auth échoue (par défaut inactif).",
    )
    return parser


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def write_json_report(path: str, report: QAReport) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, ensure_ascii=False)


def main(argv: Optional[Sequence[str]] = None) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    args = parse_args(argv)
    report = asyncio.run(run_cli(args))
    print(format_report(report))
    if args.json_output:
        write_json_report(args.json_output, report)


if __name__ == "__main__":
    main()
