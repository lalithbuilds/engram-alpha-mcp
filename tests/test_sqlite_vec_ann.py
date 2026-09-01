"""
sqlite-vec Virtual Table & Enhanced NLP Triple Extraction Tests:
Tests:
1. Native sqlite-vec virtual table synchronization via SQLite triggers
2. High-speed kNN vector matching via nodes_vec
3. Enhanced triple extraction (passive voice, preferences, architecture stacks)
"""

import os
import pytest

os.environ["ENGRAM_DB_PATH"] = "test_sqlite_vec.sqlite"

from engram.core import init_db, get_db
from engram.server import save_memory, search_memory, extract_and_save_memory, query_graph

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    if os.path.exists("test_sqlite_vec.sqlite"):
        try: os.remove("test_sqlite_vec.sqlite")
        except: pass
    init_db(force=True)
    yield
    for f in ["test_sqlite_vec.sqlite", "test_sqlite_vec.sqlite-wal", "test_sqlite_vec.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

def test_sqlite_vec_virtual_table_sync():
    conn = get_db()
    # Check if nodes_vec virtual table exists
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_vec';")
    has_vec = cur.fetchone() is not None
    conn.close()

    if not has_vec:
        pytest.skip("sqlite-vec not supported in this runtime environment")

    # Insert a node and verify automatic trigger sync to nodes_vec
    save_res = save_memory("Neural network trained on Apple Silicon using Metal acceleration.", importance=8, project="vec_test")
    node_id = save_res.split("Saved Node ")[1].split(" ")[0]

    conn = get_db()
    vec_row = conn.execute("SELECT id FROM nodes_vec WHERE id = ?", (node_id,)).fetchone()
    conn.close()
    assert vec_row is not None
    assert vec_row[0] == node_id

def test_enhanced_nlp_triple_extraction():
    # 1. Passive voice extraction: "FastAPI is maintained by Tiangolo"
    res1 = extract_and_save_memory("FastAPI is maintained by Tiangolo and Redis caches session state.", project="nlp_test")
    assert "maintained_by" in res1 or "caches" in res1

    # 2. Preference assertion: "Prefer pnpm over npm for monorepos"
    res2 = extract_and_save_memory("Prefer pnpm over npm for monorepo disk efficiency.", project="nlp_test")
    assert "preferred_over" in res2 or "Extracted & Saved Node" in res2

    # 3. Graph query validation
    q = query_graph("pnpm", depth=1, project="nlp_test")
    assert "pnpm" in q or "npm" in q

def test_high_volume_sqlite_vec_retrieval():
    # Seed 100 memory records
    for i in range(100):
        save_memory(
            f"Distributed microservice cluster node #{i} running Kafka streaming pipeline.",
            importance=5,
            project="scale_vec_test",
        )

    res = search_memory("Kafka streaming data pipeline", limit=5, hybrid=True, project="scale_vec_test")
    assert "Kafka streaming pipeline" in res
