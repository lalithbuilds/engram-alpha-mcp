# 🚀 EPISODA MCP: GLOBAL LAUNCH & DISTRIBUTION KIT

Author: Lalith Chandra (@lalithbuilds), Nashik, Maharashtra
Repos:
- Flagship: https://github.com/lalithbuilds/episodai
- Standard: https://github.com/lalithbuilds/episoda-core-mcp

---

## 1. 📢 Hacker News ("Show HN") Pitch
**Title:** Show HN: Episoda – 1.25M vecs/sec local memory MCP for Claude & Cursor (AMX, zero cloud)
**Link / Text:**
Hey HN,

I built Episoda to solve a persistent issue in AI-assisted coding: LLM amnesia and the ridiculous overhead of cloud memory systems.

Existing agent memory tools either:
1. Drag in 500MB+ Docker stacks (Chroma, Postgres, pgvector) with 50ms+ query lag.
2. Route code secrets and embeddings to cloud APIs ($$$ and 300ms roundtrips).

Episoda is an open-source Model Context Protocol (MCP) server running 100% locally with zero cloud egress:

- **Episodai:** Leverages Apple Silicon AMX (Accelerate.framework `cblas_sdot`) to scan 1,248,500 vecs/sec at 1.21ms p50 latency. Fuses dense vectors + FTS5 trigrams + knowledge graph CTEs + ACT-R cognitive decay (4-Way RRF). Syncs natively with Obsidian vaults.
- **Episoda Core:** Strictly 0 dependencies. Pure Python 3 standard library with Ebbinghaus exponential auto-decay and SQLite WAL.

Run it in Claude Desktop or Cursor instantly:
```json
{
  "mcpServers": {
    "episoda": {
      "command": "uvx",
      "args": ["episodai"]
    }
  }
}
```

GitHub: https://github.com/lalithbuilds/episodai
Documentation: https://lalithbuilds.github.io/episodai/

Would love your feedback on our benchmark harness and multi-tier concurrency testing.

---

## 2. 🧵 X (Twitter) Launch Thread

**Post 1:**
Tired of Claude & Cursor forgetting your architecture decisions between sessions? 🧠

Introducing **Episoda MCP**: Sovereign, hardware-accelerated local memory for AI coding agents.

⚡ 1,248,500 vecs/sec (Apple Silicon AMX)
⏱️ 1.21ms p50 latency
🔒 100% zero cloud egress
💎 Zero-config `uvx episodaii`

Thread 🧵👇

**Post 2:**
Why another memory tool?
Most solutions (Mem0, Zep) force your proprietary code into third-party cloud APIs or drag in massive Docker stacks.

Episoda runs in-process on a single SQLite WAL file with native Obsidian vault sync and 4-Way Reciprocal Rank Fusion (RRF).

**Post 3:**
We built two editions:
1. **Episodai**: AMX SIMD acceleration + bi-temporal knowledge graph + fastembed.
2. **Episoda Core**: Strictly ZERO external dependencies. Runs on pure Python standard library (`sqlite3`, `json`, `hashlib`).

Repo: https://github.com/lalithbuilds/episodai
Docs: https://lalithbuilds.github.io/episodai/

Star ⭐ and try it in Cursor today!

---

## 3. 🔴 Reddit Pitch (r/LocalLLaMA, r/ClaudeAI, r/Cursor)

**Title:** [Release] Episoda: Sub-2ms local memory MCP server for Claude Desktop & Cursor (Apple Silicon AMX, zero cloud egress)

**Body:**
Hey everyone,

Whenever I started a new session in Cursor or Claude Code, it would re-read tens of thousands of tokens of file trees, or completely forget past architectural decisions.

I built **Episoda**, an open-source MCP memory substrate designed for speed and sovereignty:
- **Zero Cloud Leakage:** All state resides in a local SQLite WAL file on your machine.
- **Apple Silicon Hardware Acceleration:** Direct macOS Accelerate bindings (AMX) scanning 1.25M vectors/sec at 1.21ms p50.
- **4-Way RRF Hybrid Search:** Combines dense vectors, trigram FTS5 lexical matching, recursive knowledge graph walks, and ACT-R cognitive power-law decay so stale context gracefully fades away.
- **Obsidian Sync:** Turns local Markdown files and `[[wikilinks]]` into a live queryable graph for your LLM.

Instant Cursor / Claude Desktop setup:
```json
{
  "mcpServers": {
    "episoda": {
      "command": "uvx",
      "args": ["episodai"]
    }
  }
}
```

Code is MIT licensed: https://github.com/lalithbuilds/episodai
Docs: https://lalithbuilds.github.io/episodai/
