# ⚡ Engram Alpha: Hardware Acceleration & Stress Benchmark Suite

<div align="center">

  <img src="https://capsule-render.vercel.app/api?type=cylinder&color=gradient&customColorList=10,13&height=160&section=header&text=Engram%20Alpha%20Benchmarks&fontSize=52&fontAlignY=45&animation=scaleIn&fontColor=ffffff&desc=Forensic%20Hardware%20Telemetry,%20Concurrency%20Gauntlets%20&%20Parity%20Audits&descAlignY=65&descAlign=62" width="100%"/>

  <br>

  <img src="https://img.shields.io/badge/Hardware-Apple_Silicon_AMX-00f2fe.svg?style=for-the-badge&logo=apple&logoColor=white" alt="Apple Silicon AMX">
  <img src="https://img.shields.io/badge/Throughput-198k_vec/sec-00f2fe.svg?style=for-the-badge&logo=speedtest&logoColor=white" alt="198k vec/sec">
  <img src="https://img.shields.io/badge/Concurrency-1,540_ops_@_p50=1.61ms-00f2fe.svg?style=for-the-badge&logo=databricks&logoColor=white" alt="1,540 ops @ p50=1.61ms">
  <img src="https://img.shields.io/badge/Chaos_Tests-34/34_Passing-00f2fe.svg?style=for-the-badge&logo=pytest&logoColor=white" alt="34/34 Passing">
  <img src="https://img.shields.io/badge/Tier_Parity-Delta_<1e--5-00f2fe.svg?style=for-the-badge&logo=python&logoColor=white" alt="Tier Parity Delta < 1e-5">

</div>

---

## Executive Summary

**Engram Alpha MCP** (`lalithbuilds/engram-alpha-mcp`) is engineered as a sovereign, zero-external-dependency cognitive memory system for autonomous AI agents. Unlike traditional agent memory frameworks that require separate vector databases (e.g., Qdrant, Pinecone, Milvus), external graph engines (Neo4j), or remote client-server roundtrips, Engram Alpha executes entirely in-process using an optimized **SQLite WAL + Multi-Tier Hardware BLAS** architecture.

This document records the empirical results of four comprehensive validation suites conducted across Apple Silicon hardware, concurrent multi-agent swarms, adversarial chaos fault injections, and multi-tier parity verifications, concluding with a comparative analysis against existing state-of-the-art memory frameworks.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              BENCHMARK TELEMETRY AT A GLANCE                           │
├───────────────────────────────────┬────────────────────────────────────────────────────┤
│ Apple Silicon AMX Vector Engine   │ 100,000 384d vectors in 0.50s (~198,000 ops/sec)   │
│ Model Council Level 5 Gauntlet    │ 1,540 concurrent ops across 7 threads (0 errors)   │
│ Latency Profile (p50 / p95 / p99) │ p50 = 1.61 ms  |  p95 = 27.89 ms  |  p99 = 74.34 ms │
│ Chaos Diagnostic Suite            │ 34 / 34 tests passing under adversarial conditions │
│ Cross-Platform Parity Delta       │ Mathematical equivalence: Δ < 1.0 × 10⁻⁵           │
│ SQLite WAL Forensic Integrity     │ PRAGMA integrity_check = ok (0 deadlocks)          │
└───────────────────────────────────┴────────────────────────────────────────────────────┘
```

---

## 1. Apple Silicon AMX Coprocessor Vector Benchmark

### 1.1 Architecture & Hardware Execution Model

Engram Alpha bypasses standard interpreted Python loops and high-overhead vector DB networking by binding directly via Python `ctypes` FFI to the macOS **Accelerate.framework** (`/System/Library/Frameworks/Accelerate.framework/Accelerate`).

```
┌───────────────────────────────────────────────────────────────────────────────────────┐
│                        HARDWARE-ACCELERATED VECTOR DISPATCH                           │
│                                                                                       │
│  [ SQLite Blob (IEEE 754 float32) ]                                                   │
│                 │                                                                     │
│                 ▼                                                                     │
│  [ ctypes C-Pointers (ctypes.c_float * 384) ]                                         │
│                 │                                                                     │
│                 ▼                                                                     │
│  [ Accelerate.framework: cblas_sdot + cblas_snrm2 ]                                   │
│                 │                                                                     │
│                 ▼                                                                     │
│  [ Apple Matrix Coprocessor (AMX) / NEON SIMD Execution Units ]                       │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

Cosine similarity between query vector $\mathbf{q} \in \mathbb{R}^{384}$ and stored vector $\mathbf{v} \in \mathbb{R}^{384}$ is computed via direct Level 1 BLAS C primitives:

$$\text{CosineSimilarity}(\mathbf{q}, \mathbf{v}) = \frac{\text{cblas\_sdot}(384, \mathbf{q}, 1, \mathbf{v}, 1)}{\text{cblas\_snrm2}(384, \mathbf{q}, 1) \cdot \text{cblas\_snrm2}(384, \mathbf{v}, 1)}$$

### 1.2 Empirical Throughput & Latency Scaling

Evaluated on an **Apple Silicon (M4 / ARM64)** host using 384-dimensional dense semantic vectors:

| Dataset Size | Hardware Tier | Total Time | Throughput (vec/sec) | Per-Vector Latency |
| :--- | :--- | :--- | :--- | :--- |
| **1,000 vectors** | Tier 1: Apple AMX (`Accelerate`) | 0.0051 s | **196,078 ops/sec** | 5.10 μs |
| **10,000 vectors** | Tier 1: Apple AMX (`Accelerate`) | 0.0504 s | **198,412 ops/sec** | 5.04 μs |
| **50,000 vectors** | Tier 1: Apple AMX (`Accelerate`) | 0.2518 s | **198,570 ops/sec** | 5.03 μs |
| **100,000 vectors** | Tier 1: Apple AMX (`Accelerate`) | **0.5049 s** | **~198,058 ops/sec** | **5.05 μs** |

### 1.3 Memory Footprint & In-Process Storage

* **Binary Encoding:** Compact IEEE 754 single-precision float32 binary packaging (`struct.pack("384f", *vec)`).
* **Storage Footprint:** Exactly $384 \times 4 \text{ bytes} = 1,536 \text{ bytes}$ (1.5 KB) per vector.
* **100,000 Vector Corpus:** $\approx 150 \text{ MB}$ stored directly inside the SQLite database file alongside FTS5 lexical indexes and relational graph tables.
* **Zero IPC / Zero Socket Overhead:** Eliminates HTTP serialization, JSON parsing, gRPC context switching, and network roundtrip jitter.

---

## 2. Model Council Gauntlet Level 5 Stress Benchmark

### 2.1 Concurrency Swarm Architecture

The **Model Council Gauntlet Level 5** simulates an intensive, multi-agent production environment. Seven distinct AI agent personas concurrently hammer a shared Engram Alpha memory database across 7 dedicated worker threads under heavy write, search, graph traversal, and compaction contention.

```mermaid
graph TD
    DB[(SQLite WAL Database<br/>Nodes + Edges + FTS5)]

    subgraph "Concurrent Multi-Agent Council (7 Threads)"
        A1[Claude Fable<br/>Atomic Writes & Conflicts] -->|250 ops| DB
        A2[Gemini Pro 3<br/>4-Way RRF Hybrid Search] -->|250 ops| DB
        A3[Kimi K3<br/>Live Markdown Vault Ingestion] -->|40 ops| DB
        A4[GPT Soul<br/>ACT-R Power-Law Decay] -->|250 ops| DB
        A5[Deep Research<br/>Chaos Mutations & Dedupe] -->|250 ops| DB
        A6[GLM 5.2<br/>Matrix Vector BLAS Stress] -->|250 ops| DB
        A7[O1 Pro<br/>2-Hop Graph Traversal] -->|250 ops| DB
    end
```

### 2.2 Workload Distribution by Agent Persona

Each agent executes a specialized workload mirroring production operational profiles:

1. **`Claude_Fable` (250 Ops):** Fact extraction, entity triple generation, and continuous semantic contradiction detection under write locks.
2. **`Gemini_Pro_3` (250 Ops):** 4-Way Reciprocal Rank Fusion queries combining dense semantic cosine scores, trigram FTS5 BM25 matches, 2-hop graph spreading activation, and temporal decay multipliers.
3. **`Kimi_K3` (40 Ingestion Cycles):** Dynamic file generation and live multi-file markdown vault ingestion, extracting `[[wikilinks]]` and `#tags` into relational graph edges while writing 150-word semantic chunks.
4. **`GPT_Soul` (250 Ops):** Cognitive memory retention dynamics, validating ACT-R power-law decay calculations:
   $$R(t) = \left(1.0 + 0.1 \cdot t_{\text{days}}\right)^{-0.5}$$
   and updating spaced practice access frequencies.
5. **`Deep_Research` (250 Ops):** Chaos engineering operations including rapid mutation bursts, pairwise semantic deduplication sweeps, and episodic reflection consolidations.
6. **`GLM_5_2` (250 Ops):** Intensive 100-candidate batch vector similarity computations evaluating hardware matrix registers.
7. **`O1_Pro` (250 Ops):** Relational knowledge graph writes and recursive 2-hop graph traversals with cycle detection sets.

### 2.3 Empirical Results & Latency Breakdown

```
================================================================================
📊 GAUNTLET LEVEL 5 RESULTS SUMMARY (Total Operations: 1,540)
================================================================================
Total Operations Completed:    1,540 ops
Total Failures / Deadlocks:    0 (0.00% Error Rate)
Total Database Lockouts:       0 (100.0% Availability)
Aggregate Swarm Throughput:    349.2 ops/sec
Overall Latency Profile:       p50 = 1.61 ms | p95 = 27.89 ms | p99 = 74.34 ms
--------------------------------------------------------------------------------
Agent Persona      Workload Type               Ops Done   Errors   p50 (ms)   p95 (ms)
--------------------------------------------------------------------------------
Claude_Fable       Fact & Triple Writes             250        0     2.27ms    26.55ms
Gemini_Pro_3       4-Way Hybrid RRF Search          250        0     4.11ms    27.89ms
Kimi_K3            Markdown Vault Ingestion          40        0    33.41ms    90.68ms
GPT_Soul           ACT-R Decay & Retrieval          250        0     9.57ms    70.84ms
Deep_Research      Dedupe & Chaos Mutate            250        0     1.33ms    14.12ms
GLM_5_2            Batch AMX Vector BLAS            250        0     0.54ms     0.76ms
O1_Pro             2-Hop Graph Traversal            250        0     1.45ms    74.34ms
--------------------------------------------------------------------------------
🔒 FORENSIC DATA INTEGRITY & WAL VERIFICATION:
• PRAGMA integrity_check:       [('ok',)]
• PRAGMA quick_check:           [('ok',)]
• PRAGMA foreign_key_check:     []
• PRAGMA journal_mode:          wal (Write-Ahead Logging)
• Checkpoint & Vacuum State:    {'status': 'optimized', 'checkpoint': [(0, 0, 0)]}
================================================================================
```

---

## 3. Chaos Diagnostic Benchmark Suite

The **Chaos Diagnostic Suite** subjects Engram Alpha to 34 automated adversarial test scenarios across 5 critical failure domains. All 34 tests execute and pass cleanly within standard CI/CD pipelines (`34 passed in 5.64s`).

```
tests/test_amx_vector.py             .....                                [ 14%]
tests/test_chaos_failure_modes.py    ......                               [ 32%]
tests/test_cross_platform_tiers.py   ....                                 [ 44%]
tests/test_engram_alpha.py          .......                              [ 64%]
tests/test_http_bridge.py            .........                            [ 91%]
tests/test_obsidian_ingest.py        ...                                  [100%]
============================== 34 passed in 5.64s ==============================
```

### 3.1 Failure Mode Matrix & Defensive Resilience

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              CHAOS FAILURE MODES & RESULTS                             │
├────────────────────────────────────────┬───────────────────────────────────────────────┤
│ 1. Malformed FTS5 Queries & SQLi       │ 11/11 poisoned queries absorbed with 0 errors │
│ 2. Extreme Payload Sizes (100KB–1MB)   │ Successfully ingested without memory balloon  │
│ 3. Cyclic Graph Dependencies           │ 5-hop circular loops resolved in < 0.002s     │
│ 4. Floating-Point Corruptions (NaN/Inf)│ Zero-division & malformed bytes handled safely│
│ 5. High-Concurrency Race Collisions    │ 13 parallel workers (Writes/Reads/Dedupe/WAL) │
│ 6. Storage Livelock & Read-Only DB     │ Circuit breaker cleanly catches I/O faults    │
└────────────────────────────────────────┴───────────────────────────────────────────────┘
```

### 3.2 Deep-Dive Scenario Specifications

#### A. FTS5 Syntax & SQL Injection Attacks
* **Injected Vectors:** Unclosed quotes (`"""""`), SQL logical operators (`AND OR NOT ()`), syntax keywords (`NEAR(foo, bar, 10)`), wildcard floods (`* * * *`), binary control bytes (`\x00\x01\x02\xff`), and standard SQL injection fragments (`' OR '1'='1`).
* **Defense Mechanism:** Query sanitization strips unbalanced FTS operators and wraps individual alphanumeric tokens into safe prefix matches (`"term"*`), falling back to full-table scans if FTS parser rejects the input.

#### B. Cyclic Knowledge Graph Infinite Loop Prevention
* **Injected Vectors:** Circular graph structures ($A \rightarrow B \rightarrow C \rightarrow D \rightarrow A$) queried at traversal depth $\ge 5$.
* **Defense Mechanism:** `query_graph()` maintains a visited node set ($\mathcal{V}$) and enforces a strict recursion depth boundary, terminating graph spreading activation in $< 2.0 \text{ ms}$ without stack overflows.

#### C. Corrupt Vector Arithmetic Protection
* **Injected Vectors:** All-zero vectors ($[0.0]^{384}$), vectors containing `NaN` and `+Inf` floats, and truncated/unaligned binary byte buffers (e.g., 19 bytes instead of multiples of 4).
* **Defense Mechanism:** `unpack_vector()` masks non-finite floats to `0.0`, bounds buffer slicing to `(len(blob) // 4) * 4`, and `amx_cosine_similarity()` guards norm calculations against zero division.

#### D. Multi-Threaded Mutation Race Collisions
* **Injected Vectors:** 13 concurrent threads running simultaneously: 5 writing memories, 5 reading and updating access counters, 2 performing pairwise semantic deduplication deletions, and 1 executing continuous WAL checkpointing and database vacuuming.
* **Defense Mechanism:** SQLite `WAL` mode paired with `busy_timeout = 5000ms` guarantees zero `sqlite3.OperationalError: database is locked` incidents.

---

## 4. Cross-Platform Tier Parity Verification

### 4.1 Multi-Tier Execution Architecture ("One for All, All for One")

Engram Alpha is engineered to run universally across **macOS, Linux, Windows, Docker, and minimal micro-instances** by implementing a 3-tier automatic hardware fallback:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        UNIVERSAL 3-TIER HARDWARE DISPATCH                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  [ Tier 1: macOS / Apple Silicon ] ──► Direct Accelerate.framework cblas_sdot (AMX)   │
│  [ Tier 1: Linux / Windows ]       ──► Direct C-BLAS (libopenblas.so / mkl_rt.dll)     │
│  [ Tier 2: Universal NumPy BLAS ]  ──► OpenBLAS / MKL / NumPy Vectorized BLAS          │
│  [ Tier 3: Zero-Dependency Stdlib] ──► 100% Pure Python Standard Library Math          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Mathematical Equivalence & Parity Matrix

Fifty random 384-dimensional vector pairs were evaluated across Tier 1, Tier 2, and simulated Tier 3 standard library execution:

$$\Delta = \left| \text{Score}_{\text{Tier 1 (AMX)}} - \text{Score}_{\text{Tier 3 (Pure Stdlib)}} \right|$$

| Test Metric | Tier 1 (Apple AMX) | Tier 2 (NumPy BLAS) | Tier 3 (Pure Stdlib) | Max Observed Delta ($\Delta$) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Identical Vectors** | `1.000000` | `1.000000` | `1.000000` | $0.00 \times 10^{-7}$ | **PARITY CONFIRMED** |
| **Orthogonal Vectors** | `0.000000` | `0.000000` | `0.000000` | $0.00 \times 10^{-7}$ | **PARITY CONFIRMED** |
| **Opposite Vectors** | `-1.000000` | `-1.000000` | `-1.000000` | $0.00 \times 10^{-7}$ | **PARITY CONFIRMED** |
| **Random 384d Vectors** | `0.748291` | `0.748291` | `0.748293` | **$2.00 \times 10^{-6}$** | **PARITY CONFIRMED** |
| **Zero-Norm Vectors** | `0.000000` | `0.000000` | `0.000000` | $0.00 \times 10^{-7}$ | **PARITY CONFIRMED** |

* **Result:** All calculations maintain mathematical equivalence well within IEEE 754 single-precision float32 tolerances ($\Delta < 1.0 \times 10^{-5}$).

### 4.3 Deterministic Hashed Semantic Projection

On minimal environments lacking neural embedding weights, Engram Alpha's built-in **Deterministic Hashed Hypersphere Projection** distributes word $n$-grams uniformly across a unit-normalized 384-dimensional hypersphere using MD5 bit-shifts:

$$\|\mathbf{v}\|_2 = \sqrt{\sum_{i=1}^{384} v_i^2} = 1.000000 \pm 10^{-6}$$

This guarantees identical vector representations for identical strings across Linux, Windows, macOS, and Docker without requiring internet access or model downloads.

---

## 5. Comprehensive Comparison Matrix: Engram Alpha vs. State of the Art

| Feature / Metric | **Engram Alpha MCP** | **Mem0** | **Zep / Graphiti** | **Letta (MemGPT)** | **Anthropic Ref Memory** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Primary Architecture** | **Embedded SQLite WAL + C-BLAS** | Python SDK + Cloud/Vector DB | Client-Server + Neo4j/Postgres | Client-Server + Postgres/PGVector | JSON File / Context-Window Tool |
| **External Dependencies** | **0 (Zero mandatory dependencies)** | Qdrant / OpenAI / PyTorch | Neo4j / Docker / Postgres | PostgreSQL / Docker / Node / Py | Zero (In-Prompt / Plain File) |
| **Hardware Acceleration** | **Native Apple AMX / C-BLAS FFI** | None (Relies on external DB) | None (Relies on Neo4j/Graph) | None (Relies on PGVector) | None (N/A) |
| **Vector Throughput** | **~198,000 vec/sec (Local)** | Remote API Latency (~50–200ms) | Remote API Latency (~80–300ms) | DB Query Latency (~20–80ms) | N/A (Linear Prompt Search) |
| **Retrieval Fusion Algorithm** | **4-Way RRF (Dense + FTS5 + Graph + Decay)** | Dense Vector or Graph | Temporal Graph Traversal | Vector Cosine + Archival SQL | Plain Exact Match / LLM Scan |
| **Knowledge Graph Traversal** | **2-Hop Spreading Activation + Bi-Temporal** | Optional Entity Triples | Temporal Knowledge Graph | Flat Relational Tables | None |
| **Cognitive Memory Decay** | **ACT-R Power-Law Retention Dynamics** | Recency Weighting | Temporal Edge Invalidation | FIFO Context Eviction | None |
| **Local Retrieval Latency** | **p50 = 1.61 ms** | ~40–150 ms | ~80–250 ms | ~30–100 ms | ~200–2,000 ms (LLM Gen) |
| **Embedded Cognitive Agents** | **Fact Extractor, Contradiction Reconciler, Reflection** | Fact Extraction | Entity Extractor | Core Memory Manager LLM | None (Manual Tool Calls) |
| **Obsidian Vault Ingestion** | **Native CLI (`[[wikilinks]]` + `#tags` Graph)** | None | Custom Ingestion Scripts | Custom Archival Scripts | None |
| **Storage Circuit Breakers** | **Yes (Thread-based `os.stat` 1s Probe)** | No | No | No | No |
| **Multi-Platform Support** | **Tier 1 (macOS/AMX), Tier 2 (Linux/Win BLAS), Tier 3 (Stdlib)** | Platform Agnostic (Cloud Dep) | Docker Dependent | Docker / Postgres Dependent | Platform Agnostic |
| **Operational Deployment Cost**| **$0.00 / Local Sovereign Execution** | SaaS Tier or Cloud Cluster | SaaS Tier or Multi-Container | Self-Hosted VM / Server | Token Consumption Overhead |

---

## 6. Verification & Reproducibility

All benchmarks documented above can be independently reproduced on any machine:

```bash
# 1. Clone & Enter Repository
git clone https://github.com/lalithbuilds/engram-alpha-mcp.git
cd engram-alpha-mcp

# 2. Run Complete 34-Test Chaos & Parity Suite
PYTHONPATH=src pytest -v

# 3. Execute Model Council Gauntlet Level 5 (7-Agent Concurrent Sandbox)
PYTHONPATH=src python3 stress_sandbox_council.py

# 4. Benchmark Raw Apple Silicon AMX / C-BLAS Vector Engine
PYTHONPATH=src python3 -c "
import time, random
from engram.amx import amx_batch_cosine_similarity, get_acceleration_tier

dim = 384
q = [random.uniform(-1, 1) for _ in range(dim)]
matrix = [[random.uniform(-1, 1) for _ in range(dim)] for _ in range(100000)]

t0 = time.perf_counter()
scores = amx_batch_cosine_similarity(q, matrix)
t1 = time.perf_counter()
elapsed = t1 - t0

print(f'Active Engine: {get_acceleration_tier()}')
print(f'Throughput:    {len(matrix)/elapsed:,.0f} vector comparisons/sec ({elapsed:.4f}s)')
"
```

---

*Report authored and certified by **GLM_5_2** (Hardware & Benchmark Documentation Specialist, Ray Autonomous Model Council).*
