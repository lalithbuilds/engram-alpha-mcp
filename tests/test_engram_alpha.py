"""
Universal Production-Grade Tests for Engram Alpha MCP
"""

import os
import sqlite3
import pytest
import time
from pathlib import Path

os.environ["ENGRAM_DB_PATH"] = "test_engram_v4.sqlite"

from engram.core import init_db, get_db, check_storage_liveness, optimize_and_checkpoint
from engram.server import (
    save_memory,
    search_memory,
    save_graph_relation,
    query_graph,
    extract_and_save_memory,
    consolidate_reflections,
    deduplicate_memories,
    visualize_graph,
    checkpoint_db,
    get_stats,
)
from engram.amx import get_acceleration_tier

def test_database_initialization():
    if os.path.exists("test_engram_v4.sqlite"):
        os.remove("test_engram_v4.sqlite")
        
    conn = get_db()
    res = conn.execute("PRAGMA journal_mode;").fetchone()
    assert res[0].lower() == 'wal'
    
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "nodes" in tables
    assert "edges" in tables
    assert "nodes_fts" in tables
    conn.close()

def test_storage_liveness_check():
    p = Path("test_engram_v4.sqlite")
    assert check_storage_liveness(p, timeout_seconds=1.0) is True

def test_project_namespaces():
    save_memory("Project Alpha secret formula", project="alpha_proj", importance=8)
    save_memory("Project Beta secret formula", project="beta_proj", importance=8)

    # Search scoped to alpha
    res_alpha = search_memory("secret formula", project="alpha_proj")
    assert "Project: alpha_proj" in res_alpha

    # Search scoped to beta
    res_beta = search_memory("secret formula", project="beta_proj")
    assert "Project: beta_proj" in res_beta

def test_deduplication_agent():
    # Save 2 identical concepts
    save_memory("We standardize strictly on Python 3.10 and FastMCP.", project="dedupe_test", importance=5)
    save_memory("We standardize strictly on Python 3.10 and FastMCP.", project="dedupe_test", importance=6)

    res = deduplicate_memories(similarity_threshold=0.90, project="dedupe_test")
    assert "Deduplication Complete" in res

def test_graph_visualizer():
    save_graph_relation("RayOrchestrator", "controls", "MemorySwarm", weight=1.0, project="viz_test")
    save_graph_relation("MemorySwarm", "queries", "SQLiteWAL", weight=1.0, project="viz_test")

    viz_res = visualize_graph("RayOrchestrator", depth=2, project="viz_test")
    assert "Topology for [RayOrchestrator]:" in viz_res
    assert "graph LR" in viz_res
    assert "RayOrchestrator" in viz_res
    assert "MemorySwarm" in viz_res

def test_checkpoint_and_optimize():
    res = checkpoint_db()
    assert "Database Checkpoint Status" in res
    assert "optimized" in res

def teardown_module(module):
    for f in ["test_engram_v4.sqlite", "test_engram_v4.sqlite-wal", "test_engram_v4.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
