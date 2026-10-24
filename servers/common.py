"""Shared helpers for the MCP servers: server-side audit log + SDK compatibility.

The audit log is written BY THE SERVER, independently of the agent. It is ground truth for what the
tool actually did (resolved paths, SQL effects, outbound URLs), so the judge can cross-check the
agent's own trace against it.
"""
import contextvars
import functools
import json
import os
import time
from datetime import datetime, timezone

try:                                            # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:                             # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

AUDIT_DIR = os.environ.get("AGENT_AUDIT_DIR")
_CTX: contextvars.ContextVar = contextvars.ContextVar("audit_ctx", default=None)

TICKETS_SCHEMA = """CREATE TABLE IF NOT EXISTS tickets(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'open',
    priority TEXT DEFAULT 'medium',
    created_at TEXT,
    updated_at TEXT)"""


def make_server(name: str):
    return _Server(name)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def audit(server: str, tool: str, args: dict, **extra):
    if not AUDIT_DIR:
        return
    os.makedirs(AUDIT_DIR, exist_ok=True)
    rec = {"ts": now(), "pid": os.getpid(), "server": server, "tool": tool, "args": args, **extra}
    with open(os.path.join(AUDIT_DIR, f"{server}.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def note(**kw):
    """Attach extra facts (resolved path, url, rows affected...) to the current call's audit record."""
    ctx = _CTX.get()
    if ctx is not None:
        ctx.update(kw)


def audited(server: str):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            ctx: dict = {}
            _CTX.set(ctx)
            t0 = time.perf_counter()
            try:
                out = fn(*a, **kw)
            except Exception as e:
                audit(server, fn.__name__, kw, status="error", error=str(e),
                      duration_ms=round((time.perf_counter() - t0) * 1000), **ctx)
                raise
            audit(server, fn.__name__, kw, status="ok", result_preview=str(out)[:300],
                  duration_ms=round((time.perf_counter() - t0) * 1000), **ctx)
            return out
        return wrapper
    return deco
