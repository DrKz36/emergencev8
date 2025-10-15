"""
Suite de validation complète pour le système de mémoire Phase 3
- Validation des métriques Prometheus
- Stress test avec 100+ messages
- Test du clustering automatique
- Validation du recall contextuel Nexus
"""
import asyncio
import json
import time
import sys
import io
from datetime import datetime
from typing import List, Dict, Any
import aiohttp
import numpy as np
from collections import defaultdict

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuration
BASE_URL = "http://127.0.0.1:8000"
PROMETHEUS_URL = f"{BASE_URL}/metrics"
MEMORY_URL = f"{BASE_URL}/api/memory"
NEXUS_URL = f"{BASE_URL}/api/nexus/chat"

class MemoryValidationSuite:
    def __init__(self):
        self.results = {
            "prometheus_metrics": {},
            "stress_test": {},
            "clustering": {},
            "recall_contextual": {}
        }
        self.start_time = datetime.now()

    async def fetch_prometheus_metrics(self) -> Dict[str, Any]:
        """Récupère et parse les métriques Prometheus"""
        async with aiohttp.ClientSession() as session:
            async with session.get(PROMETHEUS_URL) as resp:
                if resp.status != 200:
                    return {"error": f"Status {resp.status}"}

                text = await resp.text()
                metrics = {}

                for line in text.split('\n'):
                    if line.startswith('#') or not line.strip():
                        continue

                    # Parse les métriques pertinentes au système de mémoire
                    if any(keyword in line for keyword in ['memory', 'redis', 'temporal', 'activation']):
                        parts = line.split()
                        if len(parts) >= 2:
                            metric_name = parts[0].split('{')[0]
                            try:
                                metric_value = float(parts[-1])
                                metrics[metric_name] = metric_value
                            except ValueError:
                                continue

                return metrics

    async def validate_prometheus_metrics(self):
        """Étape 1: Valider les métriques Prometheus"""
        print("\n" + "="*80)
        print("📈 VALIDATION DES MÉTRIQUES PROMETHEUS")
        print("="*80)

        metrics = await self.fetch_prometheus_metrics()

        # Métriques attendues pour le système de mémoire
        expected_metrics = [
            'memory_store_total',
            'memory_query_duration_seconds',
            'redis_activation_hits',
            'redis_activation_misses',
            'temporal_context_queries',
            'memory_consolidation_operations'
        ]

        found_metrics = []
        missing_metrics = []

        for metric in expected_metrics:
            matching = [k for k in metrics.keys() if metric in k]
            if matching:
                found_metrics.append(metric)
                print(f"✓ {metric}: {matching[0]} = {metrics[matching[0]]}")
            else:
                missing_metrics.append(metric)
                print(f"✗ {metric}: NON TROUVÉ")

        # Statistiques
        coverage = len(found_metrics) / len(expected_metrics) * 100
        print(f"\n📊 Couverture des métriques: {coverage:.1f}% ({len(found_metrics)}/{len(expected_metrics)})")

        self.results["prometheus_metrics"] = {
            "coverage_percent": coverage,
            "found_metrics": found_metrics,
            "missing_metrics": missing_metrics,
            "total_metrics_collected": len(metrics),
            "all_metrics": metrics
        }

        return coverage >= 50  # Au moins 50% des métriques attendues

    async def create_memory_entry(self, session: aiohttp.ClientSession,
                                  content: str, context: Dict = None) -> Dict:
        """Crée une entrée mémoire"""
        payload = {
            "content": content,
            "metadata": context or {},
            "timestamp": datetime.now().isoformat()
        }

        async with session.post(f"{MEMORY_URL}/store", json=payload) as resp:
            if resp.status in [200, 201]:
                return await resp.json()
            else:
                return {"error": f"Status {resp.status}", "content": content}

    async def stress_test_memories(self):
        """Étape 2: Stress test avec 100+ messages"""
        print("\n" + "="*80)
        print("🧪 STRESS TEST AVEC 100+ MESSAGES")
        print("="*80)

        # Générer des messages variés avec patterns répétitifs pour tester le clustering
        message_templates = [
            "L'utilisateur aime la programmation en {}",
            "Discussion sur {} et son importance",
            "Préférence pour {} dans le développement",
            "Question à propos de {} et ses applications",
            "Réflexion sur l'avenir de {}",
            "Analyse de {} dans le contexte actuel",
            "Comparaison entre {} et d'autres technologies",
            "Apprentissage de {} pour débutants",
            "Tutoriel avancé sur {}",
            "Débug d'un problème avec {}"
        ]

        topics = [
            "Python", "Redis", "Prometheus", "FastAPI", "Docker",
            "Kubernetes", "Machine Learning", "AI", "Cloud Computing",
            "DevOps", "Microservices", "API Design", "Testing",
            "CI/CD", "Monitoring"
        ]

        messages = []
        for i, topic in enumerate(topics * 8):  # 120 messages
            template = message_templates[i % len(message_templates)]
            messages.append(template.format(topic))

        # Métriques de départ
        metrics_before = await self.fetch_prometheus_metrics()

        # Exécution du stress test
        start = time.time()
        async with aiohttp.ClientSession() as session:
            tasks = [self.create_memory_entry(session, msg, {"index": i})
                    for i, msg in enumerate(messages)]

            results = await asyncio.gather(*tasks, return_exceptions=True)

        duration = time.time() - start

        # Métriques après
        await asyncio.sleep(1)  # Attendre que les métriques se mettent à jour
        metrics_after = await self.fetch_prometheus_metrics()

        # Analyser les résultats
        successful = sum(1 for r in results if isinstance(r, dict) and 'error' not in r)
        failed = len(results) - successful
        throughput = len(messages) / duration

        print(f"\n📝 Messages envoyés: {len(messages)}")
        print(f"✓ Succès: {successful}")
        print(f"✗ Échecs: {failed}")
        print(f"⏱️  Durée totale: {duration:.2f}s")
        print(f"🚀 Débit: {throughput:.2f} msg/s")

        # Comparaison des métriques
        print(f"\n📊 Évolution des métriques:")
        for key in metrics_before:
            if key in metrics_after:
                delta = metrics_after[key] - metrics_before[key]
                if delta != 0:
                    print(f"  {key}: {metrics_before[key]} → {metrics_after[key]} (+{delta})")

        self.results["stress_test"] = {
            "messages_sent": len(messages),
            "successful": successful,
            "failed": failed,
            "duration_seconds": duration,
            "throughput_msg_per_sec": throughput,
            "metrics_delta": {k: metrics_after.get(k, 0) - metrics_before.get(k, 0)
                            for k in metrics_before if k in metrics_after}
        }

        return successful >= len(messages) * 0.8  # Au moins 80% de succès

    async def test_concept_clustering(self):
        """Étape 3: Tester le clustering automatique de concepts similaires"""
        print("\n" + "="*80)
        print("🔍 TEST DU CLUSTERING AUTOMATIQUE DE CONCEPTS")
        print("="*80)

        # Créer des clusters de concepts similaires
        concept_groups = {
            "python_dev": [
                "J'adore coder en Python",
                "Python est mon langage préféré",
                "Je développe principalement en Python",
                "La programmation Python est géniale",
                "J'utilise Python quotidiennement"
            ],
            "redis_cache": [
                "Redis est excellent pour le cache",
                "J'utilise Redis pour la mise en cache",
                "Le cache Redis améliore les performances",
                "Redis comme système de cache distribué",
                "Configuration de Redis pour le caching"
            ],
            "monitoring": [
                "Prometheus collecte mes métriques",
                "J'aime surveiller avec Prometheus",
                "Grafana et Prometheus pour le monitoring",
                "Métriques système avec Prometheus",
                "Dashboard de monitoring Prometheus"
            ]
        }

        # Insérer les concepts
        async with aiohttp.ClientSession() as session:
            for group_name, messages in concept_groups.items():
                for msg in messages:
                    await self.create_memory_entry(session, msg, {"concept_group": group_name})

        await asyncio.sleep(2)  # Attendre que les embeddings soient générés

        # Tester la recherche pour chaque groupe
        async with aiohttp.ClientSession() as session:
            cluster_results = {}

            for group_name in concept_groups:
                # Requête qui devrait rappeler tous les concepts du groupe
                test_query = list(concept_groups[group_name])[0]

                async with session.post(f"{MEMORY_URL}/search", json={
                    "query": test_query,
                    "top_k": 10,
                    "threshold": 0.5
                }) as resp:
                    if resp.status == 200:
                        search_results = await resp.json()

                        # Compter combien de résultats appartiennent au même groupe
                        same_group = 0
                        if 'results' in search_results:
                            for result in search_results['results']:
                                meta = result.get('metadata', {})
                                if meta.get('concept_group') == group_name:
                                    same_group += 1

                        cluster_quality = same_group / len(concept_groups[group_name]) * 100
                        cluster_results[group_name] = {
                            "query": test_query,
                            "same_group_found": same_group,
                            "total_in_group": len(concept_groups[group_name]),
                            "cluster_quality_percent": cluster_quality
                        }

                        print(f"\n🎯 Groupe: {group_name}")
                        print(f"  Requête: {test_query[:50]}...")
                        print(f"  Trouvé du même groupe: {same_group}/{len(concept_groups[group_name])}")
                        print(f"  Qualité du cluster: {cluster_quality:.1f}%")

        avg_quality = np.mean([r['cluster_quality_percent'] for r in cluster_results.values()])
        print(f"\n📊 Qualité moyenne du clustering: {avg_quality:.1f}%")

        self.results["clustering"] = {
            "cluster_results": cluster_results,
            "average_quality_percent": avg_quality,
            "total_concepts_tested": sum(len(msgs) for msgs in concept_groups.values())
        }

        return avg_quality >= 60  # Au moins 60% de qualité

    async def test_nexus_contextual_recall(self):
        """Étape 4: Valider le recall contextuel lors d'une conversation Nexus"""
        print("\n" + "="*80)
        print("💬 VALIDATION DU RECALL CONTEXTUEL NEXUS")
        print("="*80)

        # Créer un contexte conversationnel
        conversation_context = [
            ("user", "Je travaille sur un projet d'IA avec Python et Redis"),
            ("assistant", "C'est une excellente combinaison ! Python pour le ML et Redis pour le cache."),
            ("user", "Comment optimiser les performances avec Redis ?"),
            ("assistant", "Utilisez le pipelining, les connexions pool et l'expiration des clés."),
            ("user", "J'ai aussi besoin de monitoring"),
            ("assistant", "Je recommande Prometheus et Grafana pour surveiller Redis."),
        ]

        # Stocker le contexte
        async with aiohttp.ClientSession() as session:
            for i, (role, content) in enumerate(conversation_context):
                await self.create_memory_entry(session, content, {
                    "role": role,
                    "turn": i,
                    "conversation_id": "test_nexus_001"
                })

        await asyncio.sleep(2)

        # Questions qui nécessitent le recall du contexte
        recall_tests = [
            {
                "query": "Quel langage j'utilise pour mon projet d'IA ?",
                "expected_keywords": ["Python", "projet", "IA"],
                "context_turn": 0
            },
            {
                "query": "Quelles étaient tes recommandations pour Redis ?",
                "expected_keywords": ["pipeline", "pool", "expiration", "clé"],
                "context_turn": 3
            },
            {
                "query": "Quels outils de monitoring as-tu suggérés ?",
                "expected_keywords": ["Prometheus", "Grafana", "Redis"],
                "context_turn": 5
            }
        ]

        async with aiohttp.ClientSession() as session:
            recall_scores = []

            for test in recall_tests:
                # Recherche mémoire contextuelle
                async with session.post(f"{MEMORY_URL}/search", json={
                    "query": test["query"],
                    "top_k": 5,
                    "threshold": 0.3,
                    "filters": {"conversation_id": "test_nexus_001"}
                }) as resp:
                    if resp.status == 200:
                        search_results = await resp.json()

                        # Vérifier si les mots-clés attendus sont dans les résultats
                        results_text = " ".join([
                            r.get('content', '') for r in search_results.get('results', [])
                        ]).lower()

                        keywords_found = sum(
                            1 for kw in test["expected_keywords"]
                            if kw.lower() in results_text
                        )

                        recall_score = keywords_found / len(test["expected_keywords"]) * 100
                        recall_scores.append(recall_score)

                        print(f"\n🔍 Question: {test['query']}")
                        print(f"  Mots-clés trouvés: {keywords_found}/{len(test['expected_keywords'])}")
                        print(f"  Score de recall: {recall_score:.1f}%")
                        print(f"  Résultats: {len(search_results.get('results', []))} entrées")

        avg_recall = np.mean(recall_scores) if recall_scores else 0
        print(f"\n📊 Score moyen de recall contextuel: {avg_recall:.1f}%")

        self.results["recall_contextual"] = {
            "tests_performed": len(recall_tests),
            "recall_scores": recall_scores,
            "average_recall_percent": avg_recall,
            "conversation_turns": len(conversation_context)
        }

        return avg_recall >= 50  # Au moins 50% de recall

    async def run_all_validations(self):
        """Exécuter toute la suite de validation"""
        print("\n" + "="*80)
        print("🚀 DÉMARRAGE DE LA SUITE DE VALIDATION MÉMOIRE PHASE 3")
        print(f"⏰ Heure de début: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)

        # Exécuter chaque validation
        validations = [
            ("Prometheus Metrics", self.validate_prometheus_metrics),
            ("Stress Test 100+", self.stress_test_memories),
            ("Concept Clustering", self.test_concept_clustering),
            ("Nexus Contextual Recall", self.test_nexus_contextual_recall)
        ]

        validation_results = {}

        for name, validation_func in validations:
            try:
                success = await validation_func()
                validation_results[name] = "✓ PASS" if success else "✗ FAIL"
            except Exception as e:
                print(f"\n❌ Erreur lors de {name}: {str(e)}")
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
        success_rate = passed / total * 100

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

        report_path = f"reports/memory_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Rapport sauvegardé: {report_path}")

        return success_rate >= 75  # Au moins 75% de validations passées


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
