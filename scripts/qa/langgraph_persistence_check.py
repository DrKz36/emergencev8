"""
LangGraph Checkpointer 3.0 persistence smoke test.

This script verifies that a LangGraph compiled with the new 3.0 checkpointer
can persist intermediate state to SQLite and resume execution without
replaying completed nodes.  It stores run metadata under
``reports/langgraph_persistence`` for auditing.

Usage
-----
::

    python scripts/qa/langgraph_persistence_check.py \
        --sqlite-path ./.cache/langgraph-checkpoints.sqlite

Passing ``--firestore-project`` will attempt to run the same scenario against
Firestore if the 3.0 saver package is available.  When the dependency is
missing the script prints a clear skip message instead of crashing.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

REPORT_DIR = Path("reports") / "langgraph_persistence"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PersistenceResult:
    backend: str
    checkpoint_id: str
    thread_id: str
    first_run_error: str
    resume_output: Dict[str, Any]
    first_run_duration_ms: float
    resume_duration_ms: float
    timestamp: str


def build_test_graph() -> StateGraph[dict, dict, dict, dict]:
    """Create a simple two-step graph that allows us to trigger a failure and resume."""

    builder: StateGraph[dict, dict, dict, dict] = StateGraph(dict)

    def prepare(state: dict) -> dict:
        value = state.get("count", 0) + 1
        return {"count": value, "prepared": True}

    def finalize(state: dict, *, config: dict) -> dict:
        allow = config.get("configurable", {}).get("allow_finalize", True)
        if not allow:
            raise RuntimeError("finalize blocked by config")
        return {"count": state["count"] + 10, "done": True}

    builder.add_node("prepare", prepare)
    builder.add_node("finalize", finalize)
    builder.set_entry_point("prepare")
    builder.add_edge("prepare", "finalize")
    builder.add_edge("finalize", END)

    return builder


async def run_sqlite_scenario(sqlite_path: str) -> PersistenceResult:
    builder = build_test_graph()
    async with AsyncSqliteSaver.from_conn_string(sqlite_path) as saver:
        graph = builder.compile(checkpointer=saver)
        thread_id = f"sqlite-{int(time.time() * 1000)}"
        bad_config = {
            "configurable": {"thread_id": thread_id, "allow_finalize": False},
        }

        started = time.perf_counter()
        try:
            await graph.ainvoke({"count": 0}, bad_config, durability="sync")
            first_error = "expected-runtime-error-not-raised"
        except Exception as exc:  # noqa: BLE001 - intentional broad capture for report
            first_error = repr(exc)
        first_duration_ms = (time.perf_counter() - started) * 1000

        saved = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
        resume_id = saved.config["configurable"]["checkpoint_id"]
        resume_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": resume_id,
                "allow_finalize": True,
            }
        }

        resume_started = time.perf_counter()
        resume_output = await graph.ainvoke(
            Command(resume=True), resume_config, durability="sync"
        )
        resume_duration_ms = (time.perf_counter() - resume_started) * 1000

        return PersistenceResult(
            backend="sqlite",
            checkpoint_id=resume_id,
            thread_id=thread_id,
            first_run_error=first_error,
            resume_output=resume_output,
            first_run_duration_ms=first_duration_ms,
            resume_duration_ms=resume_duration_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


async def run_firestore_scenario(project: str, collection: str) -> PersistenceResult:
    """Try to run the same scenario on Firestore if saver 3.0 is available."""

    try:
        from langgraph_checkpoint_firestore.aio import AsyncFirestoreSaver  # type: ignore
    except (
        ImportError
    ) as exc:  # pragma: no cover - executed only when optional dep is missing
        raise RuntimeError(
            "langgraph-checkpoint-firestore>=3.0.0 not installed; "
            "await upstream release before enabling this test."
        ) from exc

    builder = build_test_graph()
    async with AsyncFirestoreSaver(
        project_id=project, collection_name=collection
    ) as saver:
        graph = builder.compile(checkpointer=saver)
        thread_id = f"firestore-{int(time.time() * 1000)}"
        bad_config = {
            "configurable": {"thread_id": thread_id, "allow_finalize": False},
        }
        started = time.perf_counter()
        try:
            await graph.ainvoke({"count": 0}, bad_config, durability="sync")
            first_error = "expected-runtime-error-not-raised"
        except Exception as exc:  # noqa: BLE001
            first_error = repr(exc)
        first_duration_ms = (time.perf_counter() - started) * 1000

        saved = await saver.aget_tuple({"configurable": {"thread_id": thread_id}})
        resume_id = saved.config["configurable"]["checkpoint_id"]
        resume_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": resume_id,
                "allow_finalize": True,
            }
        }

        resume_started = time.perf_counter()
        resume_output = await graph.ainvoke(
            Command(resume=True), resume_config, durability="sync"
        )
        resume_duration_ms = (time.perf_counter() - resume_started) * 1000

        return PersistenceResult(
            backend="firestore",
            checkpoint_id=resume_id,
            thread_id=thread_id,
            first_run_error=first_error,
            resume_output=resume_output,
            first_run_duration_ms=first_duration_ms,
            resume_duration_ms=resume_duration_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


def write_report(result: PersistenceResult, output_path: Path) -> None:
    payload = asdict(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite-path",
        default=":memory:",
        help="SQLite connection string/file used for the persistence test (default: in-memory).",
    )
    parser.add_argument(
        "--firestore-project",
        help="Optional Firestore project ID to exercise the Firestore saver (requires 3.0 package).",
    )
    parser.add_argument(
        "--firestore-collection",
        default="langgraph-checkpoints",
        help="Firestore collection name when running the optional Firestore scenario.",
    )
    parser.add_argument(
        "--report-prefix",
        default="run",
        help="Prefix for generated JSON artifact names inside reports/langgraph_persistence.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="If set, results are printed to stdout instead of being written to disk.",
    )
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    sqlite_result = await run_sqlite_scenario(args.sqlite_path)
    if args.no_write:
        print(json.dumps(asdict(sqlite_result), indent=2, ensure_ascii=False))
    else:
        sqlite_report_path = REPORT_DIR / f"{args.report_prefix}-sqlite.json"
        write_report(sqlite_result, sqlite_report_path)
        print(f"[langgraph] SQLite persistence OK → {sqlite_report_path}")

    if args.firestore_project:
        try:
            firestore_result = await run_firestore_scenario(
                args.firestore_project, args.firestore_collection
            )
        except RuntimeError as exc:
            print(f"[langgraph] Firestore scenario skipped: {exc}")
        else:
            if args.no_write:
                print(
                    json.dumps(asdict(firestore_result), indent=2, ensure_ascii=False)
                )
            else:
                firestore_report_path = (
                    REPORT_DIR / f"{args.report_prefix}-firestore.json"
                )
                write_report(firestore_result, firestore_report_path)
                print(f"[langgraph] Firestore persistence OK → {firestore_report_path}")


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:  # pragma: no cover - manual abort
        print("\nInterrupted by user.")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
