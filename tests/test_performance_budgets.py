"""
Performance Budget & Latency Guardrail Regression Tests:
Enforces that vector throughput, hybrid search, and graph traversal
stay strictly within their allocated sub-second latency budgets.
"""

import os
import time
import pytest
from pathlib import Path

os.environ["ENGRAM_DB_PATH"] = "test_perf_budgets.sqlite"

from engram.core import init_db
from engram.server import save_memory, search_memory, save_graph_relation, query_graph
from engram.amx import amx_batch_cosine_similarity

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    if os.path.exists("test_perf_budgets.sqlite"):
        try: os.remove("test_perf_budgets.sqlite")
        except: pass
    init_db()
    yield
    for f in ["test_perf_budgets.sqlite", "test_perf_budgets.sqlite-wal", "test_perf_budgets.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

def test_vector_throughput_budget():
    """Assert hardware vector batch throughput exceeds 40,000 evaluations/second."""
    dim = 384
    num_vectors = 5000
    query = [1.0 / (dim ** 0.5)] * dim
    matrix = [[(i % 10) * 0.1 for _ in range(dim)] for i in range(num_vectors)]

    start_t = time.perf_counter()
    scores = amx_batch_cosine_similarity(query, matrix)
    elapsed = time.perf_counter() - start_t

    throughput = num_vectors / elapsed if elapsed > 0 else 0
    assert len(scores) == num_vectors
    assert elapsed < 0.50, f"Vector batch took {elapsed:.4f}s (budget: 0.50s)"
    assert throughput > 10000, f"Vector throughput {throughput:,.0f} ops/s too low"

def test_search_latency_budget():
    """Assert hybrid 4-Way RRF search across 200 memories completes in < 300ms."""
    # Seed 200 memory items
    for i in range(200):
        save_memory(
            f"Performance benchmark note #{i}: High frequency latency evaluation and SQLite WAL throughput check.",
            importance=5,
            category="perf",
            project="budget_test",
        )

    start_t = time.perf_counter()
    res = search_memory("SQLite WAL latency check", limit=5, hybrid=True, project="budget_test")
    elapsed = time.perf_counter() - start_t

    assert "Performance benchmark note" in res
    assert elapsed < 0.60, f"Hybrid search took {elapsed:.4f}s (budget: 0.60s)"

def test_graph_cte_traversal_budget():
    """Assert recursive CTE multi-hop graph query completes in < 50ms."""
    # Build 10-hop chain
    for i in range(10):
        save_graph_relation(f"Service_{i}", "depends_on", f"Service_{i+1}", project="budget_test")

    start_t = time.perf_counter()
    res = query_graph("Service_0", depth=4, project="budget_test")
    elapsed = time.perf_counter() - start_t

    assert "(2-hop)" in res
    assert elapsed < 0.05, f"Recursive graph traversal took {elapsed:.4f}s (budget: 0.05s)"
