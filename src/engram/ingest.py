"""
Engram Obsidian & Markdown Graph Ingestion Pipeline
Recursively parses markdown vaults, extracts wikilinks [[slug]] and tags #tag
into knowledge graph triples, generates 384d vectors, and bulk-inserts them atomically.
"""

import os
import re
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

from .core import get_db
from .amx import generate_dense_embedding, pack_vector

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

def ingest_obsidian_vault(vault_path_str: str) -> Dict[str, Any]:
    """
    Scans an entire Obsidian vault and ingests nodes, edges, and AMX dense vectors
    into Engram Alpha SQLite in a single atomic transaction.
    """
    vault_path = Path(vault_path_str).expanduser().resolve()
    if not vault_path.exists() or not vault_path.is_dir():
        raise ValueError(f"Vault path '{vault_path}' does not exist or is not a directory.")

    md_files = list(vault_path.rglob("*.md"))
    if not md_files:
        return {"status": "empty", "files_processed": 0, "nodes_created": 0, "edges_created": 0}

    nodes_to_insert = []
    edges_to_insert = []
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
        wikilinks, tags = extract_metadata_and_links(content)

        # Knowledge graph relations for document
        for link in wikilinks:
            edges_to_insert.append((doc_title, link, "links_to"))
        for tag in tags:
            edges_to_insert.append((doc_title, tag, "tagged_as"))

        # Chunk content
        chunks = chunk_markdown(content)
        for i, chunk in enumerate(chunks):
            node_id = str(uuid.uuid4())
            chunk_content = f"[{doc_title} (part {i+1}/{len(chunks)})]: {chunk}"
            embedding = generate_dense_embedding(chunk_content)
            packed_vec = pack_vector(embedding)
            nodes_to_insert.append((node_id, "obsidian_doc", chunk_content, now, now, 0, "", packed_vec))

    # Bulk Atomic Insertion
    conn = get_db()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        # Insert Nodes
        conn.executemany(
            """
            INSERT INTO nodes (id, type, content, created_at, updated_at, access_count, last_accessed_at, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            nodes_to_insert,
        )

        # Insert Edges
        conn.executemany(
            """
            INSERT OR IGNORE INTO edges (source, target, relation)
            VALUES (?, ?, ?)
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
    }
