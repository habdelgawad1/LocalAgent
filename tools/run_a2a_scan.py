"""Placeholder runner for Cisco's A2A scanner.

The scanner is intentionally optional. Its console command and scan flags
could not be verified in this environment, so this wrapper does not invent
them. After installing the package, run ``a2a-scanner --help`` and replace the
marked TODO below with the documented invocation.
"""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def _tool(name):
    found = shutil.which(name)
    if found:
        return found
    candidate = Path(sys.executable).with_name(name + (".exe" if sys.platform == "win32" else ""))
    return str(candidate) if candidate.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--card", type=Path)
    target.add_argument("--url")
    args = parser.parse_args()
    out_dir = args.run_dir / "a2a_scanner"
    out_dir.mkdir(parents=True, exist_ok=True)
    executable = _tool("a2a-scanner")
    if executable is None:
        print("a2a-scanner is unavailable; TODO: install cisco-ai-a2a-scanner and verify its CLI", file=sys.stderr)
        return 2
    print(
        f"TODO: verify the installed CLI with {executable} --help before adding "
        "the A2A scan command",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
