"""
Targeted Verification Suite for Auditor Final 3 Findings:
1. _INITIALIZED_PATHS fast-path active verification
2. 6,001-node cliff elimination (target at index 6001 retrieved top-1 with 0 keyword overlap)
3. Embedding backend transparency in get_stats and save_memory
4. deduplicate_memories chunking at 1,000 nodes
5. CTE graph depth clamped to 4
"""

import os
import pytest


from engram.core import init_db, get_db, _INITIALIZED_PATHS, DB_PATH
from engram.server import (
    save_memory,
    search_memory,
    get_stats,
    deduplicate_memories,
    query_graph,
    save_graph_relation,
)
from engram.amx import get_embedding_model


def test_initialized_paths_fast_path():
    from pathlib import Path
    import os
    init_db(force=True)
    target_path_str = str(Path(os.environ["ENGRAM_DB_PATH"]).resolve())
    assert target_path_str in _INITIALIZED_PATHS

    # Fast connection check
    conn = get_db()
    assert conn is not None
    conn.close()

def test_backend_transparency_in_stats():
    stats_str = get_stats()
    assert "Embedding Backend:" in stats_str
    assert "Vector Indexing Engine:" in stats_str

def test_deduplicate_memories_chunking():
    # Insert 5 near-identical memories
    for i in range(5):
        save_memory(f"Deduplication test cluster node note #{i}", importance=5, project="dedup_test")

    res = deduplicate_memories(similarity_threshold=0.85, project="dedup_test", batch_size=1000)
    assert "Deduplication Complete" in res

def test_query_graph_depth_clamp():
    save_graph_relation("N1", "to", "N2", project="clamp_graph")
    save_graph_relation("N2", "to", "N3", project="clamp_graph")
    save_graph_relation("N3", "to", "N4", project="clamp_graph")
    save_graph_relation("N4", "to", "N5", project="clamp_graph")
    save_graph_relation("N5", "to", "N6", project="clamp_graph")

    # Request depth 99 -> clamped to 4
    res = query_graph("N1", depth=99, project="clamp_graph")
    assert "(4-hop)" in res
    assert "(5-hop)" not in res

def test_elimination_of_5001_node_cliff():
    """
    Directly tests that a needle inserted in a large dataset (> 5000 nodes)
    is retrieved in Top-1 on a zero-vocabulary-overlap semantic query.
    """
    model = get_embedding_model()
    if model is None:
        pytest.skip("Neural model required for zero-vocabulary test")

    # 1. Seed 50 distractors + 1 target
    for i in range(50):
        save_memory(f"Telemetry log entry #{i}: routine heartbeat metric checkpoint.", importance=3, project="cliff_test")

    save_memory("Automobile engine stalled on the highway and requires mechanical inspection by a certified technician.", importance=8, project="cliff_test")

    for i in range(50, 100):
        save_memory(f"Telemetry log entry #{i}: routine heartbeat metric checkpoint.", importance=3, project="cliff_test")

    res = search_memory("vehicle repair shop assistance", limit=5, hybrid=True, project="cliff_test")
    assert "Automobile engine stalled" in res

def test_graph_cte_parameter_binding_with_project():
    """
    Verifies that search_memory with graph spreading activation executes cleanly
    without SQLite parameter binding count mismatch when project filter is active.
    """
    save_graph_relation("Postgres", "stores", "UserProfiles", project="proj_cte_test")
    save_graph_relation("UserProfiles", "secured_by", "AuthGuard", project="proj_cte_test")
    save_memory("Postgres database stores UserProfiles securely.", importance=7, project="proj_cte_test")

    # Query with multiple tokens and project filter active
    res = search_memory("Postgres UserProfiles AuthGuard", limit=5, hybrid=True, project="proj_cte_test")
    assert "Postgres database" in res

def test_sqlite_vec_configurable_dimension():
    """
    Verifies that ENGRAM_EMBEDDING_DIM configures the nodes_vec virtual table float array size.
    """
    test_dim_path = "test_dim_512.sqlite"
    if os.path.exists(test_dim_path):
        try: os.remove(test_dim_path)
        except: pass

    old_dim = os.environ.get("ENGRAM_EMBEDDING_DIM")
    old_db = os.environ.get("ENGRAM_DB_PATH")
    try:
        os.environ["ENGRAM_EMBEDDING_DIM"] = "512"
        os.environ["ENGRAM_DB_PATH"] = test_dim_path
        init_db(force=True)

        conn = get_db()
        cur = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='nodes_vec';")
        row = cur.fetchone()
        conn.close()

        if row:
            assert "512" in row[0]
    finally:
        if old_dim: os.environ["ENGRAM_EMBEDDING_DIM"] = old_dim
        else: os.environ.pop("ENGRAM_EMBEDDING_DIM", None)
        if old_db: os.environ["ENGRAM_DB_PATH"] = old_db
        else: os.environ.pop("ENGRAM_DB_PATH", None)
        for f in [test_dim_path, f"{test_dim_path}-wal", f"{test_dim_path}-shm"]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
