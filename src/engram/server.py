"""
Engram Alpha MCP Server (V3 Architecture)
Integrates FastMCP, AMX Hardware-Accelerated Vector Cosine Similarity,
Trigram FTS5, ACT-R Decay, and Obsidian Markdown Graph Ingestion.
"""

import sys
import math
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    try:
        from mcp.server.mcpserver import MCPServer as FastMCP
    except (ImportError, ModuleNotFoundError):
        from mcp.server import FastMCP
from .core import get_db
from .utils import retry_db_lock
from .amx import (
    generate_dense_embedding,
    pack_vector,
    unpack_vector,
    amx_batch_cosine_similarity,
    is_amx_hardware_available,
)
from .ingest import ingest_obsidian_vault

mcp = FastMCP("Engram Alpha MCP")

def escape_fts(text: str) -> str:
    """Strip special FTS5 characters to prevent syntax errors."""
    return re.sub(r"[^\w\s]", " ", text).strip()

@retry_db_lock(max_retries=7)
def _save_node(node_type: str, content: str) -> str:
    conn = get_db()
    node_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    clean_words = set(w.lower() for w in escape_fts(content).split() if len(w) > 2)
    warnings = []
    
    # Generate 384d AMX Dense Embedding
    dense_vec = generate_dense_embedding(content)
    packed_vec = pack_vector(dense_vec)
    
    conn.execute("BEGIN IMMEDIATE;")
    try:
        if clean_words:
            fts_query = " OR ".join(f'"{w}"' for w in clean_words)
            for row in conn.execute("SELECT id, content FROM nodes_fts WHERE nodes_fts MATCH ?", (fts_query,)).fetchall():
                row_words = set(w.lower() for w in escape_fts(row[1]).split() if len(w) > 2)
                if len(clean_words & row_words) >= 2:
                    warnings.append(f"Conflict found (ID {row[0]}): {row[1][:60]}... Did you mean to update?")
                    
        conn.execute(
            """
            INSERT INTO nodes (id, type, content, created_at, updated_at, access_count, last_accessed_at, embedding)
            VALUES (?, ?, ?, ?, ?, 0, '', ?)
            """,
            (node_id, node_type, content, now, now, packed_vec),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    warn_str = f" Warnings: {warnings}" if warnings else ""
    return f"Saved Node {node_id}.{warn_str}"

@mcp.tool()
def save_memory(content: str) -> str:
    """Save a new memory node with AMX dense vector embedding and conflict detection."""
    return _save_node("memory", content)

@mcp.tool()
@retry_db_lock(max_retries=7)
def search_memory(query: str, limit: int = 5, hybrid: bool = True) -> str:
    """
    Search memory using Fused Hybrid Retrieval:
    Trigram FTS5 + Apple AMX Hardware Vector Cosine Similarity + ACT-R Power Law Decay.
    """
    conn = get_db()
    safe_query = escape_fts(query)
    if not safe_query:
        conn.close()
        return "Invalid query."

    try:
        # 1. Lexical Candidates via FTS5 Trigram
        fts_query = f'"{safe_query}"'
        sql_fts = """
        SELECT n.id, n.content, n.created_at, n.last_accessed_at, n.embedding, rank,
               (rank * POWER(1.0 + (0.1 * MAX(0, (julianday('now') - julianday(COALESCE(NULLIF(n.last_accessed_at, ''), n.created_at))))), -0.5)) as fts_decay_score
        FROM nodes_fts f JOIN nodes n ON f.id=n.id
        WHERE nodes_fts MATCH ?
        ORDER BY fts_decay_score ASC
        LIMIT ?
        """
        fts_rows = conn.execute(sql_fts, (fts_query, limit * 3)).fetchall()

        # 2. Vector Semantic Scoring using Apple Silicon AMX Coprocessor
        query_vec = generate_dense_embedding(query)
        
        # If hybrid requested or few FTS results, fetch recent candidate nodes for vector projection
        all_candidate_rows = list(fts_rows)
        seen_ids = set(r[0] for r in fts_rows)

        if hybrid and len(fts_rows) < limit * 2:
            extra_rows = conn.execute(
                """
                SELECT id, content, created_at, last_accessed_at, embedding, 0.0 as rank, 0.0 as fts_decay_score
                FROM nodes
                WHERE embedding IS NOT NULL
                ORDER BY rowid DESC
                LIMIT ?
                """,
                (limit * 5,),
            ).fetchall()
            for r in extra_rows:
                if r[0] not in seen_ids:
                    all_candidate_rows.append(r)
                    seen_ids.add(r[0])

        if not all_candidate_rows:
            return "No relevant memories found."

        # Extract embeddings and compute batch cosine similarity via AMX Accelerate
        candidate_vectors = []
        valid_indices = []
        for i, row in enumerate(all_candidate_rows):
            blob = row[4]
            if blob:
                candidate_vectors.append(unpack_vector(blob))
                valid_indices.append(i)

        amx_scores = [0.0] * len(all_candidate_rows)
        if candidate_vectors:
            cos_scores = amx_batch_cosine_similarity(query_vec, candidate_vectors)
            for idx, cos_sim in zip(valid_indices, cos_scores):
                amx_scores[idx] = max(0.0, float(cos_sim))

        # 3. Fuse FTS + Vector + ACT-R Decay
        scored_results = []
        now_dt = datetime.now(timezone.utc)
        
        for idx, r in enumerate(all_candidate_rows):
            node_id, content, created_at, last_accessed_at, _, rank, fts_score = r
            v_score = amx_scores[idx]
            
            # Days old for ACT-R
            ref_date_str = last_accessed_at if last_accessed_at else created_at
            try:
                ref_dt = datetime.fromisoformat(ref_date_str.replace("Z", "+00:00"))
                days_old = max(0.0, (now_dt - ref_dt).total_seconds() / 86400.0)
            except Exception:
                days_old = 0.0
                
            decay_multiplier = math.pow(1.0 + (0.1 * days_old), -0.5)

            # Combined Score: higher is better
            # If matched FTS, invert rank (FTS rank is negative/lower is better in SQLite)
            lexical_component = max(0.0, -fts_score) if fts_score != 0.0 else 0.0
            semantic_component = v_score * 2.0
            
            final_composite_score = (lexical_component + semantic_component + 0.1) * decay_multiplier
            scored_results.append((final_composite_score, node_id, content, v_score))

        # Sort descending by composite score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_results = scored_results[:limit]

        # Update access stats atomically
        if top_results:
            conn.execute("BEGIN IMMEDIATE;")
            now_iso = now_dt.isoformat()
            for _, node_id, _, _ in top_results:
                conn.execute(
                    "UPDATE nodes SET access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
                    (now_iso, node_id),
                )
            conn.commit()

        res = [f"ID: {r[1]}\nContent: {r[2]}" for r in top_results]
        return "\n\n".join(res)
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def save_graph_relation(source: str, relation: str, target: str) -> str:
    """Save a strict Subject-Predicate-Object relation for Knowledge Graph traversal."""
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        conn.execute(
            "INSERT OR IGNORE INTO edges (source, target, relation) VALUES (?, ?, ?)",
            (source.strip(), target.strip(), relation.strip().lower()),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    return f"Saved edge: [{source}] -[{relation}]-> [{target}]"

@mcp.tool()
@retry_db_lock(max_retries=7)
def query_graph(node: str, depth: int = 1) -> str:
    """Query knowledge graph relations connected to a given entity node."""
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT source, relation, target FROM edges
            WHERE source = ? OR target = ?
            LIMIT 50
            """,
            (node.strip(), node.strip()),
        ).fetchall()
        
        if not rows:
            return f"No graph edges found for node '{node}'."
            
        triples = [f"[{r[0]}] -[{r[1]}]-> [{r[2]}]" for r in rows]
        return "\n".join(triples)
    finally:
        conn.close()

@mcp.tool()
def ingest_obsidian(vault_path: str) -> str:
    """Ingest an entire Obsidian markdown vault into the knowledge graph and AMX vector store."""
    res = ingest_obsidian_vault(vault_path)
    return f"Ingestion Complete: {res['files_processed']} files, {res['nodes_created']} nodes, {res['edges_created']} graph edges created."

@mcp.tool()
@retry_db_lock(max_retries=7)
def get_stats() -> str:
    """Get system statistics and hardware acceleration status."""
    conn = get_db()
    try:
        node_count = conn.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
        edge_count = conn.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
        amx_status = "ACTIVE (Apple Silicon AMX / Accelerate Framework)" if is_amx_hardware_available() else "INACTIVE (NumPy/Stdlib Fallback)"
        return (
            f"🧠 Engram Alpha V3 Stats:\n"
            f"- Total Memories / Nodes: {node_count}\n"
            f"- Knowledge Graph Edges: {edge_count}\n"
            f"- Hardware Coprocessor: {amx_status}"
        )
    finally:
        conn.close()

def main():
    mcp.run()

if __name__ == "__main__":
    main()
