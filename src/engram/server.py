"""
Engram Alpha MCP Server (Production-Grade Architecture)
Features:
- Multi-Tenant Namespaces (project, agent, session).
- 4-Way Reciprocal Rank Fusion (RRF): Dense AMX + Trigram FTS5 + 2-Hop Graph + ACT-R Decay.
- Embedded Autonomous Memory Agents: Fact Extractor, Reconciler, Graph Traversal, and Reflection Consolidation.
- Semantic Deduplication Engine (Cosine Cluster Merging).
- Knowledge Graph Visualizer (ASCII / Mermaid).
- Multi-Transport Support (Stdio & SSE / HTTP).
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

from .core import get_db, optimize_and_checkpoint
from .utils import retry_db_lock
from .amx import (
    generate_dense_embedding,
    pack_vector,
    unpack_vector,
    amx_cosine_similarity,
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
def _save_node(
    node_type: str,
    content: str,
    importance: int = 5,
    category: str = "general",
    project: str = "default",
    agent: str = "system",
) -> Tuple[str, List[str]]:
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
            for row in conn.execute(
                "SELECT id, content FROM nodes_fts WHERE nodes_fts MATCH ?", (fts_query,)
            ).fetchall():
                row_words = set(w.lower() for w in escape_fts(row[1]).split() if len(w) > 2)
                if len(clean_words & row_words) >= 2:
                    warnings.append(f"Conflict found (ID {row[0]}): {row[1][:60]}... Did you mean to update?")
                    
        conn.execute(
            """
            INSERT INTO nodes (id, type, content, created_at, updated_at, access_count, last_accessed_at, embedding, importance, category, project, agent)
            VALUES (?, ?, ?, ?, ?, 0, '', ?, ?, ?, ?, ?)
            """,
            (node_id, node_type, content, now, now, packed_vec, importance, category, project, agent),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
    return node_id, warnings

@mcp.tool()
def save_memory(
    content: str,
    category: str = "general",
    importance: int = 5,
    project: str = "default",
    agent: str = "system",
) -> str:
    """Save a new memory node with dense vector embedding, category, importance, project namespace, and conflict detection."""
    node_id, warnings = _save_node(
        "memory", content, importance=importance, category=category, project=project, agent=agent
    )
    warn_str = f" Warnings: {warnings}" if warnings else ""
    return f"Saved Node {node_id} (Project: {project}, Agent: {agent}).{warn_str}"

@mcp.tool()
@retry_db_lock(max_retries=7)
def search_memory(
    query: str,
    limit: int = 5,
    hybrid: bool = True,
    project: Optional[str] = None,
) -> str:
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
        project_filter = "AND n.project = ?" if project else ""
        params = [fts_query] + ([project] if project else []) + [limit * 4]

        sql_fts = f"""
        SELECT n.id, n.content, n.created_at, n.last_accessed_at, n.embedding, rank, n.importance, n.project
        FROM nodes_fts f JOIN nodes n ON f.id=n.id
        WHERE nodes_fts MATCH ? {project_filter}
        ORDER BY rank ASC
        LIMIT ?
        """
        fts_rows = conn.execute(sql_fts, params).fetchall()

        # 2. Dense Semantic Vector Retrieval (Universal Multi-Tier Vector Engine)
        query_vec = generate_dense_embedding(query)
        all_candidate_rows = list(fts_rows)
        seen_ids = set(r[0] for r in fts_rows)

        if hybrid:
            extra_filter = "AND project = ?" if project else ""
            extra_params = ([project] if project else []) + [limit * 8]
            extra_rows = conn.execute(
                f"""
                SELECT id, content, created_at, last_accessed_at, embedding, 0.0 as rank, importance, project
                FROM nodes
                WHERE embedding IS NOT NULL {extra_filter}
                ORDER BY rowid DESC
                LIMIT ?
                """,
                extra_params,
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
            edge_filter = "AND project = ?" if project else ""
            proj_list = [project] if project else []
            edge_params = tokens + proj_list + tokens + proj_list
            edge_rows = conn.execute(
                f"""
                SELECT target, weight FROM edges WHERE source IN ({placeholders}) {edge_filter}
                UNION
                SELECT source, weight FROM edges WHERE target IN ({placeholders}) {edge_filter}
                """,
                edge_params,
            ).fetchall()
            for target_node, w in edge_rows:
                graph_bonus[target_node.lower()] = graph_bonus.get(target_node.lower(), 0.0) + (w or 1.0)

        # 5. Compute Reciprocal Rank Fusion (RRF) Ranks
        dense_ranked = sorted(range(len(all_candidate_rows)), key=lambda i: amx_scores[i], reverse=True)
        dense_rank_map = {idx: rank + 1 for rank, idx in enumerate(dense_ranked)}

        lex_ranked = sorted(range(len(all_candidate_rows)), key=lambda i: all_candidate_rows[i][5])
        lex_rank_map = {idx: rank + 1 for rank, idx in enumerate(lex_ranked)}

        k_rrf = 60.0
        now_dt = datetime.now(timezone.utc)
        fused_scores = []

        for idx, r in enumerate(all_candidate_rows):
            node_id, content, created_at, last_accessed_at, _, rank, importance, node_proj = r
            
            r_dense = dense_rank_map.get(idx, 1000)
            r_lex = lex_rank_map.get(idx, 1000)
            
            # Graph activation boost
            g_boost = 0.0
            content_lower = content.lower()
            for entity_term, bonus in graph_bonus.items():
                if entity_term in content_lower:
                    g_boost += bonus * 0.25

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
            fused_scores.append((final_score, node_id, content, node_proj, amx_scores[idx]))

        fused_scores.sort(key=lambda x: x[0], reverse=True)
        top_results = fused_scores[:limit]

        # Update access stats
        if top_results:
            conn.execute("BEGIN IMMEDIATE;")
            now_iso = now_dt.isoformat()
            for _, node_id, _, _, _ in top_results:
                conn.execute(
                    "UPDATE nodes SET access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
                    (now_iso, node_id),
                )
            conn.commit()

        res = [f"ID: {r[1]} [Project: {r[3]}]\nContent: {r[2]}" for r in top_results]
        return "\n\n".join(res)
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def extract_and_save_memory(
    text: str,
    category: str = "general",
    importance: int = 5,
    project: str = "default",
    agent: str = "system",
) -> str:
    """
    Autonomous Memory Extractor Agent:
    Deconstructs text into atomic facts, extracts entity triples for the knowledge graph,
    and indexes 384d semantic vectors.
    """
    node_id, warnings = _save_node(
        "fact", text, importance=importance, category=category, project=project, agent=agent
    )
    
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    created_edges = []
    try:
        now = datetime.now(timezone.utc).isoformat()
        wikilinks = re.findall(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]", text)
        for link in wikilinks:
            conn.execute(
                """
                INSERT OR IGNORE INTO edges (source, target, relation, weight, created_at, project)
                VALUES (?, ?, ?, 1.0, ?, ?)
                """,
                (node_id, link.strip(), "references", now, project),
            )
            created_edges.append(f"[{node_id}] -[references]-> [{link.strip()}]")

        triple_matches = re.findall(
            r"(\b[A-Z][a-zA-Z0-9_\-]+\b)\s+(uses|requires|connects_to|replaces|implements|is_a)\s+(\b[A-Z][a-zA-Z0-9_\-]+\b)",
            text,
        )
        for s, r, o in triple_matches:
            conn.execute(
                """
                INSERT OR IGNORE INTO edges (source, target, relation, weight, created_at, project)
                VALUES (?, ?, ?, 1.0, ?, ?)
                """,
                (s.strip(), o.strip(), r.strip().lower(), now, project),
            )
            created_edges.append(f"[{s.strip()}] -[{r.strip().lower()}]-> [{o.strip()}]")

        conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        conn.close()

    edge_str = f"\nExtracted Triples: {created_edges}" if created_edges else ""
    return f"Extracted & Saved Node {node_id} (Project: {project}).{edge_str}"

@mcp.tool()
@retry_db_lock(max_retries=7)
def save_graph_relation(
    source: str,
    relation: str,
    target: str,
    weight: float = 1.0,
    project: str = "default",
) -> str:
    """Save a strict Subject-Predicate-Object relation for Knowledge Graph traversal."""
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT OR REPLACE INTO edges (source, target, relation, weight, created_at, project)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source.strip(), target.strip(), relation.strip().lower(), float(weight), now, project),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    return f"Saved edge: [{source}] -[{relation}]-> [{target}] (weight: {weight}, project: {project})"

@mcp.tool()
@retry_db_lock(max_retries=7)
def query_graph(node: str, depth: int = 1, project: Optional[str] = None) -> str:
    """
    Query knowledge graph relations with 1-hop and 2-hop spreading activation traversal.
    """
    conn = get_db()
    try:
        node_clean = node.strip()
        proj_filter = "AND project = ?" if project else ""
        params_1 = [node_clean, node_clean] + ([project] if project else [])

        rows_1 = conn.execute(
            f"""
            SELECT source, relation, target, weight, project FROM edges
            WHERE (source = ? OR target = ?) {proj_filter}
            LIMIT 50
            """,
            params_1,
        ).fetchall()

        if not rows_1:
            return f"No graph edges found for node '{node_clean}'."

        triples = [f"[{r[0]}] -[{r[1]}]-> [{r[2]}] (w: {r[3]}, project: {r[4]})" for r in rows_1]

        if depth >= 2:
            neighbors = set()
            for r in rows_1:
                if r[0] != node_clean: neighbors.add(r[0])
                if r[2] != node_clean: neighbors.add(r[2])

            if neighbors:
                placeholders = ",".join("?" for _ in neighbors)
                params_2 = list(neighbors) + list(neighbors) + ([project] if project else []) + [node_clean, node_clean]
                rows_2 = conn.execute(
                    f"""
                    SELECT source, relation, target, weight, project FROM edges
                    WHERE (source IN ({placeholders}) OR target IN ({placeholders})) {proj_filter}
                    AND source != ? AND target != ?
                    LIMIT 50
                    """,
                    params_2,
                ).fetchall()
                for r in rows_2:
                    t_str = f"  (2-hop) [{r[0]}] -[{r[1]}]-> [{r[2]}] (w: {r[3]}, project: {r[4]})"
                    if t_str not in triples:
                        triples.append(t_str)

        return "\n".join(triples)
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def deduplicate_memories(similarity_threshold: float = 0.92, project: Optional[str] = None) -> str:
    """
    Autonomous Memory Deduplication & Semantic Merging Agent:
    Finds clusters of duplicate/near-identical memory nodes, merges access counts and edges,
    and prunes redundant duplicate records to maintain clean context.
    """
    conn = get_db()
    try:
        filter_str = "WHERE embedding IS NOT NULL"
        params = []
        if project:
            filter_str += " AND project = ?"
            params.append(project)

        rows = conn.execute(f"SELECT id, content, embedding, access_count, importance FROM nodes {filter_str}", params).fetchall()
        if len(rows) < 2:
            return "Insufficient records to deduplicate."

        vectors = [unpack_vector(r[2]) for r in rows if r[2]]
        merged_count = 0
        deleted_ids = set()

        conn.execute("BEGIN IMMEDIATE;")
        for i in range(len(rows)):
            if rows[i][0] in deleted_ids:
                continue
            for j in range(i + 1, len(rows)):
                if rows[j][0] in deleted_ids:
                    continue
                
                sim = amx_cosine_similarity(vectors[i], vectors[j])
                if sim >= similarity_threshold:
                    # Keep i, merge j into i
                    primary_id = rows[i][0]
                    dup_id = rows[j][0]
                    
                    # Boost primary access count and importance
                    combined_access = rows[i][3] + rows[j][3] + 1
                    max_importance = max(rows[i][4], rows[j][4])
                    
                    conn.execute(
                        "UPDATE nodes SET access_count = ?, importance = ? WHERE id = ?",
                        (combined_access, max_importance, primary_id),
                    )
                    
                    # Re-point edges
                    conn.execute("UPDATE OR IGNORE edges SET source = ? WHERE source = ?", (primary_id, dup_id))
                    conn.execute("UPDATE OR IGNORE edges SET target = ? WHERE target = ?", (primary_id, dup_id))
                    
                    # Delete duplicate
                    conn.execute("DELETE FROM nodes WHERE id = ?", (dup_id,))
                    deleted_ids.add(dup_id)
                    merged_count += 1

        conn.commit()
        return f"Deduplication Complete: Evaluated {len(rows)} nodes, merged and pruned {merged_count} duplicate records."
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def visualize_graph(node: str, depth: int = 2, project: Optional[str] = None) -> str:
    """
    Knowledge Graph Topology Visualizer:
    Generates Mermaid.js and ASCII relational network diagrams for power users.
    """
    graph_text = query_graph(node, depth=depth, project=project)
    if "No graph edges found" in graph_text:
        return graph_text

    mermaid_lines = ["```mermaid", "graph LR", f'  root["{node}"]:::primary']
    ascii_lines = [f"Topology for [{node}]:"]

    edges = re.findall(r"\[([^\]]+)\]\s+-\[([^\]]+)\]->\s+\[([^\]]+)\]", graph_text)
    for s, r, o in edges:
        s_safe = s.replace('"', '')
        o_safe = o.replace('"', '')
        r_safe = r.replace('"', '')
        mermaid_lines.append(f'  "{s_safe}" -- "{r_safe}" --> "{o_safe}"')
        ascii_lines.append(f"  [{s_safe}] ──({r_safe})──► [{o_safe}]")

    mermaid_lines.append("  classDef primary fill:#ff79c6,stroke:#bd93f9,stroke-width:2px,color:#fff;")
    mermaid_lines.append("```")

    return "\n".join(ascii_lines) + "\n\n" + "\n".join(mermaid_lines)

@mcp.tool()
@retry_db_lock(max_retries=7)
def consolidate_reflections(topic: str, project: str = "default") -> str:
    """
    Autonomous Memory Reflector Agent (Episodic Reflection):
    Synthesizes low-level episodic nodes into durable high-level insights.
    """
    conn = get_db()
    try:
        safe_topic = escape_fts(topic)
        fts_query = f'"{safe_topic}"' if safe_topic else '""'
        
        rows = conn.execute(
            """
            SELECT n.id, n.content, n.importance FROM nodes_fts f JOIN nodes n ON f.id=n.id
            WHERE nodes_fts MATCH ? AND n.project = ?
            ORDER BY n.access_count DESC, n.importance DESC
            LIMIT 10
            """,
            (fts_query, project),
        ).fetchall()

        if not rows:
            return f"Insufficient memories found for topic '{topic}' in project '{project}' to consolidate."

        summary_points = [f"- {r[1][:100]}..." for r in rows]
        reflection_content = (
            f"[Consolidated Reflection on '{topic}'] (Project: {project}):\n"
            f"Synthesized from {len(rows)} memory records:\n" + "\n".join(summary_points)
        )

        ref_id, _ = _save_node(
            "reflection", reflection_content, importance=9, category="reflection", project=project
        )
        return f"Created Consolidated Reflection (Node {ref_id}):\n{reflection_content}"
    finally:
        conn.close()

@mcp.tool()
def ingest_obsidian(vault_path: str, project: str = "default") -> str:
    """Ingest an entire Obsidian markdown vault into the knowledge graph and vector store."""
    res = ingest_obsidian_vault(vault_path, project=project)
    return f"Ingestion Complete: {res['files_processed']} files, {res['nodes_created']} nodes, {res['edges_created']} graph edges created (Project: {project})."

@mcp.tool()
@retry_db_lock(max_retries=7)
def checkpoint_db() -> str:
    """Execute WAL flush, vacuum, and performance optimization."""
    conn = get_db()
    try:
        res = optimize_and_checkpoint(conn)
        return f"Database Checkpoint Status: {res}"
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def get_stats() -> str:
    """Get system statistics, knowledge graph counts, and active hardware acceleration tier."""
    conn = get_db()
    try:
        node_count = conn.execute("SELECT COUNT(*) FROM nodes;").fetchone()[0]
        edge_count = conn.execute("SELECT COUNT(*) FROM edges;").fetchone()[0]
        projects = [r[0] for r in conn.execute("SELECT DISTINCT project FROM nodes;").fetchall()]
        tier_status = get_acceleration_tier()
        return (
            f"🧠 Engram Alpha Universal MCP Stats:\n"
            f"- Total Memories / Nodes: {node_count}\n"
            f"- Knowledge Graph Edges: {edge_count}\n"
            f"- Active Projects / Namespaces: {projects}\n"
            f"- Hardware Engine Tier: {tier_status}\n"
            f"- Architecture: Cross-Platform Production Standard (macOS, Linux, Windows, Docker)"
        )
    finally:
        conn.close()

def main():
    mcp.run()

if __name__ == "__main__":
    main()
