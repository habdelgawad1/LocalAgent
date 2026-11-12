"""Run available external scanners and combine their findings."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

try:
    from .runner_common import find_tool
    from .adapters import a2a_scanner, mcp_authlab, mcp_scan, pip_audit
except ImportError:
    from runner_common import find_tool
    from adapters import a2a_scanner, mcp_authlab, mcp_scan, pip_audit

ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent


def _export_config(run_dir: Path, config_path: Path) -> bool:
    result = subprocess.run(
        [sys.executable, str(TOOLS / "export_mcp_config.py"),
         "--run-dir", str(run_dir), "--out", str(config_path)],
        cwd=ROOT, check=False,
    )
    if result.returncode != 0:
        print(f"MCP config: error (exit {result.returncode})")
        return False
    return True


def _run(label, command, executable, output_paths, adapter):
    lookup_name = "snyk-agent-scan" if executable == "mcp-scan" else executable
    aliases = ("mcp-scan",) if executable == "mcp-scan" else ()
    if not find_tool(lookup_name, aliases=aliases):
        print(f"{label}: skipped: {executable} not on PATH")
        return "skipped", []
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode != 0:
        print(f"{label}: error (exit {result.returncode})")
        return "error", []
    findings = []
    for path in output_paths:
        findings.extend(adapter(path))
    return "ran", findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--auth-url")
    parser.add_argument("--token")
    parser.add_argument("--foreign-token")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--card", type=Path)
    target.add_argument("--a2a-url")
    args = parser.parse_args()
    run_dir = args.run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    config_path = run_dir / "mcp_config.json"
    if not _export_config(run_dir, config_path):
        return 1
    rows = []
    findings = []
    status, found = _run(
        "pip-audit",
        [sys.executable, str(TOOLS / "run_pip_audit.py"), str(run_dir)],
        "pip-audit", [run_dir / "pip_audit" / "pip_audit.json"], pip_audit,
    )
    rows.append(("pip-audit", status, len(found)))
    findings.extend(found)
    status, found = _run(
        "mcp-scan",
        [sys.executable, str(TOOLS / "run_mcp_scan.py"), str(run_dir), "--config", str(config_path)],
        "mcp-scan", [run_dir / "mcp_scan" / "inspect.json"], mcp_scan,
    )
    rows.append(("mcp-scan", status, len(found)))
    findings.extend(found)
    if args.auth_url:
        command = [sys.executable, str(TOOLS / "run_authlab.py"), str(run_dir), "--url", args.auth_url]
        if args.token:
            command.extend(["--token", args.token])
        if args.foreign_token:
            command.extend(["--foreign-token", args.foreign_token])
        status, found = _run(
            "mcp-authlab", command, "mcp-authlab",
            [run_dir / "mcp_authlab" / "scan.json"], mcp_authlab,
        )
    else:
        print("mcp-authlab: skipped: no --auth-url")
        status, found = "skipped", []
    rows.append(("mcp-authlab", status, len(found)))
    findings.extend(found)
    if args.card or args.a2a_url:
        command = [sys.executable, str(TOOLS / "run_a2a_scan.py"), str(run_dir)]
        command.extend(["--card", str(args.card)] if args.card else ["--url", args.a2a_url])
        status, found = _run(
            "a2a-scanner", command, "a2a-scanner",
            [run_dir / "a2a_scanner" / "scan.json"], a2a_scanner,
        )
    else:
        print("a2a-scanner: skipped: no --card/--a2a-url")
        status, found = "skipped", []
    rows.append(("a2a-scanner", status, len(found)))
    findings.extend(found)
    (run_dir / "findings_tools.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print("\nTool       Status   Findings")
    print("---------------------------")
    for tool, status, count in rows:
        print(f"{tool:<10} {status:<8} {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
