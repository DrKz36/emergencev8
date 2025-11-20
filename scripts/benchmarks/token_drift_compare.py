"""
Latency and token-id drift comparator between OpenAI-compatible endpoints.

Prerequisites
-------------
- The upstream endpoint (OpenAI, Anthropic proxy, etc.) must support the
  ``return_token_ids`` flag introduced in vLLM 0.10.2.
- The local endpoint (vLLM) must be started with ``--openai-api``.

Typical usage
-------------
::

    python scripts/benchmarks/token_drift_compare.py \\
        --openai-base https://api.openai.com \\
        --openai-key sk-... \\
        --vllm-base http://127.0.0.1:8001 \\
        --model gpt-4o-mini \\
        --prompt \"Compute the determinant of [[2,3],[5,7]].\"

Results are appended to ``reports/benchmarks/vllm_openai_token_drift.log`` as
newline-delimited JSON entries containing latency measurements and token id
diffs.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import httpx

LOG_PATH = Path("reports") / "benchmarks" / "vllm_openai_token_drift.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class RunResult:
    prompt: str
    model: str
    openai_latency_ms: float
    vllm_latency_ms: float
    prompt_token_diff: List[int]
    completion_token_diff: List[int]
    openai_prompt_ids: List[int] | None
    vllm_prompt_ids: List[int] | None
    openai_completion_ids: List[int] | None
    vllm_completion_ids: List[int] | None
    timestamp: str


def extract_token_ids(
    payload: Dict[str, Any],
) -> tuple[list[int] | None, list[int] | None]:
    """Attempt to pull prompt + completion token ids from various OpenAI-compatible payloads."""

    prompt_ids = payload.get("prompt_token_ids")
    completion_ids = payload.get("token_ids") or payload.get("completion_token_ids")

    if prompt_ids is None or completion_ids is None:
        choices = payload.get("choices") or []
        if choices:
            choice = choices[0]
            message = choice.get("message") or {}
            prompt_ids = (
                prompt_ids
                or message.get("prompt_token_ids")
                or choice.get("prompt_token_ids")
            )
            completion_ids = (
                completion_ids or message.get("token_ids") or choice.get("token_ids")
            )
            metadata = message.get("metadata") or {}
            prompt_ids = prompt_ids or metadata.get("prompt_token_ids")
            completion_ids = completion_ids or metadata.get("token_ids")

    def _convert(maybe_sequence: Any) -> list[int] | None:
        if maybe_sequence is None:
            return None
        if isinstance(maybe_sequence, Sequence) and not isinstance(
            maybe_sequence, (str, bytes)
        ):
            try:
                return [int(item) for item in maybe_sequence]
            except Exception:  # noqa: BLE001 - permissive conversion
                return None
        return None

    return _convert(prompt_ids), _convert(completion_ids)


def diff_tokens(reference: list[int] | None, candidate: list[int] | None) -> list[int]:
    if reference is None or candidate is None:
        return []
    if len(reference) != len(candidate):
        return [len(reference) - len(candidate)]
    return [
        idx
        for idx, (r, c) in enumerate(zip(reference, candidate, strict=True))
        if r != c
    ]


def post_completion(
    client: httpx.Client, base: str, api_key: str | None, model: str, prompt: str
) -> tuple[dict, float]:
    url = f"{base.rstrip('/')}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "return_token_ids": True,
    }

    started = time.perf_counter()
    response = client.post(url, headers=headers, json=payload, timeout=60)
    latency_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return response.json(), latency_ms


def load_prompts(args: argparse.Namespace) -> Iterable[str]:
    if args.prompt:
        yield args.prompt
    if args.prompt_file:
        with Path(args.prompt_file).open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    yield stripped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--openai-base", help="Base URL for the OpenAI-compatible upstream endpoint."
    )
    parser.add_argument("--openai-key", help="API key for the upstream endpoint.")
    parser.add_argument(
        "--vllm-base",
        help="Base URL for the vLLM server (must expose /v1/chat/completions).",
    )
    parser.add_argument("--vllm-key", help="Optional bearer token for the vLLM server.")
    parser.add_argument(
        "--model", required=True, help="Model identifier shared by both endpoints."
    )
    parser.add_argument("--prompt", help="Single prompt to benchmark.")
    parser.add_argument("--prompt-file", help="File containing one prompt per line.")
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Print results instead of appending to the log file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.openai_base or not args.vllm_base:
        raise SystemExit("Both --openai-base and --vllm-base must be provided.")

    prompts = list(load_prompts(args))
    if not prompts:
        raise SystemExit("No prompt provided. Use --prompt or --prompt-file.")

    client = httpx.Client(http2=True)
    results: list[RunResult] = []
    for prompt in prompts:
        upstream_payload, openai_latency = post_completion(
            client, args.openai_base, args.openai_key, args.model, prompt
        )
        local_payload, vllm_latency = post_completion(
            client, args.vllm_base, args.vllm_key, args.model, prompt
        )

        upstream_prompt, upstream_completion = extract_token_ids(upstream_payload)
        local_prompt, local_completion = extract_token_ids(local_payload)

        results.append(
            RunResult(
                prompt=prompt,
                model=args.model,
                openai_latency_ms=openai_latency,
                vllm_latency_ms=vllm_latency,
                prompt_token_diff=diff_tokens(upstream_prompt, local_prompt),
                completion_token_diff=diff_tokens(
                    upstream_completion, local_completion
                ),
                openai_prompt_ids=upstream_prompt,
                vllm_prompt_ids=local_prompt,
                openai_completion_ids=upstream_completion,
                vllm_completion_ids=local_completion,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    if args.no_log:
        print(
            json.dumps(
                [asdict(result) for result in results], indent=2, ensure_ascii=False
            )
        )
    else:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(asdict(result), ensure_ascii=False) + "\n")
        print(f"[token-drift] Appended {len(results)} entries to {LOG_PATH}")


if __name__ == "__main__":
    main()
