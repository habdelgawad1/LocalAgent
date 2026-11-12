"""Run mcp-scan safely; remote verification is opt-in."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


def _tool(name):
    names = ["snyk-agent-scan", "mcp-scan"] if name == "mcp-scan" else [name]
    for candidate_name in names:
        found = shutil.which(candidate_name)
        if found:
            return found
        candidate = Path(sys.executable).with_name(
            candidate_name + (".exe" if sys.platform == "win32" else "")
        )
        if candidate.exists():
            return str(candidate)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", nargs="?", default="logs/_scan", type=Path)
    parser.add_argument("--config", type=Path, default=Path("mcp_config.json"))
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--dangerously-run-mcp-servers", action="store_true")
    args = parser.parse_args()
    executable = _tool("mcp-scan")
    if executable is None:
        print("mcp-scan is not installed or not on PATH", file=sys.stderr)
        return 2
    if args.scan and not args.allow_remote:
        parser.error("mcp-scan scan requires --allow-remote")
    out_dir = args.run_dir / "mcp_scan"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / ("scan.json" if args.scan else "inspect.json")
    command = [executable, "scan" if args.scan else "inspect", str(args.config)]
    if not args.scan:
        command.append("--json")
    else:
        print("WARNING: mcp-scan scan sends configuration to its remote verification server.")
        if args.dangerously_run_mcp_servers:
            command.append("--dangerously-run-mcp-servers")
    with output.open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.PIPE, text=True, check=False)
    try:
        version = subprocess.run(
            [executable, "--help"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        version = "unknown"
    (out_dir / "meta.json").write_text(json.dumps({"version": version}, indent=2), encoding="utf-8")
    if result.returncode < 0:
        print(f"mcp-scan crashed with signal {-result.returncode}: {result.stderr}", file=sys.stderr)
        return 1
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
