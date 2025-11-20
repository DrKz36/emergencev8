"""
MAVEN / Agent Misalignment adversarial probe helper.

This script ingests a JSONL export of MAVEN (or AgentMisalignment) scenarios
and derives quick heuristics on potential failure modes.  The goal is to
produce artefacts that can be plugged into CI or manual stress runs without
having to parse the raw datasets every time.

By default the script works offline: it parses the dataset, computes simple
metrics (prompt length, adversarial keywords, tool requirements) and stores a
summary under ``reports/maven``.  If a sample list is needed to drive manual
tests, ``--emit-prompts`` writes a compact NDJSON with just the essential
fields (id, instruction, expected_tools, risk_flags).
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

REPORT_DIR = Path("reports") / "maven"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Very small heuristic dictionaries – we only need lightweight signals to
# surface suspicious tasks quickly.
KEYWORD_FLAGS = {
    "sandbox": {"sandbox", "sabotage", "tamper"},
    "calculation": {"determinant", "matrix", "solver", "constraint"},
    "overload": {"rate limit", "retry storm", "exponential"},
    "compliance": {"policy", "shutdown", "override"},
    "chemical": {"synthesize", "chem", "molecule", "compound"},
}


@dataclass
class SampleSummary:
    sample_id: str
    prompt_tokens: int
    tool_count: int
    risk_flags: List[str]
    title: str | None


def tokenize(text: str) -> List[str]:
    return [token for token in text.replace("\n", " ").split(" ") if token]


def detect_flags(text: str) -> List[str]:
    lowered = text.lower()
    flags: list[str] = []
    for name, needles in KEYWORD_FLAGS.items():
        if any(needle in lowered for needle in needles):
            flags.append(name)
    return flags


def parse_dataset(path: Path, limit: int | None) -> Iterable[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            if limit is not None and idx >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON on line {idx + 1}: {line!r}") from None


def summarise_samples(records: Iterable[dict]) -> list[SampleSummary]:
    summaries: list[SampleSummary] = []
    for record in records:
        prompt = record.get("instruction") or record.get("prompt") or ""
        title = record.get("title") or record.get("task_name")
        sample_id = str(record.get("id") or record.get("sample_id") or len(summaries))
        tokens = tokenize(prompt)
        tools = record.get("tools") or record.get("available_tools") or []
        flags = detect_flags(prompt)
        summaries.append(
            SampleSummary(
                sample_id=sample_id,
                prompt_tokens=len(tokens),
                tool_count=len(tools) if isinstance(tools, list) else 0,
                risk_flags=flags,
                title=title,
            )
        )
    return summaries


def write_summary(
    summaries: list[SampleSummary], dataset_path: Path, output_path: Path
) -> None:
    prompt_lengths = [item.prompt_tokens for item in summaries] or [0]
    tool_counts = [item.tool_count for item in summaries] or [0]
    flag_counter = Counter(flag for item in summaries for flag in item.risk_flags)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset_path),
        "total_samples": len(summaries),
        "prompt_tokens": {
            "avg": statistics.mean(prompt_lengths),
            "median": statistics.median(prompt_lengths),
            "p95": statistics.quantiles(prompt_lengths, n=20)[-1]
            if len(prompt_lengths) >= 20
            else max(prompt_lengths),
            "max": max(prompt_lengths),
        },
        "tool_counts": {
            "avg": statistics.mean(tool_counts),
            "max": max(tool_counts),
        },
        "top_risk_flags": flag_counter.most_common(10),
        "samples": [asdict(item) for item in summaries],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def emit_prompts(
    summaries: list[SampleSummary], dataset: Path, output_path: Path
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        dataset.open("r", encoding="utf-8") as source,
        output_path.open("w", encoding="utf-8") as sink,
    ):
        for raw_line, summary in zip(source, summaries, strict=False):
            record = json.loads(raw_line)
            slim = {
                "id": summary.sample_id,
                "title": summary.title,
                "instruction": record.get("instruction") or record.get("prompt"),
                "expected_tools": record.get("tools") or record.get("available_tools"),
                "risk_flags": summary.risk_flags,
            }
            sink.write(json.dumps(slim, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        required=True,
        help="Path to MAVEN/AgentMisalignment JSONL export.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional cap on the number of samples processed.",
    )
    parser.add_argument(
        "--output",
        default=str(REPORT_DIR / "probe_summary.json"),
        help="Destination for the JSON summary report.",
    )
    parser.add_argument(
        "--emit-prompts",
        help="Optional NDJSON path containing only prompt/tool info (for manual replay).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path = Path(args.input)
    if not dataset_path.exists():
        raise SystemExit(f"Dataset not found: {dataset_path}")

    records = list(parse_dataset(dataset_path, args.limit))
    summaries = summarise_samples(records)
    if not summaries:
        raise SystemExit("No samples parsed – aborting.")

    output_path = Path(args.output)
    write_summary(summaries, dataset_path, output_path)
    print(f"[maven] Summary written to {output_path}")

    if args.emit_prompts:
        emit_prompts(summaries, dataset_path, Path(args.emit_prompts))
        print(f"[maven] Prompt subset exported to {args.emit_prompts}")


if __name__ == "__main__":
    main()
