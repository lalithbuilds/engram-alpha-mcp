import sys
import uuid
from datetime import datetime, timezone
from mcp.server.mcpserver import MCPServer
from .core import get_db
from .utils import retry_db_lock

mcp = MCPServer("Engram Alpha MCP")

@retry_db_lock(max_retries=7)
def _save_node(node_type: str, content: str) -> str:
    conn = get_db()
    node_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Overlap detection (Conflict Heuristic)
    # Replaced > 3 with > 2 for Acronyms (AWS, API)
    clean_words = set(w.lower() for w in content.replace(",", " ").replace(".", " ").split() if len(w) > 2)
    
    # We use ACT-R Power-Law Decay in search, but here we just do a basic check
    warnings = []
    
    conn.execute("BEGIN IMMEDIATE;")
    try:
        # Check conflicts
        for row in conn.execute("SELECT id, content FROM nodes_fts WHERE nodes_fts MATCH ?", (" OR ".join(f'"{w}"' for w in clean_words),)).fetchall() if clean_words else []:
            row_words = set(w.lower() for w in row[1].replace(",", " ").replace(".", " ").split() if len(w) > 2)
            if len(clean_words & row_words) >= 2:
                warnings.append(f"Conflict found (ID {row[0]}): {row[1]}... Did you mean to update?")
                
        conn.execute(
            "INSERT INTO nodes (id, type, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (node_id, node_type, content, now, now)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    return f"Saved Node {node_id}. Warnings: {warnings}"

@mcp.tool()
def save_memory(content: str) -> str:
    """Save a new memory node."""
    return _save_node("memory", content)

@mcp.tool()
def search_memory(query: str, limit: int = 5) -> str:
    """Search memory using ACT-R Power Law Decay and Trigram FTS5."""
    conn = get_db()
    
    # Clean query for FTS5 trigram
    safe_query = query.replace('"', '').replace("'", "")
    
    # ACT-R Power-Law time weight: POWER(1.0 + (0.1 * days_old), -0.5)
    sql = """
    SELECT n.id, n.content, rank,
           (rank * POWER(1.0 + (0.1 * (julianday('now') - julianday(COALESCE(NULLIF(n.last_accessed_at, ''), n.created_at)))), -0.5)) as final_score
    FROM nodes_fts f JOIN nodes n ON f.id=n.id
    WHERE nodes_fts MATCH ?
    ORDER BY final_score ASC
    LIMIT ?
    """
    
    try:
        rows = conn.execute(sql, (safe_query, limit)).fetchall()
        
        # Update access telemetry
        if rows:
            conn.execute("BEGIN IMMEDIATE;")
            now = datetime.now(timezone.utc).isoformat()
            for r in rows:
                conn.execute("UPDATE nodes SET access_count = access_count + 1, last_accessed_at = ? WHERE id = ?", (now, r[0]))
            conn.commit()
            
    finally:
        conn.close()
        
    if not rows:
        return "No relevant memories found."
        
    res = [f"ID: {r[0]}\nContent: {r[1]}" for r in rows]
    return "\n\n".join(res)

@mcp.tool()
def save_graph_relation(source: str, relation: str, target: str) -> str:
    """Save a strict Subject-Predicate-Object relation for Knowledge Graph traversal."""
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        conn.execute("INSERT OR IGNORE INTO edges (source, target, relation) VALUES (?, ?, ?)", 
                     (source.strip(), target.strip(), relation.strip().lower()))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    return f"Saved edge: [{source}] -[{relation}]-> [{target}]"

def main():
    mcp.run()

if __name__ == "__main__":
    main()
