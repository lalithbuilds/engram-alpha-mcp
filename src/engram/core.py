"""
Engram Core Database Engine (Universal Production-Grade Architecture)
Manages SQLite WAL semantic graph, schema migrations with versioning,
ACT-R power-law decay, multi-tenant namespaces, and storage liveness.
"""

import sys
import os
import math
import threading
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

_INIT_LOCK = threading.Lock()
_INITIALIZED_PATHS = set()

def check_storage_liveness(target_path: Path, timeout_seconds: float = 1.0) -> bool:
    """
    Universal cross-platform storage liveness probe.
    Executes standard os.stat inside a strict timeout thread to prevent hangs.
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

def init_db(force: bool = False):
    """
    Initializes database tables, triggers, indexes, and schema versions.
    Thread-safe, idempotent, and uses _INITIALIZED_PATHS fast-path.
    """
    target_path = Path(os.environ.get("ENGRAM_DB_PATH", DB_PATH)).resolve()
    target_path_str = str(target_path)
    
    with _INIT_LOCK:
        if target_path_str in _INITIALIZED_PATHS and not force:
            if target_path.exists():
                return
            else:
                _INITIALIZED_PATHS.discard(target_path_str)

        if not check_storage_liveness(target_path, timeout_seconds=1.0):
            raise OSError(f"Storage path {target_path} is unresponsive or inaccessible.")

        has_umask = hasattr(os, "umask")
        old_umask = os.umask(0o077) if has_umask else None

        try:
            target_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            conn = sqlite3.connect(target_path_str, timeout=30.0)
            
            # Check if already initialized on disk
            if not force:
                try:
                    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes';")
                    if cur.fetchone():
                        # Ensure edges schema has all required columns
                        try:
                            edge_cols = {c[1] for c in conn.execute("PRAGMA table_info(edges);").fetchall()}
                            if "valid_from" not in edge_cols:
                                conn.execute("ALTER TABLE edges ADD COLUMN valid_from TEXT DEFAULT '';")
                            if "valid_until" not in edge_cols:
                                conn.execute("ALTER TABLE edges ADD COLUMN valid_until TEXT DEFAULT '';")
                            if "superseded_by" not in edge_cols:
                                conn.execute("ALTER TABLE edges ADD COLUMN superseded_by TEXT DEFAULT '';")
                            if "transaction_time" not in edge_cols:
                                conn.execute("ALTER TABLE edges ADD COLUMN transaction_time TEXT DEFAULT CURRENT_TIMESTAMP;")
                            conn.commit()
                        except Exception:
                            pass
                        conn.close()
                        _INITIALIZED_PATHS.add(target_path_str)
                        return
                except Exception:
                    pass

            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("PRAGMA cache_size = -64000;")
            conn.execute("PRAGMA mmap_size = 268435456;")
            
            def safe_power(base, exp):
                try:
                    return math.pow(max(0.001, float(base)), float(exp))
                except Exception:
                    return 0.0
                    
            conn.create_function("POWER", 2, safe_power)

            conn.execute("BEGIN IMMEDIATE;")
            try:
                # Schema versioning table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                """)

                # Nodes table
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
                    category TEXT NOT NULL DEFAULT 'general',
                    project TEXT NOT NULL DEFAULT 'default',
                    agent TEXT NOT NULL DEFAULT 'system'
                );
                """)
                
                # Edges table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT,
                    target TEXT,
                    relation TEXT,
                    weight REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT '',
                    project TEXT NOT NULL DEFAULT 'default',
                    valid_from TEXT DEFAULT '',
                    valid_until TEXT DEFAULT '',
                    superseded_by TEXT DEFAULT '',
                    transaction_time TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (source, target, relation, project)
                );
                """)

                # Vault file hash tracking table for incremental obsidian sync
                conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_files (
                    file_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    last_modified REAL NOT NULL,
                    project TEXT NOT NULL DEFAULT 'default',
                    synced_at TEXT NOT NULL
                );
                """)

                # Indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes (project, category);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_lookup ON edges (source, target, project);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges (target, project);")

                # Auto-migrate edges columns if upgrading from earlier version
                edge_cols = {c[1] for c in conn.execute("PRAGMA table_info(edges);").fetchall()}
                if "valid_from" not in edge_cols:
                    conn.execute("ALTER TABLE edges ADD COLUMN valid_from TEXT DEFAULT '';")
                if "valid_until" not in edge_cols:
                    conn.execute("ALTER TABLE edges ADD COLUMN valid_until TEXT DEFAULT '';")
                if "superseded_by" not in edge_cols:
                    conn.execute("ALTER TABLE edges ADD COLUMN superseded_by TEXT DEFAULT '';")
                if "transaction_time" not in edge_cols:
                    conn.execute("ALTER TABLE edges ADD COLUMN transaction_time TEXT DEFAULT CURRENT_TIMESTAMP;")

                # FTS5 Trigram Full-Text Index
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

                # Mark version 1 applied
                conn.execute("INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, datetime('now'));")

                # Native sqlite-vec Virtual Table & Triggers (if sqlite-vec is available)
                has_vec = False
                try:
                    import sqlite_vec
                    conn.enable_load_extension(True)
                    sqlite_vec.load(conn)
                    conn.enable_load_extension(False)
                    has_vec = True
                except Exception:
                    pass

                if has_vec:
                    try:
                        embedding_dim = int(os.environ.get("ENGRAM_EMBEDDING_DIM", "384"))
                        conn.execute(f"""
                        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_vec USING vec0(
                            id text primary key,
                            embedding float[{embedding_dim}]
                        );
                        """)
                        conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS nodes_vec_ai AFTER INSERT ON nodes WHEN new.embedding IS NOT NULL BEGIN
                            INSERT OR REPLACE INTO nodes_vec(id, embedding) VALUES (new.id, new.embedding);
                        END;
                        """)
                        conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS nodes_vec_au AFTER UPDATE ON nodes WHEN new.embedding IS NOT NULL BEGIN
                            DELETE FROM nodes_vec WHERE id = old.id;
                            INSERT OR REPLACE INTO nodes_vec(id, embedding) VALUES (new.id, new.embedding);
                        END;
                        """)
                        conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS nodes_vec_ad AFTER DELETE ON nodes BEGIN
                            DELETE FROM nodes_vec WHERE id = old.id;
                        END;
                        """)
                    except Exception:
                        pass

                conn.commit()
                _INITIALIZED_PATHS.add(target_path_str)
            except sqlite3.Error as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
        finally:
            if has_umask and old_umask is not None:
                os.umask(old_umask)

def get_db():
    """
    Returns an active SQLite database connection with custom functions and WAL pragmas.
    Uses _INITIALIZED_PATHS fast-path to eliminate redundant DDL checks.
    """
    target_path = Path(os.environ.get("ENGRAM_DB_PATH", DB_PATH)).resolve()
    target_path_str = str(target_path)
    if target_path_str not in _INITIALIZED_PATHS or not target_path.exists():
        init_db()

    conn = sqlite3.connect(target_path_str, timeout=30.0)
    
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    
    def safe_power(base, exp):
        try:
            return math.pow(max(0.001, float(base)), float(exp))
        except Exception:
            return 0.0
            
    conn.create_function("POWER", 2, safe_power)

    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (ImportError, Exception):
        pass

    return conn

def optimize_and_checkpoint(conn=None) -> Dict[str, Any]:
    """Execute WAL checkpoint, vacuum, and index optimization."""
    close_when_done = False
    if conn is None:
        conn = get_db()
        close_when_done = True
    try:
        wal_res = conn.execute("PRAGMA wal_checkpoint(TRUNCATE);").fetchall()
        conn.execute("PRAGMA optimize;")
        return {"status": "optimized", "checkpoint": wal_res}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if close_when_done:
            conn.close()
