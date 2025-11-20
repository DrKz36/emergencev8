#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour valider le fix des couts Gemini/Anthropic
GAP #2 - Cockpit Debug

Test automatique avec conversations reelles pour les 3 providers.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.skip(
    reason="Requires live LLM providers and credentials; execute manually when validating cost fixes."
)

# Fix encodage Windows
if sys.platform == "win32":
    import locale

    locale.setlocale(locale.LC_ALL, "")

# Ajout du path pour importer les modules backend
sys.path.insert(0, str(Path(__file__).parent / "src"))

from backend.core.database.manager import DatabaseManager
from backend.features.chat.llm_stream import LLMStreamer
from backend.features.chat.pricing import MODEL_PRICING
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai

# Configuration
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "src/backend/data/db/emergence_v7.db"

# API Keys (depuis env ou .env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Modèles à tester
MODELS_TO_TEST = {
    "openai": "gpt-4o-mini",
    "google": "gemini-1.5-flash",
    "anthropic": "claude-3-5-haiku-20241022",
}

# Messages de test
TEST_PROMPTS = [
    "Explique-moi Docker en 2 phrases.",
    "Qu'est-ce que Kubernetes ?",
    "Donne-moi un exemple de CI/CD pipeline.",
]


class CostTestRunner:
    """Test runner pour valider le tracking des coûts."""

    def __init__(self):
        self.db_manager = None
        self.openai_client = None
        self.anthropic_client = None
        self.llm_streamer = None
        self.results = {}

    async def setup(self):
        """Initialize clients and DB."""
        print("[SETUP] Initialisation des clients API...")

        # Configure API keys
        if not OPENAI_API_KEY:
            print("[WARN] OPENAI_API_KEY manquante")
        if not ANTHROPIC_API_KEY:
            print("[WARN] ANTHROPIC_API_KEY manquante")
        if not GOOGLE_API_KEY:
            print("[WARN] GOOGLE_API_KEY manquante")

        # Initialize clients
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        genai.configure(api_key=GOOGLE_API_KEY)

        # Initialize LLM streamer
        self.llm_streamer = LLMStreamer(
            openai_client=self.openai_client,
            anthropic_client=self.anthropic_client,
            rate_limits={},
        )

        # Initialize DB
        self.db_manager = DatabaseManager(str(DB_PATH))
        await self.db_manager.initialize()

        print("✅ Clients initialisés\n")

    async def test_provider(self, provider: str, model: str):
        """Test un provider spécifique et vérifie les coûts."""
        print(f"\n{'=' * 60}")
        print(f"[TEST] {provider.upper()} - Modele: {model}")
        print("=" * 60)

        cost_info = {}
        full_response = ""

        try:
            # Appel au LLM
            system_prompt = "Tu es un assistant technique concis."
            history = [{"role": "user", "content": TEST_PROMPTS[0]}]

            print(f"📤 Envoi de: '{TEST_PROMPTS[0]}'")
            print("⏳ Streaming en cours...\n")

            start_time = datetime.now()

            async for chunk in self.llm_streamer.get_llm_response_stream(
                provider=provider,
                model=model,
                system_prompt=system_prompt,
                history=history,
                cost_info_container=cost_info,
            ):
                full_response += chunk
                # Print partial response (limite 80 chars)
                if len(full_response) < 80:
                    print(chunk, end="", flush=True)

            duration = (datetime.now() - start_time).total_seconds()

            print(
                f"\n\n✅ Réponse reçue ({len(full_response)} caractères en {duration:.1f}s)"
            )

            # Vérifier les coûts
            input_tokens = cost_info.get("input_tokens", 0)
            output_tokens = cost_info.get("output_tokens", 0)
            total_cost = cost_info.get("total_cost", 0.0)
            error = cost_info.get("__error__", None)

            print("\n📊 Résultats:")
            print(f"  • Input tokens:  {input_tokens}")
            print(f"  • Output tokens: {output_tokens}")
            print(f"  • Total cost:    ${total_cost:.6f}")

            if error:
                print(f"  ❌ Erreur: {error}")

            # Validation
            passed = True
            issues = []

            if input_tokens == 0:
                passed = False
                issues.append("❌ Input tokens = 0 (devrait être > 0)")
            else:
                print(f"  ✅ Input tokens OK ({input_tokens} > 0)")

            if output_tokens == 0:
                passed = False
                issues.append("❌ Output tokens = 0 (devrait être > 0)")
            else:
                print(f"  ✅ Output tokens OK ({output_tokens} > 0)")

            if total_cost == 0.0:
                passed = False
                issues.append("❌ Total cost = $0.00 (devrait être > 0)")
            else:
                print(f"  ✅ Total cost OK (${total_cost:.6f} > 0)")

            # Vérifier cohérence du pricing
            pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
            expected_cost = (input_tokens * pricing["input"]) + (
                output_tokens * pricing["output"]
            )

            if abs(expected_cost - total_cost) > 0.000001:
                passed = False
                issues.append(
                    f"❌ Coût incohérent (attendu: ${expected_cost:.6f}, obtenu: ${total_cost:.6f})"
                )
            else:
                print("  ✅ Calcul du coût cohérent")

            # Stocker résultats
            self.results[provider] = {
                "passed": passed,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_cost": total_cost,
                "issues": issues,
                "duration": duration,
                "response_length": len(full_response),
            }

            if passed:
                print(f"\n✅ Test {provider.upper()} PASSÉ !")
            else:
                print(f"\n❌ Test {provider.upper()} ÉCHOUÉ :")
                for issue in issues:
                    print(f"   {issue}")

        except Exception as e:
            print(f"\n❌ Erreur lors du test {provider}: {e}")
            import traceback

            traceback.print_exc()

            self.results[provider] = {
                "passed": False,
                "error": str(e),
                "issues": [f"Exception: {e}"],
            }

    async def check_database_costs(self):
        """Vérifie les derniers coûts enregistrés dans la BDD."""
        print(f"\n{'=' * 60}")
        print("🗄️  Vérification Base de Données")
        print("=" * 60)

        try:
            query = """
            SELECT model, input_tokens, output_tokens, total_cost, timestamp
            FROM costs
            ORDER BY timestamp DESC
            LIMIT 10
            """

            rows = await self.db_manager.fetchall(query)

            if not rows:
                print("⚠️  Aucune entrée de coût trouvée dans la BDD")
                return

            print(f"\n📋 Dernières {len(rows)} entrées de coûts :\n")

            for row in rows:
                model = row["model"]
                input_tok = row["input_tokens"]
                output_tok = row["output_tokens"]
                cost = row["total_cost"]
                timestamp = row["timestamp"]

                status = (
                    "✅" if (input_tok > 0 and output_tok > 0 and cost > 0) else "❌"
                )

                print(
                    f"{status} {model:25s} | ${cost:8.6f} | {input_tok:5d} in, {output_tok:5d} out | {timestamp}"
                )

        except Exception as e:
            print(f"❌ Erreur lors de la lecture BDD: {e}")

    async def run_all_tests(self):
        """Lance tous les tests."""
        print("\n" + "=" * 60)
        print("🚀 TEST AUTOMATIQUE - Fix Coûts Gemini/Anthropic")
        print("=" * 60)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"DB:   {DB_PATH}")

        await self.setup()

        # Test chaque provider
        for provider, model in MODELS_TO_TEST.items():
            # Skip si API key manquante
            if provider == "openai" and not OPENAI_API_KEY:
                print(f"\n⏭️  Skip {provider} (API key manquante)")
                continue
            if provider == "google" and not GOOGLE_API_KEY:
                print(f"\n⏭️  Skip {provider} (API key manquante)")
                continue
            if provider == "anthropic" and not ANTHROPIC_API_KEY:
                print(f"\n⏭️  Skip {provider} (API key manquante)")
                continue

            await self.test_provider(provider, model)
            await asyncio.sleep(1)  # Cooldown

        # Vérifier la BDD
        await self.check_database_costs()

        # Rapport final
        self.print_summary()

        await self.cleanup()

    def print_summary(self):
        """Affiche un résumé des tests."""
        print(f"\n{'=' * 60}")
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 60 + "\n")

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r.get("passed", False))

        for provider, result in self.results.items():
            status = "✅ PASSÉ" if result.get("passed", False) else "❌ ÉCHOUÉ"
            print(f"{status}  {provider.upper()}")

            if not result.get("passed", False):
                for issue in result.get("issues", []):
                    print(f"       {issue}")

        print(f"\n{'=' * 60}")
        print(f"Résultat global: {passed_tests}/{total_tests} tests réussis")

        if passed_tests == total_tests:
            print("\n🎉 TOUS LES TESTS SONT PASSÉS !")
            print("✅ Le fix des coûts Gemini/Anthropic fonctionne correctement.")
        else:
            print("\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
            print("Voir les détails ci-dessus pour plus d'informations.")

        print("=" * 60 + "\n")

    async def cleanup(self):
        """Cleanup resources."""
        if self.db_manager:
            await self.db_manager.close()


async def main():
    """Point d'entrée principal."""
    runner = CostTestRunner()

    try:
        await runner.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
