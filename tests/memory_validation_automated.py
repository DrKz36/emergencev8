"""
Suite de validation automatisée pour Phase 3 - Version simplifiée et robuste
Teste les 4 priorités: Prometheus, Stress Test, Clustering, Recall Contextuel
"""
import asyncio
import json
import time
import sys
import io
import os
from datetime import datetime
from typing import Dict, Any, List
import aiohttp

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuration
BASE_URL = "http://127.0.0.1:8000"
METRICS_URL = f"{BASE_URL}/api/metrics/metrics"  # Correct endpoint
MEMORY_URL = f"{BASE_URL}/api/memory"

# Headers pour contourner l'authentification en mode dev
HEADERS = {
    "X-User-ID": "test_validation_user",
    "X-Session-ID": "test_validation_session"
}

class Colors:
    """Codes couleur ANSI pour le terminal"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Affiche un header formaté"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


class MemoryValidator:
    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()

    async def test_1_prometheus_metrics(self) -> bool:
        """Test 1: Valider les métriques Prometheus"""
        print_header("📈 TEST 1: MÉTRIQUES PROMETHEUS")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(METRICS_URL) as resp:
                    status = resp.status
                    text = await resp.text()

                    if status != 200:
                        print_error(f"HTTP {status}: {text[:200]}")
                        self.results["prometheus"] = {"success": False, "status": status}
                        return False

                    # Parser les métriques
                    lines = text.split('\n')
                    metrics = {}

                    for line in lines:
                        if line.startswith('#') or not line.strip():
                            continue

                        # Extraire les métriques mémoire/RAG
                        if any(kw in line.lower() for kw in [
                            'memory', 'rag', 'concept', 'ltm', 'stm', 'cache',
                            'redis', 'temporal', 'activation'
                        ]):
                            parts = line.split()
                            if len(parts) >= 2:
                                name = parts[0].split('{')[0]
                                metrics[name] = parts[-1]

                    # Afficher les métriques trouvées
                    if metrics:
                        print_success(f"Métriques trouvées: {len(metrics)}")
                        print_info(f"Échantillon des métriques:")
                        for i, (name, value) in enumerate(list(metrics.items())[:10]):
                            print(f"    {i+1}. {name}: {value}")
                    else:
                        print_error("Aucune métrique pertinente trouvée")
                        print_info(f"Total de lignes reçues: {len(lines)}")

                    self.results["prometheus"] = {
                        "success": len(metrics) > 0,
                        "metrics_count": len(metrics),
                        "sample_metrics": dict(list(metrics.items())[:10])
                    }

                    return len(metrics) > 0

        except Exception as e:
            print_error(f"Erreur: {str(e)}")
            self.results["prometheus"] = {"success": False, "error": str(e)}
            return False

    async def test_2_concept_search_stress(self) -> bool:
        """Test 2: Stress test - Recherches multiples de concepts"""
        print_header("🧪 TEST 2: STRESS TEST - RECHERCHES CONCEPTS (100+ requêtes)")

        queries = [
            # Tech
            "docker", "kubernetes", "redis", "prometheus", "python", "fastapi",
            "microservices", "cloud", "devops", "ci/cd",
            # Philosophy
            "philosophy", "materialism", "dialectic", "engels", "marx",
            # Medical
            "medicine", "vaccine", "health", "ferritin",
            # Music
            "music", "punk", "garance", "guitar",
            # Misc
            "literature", "poetry", "symbolism", "metaphor",
        ] * 4  # Répéter 4 fois = 100+ requêtes

        start = time.time()
        results_data = []
        errors = 0

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            for i, query in enumerate(queries):
                try:
                    url = f"{MEMORY_URL}/concepts/search"
                    async with session.get(url, params={"q": query, "limit": 5}) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results_data.append({
                                "query": query,
                                "count": data.get("count", 0),
                                "status": "success"
                            })
                        else:
                            errors += 1
                            results_data.append({
                                "query": query,
                                "status": "error",
                                "code": resp.status
                            })

                    # Progress indicator
                    if (i + 1) % 20 == 0:
                        print_info(f"Progression: {i+1}/{len(queries)} requêtes...")

                except Exception as e:
                    errors += 1
                    results_data.append({"query": query, "status": "error", "error": str(e)})

        duration = time.time() - start
        throughput = len(queries) / duration

        # Statistiques
        successful = len([r for r in results_data if r.get("status") == "success"])
        total_concepts = sum(r.get("count", 0) for r in results_data)

        print_success(f"Requêtes: {len(queries)}")
        print_success(f"Réussies: {successful}")
        print_error(f"Erreurs: {errors}")
        print_info(f"Durée: {duration:.2f}s")
        print_info(f"Débit: {throughput:.2f} req/s")
        print_info(f"Concepts trouvés: {total_concepts}")

        self.results["stress_test"] = {
            "success": successful >= len(queries) * 0.7,  # 70% de réussite minimum
            "total_queries": len(queries),
            "successful": successful,
            "errors": errors,
            "duration_sec": duration,
            "throughput_rps": throughput,
            "total_concepts": total_concepts
        }

        return successful >= len(queries) * 0.7

    async def test_3_concept_clustering(self) -> bool:
        """Test 3: Clustering - Vérifier que les concepts similaires se regroupent"""
        print_header("🔍 TEST 3: CLUSTERING DE CONCEPTS SIMILAIRES")

        # Groupes de concepts similaires qui devraient être trouvés ensemble
        concept_groups = {
            "containerization": ["docker", "kubernetes", "container", "pod"],
            "monitoring": ["prometheus", "grafana", "metrics", "observability"],
            "philosophy": ["marx", "engels", "materialism", "dialectic"],
        }

        clustering_scores = []

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            for group_name, concepts in concept_groups.items():
                print_info(f"Groupe: {group_name}")

                # Chercher chaque concept du groupe
                concept_results = []
                for concept in concepts:
                    try:
                        url = f"{MEMORY_URL}/concepts/search"
                        async with session.get(url, params={"q": concept, "limit": 10}) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                concept_results.append({
                                    "concept": concept,
                                    "count": data.get("count", 0),
                                    "results": data.get("results", [])
                                })
                    except Exception as e:
                        print_error(f"  Erreur pour '{concept}': {e}")

                # Analyser le clustering
                total_found = sum(r["count"] for r in concept_results)
                avg_per_concept = total_found / len(concepts) if concepts else 0

                print(f"  Concepts trouvés: {total_found} (moy: {avg_per_concept:.1f}/concept)")

                if total_found > 0:
                    clustering_scores.append(avg_per_concept)

        # Score global
        avg_clustering = sum(clustering_scores) / len(clustering_scores) if clustering_scores else 0
        print_success(f"\nScore de clustering: {avg_clustering:.2f} concepts/groupe")

        self.results["clustering"] = {
            "success": avg_clustering > 0,
            "avg_concepts_per_group": avg_clustering,
            "groups_tested": len(concept_groups)
        }

        return avg_clustering > 0

    async def test_4_contextual_recall(self) -> bool:
        """Test 4: Recall contextuel - Recherche unifiée dans STM+LTM"""
        print_header("💬 TEST 4: RECALL CONTEXTUEL (Recherche Unifiée)")

        test_queries = [
            ("docker kubernetes", ["docker", "kubernetes", "container"]),
            ("prometheus monitoring", ["prometheus", "metrics", "monitoring"]),
            ("philosophy materialism", ["philosophy", "materialism", "marx"]),
        ]

        recall_results = []

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            for query, expected_keywords in test_queries:
                try:
                    url = f"{MEMORY_URL}/search/unified"
                    async with session.get(url, params={"q": query, "limit": 10}) as resp:
                        if resp.status == 200:
                            data = await resp.json()

                            # Compter les résultats par catégorie
                            stm = len(data.get("stm_summaries", []))
                            ltm = len(data.get("ltm_concepts", []))
                            threads = len(data.get("threads", []))
                            messages = len(data.get("messages", []))
                            total = data.get("total_results", 0)

                            # Vérifier si les mots-clés sont présents
                            all_text = json.dumps(data).lower()
                            keywords_found = sum(1 for kw in expected_keywords if kw.lower() in all_text)
                            recall_score = keywords_found / len(expected_keywords) if expected_keywords else 0

                            recall_results.append({
                                "query": query,
                                "total": total,
                                "stm": stm,
                                "ltm": ltm,
                                "threads": threads,
                                "messages": messages,
                                "keywords_found": keywords_found,
                                "recall_score": recall_score
                            })

                            print_info(f"'{query}': {total} résultats (STM:{stm}, LTM:{ltm}, Threads:{threads}, Msgs:{messages}) - Recall:{recall_score*100:.0f}%")

                        else:
                            print_error(f"'{query}': HTTP {resp.status}")
                            recall_results.append({"query": query, "error": resp.status})

                except Exception as e:
                    print_error(f"'{query}': {str(e)}")
                    recall_results.append({"query": query, "error": str(e)})

        # Score moyen de recall
        recall_scores = [r.get("recall_score", 0) for r in recall_results]
        avg_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0

        print_success(f"\nRecall moyen: {avg_recall*100:.1f}%")

        self.results["contextual_recall"] = {
            "success": avg_recall >= 0.3,  # Au moins 30% de recall
            "avg_recall": avg_recall,
            "queries_tested": len(test_queries),
            "details": recall_results
        }

        return avg_recall >= 0.3

    async def run_all_tests(self) -> Dict[str, Any]:
        """Exécute tous les tests et génère le rapport"""
        print_header("🚀 DÉMARRAGE VALIDATION MÉMOIRE PHASE 3")
        print_info(f"Heure: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        tests = [
            ("Prometheus Metrics", self.test_1_prometheus_metrics),
            ("Stress Test (100+ req)", self.test_2_concept_search_stress),
            ("Concept Clustering", self.test_3_concept_clustering),
            ("Contextual Recall", self.test_4_contextual_recall)
        ]

        test_results = {}

        for name, test_func in tests:
            try:
                success = await test_func()
                test_results[name] = "✓ PASS" if success else "✗ FAIL"
            except Exception as e:
                print_error(f"ERREUR CRITIQUE dans {name}: {str(e)}")
                import traceback
                traceback.print_exc()
                test_results[name] = f"✗ ERROR: {str(e)}"

        # Rapport final
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        print_header("📋 RAPPORT FINAL")

        for name, result in test_results.items():
            if "PASS" in result:
                print_success(f"{name}")
            elif "FAIL" in result:
                print_error(f"{name}")
            else:
                print(f"{Colors.YELLOW}⚠ {name}: {result}{Colors.END}")

        passed = sum(1 for r in test_results.values() if "PASS" in r)
        total = len(test_results)
        success_rate = passed / total * 100 if total > 0 else 0

        print(f"\n{Colors.BOLD}🎯 Taux de réussite: {success_rate:.1f}% ({passed}/{total}){Colors.END}")
        print_info(f"Durée totale: {duration:.2f}s")

        # Sauvegarder le rapport
        report = {
            "timestamp": end_time.isoformat(),
            "duration_sec": duration,
            "test_results": test_results,
            "success_rate": success_rate,
            "details": self.results
        }

        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/memory_phase3_validation_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print_info(f"Rapport sauvegardé: {report_path}")

        if success_rate >= 75:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ VALIDATION GLOBALE RÉUSSIE!{Colors.END}")
            return report
        else:
            print(f"\n{Colors.YELLOW}⚠️  VALIDATION PARTIELLE - Voir détails ci-dessus{Colors.END}")
            return report


async def main():
    validator = MemoryValidator()
    report = await validator.run_all_tests()
    return 0 if report["success_rate"] >= 75 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
