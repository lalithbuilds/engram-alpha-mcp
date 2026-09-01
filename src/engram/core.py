"""
Engram Core Database Engine (Universal Cross-Platform Architecture)
Manages SQLite WAL semantic graph, schema migrations, ACT-R power-law decay,
and cross-platform hardware storage liveness short-circuiting (macOS, Linux, Windows).
"""

import sys
import os
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

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
    Universal cross-platform storage liveness probe.
    Executes standard os.stat inside a strict timeout thread to prevent hangs
    if external drives, network shares, or mounted volumes disconnect on any OS.
    """
    check_dir = target_path.parent
    try:
        check_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    except Exception:
        pass

    def _stat_probe():
        try:
            return check_dir.exists() and check_dir.stat() is not None
        except Exception:
            return False

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_stat_probe)
            return future.result(timeout=timeout_seconds)
    except (FutureTimeoutError, Exception):
        return False

def init_db():
    target_path = Path(os.environ.get("ENGRAM_DB_PATH", DB_PATH))
    
    # 1. Cross-Platform Storage Liveness Check
    if not check_storage_liveness(target_path, timeout_seconds=1.0):
        raise OSError(f"Storage path {target_path} is unresponsive or inaccessible.")

    # Apply secure permissions where supported
    has_umask = hasattr(os, "umask")
    old_umask = os.umask(0o077) if has_umask else None

    try:
        target_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target_path), timeout=30.0)
        
        # Cross-Platform Connection Optimization
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

        # Semantic Graph & Knowledge Schema
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
                embedding BLOB,
                importance INTEGER NOT NULL DEFAULT 5,
                category TEXT NOT NULL DEFAULT 'general'
            );
            """)
            
            # Migration check for existing columns
            cur = conn.execute("PRAGMA table_info(nodes);")
            columns = [row[1] for row in cur.fetchall()]
            if "embedding" not in columns:
                conn.execute("ALTER TABLE nodes ADD COLUMN embedding BLOB;")
            if "importance" not in columns:
                conn.execute("ALTER TABLE nodes ADD COLUMN importance INTEGER NOT NULL DEFAULT 5;")
            if "category" not in columns:
                conn.execute("ALTER TABLE nodes ADD COLUMN category TEXT NOT NULL DEFAULT 'general';")

            conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT,
                target TEXT,
                relation TEXT,
                weight REAL DEFAULT 1.0,
                created_at TEXT DEFAULT '',
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
        if has_umask and old_umask is not None:
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
