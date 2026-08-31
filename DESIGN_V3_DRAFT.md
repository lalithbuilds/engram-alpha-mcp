# Engram Alpha V3: Immortal Architecture Draft

Based on the Model Council execution (August 2026), here is the finalized blueprint for the V3 iteration of Engram Alpha.

## 1. Engine Standardization
- **Drop Qdrant:** The split-brain (SQLite text + Qdrant vectors) caused ACID violations and SIGBUS panics on external drives.
- **Adopt `sqlite-vec`:** A unified SQLite graph guarantees atomicity, meaning nodes, relationships (edges), FTS5 text search, and 384d semantic vectors commit or rollback perfectly together.

## 2. Ingestion Pipeline
- **Dependencies:** Add `fastembed` (BAAI/bge-small-en-v1.5) to `[local]` extras for CPU-native embedding generation.
- **CLI Commands:** Implement `engram ingest-obsidian <path>`.
- **Logic:** Chunk markdown by 150 words -> Embed -> Pack via `struct.pack(f'{len(v)}f', *v)` -> Batch insert into `vec_nodes USING vec0` inside a massive `BEGIN IMMEDIATE` transaction block.

## 3. Hybrid Search & Memory Decay
- **Algorithm:** Mathematically fuse Full-Text Search (BM25) + Cosine Vector Distance + ACT-R Power-Law Decay directly in the SQL statement.
- **SQL Ranking Pattern:**
  `VECTOR_DISTANCE(query_vector, memory_vector) * POWER(1.0 + (0.1 * MAX(0, days)), -0.5) * bm25()`
- **Result:** Biologically-plausible memory eviction natively at the query engine level without background cron pruning.

## 4. Hardware Liveness Protection
- **No Heavy Proxies:** Remove stateful persistent connections (like `ResilientMemoryDB`).
- **Short-Circuiting:** Inject a rapid OS-level probe (`subprocess.run(["stat"], timeout=1)`) just prior to `conn = sqlite3.connect()`. If the storage drops, instantly return a JSON-RPC error, preventing the MCP orchestrator from hanging indefinitely.
