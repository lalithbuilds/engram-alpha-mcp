"""
Engram Universal HTTP & Web Agent Gateway (Zero-Dependency Stdlib)
Enables web agents (ChatGPT Custom GPT Actions, Claude.ai, Gemini Web,
Browser Extensions, and Remote MCP Clients) to interact with Engram Alpha.
Includes built-in OpenAPI 3.0.0 specification generator.
"""

import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
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

class EngramHTTPHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()

        if path == "/openapi.json":
            host_header = self.headers.get("Host", "localhost:8000")
            proto = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
            schema = get_openapi_schema(f"{proto}://{host_header}")
            self.wfile.write(json.dumps(schema, indent=2).encode("utf-8"))
            return

        elif path == "/search":
            q = params.get("q", [""])[0]
            limit = int(params.get("limit", [5])[0])
            project = params.get("project", [None])[0]
            res = search_memory(q, limit=limit, project=project)
            self.wfile.write(json.dumps({"query": q, "results": res, "project": project}).encode("utf-8"))
            return

        elif path == "/graph":
            node = params.get("node", [""])[0]
            depth = int(params.get("depth", [2])[0])
            project = params.get("project", [None])[0]
            res = query_graph(node, depth=depth, project=project)
            self.wfile.write(json.dumps({"node": node, "depth": depth, "graph": res}).encode("utf-8"))
            return

        elif path == "/stats":
            stats_str = get_stats()
            self.wfile.write(json.dumps({"status": "ok", "stats": stats_str, "tier": get_acceleration_tier()}).encode("utf-8"))
            return

        elif path == "/health":
            self.wfile.write(json.dumps({"status": "healthy", "tier": get_acceleration_tier()}).encode("utf-8"))
            return

        else:
            self.wfile.write(json.dumps({"error": f"Path '{path}' not found. Visit /openapi.json for docs."}).encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()

        if path == "/save":
            content = data.get("content", "")
            category = data.get("category", "general")
            importance = int(data.get("importance", 5))
            project = data.get("project", "default")
            res = save_memory(content, category=category, importance=importance, project=project)
            self.wfile.write(json.dumps({"status": "success", "message": res}).encode("utf-8"))
            return

        elif path == "/extract":
            text = data.get("text", "")
            project = data.get("project", "default")
            res = extract_and_save_memory(text, project=project)
            self.wfile.write(json.dumps({"status": "success", "message": res}).encode("utf-8"))
            return

        else:
            self.wfile.write(json.dumps({"error": f"POST path '{path}' not recognized."}).encode("utf-8"))

def start_http_gateway(host: str = "0.0.0.0", port: int = 8000):
    """Start the universal Engram Alpha HTTP & Web Agent Gateway."""
    server = HTTPServer((host, port), EngramHTTPHandler)
    print("=" * 70)
    print(f"🌐 Engram Alpha Universal Web & REST Gateway Active")
    print(f"📍 Listening on: http://{host}:{port}")
    print(f"📖 OpenAPI 3.0 Specification: http://localhost:{port}/openapi.json")
    print(f"🤖 Compatible with: ChatGPT Custom Actions, Claude.ai, Gemini Web, Browser Extensions")
    print("=" * 70)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping HTTP Gateway.")
        server.server_close()
