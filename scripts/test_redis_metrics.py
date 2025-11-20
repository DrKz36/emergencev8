"""
Script de test pour valider:
1. Connexion Redis
2. Cache de mémoire consolidée avec Redis
3. Métriques Prometheus Phase 3

Usage:
    python scripts/test_redis_metrics.py
"""

import sys
import os

# Fix encoding pour Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Ajouter le répertoire src au PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_redis_connection():
    """Test 1: Connexion Redis"""
    print("=" * 60)
    print("TEST 1: Connexion Redis")
    print("=" * 60)

    try:
        import redis

        print("✓ Module redis importé")

        # Tester connexion
        r = redis.from_url(
            "redis://localhost:6379/0", decode_responses=True, socket_connect_timeout=2
        )
        r.ping()
        print("✓ Redis PING réussi")

        # Tester set/get
        r.set("test_key", "test_value")
        value = r.get("test_key")
        assert value == "test_value", f"Expected 'test_value', got '{value}'"
        print("✓ Redis SET/GET fonctionnel")

        # Nettoyer
        r.delete("test_key")
        print("✓ Test nettoyé")

        print("\n✅ Test Redis: RÉUSSI\n")
        return True

    except ImportError:
        print("❌ Module redis non installé. Installer avec: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Erreur connexion Redis: {e}")
        print("   Assurez-vous que Redis tourne: docker ps | findstr redis")
        return False


def test_rag_cache_with_redis():
    """Test 2: RAGCache avec Redis"""
    print("=" * 60)
    print("TEST 2: RAGCache avec Redis")
    print("=" * 60)

    try:
        from backend.features.chat.rag_cache import create_rag_cache

        # Créer cache avec Redis
        cache = create_rag_cache(redis_url="redis://localhost:6379/0", ttl_seconds=60)

        print(f"✓ RAGCache créé: {cache.get_stats()}")

        # Tester set/get
        cache.set(
            query_text="test_query",
            where_filter={"user_id": "test_user"},
            agent_id="test_agent",
            doc_hits=[{"content": "test_content"}],
            rag_sources=[],
            selected_doc_ids=None,
        )
        print("✓ Cache SET réussi")

        result = cache.get(
            query_text="test_query",
            where_filter={"user_id": "test_user"},
            agent_id="test_agent",
            selected_doc_ids=None,
        )

        assert result is not None, "Cache GET devrait retourner un résultat"
        assert len(result.get("doc_hits", [])) == 1, "Devrait avoir 1 doc_hit"
        print("✓ Cache GET réussi")

        print("\n✅ Test RAGCache: RÉUSSI\n")
        return True

    except Exception as e:
        print(f"❌ Erreur RAGCache: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_prometheus_metrics():
    """Test 3: Métriques Prometheus Phase 3"""
    print("=" * 60)
    print("TEST 3: Métriques Prometheus Phase 3")
    print("=" * 60)

    try:
        from backend.features.chat import rag_metrics

        # Vérifier que les métriques existent
        metrics_to_check = [
            "memory_temporal_queries_total",
            "memory_temporal_concepts_found_total",
            "memory_temporal_search_duration_seconds",
            "memory_temporal_context_size_bytes",
            "memory_temporal_cache_hit_rate",
        ]

        for metric_name in metrics_to_check:
            assert hasattr(rag_metrics, metric_name), (
                f"Métrique {metric_name} manquante"
            )
            print(f"✓ Métrique {metric_name} présente")

        # Tester fonctions helper
        rag_metrics.record_temporal_query(True)
        print("✓ record_temporal_query() fonctionnel")

        rag_metrics.record_temporal_concepts_found(4)
        print("✓ record_temporal_concepts_found() fonctionnel")

        rag_metrics.record_temporal_search_duration(0.175)
        print("✓ record_temporal_search_duration() fonctionnel")

        rag_metrics.record_temporal_context_size(2048)
        print("✓ record_temporal_context_size() fonctionnel")

        rag_metrics.update_temporal_cache_hit_rate(35.5)
        print("✓ update_temporal_cache_hit_rate() fonctionnel")

        print("\n✅ Test Métriques Prometheus: RÉUSSI\n")
        return True

    except Exception as e:
        print(f"❌ Erreur Métriques: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Exécute tous les tests"""
    print("\n" + "=" * 60)
    print("TESTS REDIS & MÉTRIQUES PROMETHEUS - PHASE 3")
    print("=" * 60 + "\n")

    results = []

    # Test 1: Redis
    results.append(("Redis Connection", test_redis_connection()))

    # Test 2: RAGCache
    results.append(("RAGCache with Redis", test_rag_cache_with_redis()))

    # Test 3: Métriques
    results.append(("Prometheus Metrics", test_prometheus_metrics()))

    # Résumé
    print("=" * 60)
    print("RÉSUMÉ DES TESTS")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!\n")
        print("Prochaines étapes:")
        print("1. Redémarrer le backend avec: pwsh -File scripts/run-backend.ps1")
        print("2. Vérifier les logs: [RAG Cache] Connected to Redis")
        print("3. Tester une question temporelle")
        print(
            "4. Consulter /metrics: curl http://localhost:8000/metrics | grep memory_temporal"
        )
        return 0
    else:
        print("\n❌ CERTAINS TESTS ONT ÉCHOUÉ\n")
        print("Vérifier:")
        print("1. Redis tourne: docker ps | findstr redis")
        print("2. Module redis installé: pip install redis")
        print("3. Variables .env configurées")
        return 1


if __name__ == "__main__":
    sys.exit(main())
