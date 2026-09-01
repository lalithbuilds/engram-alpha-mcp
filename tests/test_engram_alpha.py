"""
Universal Cross-Platform Integration & Feature Tests for Engram Alpha MCP
"""

import os
import sqlite3
import pytest
import time
from pathlib import Path

os.environ["ENGRAM_DB_PATH"] = "test_engram_v3.sqlite"

from engram.core import init_db, get_db, check_storage_liveness
from engram.server import (
    save_memory,
    search_memory,
    save_graph_relation,
    query_graph,
    extract_and_save_memory,
    consolidate_reflections,
    get_stats,
)
from engram.amx import get_acceleration_tier

def test_database_initialization():
    if os.path.exists("test_engram_v3.sqlite"):
        os.remove("test_engram_v3.sqlite")
        
    conn = get_db()
    res = conn.execute("PRAGMA journal_mode;").fetchone()
    assert res[0].lower() == 'wal'
    
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "nodes" in tables
    assert "edges" in tables
    assert "nodes_fts" in tables
    conn.close()

def test_storage_liveness_check():
    p = Path("test_engram_v3.sqlite")
    assert check_storage_liveness(p, timeout_seconds=1.0) is True

def test_save_and_conflict_detection():
    res1 = save_memory("We use PostgreSQL for database storage.", category="db", importance=8)
    assert "Saved Node" in res1
    
    # Overlapping fact detection
    res2 = save_memory("We use PostgreSQL for persistent data storage.", category="db", importance=7)
    assert "Conflict found" in res2

def test_extract_and_save_memory_agent():
    raw_text = "RayDaemon connects_to EngramAlpha for memory recall. See also [[ModelCouncil]]."
    res = extract_and_save_memory(raw_text)
    assert "Extracted & Saved Node" in res
    assert "connects_to" in res
    assert "references" in res

    # Query graph
    g_res = query_graph("RayDaemon", depth=1)
    assert "connects_to" in g_res
    assert "EngramAlpha" in g_res

def test_2_hop_graph_spreading_activation():
    save_graph_relation("NodeA", "links", "NodeB", weight=2.0)
    save_graph_relation("NodeB", "links", "NodeC", weight=1.5)

    # 1-hop
    res_1hop = query_graph("NodeA", depth=1)
    assert "NodeB" in res_1hop
    assert "NodeC" not in res_1hop

    # 2-hop
    res_2hop = query_graph("NodeA", depth=2)
    assert "NodeB" in res_2hop
    assert "NodeC" in res_2hop

def test_reflection_consolidation_agent():
    save_memory("Benchmarking showed AMX vector engine is 195k ops/sec.", category="perf", importance=9)
    save_memory("Benchmarking proved SQLite WAL survives 1400 concurrent writes.", category="perf", importance=9)

    res = consolidate_reflections("Benchmarking")
    assert "Created Consolidated Reflection" in res
    assert "Consolidated Reflection on 'Benchmarking'" in res

def test_stats_and_acceleration_tier():
    stats = get_stats()
    assert "Engram Alpha Universal MCP Stats" in stats
    assert "Hardware Engine Tier" in stats

def teardown_module(module):
    for f in ["test_engram_v3.sqlite", "test_engram_v3.sqlite-wal", "test_engram_v3.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
