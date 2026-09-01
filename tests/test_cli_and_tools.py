"""
Comprehensive Unit Tests for Full Engram Alpha Command & Tool Suite:
Tests auto_context, edit_memory, delete_memory, list_memories, export, and import.
"""

import os
import json
import pytest
from pathlib import Path

os.environ["ENGRAM_DB_PATH"] = "test_full_suite.sqlite"

from engram.core import init_db
from engram.server import (
    save_memory,
    search_memory,
    auto_context,
    edit_memory,
    delete_memory,
    list_memories,
)
from engram.cli import cmd_export, cmd_import

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    if os.path.exists("test_full_suite.sqlite"):
        try: os.remove("test_full_suite.sqlite")
        except: pass
    init_db(force=True)
    yield
    for f in ["test_full_suite.sqlite", "test_full_suite.sqlite-wal", "test_full_suite.sqlite-shm", "test_export.json"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

def test_auto_context_xml_formatting():
    save_memory("System architectural invariant: Never bypass SQLite WAL.", importance=10, category="architecture", project="ctx_test")
    save_memory("Low importance noise entry.", importance=2, category="noise", project="ctx_test")

    xml_res = auto_context(limit=3, min_importance=7, project="ctx_test")
    assert "<engram_context count='" in xml_res
    assert "Never bypass SQLite WAL" in xml_res
    assert "Low importance noise entry" not in xml_res

def test_edit_and_delete_memory():
    save_res = save_memory("Memory node to edit and delete", importance=5, project="edit_test")
    node_id = save_res.split("Saved Node ")[1].split(" ")[0]

    # Edit memory
    edit_res = edit_memory(node_id, content="Updated memory content", importance=9, category="updated_cat")
    assert "Successfully updated" in edit_res

    # Search for updated content
    search_res = search_memory("Updated memory content", limit=1, hybrid=False, project="edit_test")
    assert "Updated memory content" in search_res

    # Delete memory
    del_res = delete_memory(node_id)
    assert "Successfully deleted" in del_res

    # Verify deleted
    post_del_search = search_memory("Updated memory content", limit=1, hybrid=False, project="edit_test")
    assert "No relevant memories found" in post_del_search

def test_export_and_import():
    save_memory("Exportable memory fact 1", importance=8, category="export_cat", project="exp_test")
    save_memory("Exportable memory fact 2", importance=7, category="export_cat", project="exp_test")

    # Export
    cmd_export("test_export.json", project="exp_test")
    assert os.path.exists("test_export.json")

    with open("test_export.json", "r") as f:
        data = json.load(f)
        assert len(data["nodes"]) >= 2

    # Import into new project
    cmd_import("test_export.json", project="imp_test")
    imp_list = list_memories(project="imp_test")
    assert "Exportable memory fact 1" in imp_list
    assert "Exportable memory fact 2" in imp_list
