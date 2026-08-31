import re

with open("src/engram/server.py", "r") as f:
    code = f.read()

# Fix FTS syntax error: generate match query from clean_words instead of raw content
code = code.replace(
    'conn.execute("SELECT id, content FROM nodes_fts WHERE nodes_fts MATCH ?", (content,)).fetchall()',
    'conn.execute("SELECT id, content FROM nodes_fts WHERE nodes_fts MATCH ?", (" OR ".join(f\'"{w}"\' for w in clean_words),)).fetchall() if clean_words else []'
)
with open("src/engram/server.py", "w") as f:
    f.write(code)

with open("tests/test_engram_alpha.py", "r") as f:
    test_code = f.read()
test_code = test_code.replace(
    "INSERT INTO nodes (id, type, content, created_at)",
    "INSERT INTO nodes (id, type, content, created_at, updated_at)"
).replace(
    "'2020-01-01T00:00:00Z')",
    "'2020-01-01T00:00:00Z', '2020-01-01T00:00:00Z')"
).replace(
    "'2026-08-31T00:00:00Z')",
    "'2026-08-31T00:00:00Z', '2026-08-31T00:00:00Z')"
)
with open("tests/test_engram_alpha.py", "w") as f:
    f.write(test_code)
