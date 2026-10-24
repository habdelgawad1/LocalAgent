"""Tickets MCP server: a small task tracker in SQLite. This is the side-effect tool with a destructive action."""
import json
import os
import sqlite3
from datetime import datetime, timezone

from common import TICKETS_SCHEMA, audited, make_server, note

DB = os.environ["AGENT_TICKETS_DB"]
mcp = make_server("tickets")


def _con():
    con = sqlite3.connect(DB, timeout=5)
    con.row_factory = sqlite3.Row
    con.execute(TICKETS_SCHEMA)
    return con


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@mcp.tool()
@audited("tickets")
def list_tickets(status: str = "", limit: int = 20) -> str:
    """List tickets, optionally filtered by status (open, in_progress, done)."""
    with _con() as con:
        if status:
            rows = con.execute("SELECT * FROM tickets WHERE status=? ORDER BY id LIMIT ?", (status, limit))
        else:
            rows = con.execute("SELECT * FROM tickets ORDER BY id LIMIT ?", (limit,))
        out = [dict(r) for r in rows]
    note(rows_returned=len(out))
    return json.dumps(out, ensure_ascii=False) if out else "(no tickets)"


@mcp.tool()
@audited("tickets")
def create_ticket(title: str, description: str = "", priority: str = "medium") -> str:
    """Create a ticket. Priority is low, medium or high."""
    with _con() as con:
        cur = con.execute(
            "INSERT INTO tickets(title,description,priority,created_at,updated_at) VALUES(?,?,?,?,?)",
            (title, description, priority, _now(), _now()))
        tid = cur.lastrowid
    note(ticket_id=tid)
    return f"Created ticket #{tid}: {title}"


@mcp.tool()
@audited("tickets")
def update_ticket(ticket_id: int, status: str = "", priority: str = "", description: str = "") -> str:
    """Update a ticket's status, priority or description. Leave a field empty to keep it unchanged."""
    sets, vals = [], []
    for col, val in (("status", status), ("priority", priority), ("description", description)):
        if val:
            sets.append(f"{col}=?")
            vals.append(val)
    if not sets:
        raise ValueError("nothing to update")
    with _con() as con:
        cur = con.execute(f"UPDATE tickets SET {','.join(sets)}, updated_at=? WHERE id=?",
                          (*vals, _now(), ticket_id))
        n = cur.rowcount
    note(ticket_id=ticket_id, rows_affected=n)
    if n == 0:
        raise ValueError(f"ticket #{ticket_id} not found")
    return f"Updated ticket #{ticket_id}"


@mcp.tool()
@audited("tickets")
def delete_ticket(ticket_id: int) -> str:
    """Permanently delete a ticket. This cannot be undone."""
    with _con() as con:
        cur = con.execute("DELETE FROM tickets WHERE id=?", (ticket_id,))
        n = cur.rowcount
    note(ticket_id=ticket_id, rows_affected=n)
    if n == 0:
        raise ValueError(f"ticket #{ticket_id} not found")
    return f"Deleted ticket #{ticket_id}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
