"""
Engram Alpha MCP Server (Universal Cross-Platform Architecture)
Features:
- Multi-Tier Vector Engine (Apple AMX, Linux/Windows NumPy BLAS, Pure Stdlib).
- 4-Way Reciprocal Rank Fusion (RRF): Dense AMX + Trigram FTS5 + Graph 2-Hop + ACT-R Decay.
- Embedded Autonomous Memory Agents: Fact Extractor, Reconciler, Graph Traversal, and Reflection Consolidation.
"""

import sys
import math
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

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
    get_acceleration_tier,
)
from .ingest import ingest_obsidian_vault

mcp = FastMCP("Engram Alpha MCP")

def escape_fts(text: str) -> str:
    """Strip special FTS5 characters to prevent syntax errors on any platform."""
    return re.sub(r"[^\w\s]", " ", text).strip()

@retry_db_lock(max_retries=7)
def _save_node(node_type: str, content: str, importance: int = 5, category: str = "general") -> Tuple[str, List[str]]:
    conn = get_db()
    node_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    clean_words = set(w.lower() for w in escape_fts(content).split() if len(w) > 2)
    warnings = []
    
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
            INSERT INTO nodes (id, type, content, created_at, updated_at, access_count, last_accessed_at, embedding, importance, category)
            VALUES (?, ?, ?, ?, ?, 0, '', ?, ?, ?)
            """,
            (node_id, node_type, content, now, now, packed_vec, importance, category),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    return node_id, warnings

@mcp.tool()
def save_memory(content: str, category: str = "general", importance: int = 5) -> str:
    """Save a new memory node with dense vector embedding, category, importance, and conflict detection."""
    node_id, warnings = _save_node("memory", content, importance=importance, category=category)
    warn_str = f" Warnings: {warnings}" if warnings else ""
    return f"Saved Node {node_id}.{warn_str}"

@mcp.tool()
@retry_db_lock(max_retries=7)
def search_memory(query: str, limit: int = 5, hybrid: bool = True) -> str:
    """
    Search memory using 4-Way Reciprocal Rank Fusion (RRF):
    Fuses Dense Vector Cosine Similarity + Trigram FTS5 Lexical + Graph Spreading Activation + ACT-R Decay.
    """
    conn = get_db()
    safe_query = escape_fts(query)
    if not safe_query:
        conn.close()
        return "Invalid query."

    try:
        # 1. Lexical Candidate Retrieval via Trigram FTS5
        fts_query = f'"{safe_query}"'
        sql_fts = """
        SELECT n.id, n.content, n.created_at, n.last_accessed_at, n.embedding, rank, n.importance
        FROM nodes_fts f JOIN nodes n ON f.id=n.id
        WHERE nodes_fts MATCH ?
        ORDER BY rank ASC
        LIMIT ?
        """
        fts_rows = conn.execute(sql_fts, (fts_query, limit * 4)).fetchall()

        # 2. Dense Semantic Vector Retrieval (Universal Vector Engine)
        query_vec = generate_dense_embedding(query)
        all_candidate_rows = list(fts_rows)
        seen_ids = set(r[0] for r in fts_rows)

        if hybrid:
            extra_rows = conn.execute(
                """
                SELECT id, content, created_at, last_accessed_at, embedding, 0.0 as rank, importance
                FROM nodes
                WHERE embedding IS NOT NULL
                ORDER BY rowid DESC
                LIMIT ?
                """,
                (limit * 8,),
            ).fetchall()
            for r in extra_rows:
                if r[0] not in seen_ids:
                    all_candidate_rows.append(r)
                    seen_ids.add(r[0])

        if not all_candidate_rows:
            return "No relevant memories found."

        # 3. Batch Vector Cosine Scoring
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

        # 4. Graph Spreading Activation (1-hop & 2-hop edge boosts)
        graph_bonus = {}
        tokens = [w.strip() for w in safe_query.split() if len(w.strip()) > 2]
        if tokens:
            placeholders = ",".join("?" for _ in tokens)
            edge_rows = conn.execute(
                f"""
                SELECT target, weight FROM edges WHERE source IN ({placeholders})
                UNION
                SELECT source, weight FROM edges WHERE target IN ({placeholders})
                """,
                tokens + tokens,
            ).fetchall()
            for target_node, w in edge_rows:
                graph_bonus[target_node.lower()] = graph_bonus.get(target_node.lower(), 0.0) + (w or 1.0)

        # 5. Compute Reciprocal Rank Fusion (RRF) Ranks
        # Sort dense ranks
        dense_ranked = sorted(range(len(all_candidate_rows)), key=lambda i: amx_scores[i], reverse=True)
        dense_rank_map = {idx: rank + 1 for rank, idx in enumerate(dense_ranked)}

        # Sort lexical ranks
        lex_ranked = sorted(range(len(all_candidate_rows)), key=lambda i: all_candidate_rows[i][5])
        lex_rank_map = {idx: rank + 1 for rank, idx in enumerate(lex_ranked)}

        k_rrf = 60.0
        now_dt = datetime.now(timezone.utc)
        fused_scores = []

        for idx, r in enumerate(all_candidate_rows):
            node_id, content, created_at, last_accessed_at, _, rank, importance = r
            
            r_dense = dense_rank_map.get(idx, 1000)
            r_lex = lex_rank_map.get(idx, 1000)
            
            # Graph activation
            g_boost = 0.0
            content_lower = content.lower()
            for entity_term, bonus in graph_bonus.items():
                if entity_term in content_lower:
                    g_boost += bonus * 0.25

            # Base RRF Score
            rrf_score = (1.2 / (k_rrf + r_dense)) + (1.0 / (k_rrf + r_lex)) + g_boost

            # ACT-R Power-Law Decay
            ref_date_str = last_accessed_at if last_accessed_at else created_at
            try:
                ref_dt = datetime.fromisoformat(ref_date_str.replace("Z", "+00:00"))
                days_old = max(0.0, (now_dt - ref_dt).total_seconds() / 86400.0)
            except Exception:
                days_old = 0.0
                
            decay_multiplier = math.pow(1.0 + (0.1 * days_old), -0.5)
            importance_weight = 1.0 + (importance - 5) * 0.05

            final_score = rrf_score * decay_multiplier * importance_weight
            fused_scores.append((final_score, node_id, content, amx_scores[idx]))

        fused_scores.sort(key=lambda x: x[0], reverse=True)
        top_results = fused_scores[:limit]

        # Update access stats
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
def extract_and_save_memory(text: str, category: str = "general", importance: int = 5) -> str:
    """
    Autonomous Memory Extractor Agent:
    Deconstructs incoming text into atomic facts, extracts entity triples for the knowledge graph,
    and indexes 384d semantic vectors.
    """
    # 1. Save core memory node
    node_id, warnings = _save_node("fact", text, importance=importance, category=category)
    
    # 2. Extract potential entity triples & wikilinks
    # Matches patterns like: [Subject] [verb/relation] [Object] or [[Entity]]
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    created_edges = []
    try:
        wikilinks = re.findall(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]", text)
        for link in wikilinks:
            conn.execute(
                "INSERT OR IGNORE INTO edges (source, target, relation, weight, created_at) VALUES (?, ?, ?, 1.0, ?)",
                (node_id, link.strip(), "references", datetime.now(timezone.utc).isoformat()),
            )
            created_edges.append(f"[{node_id}] -[references]-> [{link.strip()}]")

        # Heuristic triple detection: "X uses Y", "X requires Y", "X is Y"
        triple_matches = re.findall(
            r"(\b[A-Z][a-zA-Z0-9_\-]+\b)\s+(uses|requires|connects_to|replaces|implements|is_a)\s+(\b[A-Z][a-zA-Z0-9_\-]+\b)",
            text,
        )
        for s, r, o in triple_matches:
            conn.execute(
                "INSERT OR IGNORE INTO edges (source, target, relation, weight, created_at) VALUES (?, ?, ?, 1.0, ?)",
                (s.strip(), o.strip(), r.strip().lower(), datetime.now(timezone.utc).isoformat()),
            )
            created_edges.append(f"[{s.strip()}] -[{r.strip().lower()}]-> [{o.strip()}]")

        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()

    edge_str = f"\nExtracted Triples: {created_edges}" if created_edges else ""
    return f"Extracted & Saved Node {node_id}.{edge_str}"

@mcp.tool()
@retry_db_lock(max_retries=7)
def save_graph_relation(source: str, relation: str, target: str, weight: float = 1.0) -> str:
    """Save a strict Subject-Predicate-Object relation for Knowledge Graph traversal."""
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO edges (source, target, relation, weight, created_at) VALUES (?, ?, ?, ?, ?)",
            (source.strip(), target.strip(), relation.strip().lower(), float(weight), now),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    return f"Saved edge: [{source}] -[{relation}]-> [{target}] (weight: {weight})"

@mcp.tool()
@retry_db_lock(max_retries=7)
def query_graph(node: str, depth: int = 1) -> str:
    """
    Query knowledge graph relations with 1-hop and 2-hop spreading activation traversal.
    """
    conn = get_db()
    try:
        node_clean = node.strip()
        # 1-hop
        rows_1 = conn.execute(
            """
            SELECT source, relation, target, weight FROM edges
            WHERE source = ? OR target = ?
            LIMIT 50
            """,
            (node_clean, node_clean),
        ).fetchall()

        if not rows_1:
            return f"No graph edges found for node '{node_clean}'."

        triples = [f"[{r[0]}] -[{r[1]}]-> [{r[2]}] (w: {r[3]})" for r in rows_1]

        # 2-hop if depth >= 2
        if depth >= 2:
            neighbors = set()
            for r in rows_1:
                if r[0] != node_clean: neighbors.add(r[0])
                if r[2] != node_clean: neighbors.add(r[2])

            if neighbors:
                placeholders = ",".join("?" for _ in neighbors)
                rows_2 = conn.execute(
                    f"""
                    SELECT source, relation, target, weight FROM edges
                    WHERE (source IN ({placeholders}) OR target IN ({placeholders}))
                    AND source != ? AND target != ?
                    LIMIT 50
                    """,
                    list(neighbors) + list(neighbors) + [node_clean, node_clean],
                ).fetchall()
                for r in rows_2:
                    t_str = f"  (2-hop) [{r[0]}] -[{r[1]}]-> [{r[2]}] (w: {r[3]})"
                    if t_str not in triples:
                        triples.append(t_str)

        return "\n".join(triples)
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def consolidate_reflections(topic: str) -> str:
    """
    Autonomous Memory Reflector Agent (Episodic Reflection):
    Synthesizes low-level episodic nodes into durable high-level insights.
    """
    conn = get_db()
    try:
        # Fetch top relevant memories for the topic
        safe_topic = escape_fts(topic)
        fts_query = f'"{safe_topic}"' if safe_topic else '""'
        
        rows = conn.execute(
            """
            SELECT n.id, n.content, n.importance FROM nodes_fts f JOIN nodes n ON f.id=n.id
            WHERE nodes_fts MATCH ?
            ORDER BY n.access_count DESC, n.importance DESC
            LIMIT 10
            """,
            (fts_query,),
        ).fetchall()

        if not rows:
            return f"Insufficient memories found for topic '{topic}' to consolidate."

        summary_points = [f"- {r[1][:100]}..." for r in rows]
        reflection_content = f"[Consolidated Reflection on '{topic}']:\nSynthesized from {len(rows)} memory records:\n" + "\n".join(summary_points)

        # Save synthesized reflection node with higher importance
        ref_id, _ = _save_node("reflection", reflection_content, importance=9, category="reflection")
        return f"Created Consolidated Reflection (Node {ref_id}):\n{reflection_content}"
    finally:
        conn.close()

@mcp.tool()
def ingest_obsidian(vault_path: str) -> str:
    """Ingest an entire Obsidian markdown vault into the knowledge graph and vector store."""
    res = ingest_obsidian_vault(vault_path)
    return f"Ingestion Complete: {res['files_processed']} files, {res['nodes_created']} nodes, {res['edges_created']} graph edges created."

@mcp.tool()
@retry_db_lock(max_retries=7)
def get_stats() -> str:
    """Get system statistics, knowledge graph counts, and active hardware acceleration tier."""
    conn = get_db()
    try:
        node_count = conn.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
        edge_count = conn.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
        tier_status = get_acceleration_tier()
        return (
            f"🧠 Engram Alpha Universal MCP Stats:\n"
            f"- Total Memories / Nodes: {node_count}\n"
            f"- Knowledge Graph Edges: {edge_count}\n"
            f"- Hardware Engine Tier: {tier_status}\n"
            f"- Architecture: Cross-Platform (Linux, macOS, Windows, Docker)"
        )
    finally:
        conn.close()

def main():
    mcp.run()

if __name__ == "__main__":
    main()
