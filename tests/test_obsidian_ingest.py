"""
Tests for Engram Obsidian Markdown Graph Ingestion Pipeline
"""

import os
import pytest
import tempfile
from pathlib import Path

os.environ["ENGRAM_DB_PATH"] = "test_ingest.sqlite"

from engram.core import init_db, get_db, _INITIALIZED_PATHS
from engram.ingest import (
    chunk_markdown,
    extract_metadata_and_links,
    ingest_obsidian_vault,
)
from engram.server import query_graph, search_memory

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    for f in ["test_ingest.sqlite", "test_ingest.sqlite-wal", "test_ingest.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except Exception: pass
    _INITIALIZED_PATHS.clear()
    init_db(force=True)
    yield
    for f in ["test_ingest.sqlite", "test_ingest.sqlite-wal", "test_ingest.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except Exception: pass
    _INITIALIZED_PATHS.clear()

def test_chunk_markdown():
    text = " ".join([f"word{i}" for i in range(350)])
    chunks = chunk_markdown(text, chunk_size_words=150, overlap_words=25)
    assert len(chunks) == 3
    assert len(chunks[0].split()) == 150
    assert len(chunks[1].split()) == 150

def test_extract_metadata_and_links():
    md_content = """
    # Architecture Overview
    We utilize [[Ray_Daemon]] and [[Quant_Engine]] for processing.
    Tags: #agent_memory #apple_silicon/m4 #finance
    See also [[Ray_Daemon|Ray Core Daemon]].
    """
    wikilinks, tags = extract_metadata_and_links(md_content)
    assert "Ray_Daemon" in wikilinks
    assert "Quant_Engine" in wikilinks
    assert "agent_memory" in tags
    assert "apple_silicon/m4" in tags
    assert "finance" in tags

def test_ingest_obsidian_vault(tmp_path):
    # Setup test markdown files
    doc1 = tmp_path / "System_Architecture.md"
    doc1.write_text("""
    # System Architecture
    The system connects to [[Central_Memory]] and executes [[AMX_Vector_Engine]].
    Tagged with #memory #apple_m4
    Engram Alpha delivers immortal memory for AI coding agents.
    """)

    doc2 = tmp_path / "Central_Memory.md"
    doc2.write_text("""
    # Central Memory
    Central memory manages SQLite WAL and links to [[Ray_Daemon]].
    Tagged with #database #sqlite
    """)

    res = ingest_obsidian_vault(str(tmp_path))
    assert res["status"] == "success"
    assert res["files_processed"] == 2
    assert res["nodes_created"] >= 2
    assert res["edges_created"] >= 4

    # Verify Knowledge Graph relations
    graph_res = query_graph("System_Architecture")
    assert "links_to" in graph_res
    assert "Central_Memory" in graph_res

    # Verify Search
    search_res = search_memory("Engram Alpha immortal memory")
    assert "System_Architecture" in search_res

def teardown_module(module):
    for f in ["test_ingest.sqlite", "test_ingest.sqlite-wal", "test_ingest.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass
