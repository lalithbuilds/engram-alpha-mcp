"""
Engram Alpha CLI (Universal Production-Grade Architecture)
Full command-line interface for Engram Alpha MCP:
Memory recall, search, graph exploration, live obsidian sync,
import/export, curses TUI, HTTP OpenAPI gateway, and hardware benchmarks.
"""

import argparse
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, Any

from .utils import foolproof_update_json
from .core import get_db
from .server import (
    save_memory,
    search_memory,
    save_graph_relation,
    query_graph,
    ingest_obsidian,
    extract_and_save_memory,
    consolidate_reflections,
    deduplicate_memories,
    visualize_graph,
    checkpoint_db,
    get_stats,
    auto_context,
    edit_memory,
    delete_memory,
    list_memories,
)
from .ingest import watch_obsidian_vault
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
        print(f"❌ Failed to configure Claude Desktop: {e}")

def run_hardware_benchmark(num_vectors: int = 10000):
    """Run empirical throughput and vector dot product evaluation benchmark."""
    print("=" * 60)
    print("⚡ ENGRAM ALPHA HARDWARE ACCELERATION BENCHMARK")
    print("=" * 60)
    tier_name = get_acceleration_tier()
    print(f"Active Hardware Tier: {tier_name}")
    print(f"Evaluating {num_vectors:,} 384-dimensional normalized float vectors...")

    # Generate synthetic vector matrix
    query = [1.0 / (384 ** 0.5)] * 384
    matrix = [[(i % 10) * 0.1 for _ in range(384)] for i in range(num_vectors)]

    start_t = time.perf_counter()
    scores = amx_batch_cosine_similarity(query, matrix)
    elapsed = time.perf_counter() - start_t

    throughput = num_vectors / elapsed if elapsed > 0 else 0
    print(f"✅ Completed {num_vectors:,} vector evaluations in {elapsed:.4f}s")
    print(f"🚀 Throughput: {throughput:,.1f} vector comparisons/second")
    print(f"🎯 Latency per vector: {(elapsed / num_vectors) * 1_000_000:.2f} microseconds")
    print("=" * 60)

def cmd_export(file_path: str, project: str = None):
    """Export memory nodes and graph edges to a JSON file."""
    conn = get_db()
    try:
        proj_filter = "WHERE project = ?" if project else ""
        params = [project] if project else []

        node_rows = conn.execute(f"SELECT id, type, content, importance, category, project, agent, created_at FROM nodes {proj_filter}", params).fetchall()
        nodes = [
            {"id": r[0], "type": r[1], "content": r[2], "importance": r[3], "category": r[4], "project": r[5], "agent": r[6], "created_at": r[7]}
            for r in node_rows
        ]

        edge_rows = conn.execute(f"SELECT source, target, relation, weight, project, valid_from, valid_until FROM edges {proj_filter}", params).fetchall()
        edges = [
            {"source": r[0], "target": r[1], "relation": r[2], "weight": r[3], "project": r[4], "valid_from": r[5], "valid_until": r[6]}
            for r in edge_rows
        ]
        
        data = {"nodes": nodes, "edges": edges, "exported_at": time.time()}
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Exported {len(nodes)} nodes and {len(edges)} graph edges to {file_path}")
    finally:
        conn.close()

def cmd_import(file_path: str, project: str = None):
    """Import memory nodes and graph edges from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("nodes", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    edges = data.get("edges", []) if isinstance(data, dict) else []

    imported_nodes = 0
    for n in nodes:
        content = n.get("content", "")
        cat = n.get("category", "general")
        try:
            imp = int(n.get("importance", 5))
        except (ValueError, TypeError):
            imp = 5
        proj = project if project is not None else n.get("project", "default")
        save_memory(content, category=cat, importance=imp, project=proj)
        imported_nodes += 1

    imported_edges = 0
    for e in edges:
        s = e.get("source", "")
        t = e.get("target", "")
        r = e.get("relation", "connects_to")
        try:
            w = float(e.get("weight", 1.0))
        except (ValueError, TypeError):
            w = 1.0
        proj = project if project is not None else e.get("project", "default")
        vf = e.get("valid_from", "")
        vu = e.get("valid_until", "")
        save_graph_relation(s, r, t, weight=w, project=proj, valid_from=vf, valid_until=vu)
        imported_edges += 1

    print(f"✅ Imported {imported_nodes} nodes and {imported_edges} graph edges from {file_path}")

def cmd_tui():
    """Launch interactive curses terminal UI for browsing memory nodes."""
    try:
        import curses
    except ImportError:
        print("curses module not available on this platform.")
        return

    if not sys.stdout.isatty():
        print("TUI requires an interactive terminal.")
        return

    def run_tui(stdscr):
        curses.curs_set(0)
        conn = get_db()
        rows = conn.execute(
            "SELECT id, category, content, importance, project, created_at FROM nodes ORDER BY importance DESC, created_at DESC LIMIT 500"
        ).fetchall()
        conn.close()

        if not rows:
            stdscr.addstr(0, 0, "Engram Alpha Memory Bank is empty. Press any key to exit.")
            stdscr.getch()
            return

        current_row = 0
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            stdscr.addstr(0, 0, f"🧠 Engram Alpha TUI - {len(rows)} Memories - (UP/DOWN to scroll, 'q' to quit)", curses.A_REVERSE)

            max_items = h - 2
            start = max(0, current_row - max_items // 2)
            end = min(len(rows), start + max_items)

            for idx, i in enumerate(range(start, end)):
                r = rows[i]
                y = idx + 1
                prefix = "> " if i == current_row else "  "
                preview = r[2][: max(10, w - 45)].replace("\n", " ")
                line = f"{prefix}[{r[0][:8]}] [{r[1][:8]:8s}] IMP:{r[3]:2d} | {preview}"

                if i == current_row:
                    stdscr.addstr(y, 0, line[:w-1], curses.A_BOLD)
                else:
                    stdscr.addstr(y, 0, line[:w-1])

            key = stdscr.getch()
            if key == ord('q'):
                break
            elif key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif (key == curses.KEY_DOWN or key == ord('j')) and current_row < len(rows) - 1:
                current_row += 1
            elif key == ord('k') and current_row > 0:
                current_row -= 1

    curses.wrapper(run_tui)

def main():
    parser = argparse.ArgumentParser(description="Engram Alpha CLI — Sovereign Cognitive Memory Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Save
    p_save = subparsers.add_parser("save", help="Save a memory node")
    p_save.add_argument("content", help="Memory content string")
    p_save.add_argument("--category", default="general", help="Memory category")
    p_save.add_argument("--importance", type=int, default=5, help="Importance level (1-10)")
    p_save.add_argument("--project", default="default", help="Project namespace")

    # Extract
    p_extract = subparsers.add_parser("extract", help="Autonomous deconstruct & save memory triples")
    p_extract.add_argument("text", help="Raw conversational or contextual text")
    p_extract.add_argument("--project", default="default", help="Project namespace")

    # Search
    p_search = subparsers.add_parser("search", help="4-Way RRF Hybrid Search (Vector + FTS5 + Graph + Decay)")
    p_search.add_argument("query", help="Search query string")
    p_search.add_argument("--limit", type=int, default=5, help="Number of results")
    p_search.add_argument("--project", default=None, help="Project namespace")

    # Recall (Auto-Context boot)
    p_recall = subparsers.add_parser("recall", help="Auto-context recall of top memories for session start")
    p_recall.add_argument("--limit", type=int, default=5, help="Number of results")
    p_recall.add_argument("--min-importance", type=int, default=7, help="Minimum importance threshold")
    p_recall.add_argument("--project", default=None, help="Project namespace")

    # List
    p_list = subparsers.add_parser("list", help="List recent memories")
    p_list.add_argument("--limit", type=int, default=50, help="Number of memories to list")
    p_list.add_argument("--project", default=None, help="Project namespace")

    # Edit
    p_edit = subparsers.add_parser("edit", help="Edit an existing memory by ID")
    p_edit.add_argument("id", help="Memory Node UUID")
    p_edit.add_argument("--content", default=None, help="New content")
    p_edit.add_argument("--importance", type=int, default=None, help="New importance (1-10)")
    p_edit.add_argument("--category", default=None, help="New category")

    # Delete
    p_del = subparsers.add_parser("delete", help="Delete a memory by ID")
    p_del.add_argument("id", help="Memory Node UUID")

    # Export / Import
    p_exp = subparsers.add_parser("export", help="Export memory database to JSON file")
    p_exp.add_argument("file", help="Destination JSON filepath")
    p_exp.add_argument("--project", default=None, help="Project namespace")

    p_imp = subparsers.add_parser("import", help="Import memory JSON file")
    p_imp.add_argument("file", help="Source JSON filepath")
    p_imp.add_argument("--project", default="default", help="Project namespace")

    # Graph
    p_graph = subparsers.add_parser("graph", help="Save a knowledge graph relation")
    p_graph.add_argument("source", help="Source entity")
    p_graph.add_argument("relation", help="Predicate relation")
    p_graph.add_argument("target", help="Target entity")
    p_graph.add_argument("--weight", type=float, default=1.0, help="Edge weight")
    p_graph.add_argument("--project", default="default", help="Project namespace")
    p_graph.add_argument("--valid-from", default="", help="Valid from timestamp/date")
    p_graph.add_argument("--valid-until", default="", help="Valid until timestamp/date")

    # Query Graph
    p_qgraph = subparsers.add_parser("query-graph", help="Query knowledge graph relations with recursive CTEs")
    p_qgraph.add_argument("node", help="Entity to query")
    p_qgraph.add_argument("--depth", type=int, default=2, help="Search depth (1-5)")
    p_qgraph.add_argument("--project", default=None, help="Project namespace")

    # Inspect Graph (Mermaid & ASCII)
    p_inspect = subparsers.add_parser("inspect", help="Visualize knowledge graph neighborhood (ASCII & Mermaid.js)")
    p_inspect.add_argument("node", help="Central entity to visualize")
    p_inspect.add_argument("--depth", type=int, default=2, help="Graph depth")
    p_inspect.add_argument("--project", default=None, help="Project namespace")

    # Dedupe
    p_dedupe = subparsers.add_parser("dedupe", help="Semantic cluster deduplication & merge")
    p_dedupe.add_argument("--threshold", type=float, default=0.92, help="Similarity threshold (0.80 - 0.99)")
    p_dedupe.add_argument("--project", default=None, help="Project namespace")

    # Reflect
    p_reflect = subparsers.add_parser("reflect", help="Episodic Reflection & Synthesis Agent")
    p_reflect.add_argument("topic", help="Topic to synthesize into durable insights")
    p_reflect.add_argument("--project", default="default", help="Project namespace")

    # Ingest Obsidian
    p_ingest = subparsers.add_parser("ingest-obsidian", help="Ingest an Obsidian vault")
    p_ingest.add_argument("vault_path", help="Path to Obsidian vault directory")
    p_ingest.add_argument("--project", default="default", help="Project namespace")

    # Watch Obsidian
    p_watch = subparsers.add_parser("watch", help="Live real-time Obsidian vault sync daemon")
    p_watch.add_argument("vault_path", help="Path to Obsidian vault directory")
    p_watch.add_argument("--project", default="default", help="Project namespace")

    # Checkpoint
    subparsers.add_parser("checkpoint", help="Execute WAL checkpoint and database optimization")

    # Stats
    subparsers.add_parser("stats", help="Show system statistics")

    # Benchmark
    p_bench = subparsers.add_parser("benchmark", help="Run hardware coprocessor benchmark")
    p_bench.add_argument("--vectors", type=int, default=10000, help="Number of test vectors")

    # Serve (HTTP & OpenAPI Gateway for Web Agents)
    p_serve = subparsers.add_parser("serve", help="Start HTTP & OpenAPI Gateway for Web Agents (ChatGPT, Claude, Gemini)")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host address")
    p_serve.add_argument("--port", type=int, default=8000, help="Port number")

    # TUI
    subparsers.add_parser("tui", help="Launch interactive Terminal UI dashboard")

    # Setup
    subparsers.add_parser("setup", help="Auto-configure Claude Desktop")

    args = parser.parse_args()

    if args.command == "save":
        res = save_memory(args.content, category=args.category, importance=args.importance, project=args.project)
        print(res)
    elif args.command == "extract":
        res = extract_and_save_memory(args.text, project=args.project)
        print(res)
    elif args.command == "search":
        res = search_memory(args.query, limit=args.limit, project=args.project)
        print(res)
    elif args.command == "recall":
        res = auto_context(limit=args.limit, min_importance=args.min_importance, project=args.project)
        print(res)
    elif args.command == "list":
        res = list_memories(limit=args.limit, project=args.project)
        print(res)
    elif args.command == "edit":
        res = edit_memory(args.id, content=args.content, importance=args.importance, category=args.category)
        print(res)
    elif args.command == "delete":
        res = delete_memory(args.id)
        print(res)
    elif args.command == "export":
        cmd_export(args.file, project=args.project)
    elif args.command == "import":
        cmd_import(args.file, project=args.project)
    elif args.command == "tui":
        cmd_tui()
    elif args.command == "graph":
        res = save_graph_relation(args.source, args.relation, args.target, weight=args.weight, project=args.project, valid_from=args.valid_from, valid_until=args.valid_until)
        print(res)
    elif args.command == "query-graph":
        res = query_graph(args.node, depth=args.depth, project=args.project)
        print(res)
    elif args.command == "inspect":
        res = visualize_graph(args.node, depth=args.depth, project=args.project)
        print(res)
    elif args.command == "dedupe":
        res = deduplicate_memories(similarity_threshold=args.threshold, project=args.project)
        print(res)
    elif args.command == "reflect":
        res = consolidate_reflections(args.topic, project=args.project)
        print(res)
    elif args.command == "ingest-obsidian":
        res = ingest_obsidian(args.vault_path, project=args.project)
        print(res)
    elif args.command == "watch":
        watch_obsidian_vault(args.vault_path, project=args.project)
    elif args.command == "checkpoint":
        res = checkpoint_db()
        print(res)
    elif args.command == "stats":
        print(get_stats())
    elif args.command == "benchmark":
        run_hardware_benchmark(num_vectors=args.vectors)
    elif args.command == "serve":
        from .http_bridge import start_http_gateway
        start_http_gateway(host=args.host, port=args.port)
    elif args.command == "setup":
        setup_claude_desktop()

if __name__ == "__main__":
    main()
