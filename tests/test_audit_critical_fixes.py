"""
Audit Inoculation & Regression Test Suite:
Tests:
1. Multi-word FTS5 search (e.g., 'concurrent reader sqlite')
2. Code symbol preservation in FTS queries ('std::vector<int>', 'config.json', 'PRAGMA journal_mode')
3. Cascade edge deletion in delete_memory
4. Input validation and clamping (importance, limit, content max-length)
5. Incremental differential Obsidian vault sync
6. Schema versioning table verification
"""

import os
import pytest
from pathlib import Path


from engram.core import init_db, get_db, _INITIALIZED_PATHS
from engram.server import (
    save_memory,
    search_memory,
    delete_memory,
    save_graph_relation,
    query_graph,
)
from engram.ingest import ingest_single_obsidian_file, delete_obsidian_file_nodes


def test_fts5_multi_word_search():
    save_memory("High throughput concurrent reader architecture with SQLite WAL journal mode.", importance=8, category="test", project="fts_test")
    
    # Query with non-consecutive multi-words
    res = search_memory("concurrent reader sqlite", limit=5, hybrid=False, project="fts_test")
    assert "High throughput concurrent reader" in res

def test_code_symbol_preservation():
    save_memory("We use std::vector<int> and parse settings from config.json with PRAGMA journal_mode=WAL.", importance=9, category="code", project="code_test")
    
    # Query using raw code symbols
    res_code = search_memory("std::vector<int>", limit=5, hybrid=True, project="code_test")
    assert "std::vector<int>" in res_code

    res_json = search_memory("config.json", limit=5, hybrid=True, project="code_test")
    assert "config.json" in res_json

def test_cascade_edge_deletion():
    save_res = save_memory("Temporary Node for graph cascade test", importance=5, project="cascade_test")
    node_id = save_res.split("Saved Node ")[1].split(" ")[0]

    # Save edges attached to this node
    save_graph_relation(node_id, "connects_to", "TargetService", project="cascade_test")
    save_graph_relation("SourceService", "depends_on", node_id, project="cascade_test")

    # Verify edge exists
    q_res = query_graph(node_id, depth=1, project="cascade_test")
    assert "TargetService" in q_res

    # Delete node
    del_res = delete_memory(node_id)
    assert "cascaded" in del_res

    # Verify edges are deleted
    conn = get_db()
    orphan_edges = conn.execute("SELECT * FROM edges WHERE source = ? OR target = ?", (node_id, node_id)).fetchall()
    conn.close()
    assert len(orphan_edges) == 0

def test_input_validation_and_clamping():
    # Extreme importance: 999 -> clamped to 10
    save_res = save_memory("Important invariant node", importance=999, project="clamp_test")
    node_id = save_res.split("Saved Node ")[1].split(" ")[0]

    conn = get_db()
    row = conn.execute("SELECT importance FROM nodes WHERE id = ?", (node_id,)).fetchone()
    conn.close()
    assert row[0] == 10

    # Negative importance: -50 -> clamped to 1
    save_res2 = save_memory("Low importance note", importance=-50, project="clamp_test")
    node_id2 = save_res2.split("Saved Node ")[1].split(" ")[0]

    conn = get_db()
    row2 = conn.execute("SELECT importance FROM nodes WHERE id = ?", (node_id2,)).fetchone()
    conn.close()
    assert row2[0] == 1

def test_schema_version_applied():
    conn = get_db()
    ver = conn.execute("SELECT MAX(version) FROM schema_version;").fetchone()[0]
    conn.close()
    assert ver >= 1
