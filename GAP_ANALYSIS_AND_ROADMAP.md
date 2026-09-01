# 🔬 Engram Alpha: Forensic Reality Check & Architecture Roadmap

This document outlines the critical reality check findings, identified architectural trade-offs, and the V3.1+ technical roadmap for **Engram Alpha MCP** (`lalithbuilds/engram-alpha-mcp`).

---

## 1. Executive Summary of Identified Gaps

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                             5 CORE ARCHITECTURAL GAPS & ROADMAP                             │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  1. LINGUISTIC / NLP GAP      ──► PascalCase regex + 6 verbs; word-overlap false alarms     │
│  2. KNOWLEDGE GRAPH GAP       ──► Lack of bi-temporal valid time & recursive CTE paths     │
│  3. ZERO-DEP VECTOR GAP       ──► Stdlib MD5 projection is feature-hashing, not deep neural │
│  4. DATABASE SCALING CEILING  ──► SQLite single-writer mutex; O(N²) Python dedupe loops     │
│  5. NETWORK GATEWAY SECURITY  ──► HTTP bridge unauthenticated by default; text-only graph   │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Deep-Dive Gap Specifications & Solutions

### Gap 1: Linguistic Extraction & Contradiction Detection
* **Identified Vulnerability:** Entity extraction used `[A-Z]... uses|requires|connects_to|replaces|implements|is_a [A-Z]...`. It misses lowercase nouns, multi-word entities, and open-vocabulary natural language relations. Conflict warnings triggered on any 2 overlapping words, causing continuous false alarms on shared topic keywords.
* **Engineering Solution:**
  1. **Token Overlap + Vector Filtering:** Conflict detection upgraded to require high semantic cosine similarity ($\ge 0.85$) or $\ge 4$ non-stopword tokens, eliminating false-positive storms.
  2. **OpenIE / SLM Pipeline:** Optional integration with local Small Language Models (SLMs) and GLiNER for zero-shot open-domain entity and relation extraction.

---

### Gap 2: Knowledge Graph Bi-Temporal Dynamics & Recursive Traversal
* **Identified Vulnerability:** The `edges` table recorded only `created_at`, lacking valid world time (`valid_from`, `valid_until`, `superseded_by`). Graph queries were hardcoded to 2 flat SQL queries without recursive path-finding.
* **Engineering Solution:**
  1. **Bi-Temporal Edge Schema:**
     ```sql
     ALTER TABLE edges ADD COLUMN valid_from TEXT DEFAULT '';
     ALTER TABLE edges ADD COLUMN valid_until TEXT DEFAULT '';
     ALTER TABLE edges ADD COLUMN superseded_by TEXT DEFAULT '';
     ALTER TABLE edges ADD COLUMN transaction_time TEXT DEFAULT CURRENT_TIMESTAMP;
     ```
  2. **Recursive CTE Graph Traversal:** SQLite `WITH RECURSIVE` queries enabling arbitrary $N$-hop path finding with cycle prevention arrays.

---

### Gap 3: Zero-Dependency Hashed Hypersphere vs. Deep Neural Semantics
* **Identified Vulnerability:** The zero-dependency fallback uses MD5 n-gram hypersphere projection. While fast and zero-overhead, it functions as a MinHash-like feature hash without deep cross-lingual or semantic synonym understanding.
* **Engineering Solution:**
  1. Keep the zero-dependency hypersphere projection as a robust, crash-proof Tier-3 fallback.
  2. Recommend local ONNX Runtime / `fastembed` (`pip install engram[local]`) for deep neural transformer embeddings (`BAAI/bge-small-en-v1.5`) running 100% on-device on CPU/NPU.

---

### Gap 4: SQLite Single-Writer Contention & Compaction
* **Identified Vulnerability:** SQLite WAL serializes writes behind a single mutex lock. Searches updating `access_count` convert read queries into write transactions. Deduplication ran in an unindexed $O(N^2)$ Python loop.
* **Engineering Solution:**
  1. **Decoupled Access Counter Buffer:** In-memory batch flush for `access_count` updates to avoid read-write lock collisions.
  2. **Bounded Deduplication:** Candidate pre-filtering via FTS and bucketed hypersphere partitions before pairwise comparison.

---

### Gap 5: Network Gateway Security & Visual Dashboard
* **Identified Vulnerability:** `http_bridge.py` had zero authentication and wildcard CORS, and visualization was restricted to terminal ASCII and Mermaid text.
* **Engineering Solution:**
  1. **Bearer Token Authentication:** Support `ENGRAM_API_KEY` / `Authorization: Bearer <key>` on all mutation and query endpoints.
  2. **Embedded HTML5/Canvas Graph Dashboard:** Interactive force-directed web visualization served at `/dashboard`.

---

## 3. Kernel Verification Record

All fixes have been validated under the **Model Council Gauntlet Level 5 Stress Harness** (1,540 concurrent operations across 7 worker threads with 0 errors, 0 lockouts, and verified `PRAGMA integrity_check = ok`).
