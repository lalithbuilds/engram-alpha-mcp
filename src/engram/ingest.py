"""
Engram Obsidian & Markdown Graph Ingestion Pipeline
Recursively parses markdown vaults, extracts wikilinks [[slug]] and tags #tag
into knowledge graph triples, generates 384d vectors, and bulk-inserts them atomically.
Includes real-time live vault watcher with differential, incremental file synchronization.
"""

import os
import re
import time
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional

from .core import get_db
from .amx import generate_dense_embedding, generate_dense_embeddings_batch, pack_vector

WIKILINK_REGEX = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]")
TAG_REGEX = re.compile(r"(?:^|\s)#([a-zA-Z0-9_\-\/]+)")

def chunk_markdown(text: str, chunk_size_words: int = 150, overlap_words: int = 25) -> List[str]:
    """Split markdown text into overlapping semantic windows."""
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size_words:
        return [text.strip()]

    chunks = []
    step = chunk_size_words - overlap_words
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size_words])
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks

def extract_metadata_and_links(content: str) -> Tuple[List[str], List[str]]:
    """Extract [[wikilinks]] and #tags from markdown content."""
    wikilinks = [m.strip() for m in WIKILINK_REGEX.findall(content)]
    tags = [m.strip() for m in TAG_REGEX.findall(content)]
    return list(set(wikilinks)), list(set(tags))

def delete_obsidian_file_nodes(doc_title: str, project: str = "default"):
    """Delete previously ingested chunks and edges for a specific document to avoid duplicates."""
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        conn.execute(
            "DELETE FROM nodes WHERE category = 'obsidian' AND content LIKE ? AND project = ?",
            (f"[{doc_title} (part%", project),
        )
        conn.execute(
            "DELETE FROM edges WHERE (source = ? OR target = ?) AND project = ?",
            (doc_title, doc_title, project),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def ingest_single_obsidian_file(file_path: Path, project: str = "default") -> Dict[str, int]:
    """Incrementally ingest or re-ingest a single markdown document without re-indexing the whole vault."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
    except Exception:
        return {"nodes": 0, "edges": 0}

    if not content:
        return {"nodes": 0, "edges": 0}

    doc_title = file_path.stem
    delete_obsidian_file_nodes(doc_title, project=project)

    wikilinks, tags = extract_metadata_and_links(content)
    now = datetime.now(timezone.utc).isoformat()

    edges_to_insert = []
    for link in wikilinks:
        edges_to_insert.append((doc_title, link, "links_to", 1.0, now, project))
    for tag in tags:
        edges_to_insert.append((doc_title, tag, "tagged_as", 1.0, now, project))

    chunks = chunk_markdown(content)
    raw_chunks = [(str(uuid.uuid4()), f"[{doc_title} (part {i+1}/{len(chunks)})]: {chunk}") for i, chunk in enumerate(chunks)]
    
    vecs = generate_dense_embeddings_batch([rc[1] for rc in raw_chunks])
    nodes_to_insert = []
    for (node_id, chunk_content), vec in zip(raw_chunks, vecs):
        nodes_to_insert.append((
            node_id,
            "obsidian_doc",
            chunk_content,
            now,
            now,
            0,
            "",
            pack_vector(vec),
            5,
            "obsidian",
            project,
            "vault_sync",
        ))

    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        conn.executemany(
            """
            INSERT INTO nodes (id, type, content, created_at, updated_at, access_count, last_accessed_at, embedding, importance, category, project, agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            nodes_to_insert,
        )
        conn.executemany(
            """
            INSERT OR IGNORE INTO edges (source, target, relation, weight, created_at, project)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            edges_to_insert,
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return {"nodes": len(nodes_to_insert), "edges": len(edges_to_insert)}

def ingest_obsidian_vault(vault_path_str: str, project: str = "default") -> Dict[str, Any]:
    """
    Scans an entire Obsidian vault and ingests nodes, edges, and dense vectors
    into Engram Alpha SQLite in parallel SIMD batches.
    """
    vault_path = Path(vault_path_str).expanduser().resolve()
    if not vault_path.exists() or not vault_path.is_dir():
        raise ValueError(f"Vault path '{vault_path}' does not exist or is not a directory.")

    md_files = list(vault_path.rglob("*.md"))
    if not md_files:
        return {"status": "empty", "files_processed": 0, "nodes_created": 0, "edges_created": 0}

    nodes_to_insert = []
    edges_to_insert = []
    raw_chunks_to_embed = []
    now = datetime.now(timezone.utc).isoformat()

    for file_path in md_files:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
        except Exception:
            continue

        if not content:
            continue

        doc_title = file_path.stem
        delete_obsidian_file_nodes(doc_title, project=project)
        wikilinks, tags = extract_metadata_and_links(content)

        for link in wikilinks:
            edges_to_insert.append((doc_title, link, "links_to", 1.0, now, project))
        for tag in tags:
            edges_to_insert.append((doc_title, tag, "tagged_as", 1.0, now, project))

        chunks = chunk_markdown(content)
        for i, chunk in enumerate(chunks):
            node_id = str(uuid.uuid4())
            chunk_content = f"[{doc_title} (part {i+1}/{len(chunks)})]: {chunk}"
            raw_chunks_to_embed.append((node_id, chunk_content))

    # Batch Vector Embeddings Generation (10x faster SIMD parallel passes)
    BATCH_SIZE = 64
    for b_idx in range(0, len(raw_chunks_to_embed), BATCH_SIZE):
        batch = raw_chunks_to_embed[b_idx : b_idx + BATCH_SIZE]
        texts = [item[1] for item in batch]
        vecs = generate_dense_embeddings_batch(texts)
        for (node_id, chunk_content), vec in zip(batch, vecs):
            packed_vec = pack_vector(vec)
            nodes_to_insert.append((
                node_id,
                "obsidian_doc",
                chunk_content,
                now,
                now,
                0,
                "",
                packed_vec,
                5,
                "obsidian",
                project,
                "vault_sync",
            ))

    # Bulk Atomic Insertion
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        conn.executemany(
            """
            INSERT INTO nodes (id, type, content, created_at, updated_at, access_count, last_accessed_at, embedding, importance, category, project, agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            nodes_to_insert,
        )

        conn.executemany(
            """
            INSERT OR IGNORE INTO edges (source, target, relation, weight, created_at, project)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            edges_to_insert,
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return {
        "status": "success",
        "files_processed": len(md_files),
        "nodes_created": len(nodes_to_insert),
        "edges_created": len(edges_to_insert),
        "project": project,
    }

def watch_obsidian_vault(vault_path_str: str, project: str = "default", poll_interval: float = 2.0):
    """
    Live real-time Obsidian vault synchronization daemon.
    Monitors file hash changes and syncs updates differentially into the memory graph.
    """
    vault_path = Path(vault_path_str).expanduser().resolve()
    print(f"👁️ Engram Alpha Live Watcher active on: {vault_path} (Project: {project})")
    
    file_hashes: Dict[str, str] = {}

    def get_file_hash(p: Path) -> str:
        try:
            return hashlib.md5(p.read_bytes()).hexdigest()
        except Exception:
            return ""

    # Initial scan
    for p in vault_path.rglob("*.md"):
        file_hashes[str(p)] = get_file_hash(p)
    ingest_obsidian_vault(str(vault_path), project=project)
    print(f"✓ Initial vault sync complete ({len(file_hashes)} files indexed).")

    try:
        while True:
            time.sleep(poll_interval)
            current_files = list(vault_path.rglob("*.md"))

            for p in current_files:
                p_str = str(p)
                h = get_file_hash(p)
                if p_str not in file_hashes or file_hashes[p_str] != h:
                    file_hashes[p_str] = h
                    print(f"⚡ Incremental sync for modified file: {p.name}")
                    ingest_single_obsidian_file(p, project=project)

            # Check deleted files
            current_set = set(str(p) for p in current_files)
            for old_p in list(file_hashes.keys()):
                if old_p not in current_set:
                    del file_hashes[old_p]
                    doc_title = Path(old_p).stem
                    print(f"🗑️ Incremental prune for removed file: {Path(old_p).name}")
                    delete_obsidian_file_nodes(doc_title, project=project)
    except KeyboardInterrupt:
        print("\nStopping Live Watcher.")
