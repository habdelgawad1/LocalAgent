"""Run mcp-authlab against an HTTP/OAuth MCP server.

LocalAgent's servers use stdio and therefore have no default URL. Use
``mcp-authlab fixture --profile passthrough`` (or another fixture profile) as
the intended reference target, or provide another HTTP/OAuth MCP endpoint.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--url", required=True)
    parser.add_argument("--token")
    parser.add_argument("--foreign-token")
    parser.add_argument("--fail-under")
    args = parser.parse_args()
    if shutil.which("mcp-authlab") is None:
        print("mcp-authlab is not installed or not on PATH", file=sys.stderr)
        return 2
    out_dir = args.run_dir / "mcp_authlab"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "scan.json"
    command = ["mcp-authlab", "scan", args.url, "--format", "json", "-o", str(output)]
    for flag, value in (("--token", args.token), ("--foreign-token", args.foreign_token),
                        ("--fail-under", args.fail_under)):
        if value is not None:
            command.extend([flag, value])
    result = subprocess.run(command, check=False)
    try:
        version = subprocess.run(
            ["mcp-authlab", "--version"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        version = "unknown"
    (out_dir / "meta.json").write_text(json.dumps({"version": version}, indent=2), encoding="utf-8")
    if result.returncode < 0:
        return 1
    return 0 if result.returncode == 2 else result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
