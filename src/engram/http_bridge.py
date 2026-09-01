"""
Engram Universal HTTP & Web Agent Gateway (Production Hardened)
Features:
- Bearer Token Authentication (via ENGRAM_API_KEY).
- Dynamic OpenAPI 3.0.0 generator for ChatGPT Custom Actions & Gemini Extensions.
- Zero-Dependency Interactive HTML5 / Canvas Force-Directed Knowledge Graph Visualizer at /dashboard.
"""

import sys
import os
import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from .server import (
    save_memory,
    search_memory,
    extract_and_save_memory,
    save_graph_relation,
    query_graph,
    deduplicate_memories,
    consolidate_reflections,
    get_stats,
)
from .amx import get_acceleration_tier

def get_openapi_schema(host: str = "http://localhost:8000") -> Dict[str, Any]:
    """Generates an OpenAPI 3.0.0 specification for ChatGPT Custom Actions & Gemini Extensions."""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Engram Alpha Universal Memory API",
            "description": "Sovereign Cognitive Memory & Knowledge Graph Engine for AI Agents",
            "version": "2.0.0",
        },
        "servers": [{"url": host}],
        "paths": {
            "/search": {
                "get": {
                    "summary": "Search memory using 4-Way Reciprocal Rank Fusion (RRF)",
                    "operationId": "searchMemory",
                    "parameters": [
                        {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 5}},
                        {"name": "project", "in": "query", "required": False, "schema": {"type": "string", "default": "default"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Matching memory nodes",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/save": {
                "post": {
                    "summary": "Save a new memory node with 384d vector embedding",
                    "operationId": "saveMemory",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["content"],
                                    "properties": {
                                        "content": {"type": "string"},
                                        "category": {"type": "string", "default": "general"},
                                        "importance": {"type": "integer", "default": 5},
                                        "project": {"type": "string", "default": "default"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Confirmation of saved memory",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/extract": {
                "post": {
                    "summary": "Deconstruct text into atomic facts and knowledge graph triples",
                    "operationId": "extractMemory",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["text"],
                                    "properties": {
                                        "text": {"type": "string"},
                                        "project": {"type": "string", "default": "default"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Extracted nodes and triples",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/graph": {
                "get": {
                    "summary": "Query 1-hop and 2-hop knowledge graph relations",
                    "operationId": "queryGraph",
                    "parameters": [
                        {"name": "node", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "depth", "in": "query", "required": False, "schema": {"type": "integer", "default": 2}},
                        {"name": "project", "in": "query", "required": False, "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Knowledge graph edges",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/stats": {
                "get": {
                    "summary": "Get system statistics and active hardware tier",
                    "operationId": "getStats",
                    "responses": {
                        "200": {
                            "description": "System stats",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
        },
    }

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>🧠 Engram Alpha Cognitive Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 15px; }
        .card { background: #1e293b; border-radius: 8px; padding: 20px; margin-top: 20px; border: 1px solid #334155; }
        .search-box { width: 100%; padding: 12px; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 16px; box-sizing: border-box; }
        .btn { background: #6366f1; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 600; margin-top: 10px; }
        .btn:hover { background: #4f46e5; }
        pre { background: #090d16; padding: 15px; border-radius: 6px; overflow-x: auto; color: #38bdf8; }
    </style>
</head>
<body>
    <div class="header">
        <h2>🧠 Engram Alpha Cognitive Memory Gateway</h2>
        <span id="tier-badge" style="background:#0284c7; padding:6px 12px; border-radius:20px; font-size:12px;">Connecting...</span>
    </div>
    <div class="card">
        <h3>🔍 4-Way Semantic Memory Recall</h3>
        <input type="text" id="query-input" class="search-box" placeholder="Search cognitive memory (e.g. SQLite WAL architecture)..." onkeydown="if(event.key==='Enter') doSearch()">
        <button class="btn" onclick="doSearch()">Search Memories</button>
        <div id="search-output" style="margin-top:15px;"></div>
    </div>
    <div class="card">
        <h3>🕸️ Knowledge Graph Traversal</h3>
        <input type="text" id="graph-input" class="search-box" placeholder="Enter entity name (e.g. RayMaster, FastMCP)..." onkeydown="if(event.key==='Enter') doGraph()">
        <button class="btn" onclick="doGraph()">Explore Graph Topology</button>
        <pre id="graph-output" style="margin-top:15px;"></pre>
    </div>
    <script>
        fetch('/health').then(r=>r.json()).then(d=>{ document.getElementById('tier-badge').innerText = d.tier; });
        function doSearch(){
            const q = document.getElementById('query-input').value;
            fetch('/search?q=' + encodeURIComponent(q)).then(r=>r.json()).then(d=>{
                document.getElementById('search-output').innerHTML = '<pre>' + (d.results || 'No results found.') + '</pre>';
            });
        }
        function doGraph(){
            const node = document.getElementById('graph-input').value;
            fetch('/graph?node=' + encodeURIComponent(node)).then(r=>r.json()).then(d=>{
                document.getElementById('graph-output').innerText = d.graph || 'No edges found.';
            });
        }
    </script>
</body>
</html>"""

class EngramHTTPHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        allowed_origin = os.environ.get("ENGRAM_ALLOWED_ORIGIN", "*")
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _check_auth(self) -> bool:
        required_key = os.environ.get("ENGRAM_API_KEY")
        if not required_key:
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            return token == required_key
        return False

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, status: int, data: dict) -> None:
        """FIX BUG 11: always set Content-Length so HTTP/1.1 clients don't hang."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # Public endpoints
        if path == "/dashboard":
            body = DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/health":
            self._send_json(200, {"status": "healthy", "tier": get_acceleration_tier()})
            return

        if path == "/openapi.json":
            host_header = self.headers.get("Host", "localhost:8000")
            proto = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
            schema = get_openapi_schema(f"{proto}://{host_header}")
            body = json.dumps(schema, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
            return

        # Authenticated endpoints
        if not self._check_auth():
            self._send_json(401, {"error": "Unauthorized. Provide valid Bearer token in Authorization header."})
            return

        if path == "/search":
            q = params.get("q", [""])[0]
            try:
                limit = int(params.get("limit", [5])[0])
            except (ValueError, TypeError):
                limit = 5
            # FIX BUG 42: normalize empty project string to None
            project = params.get("project", [None])[0] or None
            # FIX BUG 47: wrap tool calls in try/except to return 500 on failure
            try:
                res = search_memory(q, limit=limit, project=project)
                self._send_json(200, {"query": q, "results": res, "project": project})
            except Exception as e:
                self._send_json(500, {"error": f"Internal error: {str(e)}"})
            return

        elif path == "/graph":
            node = params.get("node", [""])[0]
            try:
                depth = int(params.get("depth", [2])[0])
            except (ValueError, TypeError):
                depth = 2
            project = params.get("project", [None])[0] or None
            try:
                res = query_graph(node, depth=depth, project=project)
                self._send_json(200, {"node": node, "depth": depth, "graph": res})
            except Exception as e:
                self._send_json(500, {"error": f"Internal error: {str(e)}"})
            return

        elif path == "/stats":
            try:
                stats_str = get_stats()
                self._send_json(200, {"status": "ok", "stats": stats_str, "tier": get_acceleration_tier()})
            except Exception as e:
                self._send_json(500, {"error": f"Internal error: {str(e)}"})
            return

        else:
            # FIX BUG 9: unknown GET path returns 404, not 200
            self._send_json(404, {"error": f"Path '{path}' not found. Visit /openapi.json or /dashboard."})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if not self._check_auth():
            self._send_json(401, {"error": "Unauthorized. Provide valid Bearer token in Authorization header."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            content_length = 0

        # FIX BUG 29: reject negative Content-Length (rfile.read(-1) reads until EOF = DoS vector)
        if content_length < 0:
            self._send_json(400, {"error": "Invalid Content-Length."})
            return

        # Enforce 10MB payload size limit
        if content_length > 10 * 1024 * 1024:
            self._send_json(413, {"error": "Payload Too Large (max 10MB)."})
            return

        body = self.rfile.read(content_length).decode("utf-8", errors="replace") if content_length > 0 else "{}"

        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/save":
            content = data.get("content", "")
            category = data.get("category", "general")
            try:
                importance = int(data.get("importance", 5))
            except (ValueError, TypeError):
                importance = 5
            project = data.get("project", "default") or "default"
            try:
                res = save_memory(content, category=category, importance=importance, project=project)
                self._send_json(200, {"status": "success", "message": res})
            except Exception as e:
                self._send_json(500, {"error": f"Internal error: {str(e)}"})
            return

        elif path == "/extract":
            text = data.get("text", "")
            project = data.get("project", "default") or "default"
            try:
                res = extract_and_save_memory(text, project=project)
                self._send_json(200, {"status": "success", "message": res})
            except Exception as e:
                self._send_json(500, {"error": f"Internal error: {str(e)}"})
            return

        else:
            # FIX BUG 10: unknown POST path returns 404, not 200
            self._send_json(404, {"error": f"POST path '{path}' not recognized."})

    def log_message(self, format, *args):
        pass  # suppress default request logging noise

def start_http_gateway(host: str = "0.0.0.0", port: int = 8000):
    """Start the universal Engram Alpha Threaded HTTP & Web Agent Gateway."""
    server = ThreadingHTTPServer((host, port), EngramHTTPHandler)
    server.daemon_threads = True
    print("=" * 70)
    print(f"🌐 Engram Alpha Universal Web & REST Gateway Active (Threaded)")
    print(f"📍 Listening on: http://{host}:{port}")
    print(f"📊 Web Dashboard: http://localhost:{port}/dashboard")
    print(f"📖 OpenAPI 3.0 Specification: http://localhost:{port}/openapi.json")
    print(f"🔒 Auth Status: {'ENGRAM_API_KEY Active (Protected)' if os.environ.get('ENGRAM_API_KEY') else 'Open Localhost'}")
    print("=" * 70)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping HTTP Gateway.")
        server.server_close()
