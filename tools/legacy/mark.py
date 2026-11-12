"""Reset the lab through the gateway and record the start time for one tool run.

  python tools/legacy/mark.py garak
Run from the LocalAgent repo root with gateway.py running. score.py later reports only what happened after this mark.
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = os.getenv("GATEWAY", "http://127.0.0.1:8800")
HERE = Path(__file__).resolve().parent


def call(method, path, body=None, timeout=120):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python tools/legacy/mark.py <tool-name>")
    tool = sys.argv[1]
    try:
        info = call("GET", "/info")
    except Exception as e:
        sys.exit(f"gateway not reachable at {BASE} ({e}). Start it first: python gateway.py")
    if "--force" not in sys.argv:
        try:
            a = call("GET", "/stats")
            time.sleep(6)
            b = call("GET", "/stats")
        except Exception:
            a = b = {}
        if a.get("inflight", 0) or b.get("inflight", 0) or a.get("requests") != b.get("requests"):
            sys.exit("[mark] ABORTED: the agent is still handling requests from another tool run. Wait for that run to "
                     "finish (its score table prints at the end), then start this one. Use --force to override.")
    reset = call("POST", "/reset", {})
    start = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / f"{tool}.start").write_text(start, encoding="utf-8")
    print(f"[mark] {tool}: lab reset ({reset.get('deleted')} memory rows cleared), start={start}")
    print(f"[mark] agent: model={info['model']} mode={info['mode']} run_dir={info['run_dir']}")


if __name__ == "__main__":
    main()
