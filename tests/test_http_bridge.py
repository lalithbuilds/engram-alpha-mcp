"""
Unit & Integration Tests for Engram Alpha HTTP & OpenAPI Web Gateway
Tests ChatGPT Custom Actions, Claude.ai Web, Gemini Web, and Browser Extension endpoints.
"""

import os
import json
import time
import urllib.request
import urllib.parse
import threading
import pytest
from pathlib import Path

os.environ["ENGRAM_DB_PATH"] = "test_http_gateway.sqlite"

from engram.core import init_db
from engram.http_bridge import start_http_gateway, get_openapi_schema
from engram.server import save_memory

TEST_PORT = 8999
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

@pytest.fixture(scope="module", autouse=True)
def run_test_server():
    if os.path.exists("test_http_gateway.sqlite"):
        try: os.remove("test_http_gateway.sqlite")
        except: pass

    init_db()
    server_thread = threading.Thread(
        target=start_http_gateway,
        kwargs={"host": "127.0.0.1", "port": TEST_PORT},
        daemon=True,
    )
    server_thread.start()
    time.sleep(0.5)
    yield
    for f in ["test_http_gateway.sqlite", "test_http_gateway.sqlite-wal", "test_http_gateway.sqlite-shm"]:
        if os.path.exists(f):
            try: os.remove(f)
            except: pass

def test_openapi_schema_generation():
    schema = get_openapi_schema("https://engram.example.com")
    assert schema["openapi"] == "3.0.0"
    assert "paths" in schema
    assert "/search" in schema["paths"]
    assert "/save" in schema["paths"]
    assert "/extract" in schema["paths"]
    assert "/graph" in schema["paths"]

def test_http_get_openapi_endpoint():
    req = urllib.request.Request(f"{BASE_URL}/openapi.json")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["openapi"] == "3.0.0"
        assert data["info"]["title"] == "Engram Alpha Universal Memory API"

def test_http_health_check():
    with urllib.request.urlopen(f"{BASE_URL}/health") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "healthy"
        assert "tier" in data

def test_http_save_and_search_endpoints():
    # 1. Save Memory via HTTP POST (Simulating ChatGPT Action)
    save_payload = json.dumps({
        "content": "ChatGPT Custom Action saved this architectural decision: use SQLite WAL for zero split-brain.",
        "category": "architecture",
        "importance": 9,
        "project": "chatgpt_project",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/save",
        data=save_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        save_resp = json.loads(resp.read().decode())
        assert save_resp["status"] == "success"

    # 2. Search Memory via HTTP GET (Simulating Claude.ai / Gemini Web prompt pre-fetch)
    query_url = f"{BASE_URL}/search?q=architectural+decision+SQLite+WAL&project=chatgpt_project"
    with urllib.request.urlopen(query_url) as resp:
        assert resp.status == 200
        search_resp = json.loads(resp.read().decode())
        assert search_resp["project"] == "chatgpt_project"
        assert "zero split-brain" in search_resp["results"]

def test_http_extract_and_graph_endpoints():
    # 1. Extract Triples via HTTP POST (Simulating web hook)
    extract_payload = json.dumps({
        "text": "RayOrchestrator uses FastMCP to connect with ClaudeWeb. [[WebBridge]]",
        "project": "web_graph_proj",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/extract",
        data=extract_payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        ext_resp = json.loads(resp.read().decode())
        assert ext_resp["status"] == "success"

    # 2. Query Knowledge Graph via HTTP GET
    graph_url = f"{BASE_URL}/graph?node=RayOrchestrator&depth=2&project=web_graph_proj"
    with urllib.request.urlopen(graph_url) as resp:
        assert resp.status == 200
        graph_resp = json.loads(resp.read().decode())
        assert "RayOrchestrator" in graph_resp["node"]
        assert "uses" in graph_resp["graph"] or "references" in graph_resp["graph"]

def test_http_cors_headers():
    # Verify browser extensions from chatgpt.com or claude.ai can call local gateway
    req = urllib.request.Request(f"{BASE_URL}/search?q=test", method="OPTIONS")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
        assert "GET" in resp.headers.get("Access-Control-Allow-Methods")

def test_concurrent_web_agent_requests():
    # Simulate simultaneous requests from ChatGPT, Claude Web, and Gemini Web
    def make_request(query, proj):
        url = f"{BASE_URL}/search?q={urllib.parse.quote(query)}&project={proj}"
        with urllib.request.urlopen(url) as resp:
            return resp.status == 200

    threads = []
    results = []

    def thread_worker(q, p):
        results.append(make_request(q, p))

    for i in range(20):
        t = threading.Thread(target=thread_worker, args=(f"Query_{i}", "chatgpt_project"))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(results) == 20
    assert all(results)

def test_http_dashboard_endpoint():
    with urllib.request.urlopen(f"{BASE_URL}/dashboard") as resp:
        assert resp.status == 200
        html = resp.read().decode()
        assert "<!DOCTYPE html>" in html
        assert "Engram Alpha Cognitive Dashboard" in html
        assert "Force-Directed" in html or "Semantic Memory Recall" in html

def test_http_bearer_auth(monkeypatch):
    monkeypatch.setenv("ENGRAM_API_KEY", "secret_test_token_123")

    # 1. Unauthenticated request should fail with 401
    try:
        req = urllib.request.Request(f"{BASE_URL}/search?q=test")
        urllib.request.urlopen(req)
        assert False, "Should have raised HTTP 401"
    except urllib.error.HTTPError as e:
        assert e.code == 401

    # 2. Authenticated request with Bearer token should succeed
    req_auth = urllib.request.Request(
        f"{BASE_URL}/search?q=test",
        headers={"Authorization": "Bearer secret_test_token_123"},
    )
    with urllib.request.urlopen(req_auth) as resp:
        assert resp.status == 200

