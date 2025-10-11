#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test simple pour valider le fix des couts Gemini/Anthropic"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(
    reason="Requires external LLM providers and API keys; run manually for cost tracking verification."
)

sys.path.insert(0, str(Path(__file__).parent / "src"))

from backend.core.database.manager import DatabaseManager
from backend.features.chat.llm_stream import LLMStreamer
from backend.features.chat.pricing import MODEL_PRICING
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "src/backend/data/db/emergence_v7.db"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

MODELS_TO_TEST = {
    "google": "gemini-1.5-flash",
    "anthropic": "claude-3-5-haiku-20241022"
}


async def test_provider(llm_streamer, provider, model):
    """Test un provider specifique."""
    print(f"\n{'='*60}")
    print(f"[TEST] {provider.upper()} - Model: {model}")
    print('='*60)

    cost_info = {}
    full_response = ""

    try:
        system_prompt = "Tu es un assistant technique concis."
        history = [{"role": "user", "content": "Explique Docker en 1 phrase."}]

        print(f"[SEND] Prompt: 'Explique Docker en 1 phrase.'")
        print("[WAIT] Streaming...")

        start_time = datetime.now()

        async for chunk in llm_streamer.get_llm_response_stream(
            provider=provider,
            model=model,
            system_prompt=system_prompt,
            history=history,
            cost_info_container=cost_info
        ):
            full_response += chunk
            if len(full_response) < 100:
                print(chunk, end="", flush=True)

        duration = (datetime.now() - start_time).total_seconds()

        print(f"\n\n[DONE] Response received ({len(full_response)} chars in {duration:.1f}s)")

        input_tokens = cost_info.get("input_tokens", 0)
        output_tokens = cost_info.get("output_tokens", 0)
        total_cost = cost_info.get("total_cost", 0.0)
        error = cost_info.get("__error__", None)

        print("\n[RESULTS]:")
        print(f"  Input tokens:  {input_tokens}")
        print(f"  Output tokens: {output_tokens}")
        print(f"  Total cost:    ${total_cost:.6f}")

        if error:
            print(f"  [ERROR] {error}")

        passed = True
        if input_tokens == 0:
            print("  [FAIL] Input tokens = 0 (should be > 0)")
            passed = False
        else:
            print(f"  [OK] Input tokens ({input_tokens} > 0)")

        if output_tokens == 0:
            print("  [FAIL] Output tokens = 0 (should be > 0)")
            passed = False
        else:
            print(f"  [OK] Output tokens ({output_tokens} > 0)")

        if total_cost == 0.0:
            print("  [FAIL] Total cost = $0.00 (should be > 0)")
            passed = False
        else:
            print(f"  [OK] Total cost (${total_cost:.6f} > 0)")

        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
        expected_cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

        if abs(expected_cost - total_cost) > 0.000001:
            print(f"  [FAIL] Cost mismatch (expected: ${expected_cost:.6f}, got: ${total_cost:.6f})")
            passed = False
        else:
            print(f"  [OK] Cost calculation consistent")

        if passed:
            print(f"\n[PASS] Test {provider.upper()} PASSED!")
        else:
            print(f"\n[FAIL] Test {provider.upper()} FAILED!")

        return passed

    except Exception as e:
        print(f"\n[ERROR] Test {provider} failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_database():
    """Verifie les derniers couts dans la BDD."""
    print(f"\n{'='*60}")
    print("[DATABASE] Checking last cost entries")
    print('='*60)

    db_manager = DatabaseManager(str(DB_PATH))
    await db_manager.initialize()

    try:
        query = """
        SELECT model, input_tokens, output_tokens, total_cost, timestamp
        FROM costs
        ORDER BY timestamp DESC
        LIMIT 10
        """

        rows = await db_manager.fetchall(query)

        if not rows:
            print("[WARN] No cost entries found in database")
            return

        print(f"\n[INFO] Last {len(rows)} cost entries:\n")

        for row in rows:
            model = row["model"]
            input_tok = row["input_tokens"]
            output_tok = row["output_tokens"]
            cost = row["total_cost"]
            timestamp = row["timestamp"]

            status = "[OK]" if (input_tok > 0 and output_tok > 0 and cost > 0) else "[FAIL]"

            print(f"{status} {model:25s} | ${cost:8.6f} | {input_tok:5d} in, {output_tok:5d} out | {timestamp}")

    except Exception as e:
        print(f"[ERROR] Database read failed: {e}")
    finally:
        await db_manager.close()


async def main():
    """Point d'entree principal."""
    print("\n" + "="*60)
    print("[START] Testing Gemini/Anthropic Cost Tracking Fix")
    print("="*60)
    print(f"[INFO] Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[INFO] DB:   {DB_PATH}")

    # Initialize clients
    print("\n[SETUP] Initializing API clients...")

    if not GOOGLE_API_KEY:
        print("[WARN] GOOGLE_API_KEY missing - skipping Gemini")
    if not ANTHROPIC_API_KEY:
        print("[WARN] ANTHROPIC_API_KEY missing - skipping Anthropic")

    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    genai.configure(api_key=GOOGLE_API_KEY)

    llm_streamer = LLMStreamer(
        openai_client=openai_client,
        anthropic_client=anthropic_client,
        rate_limits={}
    )

    print("[OK] Clients initialized\n")

    results = {}

    # Test providers
    for provider, model in MODELS_TO_TEST.items():
        if provider == "google" and not GOOGLE_API_KEY:
            print(f"\n[SKIP] {provider} (API key missing)")
            continue
        if provider == "anthropic" and not ANTHROPIC_API_KEY:
            print(f"\n[SKIP] {provider} (API key missing)")
            continue

        passed = await test_provider(llm_streamer, provider, model)
        results[provider] = passed
        await asyncio.sleep(1)

    # Check database
    await check_database()

    # Summary
    print(f"\n{'='*60}")
    print("[SUMMARY] Test Results")
    print('='*60 + "\n")

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    for provider, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {provider.upper()}")

    print(f"\n{'='*60}")
    print(f"[RESULT] {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        print("[INFO] Gemini/Anthropic cost tracking fix is working correctly.")
    else:
        print("\n[WARNING] SOME TESTS FAILED")
        print("[INFO] Check details above for more information.")

    print('='*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test interrupted by user")
    except Exception as e:
        print(f"\n\n[FATAL] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
