# 📊 Engram Alpha: Benchmark Suite & Reproducibility Guide

This document contains empirical performance benchmarks, hardware tier specifications, and step-by-step instructions to reproduce all latency, throughput, and accuracy metrics for **Engram Alpha**.

---

## 🏛️ Hardware Tier Matrix

Engram Alpha dynamically detects and leverages host hardware capabilities through a 3-tier compute hierarchy:

| Tier | Engine / Architecture | Acceleration Target | Typical Vector Scan Rate |
| :--- | :--- | :--- | :---: |
| **Tier 1 (macOS)** | Apple Silicon AMX via `Accelerate.framework` | M1/M2/M3/M4 Matrix Coprocessor | **1,200,000+ vecs/sec** |
| **Tier 2 (Linux/Win)**| C-BLAS via `libblas.so.3` / `cblas.dll` | SIMD / AVX2 / AVX-512 | **~350,000 vecs/sec** |
| **Tier 3 (Generic)** | Pure Python Stdlib Matrix Fallback | Generic CPU / Shared Containers | **~85,000 vecs/sec** |

---

## 🔬 Benchmark 1: Micro-Architecture Performance (`benchmark_custom.py`)

Measures pure memory substrate latency and computational throughput without disk I/O bottlenecks.

### Test Protocol
* **Vector Dimension:** 384-float dense embeddings (`BAAI/bge-small-en-v1.5`)
* **Runs:** 5 consecutive runs (reporting Min / Median / Max)

### Empirical Results

| Metric | Tier 1: Apple Silicon M4 Max | Tier 2: Linux x86_64 (C-BLAS) | Tier 3: Stdlib Fallback |
| :--- | :---: | :---: | :---: |
| **4-Way RRF Hybrid Search (p50)** | **1.21 ms** (1.10–1.35 ms) | **5.40 ms** (4.80–6.20 ms) | **14.20 ms** (12.5–16.8 ms) |
| **Vector Dot-Product Scan Rate** | **1,248,500 / sec** | **342,000 / sec** | **84,500 / sec** |
| **4-Hop Recursive CTE Graph Walk** | **0.34 ms** (0.30–0.41 ms) | **1.15 ms** (1.05–1.30 ms) | **2.90 ms** (2.50–3.40 ms) |

### How to Reproduce
```bash
git clone https://github.com/lalithbuilds/engram-alpha-mcp.git
cd engram-alpha-mcp
pip install -e .
PYTHONPATH=src python3 benchmark/benchmark_custom.py
```

---

## 🧪 Benchmark 2: LongMemEval Needle-in-a-Haystack (`benchmark_longmemeval.py`)

Measures multi-session retrieval accuracy, temporal reasoning, and contradiction resistance against 10 multi-step needle queries embedded across noisy distraction memories.

### Empirical Results

| Metric | Measured Score | Baseline Target |
| :--- | :---: | :---: |
| **Accuracy (Exact Match)** | **100.0% (10/10)** | $\ge 90.0\%$ |
| **Recall@5** | **1.00 (10/10)** | $\ge 0.95$ |
| **Total Evaluation Latency** | **0.176 s** | $< 2.0 s$ |

### How to Reproduce
```bash
PYTHONPATH=src python3 benchmark/benchmark_longmemeval.py
```

---

## ⚡ Benchmark 3: Model Council Gauntlet Level 5 (`stress_sandbox_council.py`)

Measures high-concurrency ACID SQLite WAL performance under extreme multi-threaded read/write contention, live Markdown file parsing, and semantic deduplication.

### Architecture & Workload Definition
The **7-Agent Model Council** is a concurrent test harness simulating 7 heterogeneous worker archetypes running in parallel:
1. **`Claude_Fable` (250 ops):** Complex Entity Extraction & Knowledge Triples.
2. **`Gemini_Pro_3` (250 ops):** High-frequency 4-Way RRF Hybrid Searches across projects.
3. **`Kimi_K3` (40 ops):** Live filesystem vault generation, note creation, and incremental chunking.
4. **`GPT_Soul` (250 ops):** ACT-R Power-Law Decay scoring & spaced practice updates.
5. **`Deep_Research` (250 ops):** Semantic deduplication clustering & reflection synthesis.
6. **`GLM_5_2` (250 ops):** Batch matrix vector dot-product operations.
7. **`O1_Pro` (250 ops):** 2-hop relational knowledge graph traversals.

### Empirical Results Across Environments (Median of 5 Runs)

| Metric | Tier 1: Apple Silicon (Local NVMe) | Tier 2: Shared Cloud Linux Container |
| :--- | :---: | :---: |
| **Total Operations Executed** | **1,540 ops** | **1,540 ops** |
| **Aggregate Throughput** | **278.9 ops/sec** | **96.2 – 135.0 ops/sec** |
| **Latency p50** | **1.12 ms** | **8.00 ms** |
| **Latency p95** | **39.50 ms** | **126.07 ms** |
| **Latency p99** | **141.13 ms** | **538.53 ms** |
| **Concurrency Deadlocks / Errors** | **0 (0.00%)** | **0 (0.00%)** |
| **`PRAGMA integrity_check`** | **`ok` (100% Verified)** | **`ok` (100% Verified)** |

> **Root Cause of Hardware Variance:** `Kimi_K3` generates and writes physical Markdown files to disk while `Claude_Fable` and `Deep_Research` commit WAL transactions. Systems with high-speed NVMe flash storage achieve ~280 ops/sec with low tail latencies; virtualized cloud containers with throttled disk I/O experience higher p95/p99 tail latencies due to shared virtual filesystem write barriers.

### How to Reproduce
```bash
PYTHONPATH=src python3 stress_sandbox_council.py
```

---

## 🛠️ Concurrency & Connection Pool Architecture

Engram Alpha implements **Thread-Local Connection Pooling (`threading.local()`)**:
* **Connection Reuse:** Each worker thread maintains a persistent, warm SQLite connection handle.
* **Elimination of Lock Churn:** Eliminates redundant `sqlite3.connect()` allocations, PRAGMA re-evaluations, and file-descriptor negotiation overhead during concurrent bursts.
* **ACID Safety:** Uncommitted transactions are safely rolled back upon tool completion (`conn.close()`), ensuring zero transaction leakage across worker threads.
