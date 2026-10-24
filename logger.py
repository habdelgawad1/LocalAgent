"""Append-only, hash-chained JSONL trace.

Every record carries the previous record's hash, so edits, deletions or reordering after the fact
are detectable (verify_chain). This is the evidence base the judge works from.
"""
import hashlib
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

GENESIS = "0" * 64


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _canon(rec: dict) -> str:
    return json.dumps(rec, sort_keys=True, ensure_ascii=False, default=str)


def _short(obj, n=140) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str)
    s = s.replace("\n", "\\n")
    return s if len(s) <= n else s[: n - 3] + "..."


class TraceLogger:
    def __init__(self, run_dir, run_id: str, echo: bool = False):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.echo = echo
        self._trace = open(self.run_dir / "trace.jsonl", "a", encoding="utf-8", buffering=1)
        self._human = open(self.run_dir / "trace.log", "a", encoding="utf-8", buffering=1)
        self._lock = threading.Lock()
        self.seq = 0
        self.prev = GENESIS
        self.ctx = {"session_id": None, "turn": 0, "step": 0}

    def set_ctx(self, **kw):
        self.ctx.update(kw)

    def event(self, name: str, **data) -> int:
        with self._lock:
            self.seq += 1
            rec = {
                "seq": self.seq,
                "ts": now_iso(),
                "run_id": self.run_id,
                "session_id": self.ctx["session_id"],
                "turn": self.ctx["turn"],
                "step": self.ctx["step"],
                "event": name,
                "data": data,
                "prev_hash": self.prev,
            }
            rec["hash"] = hashlib.sha256(_canon(rec).encode("utf-8")).hexdigest()
            self.prev = rec["hash"]
            self._trace.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            line = (f"{rec['seq']:05d} {rec['ts']} s={rec['session_id']} t={rec['turn']}.{rec['step']} "
                    f"{name} {_short(data)}")
            self._human.write(line + "\n")
            if self.echo:
                print(line, flush=True)
            return rec["seq"]

    def close(self):
        self._trace.close()
        self._human.close()


def read_trace(path) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def verify_chain(path) -> tuple[bool, str]:
    prev = GENESIS
    for i, rec in enumerate(read_trace(path), 1):
        claimed = rec.get("hash")
        body = {k: v for k, v in rec.items() if k != "hash"}
        if rec.get("prev_hash") != prev:
            return False, f"record {i} (seq {rec.get('seq')}): prev_hash does not match"
        if hashlib.sha256(_canon(body).encode("utf-8")).hexdigest() != claimed:
            return False, f"record {i} (seq {rec.get('seq')}): content hash mismatch"
        if rec.get("seq") != i:
            return False, f"record {i}: sequence gap (seq={rec.get('seq')})"
        prev = claimed
    return True, "ok"
