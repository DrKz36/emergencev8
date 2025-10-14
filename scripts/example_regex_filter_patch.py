#!/usr/bin/env python3
"""
Example patch: Add regex filtering capability to hybrid_retriever.py

This demonstrates how to add post-query regex filtering to work around
Chroma's limited native regex support (as of 0.4-0.5.x).

Usage:
    1. Review this patch
    2. Manually apply changes to src/backend/features/memory/hybrid_retriever.py
    3. Test with examples below
"""
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


# ===== NEW FUNCTION TO ADD =====
def regex_filter_results(
    results: List[Dict[str, Any]],
    field_path: str,
    pattern: str,
    flags: int = re.IGNORECASE
) -> List[Dict[str, Any]]:
    """
    Apply regex filter to query results (post-query filtering).

    Args:
        results: List of result dicts from VectorService.query()
        field_path: Dot-separated path to field (e.g., "metadata.email")
        pattern: Regex pattern to match
        flags: re flags (default: re.IGNORECASE)

    Returns:
        Filtered results where field matches pattern

    Examples:
        # Filter by email domain
        results = vector_service.query(collection, "user emails", n_results=100)
        filtered = regex_filter_results(results, "metadata.email", r".*@example\.com")

        # Filter by phone format
        filtered = regex_filter_results(results, "text", r"\d{3}-\d{3}-\d{4}")

        # Filter by user_id pattern
        filtered = regex_filter_results(results, "metadata.user_id", r"^user_[0-9]+$")
    """
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        return results

    filtered: List[Dict[str, Any]] = []

    for result in results:
        # Navigate nested field path
        value = result
        for key in field_path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break

        # Apply regex match
        if value is not None and regex.search(str(value)):
            filtered.append(result)

    logger.info(
        f"Regex filter '{pattern}' on '{field_path}': "
        f"{len(results)} → {len(filtered)} results"
    )

    return filtered


# ===== USAGE EXAMPLES =====

def example_1_email_domain_filter():
    """Example: Filter memory entries by email domain."""
    # Simulated vector_service and collection
    from backend.features.memory.vector_service import VectorService

    service = VectorService(
        persist_directory="./data/vector_store",
        embed_model_name="all-MiniLM-L6-v2"
    )
    collection = service.get_or_create_collection("emergence_ltm")

    # Query broadly
    results = service.query(
        collection,
        query_text="user communication preferences",
        n_results=100,
        where_filter={"type": "user_preference"},
    )

    # Apply regex filter for specific email domain
    example_users = regex_filter_results(
        results,
        field_path="metadata.email",
        pattern=r".*@example\.(com|org)"
    )

    print(f"Found {len(example_users)} users from example.com/org")
    return example_users


def example_2_phone_number_extraction():
    """Example: Find entries with phone numbers."""
    from backend.features.memory.vector_service import VectorService

    service = VectorService(
        persist_directory="./data/vector_store",
        embed_model_name="all-MiniLM-L6-v2"
    )
    collection = service.get_or_create_collection("emergence_documents")

    # Query documents
    results = service.query(
        collection,
        query_text="contact information",
        n_results=50,
    )

    # Filter for US phone numbers
    phone_results = regex_filter_results(
        results,
        field_path="text",
        pattern=r"\d{3}[-.]?\d{3}[-.]?\d{4}"
    )

    print(f"Found {len(phone_results)} documents with phone numbers")
    return phone_results


def example_3_advanced_user_id_filter():
    """Example: Filter by complex user_id pattern."""
    from backend.features.memory.vector_service import VectorService

    service = VectorService(
        persist_directory="./data/vector_store",
        embed_model_name="all-MiniLM-L6-v2"
    )
    collection = service.get_or_create_collection("emergence_knowledge")

    # Query knowledge base
    results = service.query(
        collection,
        query_text="technical documentation",
        n_results=100,
    )

    # Filter for test users (user_test_*)
    test_users = regex_filter_results(
        results,
        field_path="metadata.user_id",
        pattern=r"^user_test_\d{3,}$"
    )

    print(f"Found {len(test_users)} entries from test users")
    return test_users


# ===== INTEGRATION EXAMPLE: MemoryAnalyzer =====

class MemoryAnalyzerRegexPatch:
    """
    Example patch for MemoryAnalyzer to add regex search capability.

    Add these methods to src/backend/features/memory/analyzer.py
    """

    async def search_by_regex(
        self,
        collection_name: str,
        query_text: str,
        field_path: str,
        regex_pattern: str,
        n_results: int = 20,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search with regex filtering.

        Args:
            collection_name: "emergence_ltm", "emergence_documents", etc.
            query_text: Semantic query text
            field_path: Field to apply regex (e.g., "metadata.email")
            regex_pattern: Regex pattern
            n_results: Final number of results (after filtering)
            where_filter: Additional metadata filters

        Returns:
            Filtered results

        Example:
            analyzer = MemoryAnalyzer(...)
            results = await analyzer.search_by_regex(
                collection_name="emergence_ltm",
                query_text="user preferences",
                field_path="metadata.email",
                regex_pattern=r".*@example\.com",
                n_results=10,
            )
        """
        # Query with wider results to allow for filtering
        broad_n = n_results * 5  # Over-fetch to compensate for filtering

        # NOTE: Assuming self.vector_service exists in MemoryAnalyzer
        collection = self.vector_service.get_or_create_collection(collection_name)

        results = self.vector_service.query(
            collection,
            query_text=query_text,
            n_results=broad_n,
            where_filter=where_filter,
        )

        # Apply regex filter
        filtered = regex_filter_results(results, field_path, regex_pattern)

        # Return top N after filtering
        return filtered[:n_results]


# ===== PERFORMANCE TESTING =====

def benchmark_regex_filter_performance():
    """Benchmark regex filtering performance."""
    import time
    from backend.features.memory.vector_service import VectorService

    service = VectorService(
        persist_directory="./data/vector_store",
        embed_model_name="all-MiniLM-L6-v2"
    )
    collection = service.get_or_create_collection("bench_regex_perf")

    # Generate test data
    test_data = []
    for i in range(1000):
        test_data.append({
            "id": f"doc_{i}",
            "text": f"Document {i} content",
            "metadata": {
                "email": f"user{i}@{'example' if i % 2 == 0 else 'test'}.com",
                "user_id": f"user_{i}",
            }
        })

    service.add_items(collection, test_data, item_text_key="text")

    # Query all
    results = service.query(collection, "documents", n_results=1000)

    # Benchmark regex filtering
    patterns = [
        (r".*@example\.com", "Email domain"),
        (r"^user_[0-9]{1,3}$", "User ID range"),
        (r"user[5-9][0-9]{2}@.*", "Complex email pattern"),
    ]

    for pattern, desc in patterns:
        start = time.perf_counter()
        filtered = regex_filter_results(results, "metadata.email", pattern)
        duration = time.perf_counter() - start

        print(f"{desc}:")
        print(f"  Pattern: {pattern}")
        print(f"  Results: {len(results)} → {len(filtered)}")
        print(f"  Duration: {duration*1000:.2f}ms")
        print()


# ===== MAIN =====

if __name__ == "__main__":
    print("="*60)
    print("Regex Filter Patch Examples")
    print("="*60)

    print("\n📝 Usage Instructions:")
    print("1. Review the regex_filter_results() function above")
    print("2. Add to src/backend/features/memory/hybrid_retriever.py")
    print("3. Import in MemoryAnalyzer: from .hybrid_retriever import regex_filter_results")
    print("4. Use in search methods as shown in examples")

    print("\n📊 Running benchmark...")
    try:
        benchmark_regex_filter_performance()
    except Exception as e:
        print(f"⚠️  Benchmark failed (expected if vector_store not initialized): {e}")

    print("\n✅ Patch examples completed")
    print("See function docstrings for integration instructions")
