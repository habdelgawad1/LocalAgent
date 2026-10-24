"""Environment snapshots and diffs: the 'what actually changed in the world' evidence.

Watches:
  * files under the sandbox and under the decoy 'outside' folder (content kept for small text files)
  * every row of the tickets database
  * every row of the long-term memory database (embeddings excluded)

The agent takes a snapshot before and after every tool call. The diff is logged next to the
tool result, so a judge can compare what the agent *said* it did with what *really* changed.
"""
import difflib
import hashlib
import sqlite3
from pathlib import Path

TEXT_MAX = 20_000
DIFF_MAX = 4_000

TICKETS_Q = ("SELECT id,title,description,status,priority,created_at,updated_at "
             "FROM tickets ORDER BY id")
MEMORY_Q = ("SELECT id,kind,content,source,session_id,tainted,created_at "
            "FROM memories ORDER BY id")


class EnvWatcher:
    def __init__(self, roots: dict, tickets_db, memory_db):
        self.roots = {k: Path(v) for k, v in roots.items()}   # e.g. {"sandbox": ..., "outside": ...}
        self.tickets_db = Path(tickets_db)
        self.memory_db = Path(memory_db)

    # ------------------------------------------------------------ snapshot
    def snapshot(self) -> dict:
        return {
            "files": self._files(),
            "tickets": self._rows(self.tickets_db, TICKETS_Q),
            "memory": self._rows(self.memory_db, MEMORY_Q),
        }

    def _files(self) -> dict:
        out = {}
        for prefix, root in self.roots.items():
            if not root.exists():
                continue
            for p in sorted(root.rglob("*")):
                if not p.is_file():
                    continue
                rel = f"{prefix}/{p.relative_to(root).as_posix()}"
                try:
                    data = p.read_bytes()
                except OSError:
                    continue
                entry = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "text": None}
                if len(data) <= TEXT_MAX:
                    try:
                        entry["text"] = data.decode("utf-8")
                    except UnicodeDecodeError:
                        pass
                out[rel] = entry
        return out

    @staticmethod
    def _rows(db: Path, query: str) -> list:
        if not db.exists():
            return []
        try:
            con = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True, timeout=2)
            con.row_factory = sqlite3.Row
            rows = [dict(r) for r in con.execute(query)]
            con.close()
            return rows
        except sqlite3.Error:
            return []

    # ---------------------------------------------------------------- diff
    @staticmethod
    def diff(before: dict, after: dict) -> dict:
        d = {"files": {"added": [], "removed": [], "modified": []},
             "tickets": _row_diff(before["tickets"], after["tickets"]),
             "memory": _row_diff(before["memory"], after["memory"])}
        bf, af = before["files"], after["files"]
        for path in sorted(af.keys() - bf.keys()):
            d["files"]["added"].append({"path": path, "size": af[path]["size"],
                                        "sha256": af[path]["sha256"], "content": af[path]["text"]})
        for path in sorted(bf.keys() - af.keys()):
            d["files"]["removed"].append({"path": path, "size": bf[path]["size"],
                                          "sha256": bf[path]["sha256"], "last_content": bf[path]["text"]})
        for path in sorted(bf.keys() & af.keys()):
            if bf[path]["sha256"] != af[path]["sha256"]:
                ud = None
                if bf[path]["text"] is not None and af[path]["text"] is not None:
                    ud = "\n".join(difflib.unified_diff(
                        bf[path]["text"].splitlines(), af[path]["text"].splitlines(),
                        "before", "after", lineterm="", n=2))[:DIFF_MAX]
                d["files"]["modified"].append({
                    "path": path, "before_sha256": bf[path]["sha256"], "after_sha256": af[path]["sha256"],
                    "size_before": bf[path]["size"], "size_after": af[path]["size"], "unified_diff": ud})
        return d

    @staticmethod
    def is_empty(d: dict) -> bool:
        return not any(d["files"][k] for k in d["files"]) and not any(
            d[t][k] for t in ("tickets", "memory") for k in d[t])


def _row_diff(before: list, after: list) -> dict:
    b = {r["id"]: r for r in before}
    a = {r["id"]: r for r in after}
    out = {"added": [a[i] for i in sorted(a.keys() - b.keys())],
           "removed": [b[i] for i in sorted(b.keys() - a.keys())],
           "modified": []}
    for i in sorted(a.keys() & b.keys()):
        changes = {k: [b[i][k], a[i][k]] for k in a[i] if a[i][k] != b[i].get(k)}
        if changes:
            out["modified"].append({"id": i, "changes": changes})
    return out
