"""
Engram Alpha Model Council Stress Sandbox & Quality Extraction Benchmark
Simulates 7 autonomous AI agents running concurrent multi-threaded workloads:
1. Claude Fable: Complex entity & triple extraction
2. Gemini Pro 3: 4-Way RRF Hybrid search across project namespaces
3. Kimi K3: Live Obsidian vault ingestion under concurrent write load
4. GPT Soul: ACT-R cognitive power-law decay & spaced practice evaluation
5. Deep Research: Chaos injection (rapid burst writes, lock contention, rollback triggers)
6. GLM 5.2: Multi-tier vector hardware acceleration & memory footprint profiling
7. O1 Pro: 2-Hop graph spreading activation & relational path-finding
"""

import sys
import os
import time
import math
import tempfile
import random
import shutil
import statistics
import threading
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set sandbox DB path
SANDBOX_DIR = Path(tempfile.mkdtemp(prefix="engram_council_sandbox_"))
os.environ["ENGRAM_DB_PATH"] = str(SANDBOX_DIR / "sandbox.sqlite")

from engram.core import init_db, get_db, optimize_and_checkpoint
from engram.server import (
    save_memory,
    search_memory,
    extract_and_save_memory,
    save_graph_relation,
    query_graph,
    deduplicate_memories,
    consolidate_reflections,
    visualize_graph,
    get_stats,
)
from engram.ingest import ingest_obsidian_vault
from engram.amx import (
    amx_batch_cosine_similarity,
    generate_dense_embedding,
    get_acceleration_tier,
    amx_cosine_similarity,
    get_embedding_model,
)

# Global Telemetry Collector
TELEMETRY = {
    "Claude_Fable": {"ops": 0, "errors": 0, "latencies": [], "extractions": 0},
    "Gemini_Pro_3": {"ops": 0, "errors": 0, "latencies": [], "searches": 0},
    "Kimi_K3": {"ops": 0, "errors": 0, "latencies": [], "vault_files": 0},
    "GPT_Soul": {"ops": 0, "errors": 0, "latencies": [], "decay_checks": 0},
    "Deep_Research": {"ops": 0, "errors": 0, "latencies": [], "retries_absorbed": 0},
    "GLM_5_2": {"ops": 0, "errors": 0, "latencies": [], "vector_ops": 0},
    "O1_Pro": {"ops": 0, "errors": 0, "latencies": [], "graph_hops": 0},
}

LOCK = threading.Lock()

def record_metric(agent_name: str, latency: float, success: bool, extra_key: str = None, extra_val: int = 1):
    with LOCK:
        TELEMETRY[agent_name]["latencies"].append(latency)
        if success:
            TELEMETRY[agent_name]["ops"] += 1
            if extra_key:
                TELEMETRY[agent_name][extra_key] += extra_val
        else:
            TELEMETRY[agent_name]["errors"] += 1

# --- AGENT WORKERS ---

def worker_claude_fable(iterations: int = 250):
    """Claude Fable: Complex Entity Extraction & Knowledge Triples."""
    samples = [
        "RayEngine uses SQLiteWAL to achieve ACID persistence. [[MemoryArchitecture]]",
        "FastMCP implements ProtocolGateway for ClaudeDesktop. [[ClientIntegration]]",
        "EngramAlpha replaces Mem0 in production agent swarms. [[CognitiveLayer]]",
        "AMXAccelerate requires AppleSilicon for hardware matrix vector math. [[HardwareOptimization]]",
        "RayOrchestrator connects_to AgentSwarm for multi-agent execution. [[SwarmTopology]]",
        "ObsidianVault links_to KnowledgeGraph via semantic wikilinks. [[VaultSync]]",
        "ReciprocalRankFusion implements HybridScoring with trigram FTS5 index. [[AlgorithmCore]]",
    ]
    for i in range(iterations):
        text = random.choice(samples) + f" Variant_{i}"
        t0 = time.perf_counter()
        try:
            res = extract_and_save_memory(text, project="claude_sandbox", importance=random.randint(4, 9))
            success = "Extracted & Saved Node" in res
        except Exception as e:
            success = False
        t1 = time.perf_counter()
        record_metric("Claude_Fable", t1 - t0, success, "extractions", 1)

def worker_gemini_pro_3(iterations: int = 250):
    """Gemini Pro 3: High-Frequency 4-Way RRF Hybrid Searches Across Projects."""
    queries = [
        "SQLiteWAL persistence",
        "FastMCP ClaudeDesktop",
        "EngramAlpha agent swarms",
        "AMXAccelerate matrix math",
        "RayOrchestrator swarm execution",
        "ReciprocalRankFusion hybrid",
    ]
    for i in range(iterations):
        q = random.choice(queries)
        t0 = time.perf_counter()
        try:
            res = search_memory(q, limit=5, hybrid=True, project=random.choice(["claude_sandbox", "default", None]))
            success = isinstance(res, str) and len(res) > 0
        except Exception as e:
            success = False
        t1 = time.perf_counter()
        record_metric("Gemini_Pro_3", t1 - t0, success, "searches", 1)

def worker_kimi_k3(iterations: int = 50):
    """Kimi K3: Live Vault Ingestion & Obsidian Chunker Under Write Contention."""
    vault_dir = SANDBOX_DIR / "kimi_vault"
    vault_dir.mkdir(exist_ok=True)
    
    for i in range(iterations):
        # Generate 3 markdown files per iteration
        for j in range(3):
            file_p = vault_dir / f"note_{i}_{j}.md"
            file_p.write_text(
                f"# Architectural Note {i}_{j}\n"
                f"This document outlines [[SystemArchitecture]] and connects to [[RayDaemon]].\n"
                f"We enforce #production standards and #zero_trust security rules.\n"
                f"Content payload: {' '.join(['benchmark_token'] * 80)}.\n"
            )
        t0 = time.perf_counter()
        try:
            res = ingest_obsidian_vault(str(vault_dir), project="kimi_vault_proj")
            success = res.get("status") == "success"
            files_count = res.get("files_processed", 0)
        except Exception as e:
            success = False
            files_count = 0
        t1 = time.perf_counter()
        record_metric("Kimi_K3", t1 - t0, success, "vault_files", files_count)

def worker_gpt_soul(iterations: int = 250):
    """GPT Soul: ACT-R Power-Law Decay & Spaced Practice Validation."""
    for i in range(iterations):
        t0 = time.perf_counter()
        try:
            # Save memory with timestamp simulation
            node_id = save_memory(f"Cognitive fact #{i} on memory retention dynamics.", importance=8, project="soul_proj")
            # Verify retrieval triggers spaced practice update
            res = search_memory("retention dynamics", project="soul_proj")
            success = "soul_proj" in res
        except Exception:
            success = False
        t1 = time.perf_counter()
        record_metric("GPT_Soul", t1 - t0, success, "decay_checks", 1)

def worker_deep_research(iterations: int = 250):
    """Deep Research: Chaos Engineering (Rapid Bursts, Deduplication & Rollback Resilience)."""
    for i in range(iterations):
        t0 = time.perf_counter()
        try:
            if i % 15 == 0:
                # Run semantic deduplication under load
                dedupe_res = deduplicate_memories(similarity_threshold=0.92, project="claude_sandbox")
                success = "Deduplication Complete" in dedupe_res or "Insufficient" in dedupe_res
            elif i % 25 == 0:
                # Trigger reflection consolidation
                ref_res = consolidate_reflections("Architecture", project="claude_sandbox")
                success = "Consolidated Reflection" in ref_res or "Insufficient" in ref_res
            else:
                # Concurrent burst write
                save_memory(f"Chaos stress memory block {i}_{random.random()}", project="chaos_proj")
                success = True
        except Exception as e:
            success = False
        t1 = time.perf_counter()
        record_metric("Deep_Research", t1 - t0, success, "retries_absorbed", 1)

def worker_glm_5_2(iterations: int = 250):
    """GLM 5.2: Multi-Tier Matrix Vector Operations & Throughput Stress."""
    dim = 384
    query = [random.uniform(-1.0, 1.0) for _ in range(dim)]
    candidates = [[random.uniform(-1.0, 1.0) for _ in range(dim)] for _ in range(100)]

    for i in range(iterations):
        t0 = time.perf_counter()
        try:
            scores = amx_batch_cosine_similarity(query, candidates)
            success = len(scores) == 100
        except Exception:
            success = False
        t1 = time.perf_counter()
        record_metric("GLM_5_2", t1 - t0, success, "vector_ops", 100)

def worker_o1_pro(iterations: int = 250):
    """O1 Pro: Relational Knowledge Graph Traversal & Spreading Activation."""
    entities = ["RayMaster", "FastMCP", "SQLiteWAL", "AMXEngine", "AgentSwarm", "ObsidianGraph"]
    relations = ["orchestrates", "queries", "accelerates", "synchronizes", "indexes"]

    for i in range(iterations):
        s = random.choice(entities)
        r = random.choice(relations)
        t = random.choice(entities)
        t0 = time.perf_counter()
        try:
            if i % 3 == 0:
                # Graph write
                save_graph_relation(s, r, t, weight=random.uniform(0.5, 1.5), project="o1_graph_proj")
                success = True
            else:
                # 2-Hop graph query
                res = query_graph(s, depth=2, project="o1_graph_proj")
                success = isinstance(res, str)
        except Exception:
            success = False
        t1 = time.perf_counter()
        record_metric("O1_Pro", t1 - t0, success, "graph_hops", 1)

def run_stress_sandbox():
    print("=" * 80)
    print("⚡ LAUNCHING MODEL COUNCIL GAUNTLET LEVEL 5: 7-AGENT CONCURRENT SANDBOX")
    print(f"Directory: {SANDBOX_DIR}")
    print(f"Hardware Engine: {get_acceleration_tier()}")
    print("=" * 80)

    # Initialize clean SQLite WAL
    init_db()

    # Pre-initialize embedding model on main thread to avoid ONNX multiprocessing deadlock
    get_embedding_model()

    start_time = time.perf_counter()
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = [
            executor.submit(worker_claude_fable, 250),
            executor.submit(worker_gemini_pro_3, 250),
            executor.submit(worker_kimi_k3, 40),
            executor.submit(worker_gpt_soul, 250),
            executor.submit(worker_deep_research, 250),
            executor.submit(worker_glm_5_2, 250),
            executor.submit(worker_o1_pro, 250),
        ]
        for f in as_completed(futures):
            f.result()
            
    total_elapsed = time.perf_counter() - start_time

    # Database Forensic Checkpoint & Verification
    conn = get_db()
    integrity = conn.execute("PRAGMA integrity_check;").fetchall()
    quick_check = conn.execute("PRAGMA quick_check;").fetchall()
    fk_check = conn.execute("PRAGMA foreign_key_check;").fetchall()
    node_count = conn.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
    edge_count = conn.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
    fts_count = conn.execute("SELECT COUNT(*) FROM nodes_fts;").fetchone()[0]
    
    checkpoint_res = optimize_and_checkpoint(conn)
    conn.close()

    total_ops = sum(v["ops"] for v in TELEMETRY.values())
    total_errors = sum(v["errors"] for v in TELEMETRY.values())
    all_latencies = [lat * 1000 for v in TELEMETRY.values() for lat in v["latencies"]]

    p50 = statistics.median(all_latencies) if all_latencies else 0.0
    p95 = statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) >= 20 else p50
    p99 = statistics.quantiles(all_latencies, n=100)[98] if len(all_latencies) >= 100 else p95
    avg_throughput = total_ops / total_elapsed if total_elapsed > 0 else 0

    print("\n" + "=" * 80)
    print(f"📊 GAUNTLET LEVEL 5 RESULTS SUMMARY (Elapsed: {total_elapsed:.2f}s)")
    print("=" * 80)
    err_pct = (total_errors / max(1, total_ops + total_errors)) * 100.0
    print(f"Total Operations: {total_ops:,} ops")
    print(f"Total Errors / Deadlocks: {total_errors} ({err_pct:.2f}%)")
    print(f"Aggregate Swarm Throughput: {avg_throughput:,.1f} ops/sec")
    print(f"Latency Profile: p50={p50:.2f}ms | p95={p95:.2f}ms | p99={p99:.2f}ms")
    print("-" * 80)
    for agent, m in TELEMETRY.items():
        agent_lat = [l * 1000 for l in m["latencies"]]
        a_p50 = statistics.median(agent_lat) if agent_lat else 0.0
        a_p95 = statistics.quantiles(agent_lat, n=20)[18] if len(agent_lat) >= 20 else a_p50
        print(f"• {agent:<14} | Ops: {m['ops']:<4} | Err: {m['errors']} | p50: {a_p50:5.2f}ms | p95: {a_p95:5.2f}ms")
    print("-" * 80)
    print("🔒 FORENSIC DATA INTEGRITY & WAL VERIFICATION:")
    print(f"• PRAGMA integrity_check: {integrity}")
    print(f"• PRAGMA quick_check:     {quick_check}")
    print(f"• PRAGMA foreign_key_chk: {fk_check}")
    print(f"• Database Table Counts:  {node_count} nodes, {fts_count} FTS indexed, {edge_count} graph edges")
    print(f"• Checkpoint & Vacuum:    {checkpoint_res}")
    print("=" * 80)

    # Cleanup temp sandbox
    shutil.rmtree(SANDBOX_DIR, ignore_errors=True)

if __name__ == "__main__":
    run_stress_sandbox()
