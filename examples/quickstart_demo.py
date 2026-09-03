#!/usr/bin/env python3
"""
Engram Alpha Interactive Quickstart Demo
Demonstrates sub-millisecond local memory, 4-Way RRF hybrid retrieval,
and bi-temporal knowledge graph capabilities in under 5 seconds.
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Create temporary isolated database
tmp_dir = tempfile.mkdtemp()
db_path = os.path.join(tmp_dir, "demo_memory.sqlite")
os.environ["ENGRAM_DB_PATH"] = db_path

from engram.core import init_db
from engram.server import (
    save_memory,
    search_memory,
    save_graph_relation,
    query_graph,
    visualize_graph,
    get_stats,
)

def print_banner(text):
    print("\n" + "=" * 65)
    print(f"🚀 {text}")
    print("=" * 65)

def main():
    print_banner("Engram Alpha Quickstart: Sovereign AI Memory Engine")
    init_db(force=True)
    
    # 1. System Diagnostics
    stats = get_stats()
    print(stats.strip())

    # 2. Saving High-Priority Technical Decisions
    print_banner("Step 1: Storing Technical Memories & Architecture Decisions")
    memories = [
        ("Authentication microservice standardized on Ed25519 JWT signatures with 15-minute TTL.", "architecture", 9),
        ("Database connection pool configured for maximum 25 connections to avoid Postgres starvation.", "infrastructure", 8),
        ("Billing service uses Stripe webhook endpoint with signature verification at /api/v1/stripe/webhook.", "security", 9),
        ("Developer prefer dark mode and vim keybindings across all development environments.", "preferences", 5),
    ]
    
    for content, cat, imp in memories:
        t0 = time.perf_counter()
        res = save_memory(content, category=cat, importance=imp, project="core_api")
        dt = (time.perf_counter() - t0) * 1000
        print(f"  [SAVED in {dt:.2f}ms] {content[:60]}...")

    # 3. Storing Bi-temporal Knowledge Graph Relations
    print_banner("Step 2: Constructing Bi-Temporal Knowledge Graph Triples")
    relations = [
        ("AuthService", "secures", "BillingGateway"),
        ("BillingGateway", "depends_on", "PostgresDB"),
        ("PostgresDB", "monitored_by", "Prometheus"),
        ("AuthService", "issues_token_to", "FrontendClient"),
    ]
    for s, r, t in relations:
        save_graph_relation(s, r, t, weight=1.0, project="core_api")
        print(f"  [GRAPH TRIPLE] ({s}) ───[{r}]───► ({t})")

    # 4. Executing 4-Way RRF Hybrid Search (Exact Match vs Semantic Match)
    print_banner("Step 3: 4-Way RRF Hybrid Retrieval (Exact Token vs Semantic)")
    
    # Test A: Exact token search (FTS5 trigram power)
    query_exact = "Ed25519 15-minute TTL"
    t0 = time.perf_counter()
    res_exact = search_memory(query_exact, limit=2, hybrid=True, project="core_api")
    dt_exact = (time.perf_counter() - t0) * 1000
    print(f"\n🔍 Query A (Exact Token): '{query_exact}' [{dt_exact:.2f}ms]")
    print(res_exact.strip())

    # Test B: Pure semantic conceptual search (Zero lexical overlap)
    query_semantic = "how do we protect financial payment processing transactions?"
    t0 = time.perf_counter()
    res_semantic = search_memory(query_semantic, limit=2, hybrid=True, project="core_api")
    dt_semantic = (time.perf_counter() - t0) * 1000
    print(f"\n🔍 Query B (Conceptual Semantic): '{query_semantic}' [{dt_semantic:.2f}ms]")
    print(res_semantic.strip())

    # 5. Multi-Hop Graph Traversal
    print_banner("Step 4: Recursive Multi-Hop Knowledge Graph Traversal")
    t0 = time.perf_counter()
    graph_res = query_graph("AuthService", depth=2, project="core_api")
    dt_graph = (time.perf_counter() - t0) * 1000
    print(f"🕸️ Multi-Hop Traversal from 'AuthService' [{dt_graph:.2f}ms]:")
    print(graph_res.strip())

    # 6. Mermaid.js Topology Rendering
    print_banner("Step 5: Visualizing Topology (Mermaid.js)")
    diagram = visualize_graph("AuthService", depth=2, project="core_api")
    print(diagram.strip())

    print("\n" + "=" * 65)
    print("✅ Engram Alpha Quickstart Completed Successfully!")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
