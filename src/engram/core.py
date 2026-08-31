import sys
import os
import math
from pathlib import Path
from typing import Dict, Any, List

def supports_extensions(db_module) -> bool:
    if not hasattr(db_module.Connection, "enable_load_extension"):
        return False
    try:
        with db_module.connect(":memory:") as conn:
            conn.enable_load_extension(True)
            return True
    except (AttributeError, db_module.OperationalError, db_module.NotSupportedError):
        return False

def get_sqlite_module():
    import sqlite3
    if supports_extensions(sqlite3):
        return sqlite3
        
    try:
        __import__('pysqlite3')
        sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
        import sqlite3 as patched_sqlite3
        return patched_sqlite3
    except ImportError:
        raise RuntimeError(
            "Your Python's standard 'sqlite3' module lacks extension loading support "
            "(common on macOS). To use advanced semantic features, please run:\n"
            "    pip install engram[mac]"
        )

sqlite3 = get_sqlite_module()

DB_PATH = Path(os.environ.get("ENGRAM_DB_PATH", Path.home() / ".engram" / "engram.sqlite"))

def init_db():
    DB_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    
    if not DB_PATH.is_symlink():
        os.chmod(DB_PATH, 0o600)

    # Foolproof Connection Settings
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    
    # Register Math Functions for ACT-R Power-Law Decay
    def safe_power(base, exp):
        try: return math.pow(float(base), float(exp))
        except: return 0.0
    conn.create_function("POWER", 2, safe_power)

    # Semantic Graph Schema
    conn.execute("BEGIN IMMEDIATE;")
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            access_count INTEGER NOT NULL DEFAULT 0,
            last_accessed_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS edges (
            source TEXT,
            target TEXT,
            relation TEXT,
            PRIMARY KEY (source, target, relation)
        );
        -- FTS5 with trigram index
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(id, content, tokenize='trigram');
        
        -- Native Triggers for flawless sync
        CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
            INSERT INTO nodes_fts(id, content) VALUES (new.id, new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
            DELETE FROM nodes_fts WHERE id=old.id;
            INSERT INTO nodes_fts(id, content) VALUES (new.id, new.content);
        END;
        CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
            DELETE FROM nodes_fts WHERE id=old.id;
        END;
        """)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise e
        
    return conn

def get_db():
    conn = init_db()
    # Try to load sqlite-vec if user has installed the [local] extra
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except ImportError:
        pass # Gracefully run without semantic vectors (fallback to FTS5)
    except Exception as e:
        print(f"[WARN] Failed to load sqlite-vec: {e}", file=sys.stderr)
        
    return conn
