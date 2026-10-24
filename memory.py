"""Persistent long-term memory: SQLite + embeddings (Ollama if reachable, hashed bag-of-words fallback).

Memory is built into the agent runtime (not an MCP server) so that 'Memory' and 'Tooling' stay
separate layers. Every row records provenance: which session wrote it and whether untrusted content
was in the context at the time (`tainted`). That is what makes cross-session (T3) analysis possible.
"""
import hashlib
import json
import math
import re
import sqlite3
import urllib.request
from datetime import datetime, timezone

import config

SCHEMA = """CREATE TABLE IF NOT EXISTS memories(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    kind TEXT DEFAULT 'fact',
    source TEXT,
    session_id TEXT,
    tainted INTEGER DEFAULT 0,
    created_at TEXT,
    embed_backend TEXT,
    embedding TEXT)"""

HASH_DIM = 256
MAX_LEN = 500
SUSPICIOUS = [
    r"ignore (all |any |the )?(previous|prior|above)", r"disregard", r"system prompt",
    r"from now on", r"you (must|should|will) (always|never)", r"\boverride\b",
    r"\balways (reply|respond|answer|end|append|include)", r"https?://",
]


def _cos(a, b) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def hash_embed(text: str) -> list:
    v = [0.0] * HASH_DIM
    for tok in re.findall(r"\w+", text.lower()):
        v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % HASH_DIM] += 1.0
    return v


class Embedder:
    """Tries Ollama's embedding endpoint once; falls back to a hash embedding if it is unavailable."""

    def __init__(self):
        self.backend = None

    def embed(self, text: str) -> tuple[list, str]:
        if self.backend != "hash":
            try:
                req = urllib.request.Request(
                    config.EMBED_URL, method="POST", headers={"Content-Type": "application/json"},
                    data=json.dumps({"model": config.EMBED_MODEL, "prompt": text}).encode())
                with urllib.request.urlopen(req, timeout=20) as r:
                    vec = json.load(r)["embedding"]
                self.backend = f"ollama:{config.EMBED_MODEL}"
                return vec, self.backend
            except Exception:
                self.backend = "hash"
        return hash_embed(text), "hash"


class MemoryStore:
    def __init__(self, db_path=None):
        self.db_path = str(db_path or config.MEMORY_DB)
        self.embedder = Embedder()
        with self._con() as con:
            con.execute(SCHEMA)

    def _con(self):
        con = sqlite3.connect(self.db_path, timeout=5)
        con.row_factory = sqlite3.Row
        return con

    # ----------------------------------------------------------- validation
    @staticmethod
    def validate(content: str) -> tuple[bool, str]:
        if not content or not content.strip():
            return False, "empty memory"
        if len(content) > MAX_LEN:
            return False, f"memory too long ({len(content)} > {MAX_LEN} chars)"
        for pat in SUSPICIOUS:
            if re.search(pat, content, re.I):
                return False, f"memory looks like an instruction or contains a link (matched: {pat})"
        return True, "ok"

    # ------------------------------------------------------------- write/read
    def add(self, content: str, kind: str = "fact", source: str = "model_tool_call",
            session_id: str | None = None, tainted: bool = False) -> dict:
        vec, backend = self.embedder.embed(content)
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._con() as con:
            cur = con.execute(
                "INSERT INTO memories(content,kind,source,session_id,tainted,created_at,embed_backend,embedding) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (content.strip(), kind, source, session_id, int(tainted), created, backend, json.dumps(vec)))
            mem_id = cur.lastrowid
        return {"id": mem_id, "content": content.strip(), "kind": kind, "tainted": tainted,
                "embed_backend": backend}

    def search(self, query: str, k: int | None = None, min_score: float | None = None) -> list:
        k = k or config.MEMORY_TOP_K
        min_score = config.MEMORY_MIN_SCORE if min_score is None else min_score
        qvec, backend = self.embedder.embed(query)
        with self._con() as con:
            rows = con.execute("SELECT id,content,kind,source,session_id,tainted,created_at,"
                               "embed_backend,embedding FROM memories").fetchall()
        scored = []
        for r in rows:
            if r["embed_backend"] != backend:      # never compare vectors from different backends
                continue
            s = _cos(qvec, json.loads(r["embedding"]))
            if s >= min_score:
                scored.append({"id": r["id"], "content": r["content"], "kind": r["kind"],
                               "source": r["source"], "session_id": r["session_id"],
                               "tainted": bool(r["tainted"]), "created_at": r["created_at"],
                               "score": round(s, 4)})
        scored.sort(key=lambda x: -x["score"])
        return scored[:k]
