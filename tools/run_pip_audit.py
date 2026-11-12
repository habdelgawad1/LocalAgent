"""Run pip-audit against the repository's requirements.lock."""
import argparse
import json
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
    parser.add_argument("run_dir", nargs="?", default="logs/_scan", type=Path)
    args = parser.parse_args()
    executable = _tool("pip-audit")
    if executable is None:
        print("pip-audit is not installed or not on PATH", file=sys.stderr)
        return 2
    out_dir = args.run_dir / "pip_audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "pip_audit.json"
    result = subprocess.run(
        [executable, "-r", "requirements.lock", "-f", "json", "-o", str(output)],
        check=False,
    )
    try:
        version = subprocess.run(
            [executable, "--version"], check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"pip-audit version check failed: {exc}", file=sys.stderr)
        return 1
    (out_dir / "meta.json").write_text(json.dumps({"version": version}, indent=2), encoding="utf-8")
    if result.returncode < 0:
        print(f"pip-audit crashed with signal {-result.returncode}", file=sys.stderr)
        return 1
    # A non-zero exit status is the normal vulnerability result for pip-audit.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
