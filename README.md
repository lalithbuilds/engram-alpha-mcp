<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=cylinder&color=gradient&customColorList=10,13&height=180&section=header&text=Engram%20Alpha&fontSize=70&fontAlignY=45&animation=scaleIn&fontColor=ffffff&desc=V3%20Immortal%20Architecture&descAlignY=65&descAlign=62" width="100%"/>
  
  <br>
  
  <a href="https://git.io/typing-svg">
    <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=3000&pause=1000&color=00f2fe&center=true&vCenter=true&width=800&lines=Apple+Silicon+AMX+Hardware+Matrix+Engine;Zero-Dependency+Atomic+Graph+and+Vectors;Obsidian+Vault+Graph+Ingestion+Pipeline;Fused+Hybrid+Retrieval+and+ACT-R+Decay" alt="Typing SVG" />
  </a>
  
  <br>
  
  <img src="https://img.shields.io/badge/License-MIT-1a1b26.svg?style=for-the-badge&color=00f2fe" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.10+-1a1b26.svg?style=for-the-badge&logo=python&logoColor=00f2fe&color=00f2fe" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/SQLite-1a1b26?style=for-the-badge&logo=sqlite&logoColor=00f2fe&color=00f2fe" alt="SQLite">
  <img src="https://img.shields.io/badge/Hardware-Apple_AMX_BLAS-1a1b26.svg?style=for-the-badge&color=00f2fe" alt="Hardware: Apple AMX BLAS">
</div>

<br>

![Engram Alpha Demo](./assets/demo.gif)

## ⚡ V3 Immortal Architecture

- **Apple Silicon AMX Hardware Acceleration:** Directly links to Apple's `Accelerate.framework` (`cblas_sdot` / `cblas_sgemv`) for hardware-accelerated vector dot products and batch cosine similarity at 195,000+ vector comparisons/sec with microsecond latency.
- **Unified Atomic Graph & Dense Vectors:** Nodes, Knowledge Graph Triples (`edges`), FTS5 Lexical Text, and 384d Dense Vectors commit and rollback in atomic `BEGIN IMMEDIATE` transactions inside SQLite WAL.
- **Native Obsidian Markdown Ingestion:** CLI command `engram ingest-obsidian <vault>` parses entire markdown vaults, automatically extracting `[[wikilinks]]` and `#tags` into Knowledge Graph triples alongside 150-word semantic chunk vectors.
- **Fused Hybrid Retrieval:** Combines Lexical Trigram BM25 + AMX Vector Cosine Similarity + ACT-R Power-Law Decay in a single query:
  $$\text{FinalScore} = (\text{Lexical} + \text{Semantic} \times 2.0) \times \left(1.0 + 0.1 \times \text{DaysOld}\right)^{-0.5}$$
- **Hardware Liveness Short-Circuiting:** Fast OS-level `stat` probe checks storage availability with a 1-second timeout, completely preventing agent orchestrator deadlocks if external drives drop.
- **Stateless MCP Lifecycle:** Eliminates stale file descriptor leaks (`Errno 5`) and `SIGBUS` panics through clean per-request connection lifetimes.

---

## 🛠️ Quickstart

```bash
# 1. Install
pip install engram[local,mac]

# 2. Ingest Obsidian Knowledge Vault
engram ingest-obsidian ~/Documents/MyObsidianVault

# 3. Query Memory Graph
engram search "Quantum Computing Architecture"
engram query-graph "Ray_Daemon"

# 4. Benchmark AMX Hardware Speed
engram benchmark --vectors 50000

# 5. Setup (Auto-wires Claude Desktop config)
engram setup
```
