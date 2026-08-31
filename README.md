<div align="center">
  <img src="https://capsule-render.vercel.app/api?type=cylinder&color=gradient&customColorList=10,13&height=180&section=header&text=Engram%20Alpha&fontSize=70&fontAlignY=45&animation=scaleIn&fontColor=ffffff&desc=V2%20Architecture&descAlignY=65&descAlign=62" width="100%"/>
  
  <br>
  
  <a href="https://git.io/typing-svg">
    <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=3000&pause=1000&color=00f2fe&center=true&vCenter=true&width=800&lines=Zero-Dependency+Semantic+Knowledge+Graph;Built+for+the+Model+Context+Protocol;Self-Healing+SQLite+Architecture;ACT-R+Power+Law+Memory+Decay" alt="Typing SVG" />
  </a>
  
  <br>
  
  <img src="https://img.shields.io/badge/License-MIT-1a1b26.svg?style=for-the-badge&color=00f2fe" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.10+-1a1b26.svg?style=for-the-badge&logo=python&logoColor=00f2fe&color=00f2fe" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/SQLite-1a1b26?style=for-the-badge&logo=sqlite&logoColor=00f2fe&color=00f2fe" alt="SQLite">
</div>

<br>

![Engram Alpha Demo](./assets/demo.gif)

## Architecture
- **Thin Base + Fat Extras:** `pip install engram` provides the ultra-light core. `pip install engram[local]` adds local `sqlite-vec` semantic indexing.
- **Foolproof Connection:** Handles `SQLITE_OMIT_LOAD_EXTENSION` natively. Implements Exponential Backoff and `WAL` mode with robust `BEGIN IMMEDIATE` atomic execution to survive multi-agent 7000+ concurrency deadlocks.
- **Atomic Operations:** Uses `os.replace()` + SHA256 streams for corrupted-free model downloads and `.bak` generation for config writes.
- **ACT-R Power Law Decay:** Implements `POWER(1.0 + (0.1 * MAX(0, days)), -0.5)` to mimic human memory eviction safely.
- **Security & Privacy:** Enforces strict 0600 file permissions and native `umask(0o077)` for `-wal` and `-shm` sidecar leakage prevention.
- **FTS5 Fault Tolerance:** Applies aggressive Regex syntax stripping to prevent SQL syntax panics on unescaped quotes and punctuation.

## Quickstart
```bash
# 1. Install
pip install engram[local,mac]

# 2. Setup (Auto-wires Claude Desktop config)
engram setup

# 3. Use
# The MCP server will now run seamlessly in Claude Desktop with full semantic graph support.
```
