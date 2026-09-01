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
    init_db()
    yield
    for f in ["test_full_suite.sqlite", "test_full_suite.sqlite-wal", "test_full_suite.sqlite-shm", "test_export.json"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

def test_auto_context_xml_formatting():
    save_memory("System architectural invariant: Never bypass SQLite WAL.", importance=10, category="architecture", project="ctx_test")
    save_memory("Low importance noise entry.", importance=2, category="noise", project="ctx_test")

    xml_res = auto_context(limit=3, min_importance=7, project="ctx_test")
    assert "<engram_context count='1'>" in xml_res
    assert "Never bypass SQLite WAL" in xml_res
    assert "noise entry" not in xml_res

def test_edit_and_delete_memory():
    save_res = save_memory("Original concept draft.", importance=5, category="draft", project="edit_test")
    node_id = save_res.split("Saved Node ")[1].split(" ")[0]

    # Edit
    edit_res = edit_memory(node_id, content="Refined concept finalized.", importance=9, category="final")
    assert "Successfully updated" in edit_res
    assert "Importance: 9" in edit_res

    # Verify edit in list
    list_res = list_memories(project="edit_test")
    assert "Refined concept finalized" in list_res

    # Delete
    del_res = delete_memory(node_id)
    assert f"Successfully deleted Node {node_id}" in del_res

    # Verify deletion
    list_after = list_memories(project="edit_test")
    assert "Refined concept finalized" not in list_after

def test_export_and_import():
    save_memory("Exportable memory fact 1", importance=8, category="export_cat", project="exp_test")
    save_memory("Exportable memory fact 2", importance=7, category="export_cat", project="exp_test")

    # Export
    cmd_export("test_export.json", project="exp_test")
    assert os.path.exists("test_export.json")

    with open("test_export.json", "r") as f:
        data = json.load(f)
        assert len(data["nodes"]) == 2

    # Import into new project
    cmd_import("test_export.json", project="imp_test")
    imp_list = list_memories(project="imp_test")
    assert "Exportable memory fact 1" in imp_list
    assert "Exportable memory fact 2" in imp_list
