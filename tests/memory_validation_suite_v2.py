"""
Suite de validation simplifiée pour le système de mémoire Phase 3
Adaptée aux endpoints réels de l'API
"""
import asyncio
import json
import time
import sys
import io
from datetime import datetime
from typing import Dict, Any
import aiohttp

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuration
BASE_URL = "http://127.0.0.1:8000"
PROMETHEUS_URL = f"{BASE_URL}/metrics"
MEMORY_URL = f"{BASE_URL}/api/memory"

# Headers pour authentification dev
HEADERS = {
    "X-User-ID": "test_user_validation",
    "X-Session-ID": "test_session_validation"
}


class MemoryValidationSuite:
    def __init__(self):
        self.results = {
            "prometheus_metrics": {},
            "api_health": {},
            "memory_search": {},
            "concept_search": {}
        }
        self.start_time = datetime.now()

    async def fetch_prometheus_metrics(self) -> Dict[str, Any]:
        """Récupère et parse les métriques Prometheus"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(PROMETHEUS_URL) as resp:
                    if resp.status != 200:
                        return {"error": f"Status {resp.status}"}

                    text = await resp.text()
                    metrics = {}

                    # Parser basique pour les métriques
                    for line in text.split('\n'):
                        if line.startswith('#') or not line.strip():
                            continue

                        # Métriques système de mémoire
                        if any(keyword in line for keyword in [
                            'memory', 'redis', 'temporal', 'activation',
                            'concept', 'ltm', 'stm', 'rag', 'cache'
                        ]):
                            parts = line.split()
                            if len(parts) >= 2:
                                # Extraire nom et valeur
                                metric_full = parts[0]
                                metric_name = metric_full.split('{')[0]
                                try:
                                    metric_value = parts[-1]
                                    metrics[metric_name] = metric_value
                                except (ValueError, IndexError):
                                    continue

                    return metrics
        except Exception as e:
            return {"error": str(e)}

    async def validate_prometheus_metrics(self):
        """Étape 1: Valider les métriques Prometheus"""
        print("\n" + "="*80)
        print("📈 VALIDATION DES MÉTRIQUES PROMETHEUS")
        print("="*80)

        metrics = await self.fetch_prometheus_metrics()

        if "error" in metrics:
            print(f"❌ Erreur lors de la récupération: {metrics['error']}")
            self.results["prometheus_metrics"] = {"success": False, "error": metrics['error']}
            return False

        # Afficher toutes les métriques pertinentes
        print(f"\n📊 Métriques collectées: {len(metrics)}")

        memory_metrics = [k for k in metrics.keys() if any(
            kw in k.lower() for kw in ['memory', 'cache', 'rag', 'concept', 'ltm', 'stm']
        )]

        print(f"\n🧠 Métriques mémoire trouvées ({len(memory_metrics)}):")
        for metric in sorted(memory_metrics)[:15]:  # Top 15
            print(f"  ✓ {metric}: {metrics[metric]}")

        self.results["prometheus_metrics"] = {
            "success": True,
            "total_metrics": len(metrics),
            "memory_metrics": len(memory_metrics),
            "samples": {k: metrics[k] for k in sorted(memory_metrics)[:10]}
        }

        return len(memory_metrics) > 0

    async def test_api_health(self):
        """Étape 2: Tester la santé de l'API mémoire"""
        print("\n" + "="*80)
        print("🏥 TEST DE SANTÉ DE L'API MÉMOIRE")
        print("="*80)

        endpoints = [
            ("GET", "/api/memory/tend-garden", {}),
            ("GET", "/api/memory/user/stats", {}),
            ("GET", "/api/memory/search/unified", {"q": "test", "limit": 5}),
            ("GET", "/api/memory/concepts/search", {"q": "docker", "limit": 5})
        ]

        results = {}
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            for method, endpoint, params in endpoints:
                url = f"{BASE_URL}{endpoint}"
                try:
                    if method == "GET":
                        async with session.get(url, params=params) as resp:
                            status = resp.status
                            if status == 200:
                                data = await resp.json()
                                results[endpoint] = {
                                    "status": status,
                                    "success": True,
                                    "data_keys": list(data.keys()) if isinstance(data, dict) else []
                                }
                                print(f"✓ {endpoint}: {status} OK")
                            else:
                                results[endpoint] = {"status": status, "success": False}
                                print(f"✗ {endpoint}: {status}")
                except Exception as e:
                    results[endpoint] = {"error": str(e), "success": False}
                    print(f"❌ {endpoint}: {str(e)}")

        success_count = sum(1 for r in results.values() if r.get("success"))
        print(f"\n📊 Endpoints fonctionnels: {success_count}/{len(endpoints)}")

        self.results["api_health"] = {
            "success": success_count >= len(endpoints) // 2,
            "endpoints": results,
            "total": len(endpoints),
            "working": success_count
        }

        return success_count >= len(endpoints) // 2

    async def test_memory_search(self):
        """Étape 3: Tester la recherche mémoire"""
        print("\n" + "="*80)
        print("🔍 TEST DE RECHERCHE MÉMOIRE")
        print("="*80)

        test_queries = [
            "docker",
            "kubernetes",
            "prometheus",
            "philosophy",
            "programming"
        ]

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            search_results = {}

            for query in test_queries:
                try:
                    # Test unified search
                    url = f"{BASE_URL}/api/memory/search/unified"
                    params = {"q": query, "limit": 10}

                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            total = data.get("total_results", 0)
                            search_results[query] = {
                                "status": "success",
                                "total_results": total,
                                "stm": len(data.get("stm_summaries", [])),
                                "ltm": len(data.get("ltm_concepts", [])),
                                "threads": len(data.get("threads", [])),
                                "messages": len(data.get("messages", []))
                            }
                            print(f"  ✓ '{query}': {total} résultats (STM:{search_results[query]['stm']}, LTM:{search_results[query]['ltm']}, Threads:{search_results[query]['threads']}, Msgs:{search_results[query]['messages']})")
                        else:
                            search_results[query] = {"status": "error", "code": resp.status}
                            print(f"  ✗ '{query}': HTTP {resp.status}")

                except Exception as e:
                    search_results[query] = {"status": "error", "error": str(e)}
                    print(f"  ❌ '{query}': {str(e)}")

        total_results = sum(
            r.get("total_results", 0) for r in search_results.values()
            if isinstance(r, dict)
        )

        print(f"\n📊 Total résultats trouvés: {total_results}")
        print(f"📊 Requêtes réussies: {len([r for r in search_results.values() if r.get('status') == 'success'])}/{len(test_queries)}")

        self.results["memory_search"] = {
            "success": len([r for r in search_results.values() if r.get('status') == 'success']) > 0,
            "queries": search_results,
            "total_results": total_results
        }

        return total_results > 0 or len([r for r in search_results.values() if r.get('status') == 'success']) > 0

    async def test_concept_search(self):
        """Étape 4: Tester la recherche de concepts"""
        print("\n" + "="*80)
        print("💡 TEST DE RECHERCHE DE CONCEPTS")
        print("="*80)

        test_concepts = [
            "docker",
            "redis",
            "python",
            "philosophy",
            "music"
        ]

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            concept_results = {}

            for concept in test_concepts:
                try:
                    url = f"{BASE_URL}/api/memory/concepts/search"
                    params = {"q": concept, "limit": 10}

                    async with session.get(url, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            count = data.get("count", 0)
                            concept_results[concept] = {
                                "status": "success",
                                "count": count,
                                "results": data.get("results", [])[:3]  # Top 3
                            }
                            print(f"  ✓ '{concept}': {count} concepts trouvés")

                            # Afficher quelques détails
                            for i, result in enumerate(concept_results[concept]["results"][:2], 1):
                                concept_text = result.get("concept_text", "?")[:50]
                                mentions = result.get("mention_count", 0)
                                print(f"      {i}. {concept_text}... (mentions: {mentions})")

                        else:
                            concept_results[concept] = {"status": "error", "code": resp.status}
                            print(f"  ✗ '{concept}': HTTP {resp.status}")

                except Exception as e:
                    concept_results[concept] = {"status": "error", "error": str(e)}
                    print(f"  ❌ '{concept}': {str(e)}")

        total_concepts = sum(
            r.get("count", 0) for r in concept_results.values()
            if isinstance(r, dict)
        )

        print(f"\n📊 Total concepts trouvés: {total_concepts}")
        print(f"📊 Recherches réussies: {len([r for r in concept_results.values() if r.get('status') == 'success'])}/{len(test_concepts)}")

        self.results["concept_search"] = {
            "success": len([r for r in concept_results.values() if r.get('status') == 'success']) > 0,
            "searches": concept_results,
            "total_concepts": total_concepts
        }

        return total_concepts > 0 or len([r for r in concept_results.values() if r.get('status') == 'success']) > 0

    async def run_all_validations(self):
        """Exécuter toute la suite de validation"""
        print("\n" + "="*80)
        print("🚀 DÉMARRAGE DE LA SUITE DE VALIDATION MÉMOIRE PHASE 3")
        print(f"⏰ Heure de début: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # Exécuter chaque validation
        validations = [
            ("Prometheus Metrics", self.validate_prometheus_metrics),
            ("API Health Check", self.test_api_health),
            ("Memory Search", self.test_memory_search),
            ("Concept Search", self.test_concept_search)
        ]

        validation_results = {}

        for name, validation_func in validations:
            try:
                success = await validation_func()
                validation_results[name] = "✓ PASS" if success else "✗ FAIL"
            except Exception as e:
                print(f"\n❌ Erreur lors de {name}: {str(e)}")
                import traceback
                traceback.print_exc()
                validation_results[name] = f"✗ ERROR: {str(e)}"

        # Rapport final
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        print("\n" + "="*80)
        print("📋 RAPPORT FINAL DE VALIDATION")
        print("="*80)

        for name, result in validation_results.items():
            print(f"{result} - {name}")

        passed = sum(1 for r in validation_results.values() if "PASS" in r)
        total = len(validation_results)
        success_rate = passed / total * 100 if total > 0 else 0

        print(f"\n🎯 Taux de réussite global: {success_rate:.1f}% ({passed}/{total})")
        print(f"⏱️  Durée totale: {duration:.2f}s")
        print(f"⏰ Heure de fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Sauvegarder le rapport
        report = {
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "validation_results": validation_results,
            "success_rate_percent": success_rate,
            "detailed_results": self.results
        }

        import os
        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/memory_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Rapport sauvegardé: {report_path}")

        return success_rate >= 50  # Au moins 50% de validations passées


async def main():
    suite = MemoryValidationSuite()
    overall_success = await suite.run_all_validations()

    if overall_success:
        print("\n✅ VALIDATION GLOBALE RÉUSSIE!")
        return 0
    else:
        print("\n⚠️  VALIDATION GLOBALE ÉCHOUÉE - Vérifier les détails ci-dessus")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
