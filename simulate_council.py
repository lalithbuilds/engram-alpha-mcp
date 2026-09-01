"""
Model Council V3 Swarm Gauntlet
Simulates 7 concurrent AI agent personas (Fable, Gemini, Kimi, Soul, Deep, GLM, O1)
hammering Engram Alpha V3 with concurrent saves, hybrid AMX vector searches,
graph relationship triples, and graph queries under high concurrency.
"""

import os
import time
import uuid
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ["ENGRAM_DB_PATH"] = "simulation_v3.sqlite"

from engram.server import (
    save_memory,
    search_memory,
    save_graph_relation,
    query_graph,
    get_stats,
)

AGENTS = ["FABLE", "GEMINI", "KIMI", "SOUL", "DEEP", "GLM", "O1"]
DOMAINS = [
    ("Apple Silicon AMX", "accelerates", "Matrix Multiplication"),
    ("Ray Daemon", "queries", "Engram Alpha"),
    ("Obsidian Vault", "ingests_into", "SQLite Graph"),
    ("Model Council", "orchestrates", "Autonomous Swarm"),
    ("ACT-R Decay", "optimizes", "Memory Eviction"),
    ("FTS5 Trigram", "indexes", "Lexical Keywords"),
    ("Accelerate BLAS", "computes", "Cosine Similarity"),
]

def council_agent_worker(agent_name: str, operations: int):
    successes = 0
    errors = {}

    for i in range(operations):
        try:
            action = random.choice(["save", "search", "graph_write", "graph_query"])
            
            if action == "save":
                subj, rel, obj = random.choice(DOMAINS)
                text = f"[{agent_name}] Verified that {subj} {rel} {obj} at timestamp {time.time()}."
                save_memory(text)
            elif action == "search":
                term = random.choice(["Apple Silicon", "Engram Alpha", "Model Council", "Cosine Similarity", "Decay"])
                search_memory(term, limit=3, hybrid=True)
            elif action == "graph_write":
                subj, rel, obj = random.choice(DOMAINS)
                save_graph_relation(subj, rel, obj)
            elif action == "graph_query":
                subj, _, _ = random.choice(DOMAINS)
                query_graph(subj)

            successes += 1
            # Micro-pause for realistic multi-agent cadence
            time.sleep(random.uniform(0.005, 0.02))
        except Exception as e:
            err_msg = str(e)
            errors[err_msg] = errors.get(err_msg, 0) + 1

    return agent_name, successes, errors

def main():
    print("⚡ Starting Model Council V3 Gauntlet (7 Agents, AMX Accelerated, SQLite WAL)...")
    for f in ["simulation_v3.sqlite", "simulation_v3.sqlite-wal", "simulation_v3.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

    start_time = time.time()
    ops_per_agent = 200  # 7 agents * 200 ops = 1,400 concurrent operations
    total_expected = len(AGENTS) * ops_per_agent

    results = []
    with ThreadPoolExecutor(max_workers=len(AGENTS)) as executor:
        futures = {executor.submit(council_agent_worker, agent, ops_per_agent): agent for agent in AGENTS}
        for future in as_completed(futures):
            results.append(future.result())

    elapsed = time.time() - start_time
    print(f"\n--- Model Council V3 Gauntlet Finished in {elapsed:.2f} seconds ---")

    total_success = 0
    total_errors = 0
    for agent, succ, errs in results:
        print(f"Agent {agent}: {succ} ops successful")
        if errs:
            for emsg, cnt in errs.items():
                print(f"  ✗ [{cnt}x] {emsg}")
                total_errors += cnt
        total_success += succ

    print(f"\nFinal Tally: {total_success}/{total_expected} successful operations, {total_errors} errors.")
    print(get_stats())

    # Forensic WAL & Database Integrity Gauntlet Check
    print("\n--- Running Forensic Integrity & WAL Analysis ---")
    from engram.core import get_db
    conn = get_db()
    try:
        integrity = conn.execute("PRAGMA integrity_check;").fetchall()
        quick_chk = conn.execute("PRAGMA quick_check;").fetchall()
        fk_chk = conn.execute("PRAGMA foreign_key_check;").fetchall()
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        wal_checkpoint = conn.execute("PRAGMA wal_checkpoint(PASSIVE);").fetchall()
        
        node_cnt = conn.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
        node_fts_cnt = conn.execute("SELECT COUNT(*) FROM nodes_fts;").fetchone()[0]
        edge_cnt = conn.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
        vec_cnt = conn.execute("SELECT COUNT(*) FROM nodes WHERE embedding IS NOT NULL;").fetchone()[0]

        print(f"PRAGMA journal_mode: {journal_mode}")
        print(f"PRAGMA integrity_check: {integrity}")
        print(f"PRAGMA quick_check: {quick_chk}")
        print(f"PRAGMA foreign_key_check: {fk_chk}")
        print(f"PRAGMA wal_checkpoint(PASSIVE): {wal_checkpoint} (busy, log pages, checkpointed pages)")
        print(f"Table verification: {node_cnt} nodes ({vec_cnt} embedded), {node_fts_cnt} FTS indexed, {edge_cnt} graph edges.")
        
        for f in ["simulation_v3.sqlite", "simulation_v3.sqlite-wal", "simulation_v3.sqlite-shm"]:
            if os.path.exists(f):
                sz = os.path.getsize(f)
                print(f"File: {f} -> Size: {sz} bytes")
    finally:
        conn.close()

    for f in ["simulation_v3.sqlite", "simulation_v3.sqlite-wal", "simulation_v3.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

if __name__ == "__main__":
    main()
