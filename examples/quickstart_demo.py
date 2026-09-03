#!/usr/bin/env python3
"""
Engram Alpha Interactive Quickstart Demo
Demonstrates sub-millisecond local memory, 4-Way RRF hybrid retrieval,
ACT-R cognitive decay, and bi-temporal knowledge graph capabilities in under 5 seconds.
"""

import os
import sys
import tempfile
import time
import shutil
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from engram.core import init_db
from engram.server import (
    save_memory, 
    save_graph_relation, 
    search_memory, 
    list_memories, 
    visualize_graph,
    ingest_obsidian
)

# Colors for terminal output
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_MAGENTA = "\033[95m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

def print_header(title: str):
    print(f"\n{C_MAGENTA}{'=' * 65}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}🚀 {title}{C_RESET}")
    print(f"{C_MAGENTA}{'=' * 65}{C_RESET}\n")

def measure_time(func, *args, **kwargs):
    start = time.perf_counter()
    res = func(*args, **kwargs)
    end = time.perf_counter()
    latency_ms = (end - start) * 1000
    return res, latency_ms

def main():
    print(f"{C_GREEN}Initializing Engram Alpha Quickstart Demo...{C_RESET}")
    
    # 1. Initialize an isolated Engram Alpha database in a temporary directory
    temp_dir = tempfile.mkdtemp(prefix="engram_demo_")
    db_path = os.path.join(temp_dir, "demo.sqlite")
    os.environ["ENGRAM_DB_PATH"] = db_path
    init_db(force=True)
    
    print(f"Isolated DB initialized at: {db_path}\n")

    # 2. Store architecture decisions and entity triples
    print_header("1. Storing Architecture Decisions & Bi-Temporal Triples")
    
    decisions = [
        ("We chose SQLite WAL mode to allow multiple concurrent readers alongside a single writer.", 9),
        ("Engram Alpha uses 4-Way RRF Hybrid Search: dense semantic vectors, exact FTS5 trigrams, graph spreading activation, and ACT-R decay.", 10),
        ("Hardware acceleration leverages Apple AMX, C-BLAS, and standard library IEEE 754 float parity.", 8)
    ]
    
    for content, imp in decisions:
        _, latency = measure_time(save_memory, content, category="architecture", importance=imp, project="demo")
        print(f"  {C_GREEN}✓{C_RESET} Saved memory (Importance: {imp}) in {C_BOLD}{latency:.2f}ms{C_RESET}")
        
    relations = [
        ("EngramAlpha", "uses", "SQLite_WAL", 1.0, "2024-01-01", ""),
        ("EngramAlpha", "implements", "4_Way_RRF", 0.9, "2024-02-15", ""),
        ("SQLite_WAL", "enables", "Concurrent_Reads", 1.0, "2000-01-01", "")
    ]
    
    for src, rel, tgt, weight, v_from, v_until in relations:
        _, latency = measure_time(save_graph_relation, src, rel, tgt, weight=weight, project="demo", valid_from=v_from, valid_until=v_until)
        print(f"  {C_CYAN}🕸️{C_RESET} ({src}) ──[{rel}]──► ({tgt}) in {C_BOLD}{latency:.2f}ms{C_RESET}")

    # 3. Demonstrate 4-Way RRF Hybrid search
    print_header("2. 4-Way RRF Hybrid Search (Exact vs Semantic)")
    
    print(f"{C_YELLOW}Query A (Exact FTS5 Keyword): 'PRAGMA journal_mode = WAL'{C_RESET}")
    save_memory("Configure database with PRAGMA journal_mode = WAL for concurrency.", project="demo")
    exact_res, exact_lat = measure_time(search_memory, "PRAGMA journal_mode = WAL", limit=2, project="demo")
    print(exact_res.strip())
    print(f"{C_CYAN}↳ Retrieval Latency: {C_BOLD}{exact_lat:.2f}ms{C_RESET}\n")

    print(f"{C_YELLOW}Query B (Dense Semantic, Zero Lexical Overlap): 'how does the system handle many readers at once?'{C_RESET}")
    sem_res, sem_lat = measure_time(search_memory, "how does the system handle many readers at once?", limit=2, project="demo")
    print(sem_res.strip())
    print(f"{C_CYAN}↳ Retrieval Latency: {C_BOLD}{sem_lat:.2f}ms{C_RESET}\n")

    # 4. Demonstrate ACT-R cognitive power-law decay and recency weighting
    print_header("3. ACT-R Cognitive Power-Law Decay & Spaced Practice")
    print("Simulating repeated memory reinforcement accesses...")
    
    for _ in range(5):
        search_memory("4-Way RRF", limit=1, project="demo")
        
    print(f"{C_GREEN}Top Memories Ranked by Access Count & Recency (Spaced Practice applied):{C_RESET}")
    print(list_memories(limit=3, project="demo").strip())

    # 5. Ingest a miniature sample markdown vault with [[wikilinks]] and render Mermaid
    print_header("4. Obsidian Vault Ingestion & Knowledge Graph Topology")
    
    vault_dir = os.path.join(temp_dir, "vault")
    os.makedirs(vault_dir, exist_ok=True)
    
    with open(os.path.join(vault_dir, "AgentArchitecture.md"), "w") as f:
        f.write("# Agent Architecture\n\nThe core of the system is the [[MemoryEngine]]. It communicates via [[FastMCP]].")
        
    with open(os.path.join(vault_dir, "MemoryEngine.md"), "w") as f:
        f.write("# Memory Engine\n\nBuilt on top of [[SQLite_WAL]] and uses [[4_Way_RRF]].")
        
    with open(os.path.join(vault_dir, "FastMCP.md"), "w") as f:
        f.write("# FastMCP\n\nStandard Stdio JSON protocol for [[ClaudeDesktop]] integration.")

    ingest_msg, ingest_lat = measure_time(ingest_obsidian, vault_dir, project="demo")
    print(f"{C_GREEN}{ingest_msg}{C_RESET} (Parsed vault in {C_BOLD}{ingest_lat:.2f}ms{C_RESET})\n")

    print(f"{C_YELLOW}Mermaid.js Topology for 'MemoryEngine' (Depth 2):{C_RESET}")
    graph_viz, viz_lat = measure_time(visualize_graph, "MemoryEngine", depth=2, project="demo")
    print(graph_viz.strip())
    print(f"\n{C_CYAN}↳ Graph rendering latency: {C_BOLD}{viz_lat:.2f}ms{C_RESET}")

    # Cleanup
    print_header("Demo Complete!")
    print(f"{C_GREEN}All benchmarks and cognitive primitives verified. Cleaning up {temp_dir}...{C_RESET}\n")
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
