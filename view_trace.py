"""Read a run's trace.

  python view_trace.py logs/<run>                 timeline, one line per event
  python view_trace.py logs/<run> --call call_ab12cd34   full evidence bundle for one tool call
  python view_trace.py logs/<run> --verify        check the hash chain only
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from logger import read_trace, verify_chain


def _t(ts):
    return datetime.fromisoformat(ts)


def short(x, n=110):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    s = s.replace("\n", "\\n")
    return s if len(s) <= n else s[: n - 3] + "..."


def line(e):
    d, n = e["data"], e["event"]
    if n == "user_message":
        return f"USER: {short(d['content'])}"
    if n == "memory_retrieval":
        return f"memory hits={len(d['results'])} " + short([(r['id'], r['score']) for r in d['results']])
    if n == "context_built":
        return f"~{d['est_tokens']} tokens, turns={d['turns_in_context']} dropped={d['turns_dropped']} tainted={d['tainted']}"
    if n == "model_response":
        calls = [c["name"] for c in d["tool_calls"]]
        return f"{d['latency_ms']}ms calls={calls} text={short(d['content'], 70)}"
    if n == "policy_decision":
        return (f"{d['tool']} effect={d['effect']} -> {d['action']} (would_have={d['would_have']}, "
                f"enforced={d['enforced']}, tainted={d['tainted']}) {d['reason']}")
    if n == "approval":
        return f"{d['tool']} approved={d['approved']} via {d['how']}"
    if n == "tool_blocked":
        return f"{d['tool']} BLOCKED by {d['by']}"
    if n == "tool_result":
        return f"{d['tool']} {'ERROR ' if d['is_error'] else ''}{d['duration_ms']}ms out={short(d['output'], 80)}"
    if n == "env_diff":
        if not d["changed"]:
            return f"{d['tool']} no environment change"
        df = d["diff"]
        bits = [f"files +{len(df['files']['added'])} ~{len(df['files']['modified'])} -{len(df['files']['removed'])}"]
        for t in ("tickets", "memory"):
            bits.append(f"{t} +{len(df[t]['added'])} ~{len(df[t]['modified'])} -{len(df[t]['removed'])}")
        paths = [x["path"] for k in ("added", "modified", "removed") for x in df["files"][k]]
        return f"{d['tool']} CHANGED " + ", ".join(bits) + (f" {paths}" if paths else "")
    if n == "final_answer":
        return f"ASSISTANT: {short(d['content'])}"
    return short(d)


def timeline(events):
    t0 = _t(events[0]["ts"])
    for e in events:
        off = (_t(e["ts"]) - t0).total_seconds()
        print(f"{e['seq']:04d} +{off:7.2f}s s={e['session_id']} {e['turn']}.{e['step']} {e['event']:<20} {line(e)}")


def bundle(run_dir: Path, events, call_id):
    mine = [e for e in events if e["data"].get("call_id") == call_id]
    if not mine:
        sys.exit(f"no events for {call_id}")
    for e in mine:
        print(f"\n=== [{e['seq']}] {e['event']}  {e['ts']}")
        print(json.dumps(e["data"], indent=2, ensure_ascii=False, default=str))
    # server-side audit records written during the call's time window
    tool = next((e["data"]["tool"] for e in mine if "tool" in e["data"]), "")
    start, end = _t(mine[0]["ts"]), _t(mine[-1]["ts"])
    srv, _, tname = tool.partition("__")
    f = run_dir / "server_audit" / f"{srv}.jsonl"
    if f.exists():
        print("\n=== server-side audit records in this window")
        for l in f.read_text().splitlines():
            r = json.loads(l)
            if r["tool"] == tname and (start.timestamp() - 1) <= _t(r["ts"]).timestamp() <= (end.timestamp() + 1):
                print(json.dumps(r, indent=2, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--call")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    run = Path(a.run_dir)
    ok, msg = verify_chain(run / "trace.jsonl")
    print(f"hash chain: {'OK' if ok else 'BROKEN - ' + msg}")
    if a.verify:
        sys.exit(0 if ok else 1)
    events = read_trace(run / "trace.jsonl")
    bundle(run, events, a.call) if a.call else timeline(events)


if __name__ == "__main__":
    main()
