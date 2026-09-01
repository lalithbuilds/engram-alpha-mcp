# Contributing to Engram Alpha MCP

Thank you for contributing to Engram Alpha MCP. This project enforces high standards of reliability, performance, and security for autonomous agent memory systems.

---

## Development Setup

### Prerequisites
- Python 3.11+
- `uv` (recommended) or `poetry` / `pip`
- Apple Silicon (macOS) or Linux (x86_64 / aarch64) with C++ build essentials

### Environment Setup
```bash
# Clone the repository
git clone https://github.com/lalith/engram-alpha-mcp.git
cd engram-alpha-mcp

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

## Testing & Quality Assurance

### Test Suite Execution
All code contributions must maintain 100% pass rates across unit and integration tests.

```bash
# Run standard test suite
pytest -v

# Run with async support and detailed execution logging
pytest -v -s --durations=10

# Run specific memory and security test suites
pytest tests/test_security.py tests/test_storage.py
```

### Hardware Tier Verification
Engram Alpha MCP features multi-tier hardware acceleration:
- **Tier 1 (Apple Silicon / M-Series)**: Uses `mlx` with FP16 acceleration and unified memory zero-copy optimizations.
- **Tier 2 (CUDA / ROCm)**: GPU-accelerated embedding matrices with batching.
- **Tier 3 (CPU Fallback)**: Pure vectorized NumPy / DuckDB fallback.

Ensure you verify hardware tier detection in your local tests:
```bash
pytest tests/test_hardware_tiers.py -k "tier_detection"
```

---

## Code Style & Formatting

We adhere strictly to modern Python standards with zero boilerplate and strict type safety:

- **Linter & Formatter**: `ruff` for linting and formatting.
- **Type Checking**: `mypy --strict`.

```bash
# Format code
ruff format .

# Check lint rules
ruff check . --fix

# Run static type analysis
mypy src
```

### Commit & PR Discipline
- Use conventional commit messages (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
- Always include test coverage for new tools or storage drivers.
- Never commit secrets, `.env` files, credentials, or test database artifacts.
