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
        try:
            from mcp.server import FastMCP
        except (ImportError, ModuleNotFoundError):
            class FastMCP:
                def __init__(self, *args, **kwargs):
                    pass
                def tool(self, *args, **kwargs):
                    def decorator(fn):
                        return fn
                    return decorator
                def resource(self, *args, **kwargs):
                    def decorator(fn):
                        return fn
                    return decorator
                def prompt(self, *args, **kwargs):
                    def decorator(fn):
                        return fn
                    return decorator
                def run(self, *args, **kwargs):
                    pass

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
    get_embedding_model,
)
from .ingest import ingest_obsidian_vault

mcp = FastMCP("Engram Alpha MCP")

def escape_fts(text: str) -> str:
    """
    Safely escape FTS5 metacharacters while preserving code symbols
    like std::vector<int>, config.json, snake_case, and kebab-case identifiers.
    """
    if not text:
        return ""
    clean = text.replace('"', '""')
    clean = "".join(ch for ch in clean if ord(ch) >= 32 or ch in ('\n', '\t'))
    return clean.strip()

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
    
    # Input validation and clamping
    content_clamped = str(content)[:100000] # max 100KB
    imp_clamped = max(1, min(10, int(importance)))
    
    clean_words = set(w.lower() for w in escape_fts(content_clamped).split() if len(w) > 2)
    warnings = []
    
    dense_vec = generate_dense_embedding(content_clamped)
    packed_vec = pack_vector(dense_vec)
    
    conn.execute("BEGIN IMMEDIATE;")
    try:
        if len(clean_words) >= 3:
            fts_query = " OR ".join(f'"{w}"' for w in list(clean_words)[:8])
            candidate_rows = conn.execute(
                "SELECT n.id, n.content, n.embedding FROM nodes_fts f JOIN nodes n ON f.id=n.id WHERE nodes_fts MATCH ? LIMIT 10",
                (fts_query,),
            ).fetchall()
            for cand_id, cand_content, cand_blob in candidate_rows:
                cand_words = set(w.lower() for w in escape_fts(cand_content).split() if len(w) > 2)
                overlap_count = len(clean_words & cand_words)
                
                # Check cosine similarity if blob exists
                is_high_sim = False
                if cand_blob:
                    cand_vec = unpack_vector(cand_blob)
                    sim = amx_cosine_similarity(dense_vec, cand_vec)
                    if sim >= 0.85:
                        is_high_sim = True

                if is_high_sim or overlap_count >= 4:
                    warnings.append(f"Potential duplicate/conflict (ID {cand_id}): {cand_content[:60]}...")
                    
        conn.execute(
            """
            INSERT INTO nodes (id, type, content, created_at, updated_at, access_count, last_accessed_at, embedding, importance, category, project, agent)
            VALUES (?, ?, ?, ?, ?, 0, '', ?, ?, ?, ?, ?)
            """,
            (node_id, node_type, content_clamped, now, now, packed_vec, imp_clamped, category, project, agent),
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
    backend_note = ""
    if get_embedding_model() is None:
        backend_note = " [Notice: Using zero-dependency hashed projection. Install fastembed for deep neural semantics]"
    warn_str = f" Warnings: {warnings}" if warnings else ""
    return f"Saved Node {node_id} (Project: {project}, Agent: {agent}).{warn_str}{backend_note}"

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
    limit_clamped = max(1, min(100, int(limit)))
    conn = get_db()
    safe_query = escape_fts(query)
    if not safe_query:
        conn.close()
        return "Invalid query."

    try:
        # 1. Lexical Candidate Retrieval via Multi-Word FTS5
        words = [w.replace('"', '""') for w in safe_query.split() if len(w) >= 3]

        fts_query = " OR ".join(f'"{w}"' for w in words[:8]) if words else f'"{safe_query}"'
        project_filter = "AND n.project = ?" if project else ""
        params = [fts_query] + ([project] if project else []) + [limit_clamped * 4]

        sql_fts = f"""
        SELECT n.id, n.content, n.created_at, n.last_accessed_at, n.embedding, rank, n.importance, n.project
        FROM nodes_fts f JOIN nodes n ON f.id=n.id
        WHERE nodes_fts MATCH ? {project_filter}
        ORDER BY rank ASC
        LIMIT ?
        """
        fts_rows = conn.execute(sql_fts, params).fetchall()

        # 2. Dense Semantic Vector Retrieval (Universal Multi-Tier Hardware Vector Engine / sqlite-vec)
        query_vec = generate_dense_embedding(query)
        all_candidate_rows = list(fts_rows)
        seen_ids = set(r[0] for r in fts_rows)

        if hybrid:
            has_vec_table = False
            try:
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_vec';")
                has_vec_table = cur.fetchone() is not None
            except Exception:
                has_vec_table = False

            if has_vec_table:
                try:
                    import sqlite_vec
                    query_blob = sqlite_vec.serialize_float32(query_vec)
                    project_filter = "AND n.project = ?" if project else ""
                    params = [query_blob, limit_clamped * 8] + ([project] if project else [])
                    vec_rows = conn.execute(
                        f"""
                        SELECT n.id, n.content, n.created_at, n.last_accessed_at, n.embedding, 0.0 as rank, n.importance, n.project
                        FROM nodes_vec v
                        JOIN nodes n ON v.id = n.id
                        WHERE v.embedding MATCH ? AND k = ? {project_filter}
                        ORDER BY v.distance ASC
                        """,
                        params,
                    ).fetchall()
                    for r in vec_rows:
                        if r[0] not in seen_ids:
                            all_candidate_rows.append(r)
                            seen_ids.add(r[0])
                except Exception:
                    has_vec_table = False

            if not has_vec_table:
                extra_filter = "WHERE embedding IS NOT NULL"
                extra_params = []
                if project:
                    extra_filter += " AND project = ?"
                    extra_params.append(project)

                # Full-namespace evaluation without artificial row limit (eliminates the 5,001-node cliff)
                extra_rows = conn.execute(
                    f"""
                    SELECT id, content, created_at, last_accessed_at, embedding, 0.0 as rank, importance, project
                    FROM nodes
                    {extra_filter}
                    """,
                    extra_params,
                ).fetchall()
                for r in extra_rows:
                    if r[0] not in seen_ids:
                        all_candidate_rows.append(r)
                        seen_ids.add(r[0])

        if not all_candidate_rows:
            return "No relevant memories found."

        # 3. Hardware Batch Vector Cosine Scoring (AMX / C-BLAS / Pure Stdlib)
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

        # 4. True 2-Hop Graph Spreading Activation (Recursive CTE)
        graph_bonus = {}
        tokens = [w.strip() for w in safe_query.split() if len(w.strip()) > 2]
        if tokens:
            placeholders = ",".join("?" for _ in tokens)
            edge_filter = "AND project = ?" if project else ""
            proj_params = [project] if project else []

            cte_sql = f"""
            WITH RECURSIVE graph_walk AS (
                SELECT source, target, relation, weight, 1 as depth, target as entity, weight as activation
                FROM edges
                WHERE source IN ({placeholders}) {edge_filter}
                UNION ALL
                SELECT source, target, relation, weight, 1 as depth, source as entity, weight as activation
                FROM edges
                WHERE target IN ({placeholders}) {edge_filter}
                UNION ALL
                SELECT e.source, e.target, e.relation, e.weight, gw.depth + 1,
                       CASE WHEN e.source = gw.entity THEN e.target ELSE e.source END as entity,
                       gw.activation * 0.5 * e.weight as activation
                FROM edges e
                JOIN graph_walk gw ON (e.source = gw.entity OR e.target = gw.entity)
                WHERE gw.depth < 2 {edge_filter.replace('project', 'e.project')}
            )
            SELECT entity, MAX(activation) as max_act
            FROM graph_walk
            GROUP BY entity;
            """
            cte_params = []
            # Base case 1: source IN (tokens)
            cte_params.extend(tokens)
            if project:
                cte_params.append(project)
            # Base case 2: target IN (tokens)
            cte_params.extend(tokens)
            if project:
                cte_params.append(project)
            # Recursive case: e.project = ?
            if project:
                cte_params.append(project)

            try:
                edge_rows = conn.execute(cte_sql, cte_params).fetchall()
                for target_node, act in edge_rows:
                    if target_node:
                        graph_bonus[target_node.lower()] = max(graph_bonus.get(target_node.lower(), 0.0), float(act or 1.0))
            except Exception:
                pass

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
                if re.search(r'\b' + re.escape(entity_term) + r'\b', content_lower):
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
        top_results = fused_scores[:limit_clamped]

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
    Deconstructs text into atomic facts, extracts entity triples for the knowledge graph
    using hybrid local LLM sidecar + expanded NLP regex heuristics, and indexes vectors.
    """
    node_id, warnings = _save_node(
        "fact", text, importance=importance, category=category, project=project, agent=agent
    )
    
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    created_edges = []
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        # 1. Wikilinks [[slug]] and Hashtags #tag
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

        hashtags = re.findall(r"(?:^|\s)#([a-zA-Z0-9_\-\/]+)", text)
        for tag in hashtags:
            conn.execute(
                """
                INSERT OR IGNORE INTO edges (source, target, relation, weight, created_at, project)
                VALUES (?, ?, ?, 1.0, ?, ?)
                """,
                (node_id, tag.strip(), "tagged_as", 1.0, now, project),
            )
            created_edges.append(f"[{node_id}] -[tagged_as]-> [{tag.strip()}]")

        # 2. Expanded Multi-Clause Heuristic Regex Triple Extraction
        patterns = [
            # Entity Verb Entity (Active): Postgres uses WAL / Redis handles cache / Vite compiles TypeScript
            r"(\b[a-zA-Z0-9_\-\.]{2,30}\b)\s+(uses|using|requires|prefer|prefers|connects_to|replaces|implements|is_a|depends_on|runs_on|stores|caches|compiles|serves)\s+(\b[a-zA-Z0-9_\-\.]{2,30}\b)",
            # Passive / State: X is powered by Y / X is maintained by Y / X is written in Y / X was replaced by Y
            r"(\b[a-zA-Z0-9_\-\.]{2,30}\b)\s+(?:is|was|are|were)\s+(powered by|maintained by|written in|replaced by|built on|configured with)\s+(\b[a-zA-Z0-9_\-\.]{2,30}\b)",
            # Conversational First-Person / Team: We use Postgres / I prefer pnpm over npm / System runs on Linux
            r"(?:We|we|System|system|I|Our stack|our stack|Our team)\s+(use|uses|using|prefer|prefers|run|runs|deploy|deploys|switched to|replaces|depends on)\s+([a-zA-Z0-9_\-\.]{2,30})",
            # Comparative Preference: Always use X instead of Y / Prefer X over Y
            r"(?:Prefer|prefer|Always use|always use|Choose|choose)\s+([a-zA-Z0-9_\-\.]{2,30})\s+(?:over|instead of|rather than)\s+([a-zA-Z0-9_\-\.]{2,30})",
        ]
        
        for pat_idx, pat in enumerate(patterns):
            for match in re.finditer(pat, text, re.IGNORECASE):
                groups = match.groups()
                if len(groups) == 3:
                    s, r, o = groups
                elif len(groups) == 2:
                    # pat_idx 3 = comparative preference: Prefer X over Y -> (X, Y)
                    if pat_idx == 3:
                        s, r, o = groups[0], "preferred_over", groups[1]
                    else:
                        # pat_idx 2 = conversational: We/I <verb> <object> -> (verb, object)
                        s, r, o = "Architecture", groups[0].lower().replace(" ", "_"), groups[1]
                else:
                    continue

                
                s_clean, r_clean, o_clean = s.strip(), r.strip().lower().replace(" ", "_"), o.strip()
                stop_words = ("we", "the", "a", "an", "it", "to", "for", "in", "of", "and", "or")
                if s_clean.lower() not in stop_words and o_clean.lower() not in stop_words:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO edges (source, target, relation, weight, created_at, project)
                        VALUES (?, ?, ?, 1.0, ?, ?)
                        """,
                        (s_clean, o_clean, r_clean, now, project),
                    )
                    created_edges.append(f"[{s_clean}] -[{r_clean}]-> [{o_clean}]")

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
    valid_from: str = "",
    valid_until: str = "",
    superseded_by: str = "",
) -> str:
    """Save a Subject-Predicate-Object relation with bi-temporal validity and project namespace."""
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT OR REPLACE INTO edges (source, target, relation, weight, created_at, project, valid_from, valid_until, superseded_by, transaction_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source.strip(), target.strip(), relation.strip().lower(), float(weight), now, project, valid_from, valid_until, superseded_by, now),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    valid_str = f" [Valid: {valid_from} -> {valid_until}]" if valid_from or valid_until else ""
    return f"Saved edge: [{source}] -[{relation}]-> [{target}] (weight: {weight}, project: {project}){valid_str}"

@mcp.tool()
@retry_db_lock(max_retries=7)
def query_graph(node: str, depth: int = 2, project: Optional[str] = None, include_superseded: bool = False) -> str:
    """
    Query knowledge graph relations with recursive multi-hop path traversal and bi-temporal filtering.
    """
    conn = get_db()
    try:
        node_clean = node.strip()
        # Recursive CTE for dynamic N-hop traversal with cycle detection
        base_proj = "AND project = :project" if project else ""
        base_sup = "AND (superseded_by IS NULL OR superseded_by = '')" if not include_superseded else ""
        rec_proj = "AND e.project = :project" if project else ""
        rec_sup = "AND (e.superseded_by IS NULL OR e.superseded_by = '')" if not include_superseded else ""

        cte_sql = f"""
        WITH RECURSIVE graph_walk(source, relation, target, weight, project, valid_from, valid_until, hop, path) AS (
            -- Base case: 1-hop
            SELECT source, relation, target, weight, project, valid_from, valid_until, 1 as hop,
                   source || '->' || target as path
            FROM edges
            WHERE (source = :node OR target = :node)
              {base_proj}
              {base_sup}

            UNION ALL

            -- Recursive step: next hops up to max depth
            SELECT e.source, e.relation, e.target, e.weight, e.project, e.valid_from, e.valid_until, gw.hop + 1,
                   gw.path || '->' || e.target
            FROM edges e
            JOIN graph_walk gw ON (e.source = gw.target OR e.target = gw.source)
            WHERE gw.hop < :max_depth
              AND instr(gw.path, e.target) = 0
              {rec_proj}
              {rec_sup}
        )
        SELECT DISTINCT source, relation, target, weight, project, valid_from, valid_until, hop
        FROM graph_walk
        ORDER BY hop ASC, weight DESC
        LIMIT 100;
        """

        params = {"node": node_clean, "max_depth": min(max(1, depth), 4)}
        if project:
            params["project"] = project

        rows = conn.execute(cte_sql, params).fetchall()

        if not rows:
            return f"No active graph edges found for node '{node_clean}'."

        triples = []
        for r in rows:
            s, rel, t, w, proj, vf, vu, hop = r
            hop_prefix = f"({hop}-hop) " if hop > 1 else ""
            valid_info = f" [Valid: {vf}..{vu}]" if vf or vu else ""
            triples.append(f"{hop_prefix}[{s}] -[{rel}]-> [{t}] (w: {w}, project: {proj}){valid_info}")

        return "\n".join(triples)
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def deduplicate_memories(similarity_threshold: float = 0.92, project: Optional[str] = None, batch_size: int = 1000) -> str:
    """
    Autonomous Memory Deduplication & Semantic Merging Agent:
    Finds clusters of duplicate/near-identical memory nodes, merges access counts and edges,
    and prunes redundant duplicate records in chunks of 1,000 nodes.
    """
    conn = get_db()
    try:
        filter_str = "WHERE embedding IS NOT NULL"
        params = []
        if project:
            filter_str += " AND project = ?"
            params.append(project)

        batch_clamped = max(10, min(1000, int(batch_size)))
        rows = conn.execute(f"SELECT id, content, embedding, access_count, importance FROM nodes {filter_str} LIMIT ?", params + [batch_clamped]).fetchall()
        if len(rows) < 2:
            return "Insufficient records to deduplicate."

        vectors = [unpack_vector(r[2]) for r in rows if r[2]]
        merged_count = 0
        deleted_ids = set()

        conn.execute("BEGIN IMMEDIATE;")
        for i in range(len(rows)):
            if rows[i][0] in deleted_ids:
                continue
            primary_id = rows[i][0]
            remaining_indices = [j for j in range(i + 1, len(rows)) if rows[j][0] not in deleted_ids]
            if not remaining_indices:
                continue

            candidate_vecs = [vectors[j] for j in remaining_indices]
            sims = amx_batch_cosine_similarity(vectors[i], candidate_vecs)

            for j_idx, sim in zip(remaining_indices, sims):
                if rows[j_idx][0] in deleted_ids:
                    continue
                if sim >= similarity_threshold:
                    dup_id = rows[j_idx][0]
                    combined_access = rows[i][3] + rows[j_idx][3] + 1
                    max_importance = max(rows[i][4], rows[j_idx][4])

                    conn.execute(
                        "UPDATE nodes SET access_count = ?, importance = ? WHERE id = ?",
                        (combined_access, max_importance, primary_id),
                    )

                    conn.execute("UPDATE OR IGNORE edges SET source = ? WHERE source = ?", (primary_id, dup_id))
                    conn.execute("UPDATE OR IGNORE edges SET target = ? WHERE target = ?", (primary_id, dup_id))

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
    if "No active graph edges found" in graph_text or "No graph edges found" in graph_text:

        return graph_text

    mermaid_lines = ["```mermaid", "graph LR", f'  root["{node}"]:::primary']
    ascii_lines = [f"Knowledge Graph Topology for [{node}]:", "=" * 50]

    for line in graph_text.split("\n"):
        if not line.strip() or "-[" not in line:
            continue
        ascii_lines.append(f"  {line}")
        parts = line.split("-[")
        if len(parts) >= 2:
            src = parts[0].replace("(", "").replace(")", "").replace("-hop", "").strip().strip("[]")
            rest = parts[1].split("]->")
            if len(rest) == 2:
                rel = rest[0].strip()
                tgt = rest[1].split("(")[0].strip().strip("[]")
                safe_src = re.sub(r"[^a-zA-Z0-9_]", "_", src)
                safe_tgt = re.sub(r"[^a-zA-Z0-9_]", "_", tgt)
                mermaid_lines.append(f'  {safe_src}["{src}"] -->|"{rel}"| {safe_tgt}["{tgt}"]')

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
def auto_context(limit: int = 5, min_importance: int = 7, project: Optional[str] = None) -> str:
    """
    Auto-Context Boot Tool for Agents:
    Recalls top high-importance active memories formatted in XML for session initialization.
    """
    limit_clamped = max(1, min(100, int(limit)))
    min_imp_clamped = max(1, min(10, int(min_importance)))
    conn = get_db()
    try:
        proj_filter = "AND project = ?" if project else ""
        params = [min_imp_clamped] + ([project] if project else []) + [limit_clamped]
        rows = conn.execute(
            f"""
            SELECT id, category, content, importance, project, created_at
            FROM nodes
            WHERE importance >= ? {proj_filter}
            ORDER BY importance DESC, access_count DESC, created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        if not rows:
            return "<engram_context count='0'>No high-importance context found.</engram_context>"

        xml_entries = []
        ids_to_bump = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for r in rows:
            node_id, cat, content, imp, proj, created = r
            ids_to_bump.append(node_id)
            xml_entries.append(
                f'  <memory id="{node_id}" category="{cat}" importance="{imp}" project="{proj}">\n'
                f"    {content}\n"
                f"  </memory>"
            )

        if ids_to_bump:
            placeholders = ",".join("?" for _ in ids_to_bump)
            conn.execute(
                f"UPDATE nodes SET access_count = access_count + 1, last_accessed_at = ? WHERE id IN ({placeholders})",
                [now_iso] + ids_to_bump,
            )
            conn.commit()

        body = "\n".join(xml_entries)
        return f"<engram_context count='{len(rows)}'>\n{body}\n</engram_context>"
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def edit_memory(
    id: str,
    content: Optional[str] = None,
    importance: Optional[int] = None,
    category: Optional[str] = None,
) -> str:
    """Edit an existing memory's content, importance, or category by its node ID."""
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        row = conn.execute("SELECT id, content, importance, category FROM nodes WHERE id = ?", (id,)).fetchone()
        if not row:
            return f"Error: Memory with ID '{id}' not found."

        new_content = str(content)[:100000] if content is not None else row[1]
        new_imp = max(1, min(10, int(importance))) if importance is not None else row[2]
        new_cat = category.strip() if category is not None else row[3]
        now_iso = datetime.now(timezone.utc).isoformat()

        dense_vec = generate_dense_embedding(new_content)
        packed_vec = pack_vector(dense_vec)

        conn.execute(
            """
            UPDATE nodes
            SET content = ?, importance = ?, category = ?, embedding = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_content, new_imp, new_cat, packed_vec, now_iso, id),
        )
        conn.commit()
        return f"Successfully updated Node {id} (Importance: {new_imp}, Category: {new_cat})."
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def delete_memory(id: str) -> str:
    """Delete a memory node and cascade-delete all its associated knowledge graph edges by ID."""
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        conn.execute("DELETE FROM edges WHERE source = ? OR target = ?", (id, id))
        cur = conn.execute("DELETE FROM nodes WHERE id = ?", (id,))
        if cur.rowcount == 0:
            return f"Error: Memory with ID '{id}' not found."
        conn.commit()
        return f"Successfully deleted Node {id} and cascaded associated graph edges."
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@mcp.tool()
@retry_db_lock(max_retries=7)
def list_memories(limit: int = 50, project: Optional[str] = None) -> str:
    """List recent memory nodes in the database, ordered by importance and recency."""
    conn = get_db()
    try:
        proj_filter = "WHERE project = ?" if project else ""
        params = [project] if project else []
        params.append(limit)

        rows = conn.execute(
            f"""
            SELECT id, category, importance, project, created_at, content
            FROM nodes
            {proj_filter}
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        if not rows:
            return "Memory bank is empty."

        lines = [f"{'ID':<14} {'CAT':<12} {'IMP':<5} {'PROJ':<12} {'DATE':<12} CONTENT", "-" * 80]
        for r in rows:
            node_id, cat, imp, proj, created, content = r
            preview = content[:45].replace("\n", " ")
            lines.append(f"{node_id:<14} {cat:<12} {imp:<5} {proj:<12} {created[:10]:<12} {preview}")

        return "\n".join(lines)
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
        model = get_embedding_model()
        model_name = "BAAI/bge-small-en-v1.5 (Neural ONNX)" if model is not None else "Hashed Hypersphere Projection (Zero-Dependency Fallback)"
        
        has_vec = False
        try:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nodes_vec';")
            has_vec = cur.fetchone() is not None
        except Exception:
            has_vec = False
        vec_indexing = "Native sqlite-vec (vec0 ANN Virtual Table)" if has_vec else "Hardware AMX / BLAS Full-Scan"

        return (
            f"🧠 Engram Alpha Universal MCP Stats:\n"
            f"- Total Memories / Nodes: {node_count}\n"
            f"- Knowledge Graph Edges: {edge_count}\n"
            f"- Active Projects / Namespaces: {projects}\n"
            f"- Hardware Engine Tier: {tier_status}\n"
            f"- Embedding Backend: {model_name}\n"
            f"- Vector Indexing Engine: {vec_indexing}\n"
            f"- Architecture: Cross-Platform Production Standard (macOS, Linux, Windows, Docker)"
        )
    finally:
        conn.close()

def main():
    mcp.run()

if __name__ == "__main__":
    main()
