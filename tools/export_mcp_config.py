"""Export LocalAgent's stdio MCP servers for external scanners."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


def export(run_dir: Path, output: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "server_audit").mkdir(parents=True, exist_ok=True)
    servers = {}
    for name, script in config.SERVERS.items():
        servers[name] = {
            "command": sys.executable,
            "args": [str(script.resolve())],
            "env": config.server_env(run_dir),
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"mcpServers": servers}, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", default="logs/_scan", type=Path)
    parser.add_argument("--out", default="mcp_config.json", type=Path)
    args = parser.parse_args()
    export(args.run_dir, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
