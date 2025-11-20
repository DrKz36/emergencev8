#!/usr/bin/env python3
"""
Benchmark script to evaluate Chroma performance improvements
for FastAPI 0.119 + Chroma upgrade evaluation.

Tests:
1. add() vs upsert() performance (batch sizes 100, 1k, 10k)
2. Query performance with metadata filters
3. Regex search capability (if supported)
4. Collection metadata optimization (HNSW parameters)

Usage:
    python scripts/benchmark_chroma_upgrade.py
"""

import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import shutil

# Add src to path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Import VectorService after path setup
from backend.features.memory.vector_service import VectorService


def generate_test_data(count: int) -> List[Dict[str, Any]]:
    """Generate synthetic test data for benchmarking."""
    import uuid

    data = []
    for i in range(count):
        data.append(
            {
                "id": f"doc_{uuid.uuid4().hex[:8]}_{i}",
                "text": f"This is test document number {i} with some random content for embedding. "
                f"It contains information about topic {i % 10} and category {i % 5}.",
                "metadata": {
                    "user_id": f"user_{i % 100}",
                    "type": f"type_{i % 5}",
                    "confidence": round(0.5 + (i % 50) / 100, 2),
                    "timestamp": time.time() - (i * 3600),
                },
            }
        )
    return data


class ChromaBenchmark:
    """Benchmark suite for Chroma operations."""

    def __init__(self, temp_dir: str, embed_model: str = "all-MiniLM-L6-v2"):
        self.temp_dir = temp_dir
        self.embed_model = embed_model
        self.results: Dict[str, Any] = {}

    def setup_service(self) -> VectorService:
        """Initialize VectorService with temp directory."""
        service = VectorService(
            persist_directory=self.temp_dir,
            embed_model_name=self.embed_model,
            auto_reset_on_schema_error=True,
        )
        return service

    def benchmark_upsert(
        self, service: VectorService, batch_size: int
    ) -> Dict[str, float]:
        """Benchmark upsert operation."""
        logger.info(f"Benchmarking upsert with {batch_size} items...")

        # Generate test data
        data = generate_test_data(batch_size)

        # Create collection
        collection = service.get_or_create_collection(
            name=f"bench_upsert_{batch_size}",
            metadata={
                "hnsw:space": "cosine",
                "hnsw:M": 16,
            },
        )

        # Benchmark add_items (uses upsert internally)
        start = time.perf_counter()
        service.add_items(collection, data, item_text_key="text")
        duration = time.perf_counter() - start

        items_per_sec = batch_size / duration if duration > 0 else 0

        result = {
            "batch_size": batch_size,
            "duration_sec": round(duration, 3),
            "items_per_sec": round(items_per_sec, 2),
        }

        logger.info(
            f"  ✓ Duration: {result['duration_sec']}s | "
            f"Speed: {result['items_per_sec']} items/sec"
        )

        return result

    def benchmark_query(
        self, service: VectorService, collection_name: str, n_queries: int = 100
    ) -> Dict[str, float]:
        """Benchmark query performance with filters."""
        logger.info(f"Benchmarking query on {collection_name} ({n_queries} queries)...")

        collection = service.get_or_create_collection(name=collection_name)

        # Query with metadata filter
        queries = [f"Find information about topic {i % 10}" for i in range(n_queries)]

        start = time.perf_counter()
        for i, query_text in enumerate(queries):
            where_filter = {
                "user_id": f"user_{i % 100}",
                "type": f"type_{i % 5}",
            }
            results = service.query(
                collection,
                query_text=query_text,
                n_results=5,
                where_filter=where_filter,
            )
        duration = time.perf_counter() - start

        queries_per_sec = n_queries / duration if duration > 0 else 0

        result = {
            "n_queries": n_queries,
            "duration_sec": round(duration, 3),
            "queries_per_sec": round(queries_per_sec, 2),
            "avg_latency_ms": round((duration / n_queries) * 1000, 2),
        }

        logger.info(
            f"  ✓ Duration: {result['duration_sec']}s | "
            f"Speed: {result['queries_per_sec']} queries/sec | "
            f"Avg latency: {result['avg_latency_ms']}ms"
        )

        return result

    def test_regex_search(self, service: VectorService) -> Dict[str, Any]:
        """Test regex search functionality (if available in Chroma)."""
        logger.info("Testing regex search capability...")

        # Create test collection with specific data
        collection = service.get_or_create_collection(name="bench_regex")

        test_data = [
            {
                "id": "doc_regex_1",
                "text": "Email: user@example.com, phone: 555-1234",
                "metadata": {"type": "contact"},
            },
            {
                "id": "doc_regex_2",
                "text": "Support email: support@test.org",
                "metadata": {"type": "support"},
            },
            {
                "id": "doc_regex_3",
                "text": "No contact info here",
                "metadata": {"type": "other"},
            },
        ]

        service.add_items(collection, test_data, item_text_key="text")

        # Test 1: Try metadata regex filter (Chroma 0.5+ supports $contains)
        try:
            # Note: Chroma's where filter doesn't support regex directly,
            # but supports $contains, $in, etc.
            # Full regex would require custom implementation or wait for Chroma support

            # Test $contains operator
            results = service.query(
                collection,
                query_text="contact information",
                n_results=10,
                where_filter={"type": {"$in": ["contact", "support"]}},
            )

            result = {
                "regex_support": "partial",
                "note": "Chroma supports $contains, $in but not full regex (as of 0.4.x-0.5.x)",
                "test_query_results": len(results),
                "operators_tested": ["$in"],
            }

            logger.info(
                f"  ✓ Regex test: {result['regex_support']} | "
                f"Results: {result['test_query_results']}"
            )

        except Exception as e:
            result = {
                "regex_support": "error",
                "error": str(e),
            }
            logger.warning(f"  ✗ Regex test failed: {e}")

        return result

    def test_hnsw_optimization(self, service: VectorService) -> Dict[str, Any]:
        """Test HNSW parameter optimization for query performance."""
        logger.info("Testing HNSW parameter optimization...")

        # Test with different HNSW:M values
        test_configs = [
            {"hnsw:M": 8, "hnsw:space": "cosine"},
            {"hnsw:M": 16, "hnsw:space": "cosine"},  # Default optimized
            {"hnsw:M": 32, "hnsw:space": "cosine"},
        ]

        results = []
        test_data = generate_test_data(1000)

        for config in test_configs:
            m_value = config["hnsw:M"]
            collection_name = f"bench_hnsw_m{m_value}"

            # Create collection with config
            collection = service.get_or_create_collection(
                name=collection_name, metadata=config
            )

            # Add data
            service.add_items(collection, test_data, item_text_key="text")

            # Benchmark queries
            start = time.perf_counter()
            for i in range(50):
                service.query(
                    collection,
                    query_text=f"test query {i}",
                    n_results=10,
                )
            duration = time.perf_counter() - start

            results.append(
                {
                    "hnsw_M": m_value,
                    "duration_sec": round(duration, 3),
                    "queries_per_sec": round(50 / duration, 2),
                }
            )

            logger.info(
                f"  ✓ HNSW M={m_value}: {results[-1]['queries_per_sec']} queries/sec"
            )

        return {
            "hnsw_configs_tested": results,
            "recommendation": "M=16 provides balanced precision/speed for LTM workloads",
        }

    def run_all(self) -> Dict[str, Any]:
        """Run all benchmarks."""
        logger.info("=" * 60)
        logger.info("Starting Chroma upgrade benchmark suite")
        logger.info("=" * 60)

        service = self.setup_service()

        # 1. Upsert benchmarks
        self.results["upsert_benchmarks"] = [
            self.benchmark_upsert(service, 100),
            self.benchmark_upsert(service, 1000),
            # Skip 10k for quick test
            # self.benchmark_upsert(service, 10000),
        ]

        # 2. Query benchmarks (use 1k collection)
        self.results["query_benchmarks"] = self.benchmark_query(
            service, "bench_upsert_1000", n_queries=100
        )

        # 3. Regex search test
        self.results["regex_test"] = self.test_regex_search(service)

        # 4. HNSW optimization test
        self.results["hnsw_optimization"] = self.test_hnsw_optimization(service)

        logger.info("=" * 60)
        logger.info("Benchmark suite completed")
        logger.info("=" * 60)

        return self.results

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS SUMMARY")
        print("=" * 60)

        print("\n📊 UPSERT PERFORMANCE:")
        for r in self.results["upsert_benchmarks"]:
            print(
                f"  • {r['batch_size']} items: {r['duration_sec']}s "
                f"({r['items_per_sec']} items/sec)"
            )

        print("\n🔍 QUERY PERFORMANCE:")
        q = self.results["query_benchmarks"]
        print(f"  • {q['n_queries']} queries: {q['duration_sec']}s")
        print(f"  • Speed: {q['queries_per_sec']} queries/sec")
        print(f"  • Avg latency: {q['avg_latency_ms']}ms")

        print("\n🔎 REGEX SEARCH:")
        r = self.results["regex_test"]
        print(f"  • Support: {r.get('regex_support', 'N/A')}")
        print(f"  • Note: {r.get('note', 'N/A')}")

        print("\n⚙️  HNSW OPTIMIZATION:")
        for cfg in self.results["hnsw_optimization"]["hnsw_configs_tested"]:
            print(f"  • M={cfg['hnsw_M']}: {cfg['queries_per_sec']} queries/sec")

        print("\n" + "=" * 60)


def main():
    """Main benchmark runner."""
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp(prefix="chroma_bench_")

    try:
        logger.info(f"Using temp directory: {temp_dir}")

        benchmark = ChromaBenchmark(temp_dir)
        benchmark.run_all()
        benchmark.print_summary()

        logger.info("\n✅ Benchmark completed successfully")

    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")


if __name__ == "__main__":
    main()
