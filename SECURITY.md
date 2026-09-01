# Security & Governance Policy

## Sovereign Air-Gapped Architecture

Engram Alpha MCP is architected as a sovereign, zero-telemetry, local-first memory and context orchestration engine. The system is designed to operate seamlessly in air-gapped environments with strict security guarantees:

1. **Zero External Egress**: No telemetry, analytics, crash logs, or third-party phone-home calls are permitted. All vector indexing, full-text indexing, and model embeddings execute strictly on local compute hardware.
2. **Process Isolation & Defense-in-Depth**: MCP server processes run with minimal necessary capabilities. Subprocesses and storage drivers are strictly isolated.

---

## File System & Storage Security

### Process Umask Enforcement (`0o077`)
At initialization, Engram Alpha MCP enforces a process-level file mode creation mask (`umask 0o077`). Any dynamically generated files, directories, socket endpoints, or lockfiles inherit restrictive permissions by default, preventing unauthorized read/write access from other unprivileged local accounts.

### File Permissions (`0600` / `0700`)
- **Database & WAL Files**: SQLite, DuckDB, vector storage files, and write-ahead logs (`.db`, `.duckdb`, `.wal`, `-shm`) are explicitly restricted to `0600` (read/write only by the process owner).
- **Storage Directories**: Database directories and cache roots are restricted to `0700` (read/write/execute only by the process owner).
- **Permission Verification**: On boot, the engine audits existing data directory permissions and warns or hard-fails if insecure permissions (`0644`/`0777`) are detected.

---

## Authentication & Access Control

### HTTP Gateway Bearer Token Authentication
When running in HTTP / Server-Sent Events (SSE) gateway mode:
- All inbound requests must supply an `Authorization` header with a valid bearer token:
  ```http
  Authorization: Bearer <ENGRAM_AUTH_TOKEN>
  ```
- Constant-time comparison (`hmac.compare_digest`) is enforced to protect against timing attacks.
- Requests lacking a valid token or providing malformed credentials receive an immediate `401 Unauthorized` with zero internal state disclosure.

---

## Reliability & Circuit Breaking

### 1.0s Storage Liveness Circuit Breakers
To prevent distributed deadlocks, file system hanging, or cascading starvation across MCP tool invocations:
- Storage access (read/write operations on SQLite, DuckDB, or NVMe WAL) is guarded by a **1.0-second storage liveness circuit breaker**.
- If a lock contention or file system I/O operation exceeds 1000ms, the circuit transitions to `OPEN` state, immediately failing fast and returning a structured timeout diagnostic without hanging the calling orchestrator or agent.
- Automatic half-open probing ensures recovery once storage I/O latency normalizes.

---

## Injection Defense & Query Sanitization

### Full-Text Search (FTS) Injection Defense
- **FTS5 / Query Sanitization**: User-supplied text and search strings destined for SQLite FTS5 or relational queries are strictly tokenized and escaped. Raw query interpolation is banned.
- **Parametrized Execution**: All dynamic SQL queries utilize strict parameter binding (`?` placeholders or named parameters).
- **Syntax Disarmament**: Unbalanced boolean operators (`AND`, `OR`, `NOT`, `NEAR`, `*`, `^`, `"`, `:`) in raw input are disarmed or wrapped in sanitized term phrases prior to query execution.

---

## Vulnerability Reporting

If you identify a security vulnerability or governance risk in Engram Alpha MCP, report it directly to the maintainer:
- **Lead Maintainer**: Lalith (Ray Global Model, BTM Bengaluru)
- **Reporting Channel**: Secure repository issue or direct contact.
- Response target: Initial triage within 24 hours.
