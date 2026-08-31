<div align="center">
  <h1>🧠 Engram Alpha 2.0 (MCP)</h1>
  <p><strong>Zero-dependency, semantic Knowledge Graph built for the Model Context Protocol (MCP).</strong></p>
  <img src="assets/demo.gif" alt="Engram Alpha Demo" width="100%">
  <br><br>
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
</div>


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
