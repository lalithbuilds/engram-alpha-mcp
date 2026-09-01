"""
Engram Alpha CLI (Universal Cross-Platform Architecture)
Full command-line interface for Engram Alpha MCP, Obsidian Ingestion,
Graph Traversal, Autonomous Memory Extraction, and Hardware Benchmarking.
"""

import argparse
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any

from .utils import foolproof_update_json
from .server import (
    save_memory,
    search_memory,
    save_graph_relation,
    query_graph,
    ingest_obsidian,
    extract_and_save_memory,
    consolidate_reflections,
    get_stats,
)
from .amx import (
    is_amx_hardware_available,
    amx_batch_cosine_similarity,
    get_acceleration_tier,
)

def setup_claude_desktop():
    """Auto-configure Claude Desktop configuration file across macOS, Windows, and Linux."""
    if sys.platform == "win32":
        config_path = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "darwin":
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        # Linux
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    def updater(data):
        if not isinstance(data.get("mcpServers"), dict):
            data["mcpServers"] = {}
        data["mcpServers"]["engram-alpha-mcp"] = {
            "command": sys.executable,
            "args": ["-m", "engram.server"],
            "env": {
                "PATH": os.environ.get("PATH", "")
            },
        }

    try:
        foolproof_update_json(str(config_path), updater)
        print(f"✅ Successfully configured Claude Desktop on {sys.platform}.")
        print(f"Path modified: {config_path}")
        print("Please restart Claude Desktop to apply changes.")
    except Exception as e:
        print(f"❌ Failed to setup Claude Desktop: {e}")

def run_hardware_benchmark(num_vectors: int = 10000, dim: int = 384):
    """Benchmark active hardware matrix vector engine across any OS."""
    tier = get_acceleration_tier()
    print(f"\n⚡ Benchmarking Engram Universal Vector Engine ({tier})...")
    print(f"Platform: {sys.platform} ({os.uname().machine if hasattr(os, 'uname') else 'unknown'})")
    print(f"Dataset: {num_vectors:,} candidate vectors ({dim} dimensions each)")

    import random
    query = [random.uniform(-1.0, 1.0) for _ in range(dim)]
    matrix = [[random.uniform(-1.0, 1.0) for _ in range(dim)] for _ in range(num_vectors)]

    start = time.perf_counter()
    scores = amx_batch_cosine_similarity(query, matrix)
    elapsed = time.perf_counter() - start

    qps = num_vectors / elapsed if elapsed > 0 else 0
    print(f"✓ Matrix Cosine Similarity finished in: {elapsed * 1000:.2f} ms")
    print(f"✓ Throughput: {qps:,.0f} vector comparisons/sec")
    print(f"✓ Top result score: {max(scores):.4f}\n")

def main():
    parser = argparse.ArgumentParser(
        prog="engram",
        description="🧠 Engram Alpha: Universal Zero-Dependency Semantic Graph & RRF Memory Engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Save
    p_save = subparsers.add_parser("save", help="Save a memory node")
    p_save.add_argument("content", help="Text content to save")
    p_save.add_argument("--category", default="general", help="Category tag")
    p_save.add_argument("--importance", type=int, default=5, help="Importance level (1-10)")

    # Extract
    p_extract = subparsers.add_parser("extract", help="Autonomous Fact & Graph Triples Extractor")
    p_extract.add_argument("text", help="Text to deconstruct into facts & graph relations")

    # Search
    p_search = subparsers.add_parser("search", help="Search memory with 4-Way RRF + ACT-R")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=5, help="Number of results")

    # Graph
    p_graph = subparsers.add_parser("graph", help="Save a knowledge graph relation")
    p_graph.add_argument("source", help="Subject entity")
    p_graph.add_argument("relation", help="Predicate relation (e.g. uses, links_to)")
    p_graph.add_argument("target", help="Object entity")
    p_graph.add_argument("--weight", type=float, default=1.0, help="Edge weight")

    # Query Graph
    p_qgraph = subparsers.add_parser("query-graph", help="Query graph relations for an entity")
    p_qgraph.add_argument("node", help="Node name to query")
    p_qgraph.add_argument("--depth", type=int, default=1, help="Hop depth (1 or 2)")

    # Reflect
    p_reflect = subparsers.add_parser("reflect", help="Episodic Reflection & Synthesis Agent")
    p_reflect.add_argument("topic", help="Topic to synthesize into durable insights")

    # Ingest Obsidian
    p_ingest = subparsers.add_parser("ingest-obsidian", help="Ingest an Obsidian vault")
    p_ingest.add_argument("vault_path", help="Path to Obsidian vault directory")

    # Stats
    subparsers.add_parser("stats", help="Show system statistics")

    # Benchmark
    p_bench = subparsers.add_parser("benchmark", help="Run hardware coprocessor benchmark")
    p_bench.add_argument("--vectors", type=int, default=10000, help="Number of test vectors")

    # Setup
    subparsers.add_parser("setup", help="Auto-configure Claude Desktop")

    args = parser.parse_args()

    if args.command == "save":
        res = save_memory(args.content, category=args.category, importance=args.importance)
        print(res)
    elif args.command == "extract":
        res = extract_and_save_memory(args.text)
        print(res)
    elif args.command == "search":
        res = search_memory(args.query, limit=args.limit)
        print(res)
    elif args.command == "graph":
        res = save_graph_relation(args.source, args.relation, args.target, weight=args.weight)
        print(res)
    elif args.command == "query-graph":
        res = query_graph(args.node, depth=args.depth)
        print(res)
    elif args.command == "reflect":
        res = consolidate_reflections(args.topic)
        print(res)
    elif args.command == "ingest-obsidian":
        res = ingest_obsidian(args.vault_path)
        print(res)
    elif args.command == "stats":
        print(get_stats())
    elif args.command == "benchmark":
        run_hardware_benchmark(num_vectors=args.vectors)
    elif args.command == "setup":
        setup_claude_desktop()

if __name__ == "__main__":
    main()
