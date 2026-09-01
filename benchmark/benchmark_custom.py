#!/usr/bin/env python3
"""
Custom Engram Alpha Benchmarks:
Tests: 4-Way RRF Hybrid Search, Apple AMX / C-BLAS Vector Math, Recursive CTE Graph Traversal, and Concurrency.
"""

import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

bench_dir = Path.home() / "engram-benchmarks"
bench_dir.mkdir(parents=True, exist_ok=True)
os.environ["ENGRAM_DB_PATH"] = str(bench_dir / "custom_benchmark.sqlite")

from engram.core import init_db, get_db
from engram.server import save_memory, search_memory, save_graph_relation, query_graph
from engram.amx import amx_batch_cosine_similarity, get_acceleration_tier

def benchmark_4way_rrf_vs_fts():
    db_file = Path(os.environ["ENGRAM_DB_PATH"])
    if db_file.exists():
        db_file.unlink()
    init_db()

    test_queries = [
        "Python testing framework and subagent gauntlet",
        "SQLite WAL database memory and zero split-brain",
        "ACT-R power-law auto-decay mechanism with spaced practice",
        "FTS5 trigram full-text keyword search indexing",
        "LLM agent memory graph topology with bi-temporal validity",
    ]

    for i, q in enumerate(test_queries):
        save_memory(f"Memory {i}: {q} with architectural context and invariants.", category="benchmark", importance=8, project="custom_bench")

    # Benchmark 1,000 hybrid searches
    start = time.perf_counter()
    for i in range(1000):
        search_memory(test_queries[i % len(test_queries)], limit=5, hybrid=True, project="custom_bench")
    elapsed_rrf = time.perf_counter() - start

    print(f"✅ 1,000 4-Way RRF Hybrid Searches: {elapsed_rrf:.4f}s ({1000/elapsed_rrf:.1f} queries/sec, {elapsed_rrf/1000*1000:.2f}ms/query)")

def benchmark_amx_coprocessor():
    tier = get_acceleration_tier()
    print(f"Active Hardware Tier: {tier}")
    query = [1.0 / (384 ** 0.5)] * 384
    matrix = [[(i % 10) * 0.1 for _ in range(384)] for i in range(50000)]

    start = time.perf_counter()
    scores = amx_batch_cosine_similarity(query, matrix)
    elapsed = time.perf_counter() - start

    print(f"✅ 50,000 Vector Cosine Evaluations: {elapsed:.4f}s ({50000/elapsed:,.1f} vectors/sec)")

def benchmark_recursive_cte_graph():
    # Build a 20-node chain
    for i in range(20):
        save_graph_relation(f"Node_{i}", "links_to", f"Node_{i+1}", project="custom_bench")

    start = time.perf_counter()
    for _ in range(500):
        query_graph("Node_0", depth=4, project="custom_bench")
    elapsed = time.perf_counter() - start

    print(f"✅ 500 Recursive CTE 4-Hop Graph Traversals: {elapsed:.4f}s ({500/elapsed:.1f} traversals/sec)")

if __name__ == "__main__":
    print("=" * 60)
    print("⚡ ENGRAM ALPHA CUSTOM ARCHITECTURE BENCHMARK")
    print("=" * 60)
    benchmark_4way_rrf_vs_fts()
    benchmark_amx_coprocessor()
    benchmark_recursive_cte_graph()
    print("=" * 60)
