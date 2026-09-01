"""
Engram Core Database Engine
Manages SQLite WAL semantic graph, schema migrations, ACT-R power-law decay,
and hardware liveness short-circuiting.
"""

import sys
import os
import math
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

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
        return sqlite3

sqlite3 = get_sqlite_module()

DB_PATH = Path(os.environ.get("ENGRAM_DB_PATH", Path.home() / ".engram" / "engram.sqlite"))

def check_storage_liveness(target_path: Path, timeout_seconds: float = 1.0) -> bool:
    """
    Rapid OS-level short-circuit probe to verify storage responsiveness.
    Prevents Python process hangs if external drives or mounted volumes stall.
    """
    check_dir = target_path.parent
    if not check_dir.exists():
        try:
            check_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        except Exception:
            return False

    try:
        # Run fast native OS stat with timeout
        res = subprocess.run(
            ["stat", str(check_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
        )
        return res.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False

def init_db():
    target_path = Path(os.environ.get("ENGRAM_DB_PATH", DB_PATH))
    
    # 1. Hardware Liveness Probe
    if not check_storage_liveness(target_path, timeout_seconds=1.0):
        raise OSError(f"Storage path {target_path} is unresponsive or inaccessible.")

    # Set umask to 0o077 so all files created by SQLite (-wal, -shm) are 0o600
    old_umask = os.umask(0o077)
    try:
        target_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target_path), timeout=30.0)
        
        # Connection Optimization
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        
        # Register Math Functions for ACT-R Power-Law Decay
        def safe_power(base, exp):
            try:
                return math.pow(max(0.001, float(base)), float(exp))
            except Exception:
                return 0.0
                
        conn.create_function("POWER", 2, safe_power)

        # Schema & Automatic Migrations
        conn.execute("BEGIN IMMEDIATE;")
        try:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER NOT NULL DEFAULT 0,
                last_accessed_at TEXT NOT NULL DEFAULT '',
                embedding BLOB
            );
            """)
            
            # Check for embedding column migration if upgrading from V2
            cur = conn.execute("PRAGMA table_info(nodes);")
            columns = [row[1] for row in cur.fetchall()]
            if "embedding" not in columns:
                conn.execute("ALTER TABLE nodes ADD COLUMN embedding BLOB;")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT,
                target TEXT,
                relation TEXT,
                PRIMARY KEY (source, target, relation)
            );
            """)
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(id, content, tokenize='trigram');
            """)
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
                INSERT INTO nodes_fts(id, content) VALUES (new.id, new.content);
            END;
            """)
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
                DELETE FROM nodes_fts WHERE id=old.id;
                INSERT INTO nodes_fts(id, content) VALUES (new.id, new.content);
            END;
            """)
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
                DELETE FROM nodes_fts WHERE id=old.id;
            END;
            """)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise e
    finally:
        os.umask(old_umask)
        
    return conn

def get_db():
    conn = init_db()
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (ImportError, Exception):
        pass
        
    return conn
