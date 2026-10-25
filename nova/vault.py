"""
NOVA Vault & Local Offline RAG Engine.
Enables offline document ingestion, chunk indexing, BM25/TF-IDF retrieval,
and document question-answering with local Ollama models.
"""

import os
import re
import math
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from nova.config import DATA_DIR, DEFAULT_MODEL
from nova.ollama_client import OllamaClient

logger = logging.getLogger("nova.vault")

VAULT_DB_PATH = DATA_DIR / "nova_vault.db"

class DocumentVault:
    """Manages local document indexing, chunk storage, and semantic/BM25 retrieval."""

    def __init__(self, db_path: Path = VAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes SQLite schema for document vault and chunks."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL UNIQUE,
                    file_size INTEGER NOT NULL,
                    word_count INTEGER NOT NULL,
                    ingested_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    FOREIGN KEY (doc_id) REFERENCES vault_documents (id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vault_chunks_doc ON vault_chunks(doc_id)")
            conn.commit()

    def extract_text_from_file(self, file_path: Path) -> Tuple[bool, str, str]:
        """
        Extracts plain text from various file formats (.txt, .md, .py, .json, .csv, .log, .pdf).
        Returns (success, text_content, error_msg).
        """
        path = Path(file_path)
        if not path.exists():
            return False, "", f"File does not exist: {path}"

        suffix = path.suffix.lower()

        # Handle text-based formats
        if suffix in [".txt", ".md", ".py", ".json", ".csv", ".log", ".html", ".js", ".css", ".yaml", ".yml", ".ini"]:
            try:
                for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                    try:
                        with open(path, "r", encoding=enc) as f:
                            return True, f.read(), ""
                    except UnicodeDecodeError:
                        continue
                return False, "", "Failed to decode text file with standard encodings."
            except Exception as e:
                return False, "", f"Error reading file: {e}"

        # Handle PDF files
        elif suffix == ".pdf":
            try:
                # Try pypdf or PyPDF2 if installed
                import importlib.util
                if importlib.util.find_spec("pypdf"):
                    import pypdf
                    reader = pypdf.PdfReader(str(path))
                    pages_text = [page.extract_text() or "" for page in reader.pages]
                    return True, "\n\n".join(pages_text), ""
                elif importlib.util.find_spec("PyPDF2"):
                    import PyPDF2
                    with open(path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        pages_text = [page.extract_text() or "" for page in reader.pages]
                        return True, "\n\n".join(pages_text), ""
                else:
                    # Pure-Python simple PDF text extraction fallback
                    with open(path, "rb") as f:
                        raw = f.read()
                    # Extract text blocks between BT and ET
                    matches = re.findall(rb"BT\s+(.*?)\s+ET", raw, re.DOTALL)
                    text_parts = []
                    for m in matches:
                        strings = re.findall(rb"\((.*?)\)", m)
                        for s in strings:
                            try:
                                text_parts.append(s.decode("latin-1", errors="ignore"))
                            except Exception:
                                pass
                    if text_parts:
                        return True, " ".join(text_parts), ""
                    return False, "", "PDF contains scanned raster images or could not be decoded without pypdf."
            except Exception as e:
                return False, "", f"PDF extraction error: {e}"

        return False, "", f"Unsupported file type: {suffix}"

    def chunk_text(self, text: str, chunk_size_words: int = 250, overlap_words: int = 40) -> List[str]:
        """Splits long text into overlapping chunks for high-relevance retrieval."""
        words = text.split()
        if not words:
            return []

        if len(words) <= chunk_size_words:
            return [" ".join(words)]

        chunks = []
        step = max(1, chunk_size_words - overlap_words)
        for i in range(0, len(words), step):
            chunk = " ".join(words[i : i + chunk_size_words])
            chunks.append(chunk)
            if i + chunk_size_words >= len(words):
                break

        return chunks

    def ingest_document(self, file_path: str | Path) -> Tuple[bool, str, int]:
        """
        Ingests a document into the vault, chunks it, and indexes it.
        Returns (success, message, doc_id).
        """
        p = Path(file_path).resolve()
        ok, content, err = self.extract_text_from_file(p)
        if not ok or not content.strip():
            return False, err or "Extracted content was empty", -1

        chunks = self.chunk_text(content)
        total_words = len(content.split())
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._get_connection() as conn:
            # Check if file is already ingested, delete old records if re-ingesting
            existing = conn.execute("SELECT id FROM vault_documents WHERE file_path = ?", (str(p),)).fetchone()
            if existing:
                old_id = existing["id"]
                conn.execute("DELETE FROM vault_chunks WHERE doc_id = ?", (old_id,))
                conn.execute("DELETE FROM vault_documents WHERE id = ?", (old_id,))

            cur = conn.execute("""
                INSERT INTO vault_documents (filename, file_path, file_size, word_count, ingested_at)
                VALUES (?, ?, ?, ?, ?)
            """, (p.name, str(p), p.stat().st_size, total_words, now_str))
            doc_id = cur.lastrowid

            for idx, ch in enumerate(chunks):
                conn.execute("""
                    INSERT INTO vault_chunks (doc_id, chunk_index, content, word_count)
                    VALUES (?, ?, ?, ?)
                """, (doc_id, idx, ch, len(ch.split())))

            conn.commit()

        logger.info(f"Ingested '{p.name}': {len(chunks)} chunks, {total_words} words.")
        return True, f"Ingested '{p.name}' ({len(chunks)} chunks, {total_words} words)", doc_id

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns all ingested documents."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT d.id, d.filename, d.file_path, d.file_size, d.word_count, d.ingested_at,
                       COUNT(c.id) as chunk_count
                FROM vault_documents d
                LEFT JOIN vault_chunks c ON d.id = c.doc_id
                GROUP BY d.id
                ORDER BY d.id DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def delete_document(self, doc_id: int) -> bool:
        """Removes a document and all its chunks from the vault."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM vault_chunks WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM vault_documents WHERE id = ?", (doc_id,))
            conn.commit()
            return True

    def clear_vault(self) -> bool:
        """Deletes all documents and chunks from the vault."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM vault_chunks")
            conn.execute("DELETE FROM vault_documents")
            conn.commit()
            return True

    def search_chunks(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Pure-Python BM25/TF-IDF relevance search across all chunks in the vault.
        """
        query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        if not query_terms:
            return []

        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT c.id, c.doc_id, c.chunk_index, c.content, c.word_count,
                       d.filename, d.file_path
                FROM vault_chunks c
                JOIN vault_documents d ON c.doc_id = d.id
            """).fetchall()

        if not rows:
            return []

        total_docs = len(rows)
        # 1. Compute document frequency for each query term
        doc_freq = {t: 0 for t in query_terms}
        parsed_chunks = []
        for r in rows:
            text_lower = r["content"].lower()
            chunk_tokens = re.findall(r"\w+", text_lower)
            token_counts = {}
            for tok in chunk_tokens:
                token_counts[tok] = token_counts.get(tok, 0) + 1
            for t in query_terms:
                if t in token_counts:
                    doc_freq[t] += 1
            parsed_chunks.append((r, token_counts, len(chunk_tokens)))

        # 2. Score chunks using BM25
        k1 = 1.5
        b = 0.75
        avg_len = sum(p[2] for p in parsed_chunks) / max(1, total_docs)

        scored = []
        for r, counts, doc_len in parsed_chunks:
            score = 0.0
            for t in query_terms:
                if t in counts:
                    tf = counts[t]
                    df = doc_freq.get(t, 0)
                    idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
                    tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_len)))
                    score += idf * tf_norm
            if score > 0.01:
                scored.append({
                    "chunk_id": r["id"],
                    "doc_id": r["doc_id"],
                    "filename": r["filename"],
                    "file_path": r["file_path"],
                    "content": r["content"],
                    "chunk_text": r["content"],
                    "score": round(score, 4)
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def search_vault(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Alias for search_chunks."""
        return self.search_chunks(query, top_k=top_k)

    def build_rag_prompt(self, query: str, top_k: Any = 4) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Retrieves context chunks and compiles a grounded RAG prompt for Ollama.
        Accepts either an integer top_k or pre-retrieved chunk list.
        """
        if isinstance(top_k, list):
            chunks = top_k
        else:
            chunks = self.search_chunks(query, top_k=int(top_k))

        if not chunks:
            return query, []

        context_blocks = []
        for idx, c in enumerate(chunks, 1):
            text = c.get("content") or c.get("chunk_text") or ""
            context_blocks.append(f"--- [SOURCE {idx}: {c['filename']}] ---\n{text}\n")

        prompt = (
            "You are NOVA Vault AI. Answer the user question based STRICTLY and ONLY on the following verified document sources.\n"
            "If the answer cannot be found in the provided sources, state clearly that the document vault does not contain that information.\n"
            "Cite the source filename where relevant.\n\n"
            "=== VERIFIED DOCUMENT CONTEXT ===\n"
            + "\n".join(context_blocks) +
            "\n=== USER QUESTION ===\n"
            + query +
            "\n\n=== CONCISE GROUNDED RESPONSE ==="
        )
        return prompt, chunks

_vault_instance = None

def get_vault() -> DocumentVault:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = DocumentVault()
    return _vault_instance
