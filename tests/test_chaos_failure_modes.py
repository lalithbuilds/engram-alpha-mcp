"""
Chaos, Failure Mode & Crash Diagnostic Test Suite for Engram Alpha MCP
Proactively stress-tests edge cases, malicious inputs, cyclic loops,
concurrency race collisions, and resource exhaustion.
"""

import os
import sys
import math
import struct
import time
import threading
import sqlite3
import pytest
from pathlib import Path

os.environ["ENGRAM_DB_PATH"] = "test_chaos.sqlite"

from engram.core import init_db, get_db, optimize_and_checkpoint, check_storage_liveness
from engram.amx import (
    amx_cosine_similarity,
    amx_batch_cosine_similarity,
    pack_vector,
    unpack_vector,
    generate_dense_embedding,
)
from engram.server import (
    save_memory,
    search_memory,
    save_graph_relation,
    query_graph,
    extract_and_save_memory,
    deduplicate_memories,
    checkpoint_db,
)

@pytest.fixture(autouse=True)
def setup_chaos_db():
    if os.path.exists("test_chaos.sqlite"):
        try: os.remove("test_chaos.sqlite")
        except: pass
    init_db()
    yield
    for f in ["test_chaos.sqlite", "test_chaos.sqlite-wal", "test_chaos.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

# ----------------------------------------------------------------------
# 1. MALFORMED INPUTS & FTS5 INJECTION ATTACKS
# ----------------------------------------------------------------------

def test_fts5_syntax_injection_and_malformed_queries():
    """Test malformed query strings that typically crash SQLite FTS5 (e.g. unclosed quotes, wildcards, operators)."""
    save_memory("Normal valid memory for injection testing", project="chaos_proj")

    poisoned_queries = [
        '"""""',
        'AND OR NOT ()',
        'NEAR(foo, bar, 10)',
        '* * * *',
        'content: "unclosed string',
        '\\x00\\x01\\x02\\xff',
        'SELECT * FROM nodes WHERE 1=1; --',
        '\' OR \'1\'=\'1',
        'a' * 50000,  # 50KB query string
        '',            # Empty query
        '   \t\n\r   ', # Whitespace query
    ]

    for q in poisoned_queries:
        try:
            res = search_memory(q, project="chaos_proj")
            assert isinstance(res, str)
        except Exception as e:
            pytest.fail(f"search_memory crashed on query '{q[:30]}...': {type(e).__name__} - {e}")

def test_extreme_payload_sizes():
    """Test saving huge memory strings (100KB to 1MB)."""
    large_payload = "Architecture rule: " + ("abcdefghij " * 10000) # ~110KB
    try:
        res = save_memory(large_payload, project="chaos_proj", importance=5)
        assert "Saved Node" in res
    except Exception as e:
        pytest.fail(f"save_memory crashed on large payload: {e}")

# ----------------------------------------------------------------------
# 2. CYCLIC GRAPH LOOPS & DEEP RECURSION
# ----------------------------------------------------------------------

def test_cyclic_graph_infinite_loop_prevention():
    """Test cyclic dependencies A -> B -> C -> D -> A under max recursion depth."""
    save_graph_relation("Node_Alpha", "points_to", "Node_Beta", project="loop_proj")
    save_graph_relation("Node_Beta", "points_to", "Node_Gamma", project="loop_proj")
    save_graph_relation("Node_Gamma", "points_to", "Node_Delta", project="loop_proj")
    save_graph_relation("Node_Delta", "points_to", "Node_Alpha", project="loop_proj") # Cycle!

    # Query with depth 5 - must NOT hang or raise recursion depth error
    start_t = time.perf_counter()
    res = query_graph("Node_Alpha", depth=5, project="loop_proj")
    elapsed = time.perf_counter() - start_t

    assert elapsed < 1.0, f"query_graph took too long ({elapsed:.3f}s), possible cycle hang!"
    assert "Node_Alpha" in res
    assert "Node_Delta" in res

# ----------------------------------------------------------------------
# 3. VECTOR MATH CORRUPTIONS (NaN, Inf, Zero Norm)
# ----------------------------------------------------------------------

def test_corrupt_vector_floats():
    """Test packing and cosine similarity against NaN, Inf, and Zero vectors."""
    # 1. Zero vector
    zero_vec = [0.0] * 384
    packed_zero = pack_vector(zero_vec)
    unpacked_zero = unpack_vector(packed_zero)
    assert len(unpacked_zero) == 384

    # 2. Dot product with zero vector
    norm_vec = [1.0 / math.sqrt(384)] * 384
    sim = amx_cosine_similarity(zero_vec, norm_vec)
    assert sim == 0.0 or math.isclose(sim, 0.0, abs_tol=1e-6)

    # 3. Malformed unaligned bytes blob in unpack_vector (19 bytes = 4 floats + 3 extra bytes)
    short_blob = b"short_corrupt_bytes"
    try:
        res = unpack_vector(short_blob)
        assert len(res) == 4  # Unpacks 4 valid floats, does not crash on unaligned trailing bytes
    except Exception as e:
        pytest.fail(f"unpack_vector crashed on corrupted blob: {e}")

# ----------------------------------------------------------------------
# 4. HIGH CONCURRENCY RACE COLLISIONS (Dedupe vs Write vs Read)
# ----------------------------------------------------------------------

def test_high_concurrency_race_collisions():
    """
    Simultaneously execute:
    - Thread 1-5: Heavy Writes (save_memory, extract_and_save_memory)
    - Thread 6-10: Heavy Reads (search_memory with access_count updates)
    - Thread 11-12: Deduplication Agent (deleting & merging rows)
    - Thread 13: WAL Checkpoint & Optimizer
    """
    errors = []
    stop_flag = False

    def writer(idx):
        count = 0
        while not stop_flag and count < 30:
            try:
                save_memory(f"Concurrent data entry {idx}_{count} with FastMCP knowledge.", project="race_proj")
                count += 1
            except Exception as e:
                errors.append(f"Writer {idx} error: {e}")
            time.sleep(0.01)

    def reader(idx):
        count = 0
        while not stop_flag and count < 30:
            try:
                search_memory("FastMCP knowledge", project="race_proj")
                count += 1
            except Exception as e:
                errors.append(f"Reader {idx} error: {e}")
            time.sleep(0.01)

    def deduper():
        count = 0
        while not stop_flag and count < 10:
            try:
                deduplicate_memories(similarity_threshold=0.85, project="race_proj")
                count += 1
            except Exception as e:
                errors.append(f"Deduper error: {e}")
            time.sleep(0.03)

    def optimizer():
        count = 0
        while not stop_flag and count < 5:
            try:
                optimize_and_checkpoint()
                count += 1
            except Exception as e:
                errors.append(f"Optimizer error: {e}")
            time.sleep(0.05)

    threads = []
    for i in range(5):
        threads.append(threading.Thread(target=writer, args=(i,)))
    for i in range(5):
        threads.append(threading.Thread(target=reader, args=(i,)))
    threads.append(threading.Thread(target=deduper))
    threads.append(threading.Thread(target=optimizer))

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=15.0)

    stop_flag = True

    # Check for any fatal crashes during concurrent mutations
    assert len(errors) == 0, f"Encountered {len(errors)} concurrency errors during race test: {errors[:5]}"

# ----------------------------------------------------------------------
# 5. STORAGE LIVELOCK / CORRUPT FILE BEHAVIOR
# ----------------------------------------------------------------------

def test_database_permission_error_graceful_handling():
    """Verify that a permission-denied / read-only SQLite database raises clean exceptions instead of segfaults."""
    p = Path("test_readonly.sqlite")
    if p.exists():
        p.unlink()

    # Create dummy file
    conn = sqlite3.connect("test_readonly.sqlite")
    conn.execute("CREATE TABLE t (x TEXT);")
    conn.commit()
    conn.close()

    os.chmod("test_readonly.sqlite", 0o400) # Read only

    old_env = os.environ.get("ENGRAM_DB_PATH")
    os.environ["ENGRAM_DB_PATH"] = "test_readonly.sqlite"

    try:
        # Saving should cleanly raise an error or handle without segfaulting
        try:
            save_memory("Attempting write to read-only DB", project="ro_test")
        except Exception as e:
            assert "readonly" in str(e).lower() or "permission" in str(e).lower() or "attempt to write a readonly database" in str(e).lower()
    finally:
        try:
            os.chmod("test_readonly.sqlite", 0o600)
            if p.exists():
                p.unlink()
        except Exception:
            pass
        if old_env is not None:
            os.environ["ENGRAM_DB_PATH"] = old_env
        else:
            os.environ.pop("ENGRAM_DB_PATH", None)
        from engram.core import _INITIALIZED_PATHS
        _INITIALIZED_PATHS.discard(str(p.resolve()))
