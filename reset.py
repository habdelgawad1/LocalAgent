"""Reset the lab to a clean starting state.

  python reset.py                 delete data/, logs/ and __pycache__, then re-seed data/ (asks first)
  python reset.py --yes           same, without the question
  python reset.py --archive       move logs/ into evidence/<timestamp>/ instead of deleting them
  python reset.py --keep-logs     reset data/ only (use between runs of the same experiment)
  python reset.py --logs-only     delete logs/ only, leave data/ alone

Only folders inside this project are touched. If AGENT_DATA_DIR / AGENT_LOGS_DIR point elsewhere,
the script refuses unless you pass --force.
"""
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import config
import seed

ROOT = config.ROOT


def inside_project(p: Path) -> bool:
    try:
        p.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def size_mb(p: Path) -> float:
    if not p.exists():
        return 0.0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", "-y", action="store_true", help="do not ask for confirmation")
    ap.add_argument("--archive", action="store_true", help="move logs to evidence/<timestamp>/ instead of deleting")
    ap.add_argument("--keep-logs", action="store_true", help="reset data/ only")
    ap.add_argument("--logs-only", action="store_true", help="handle logs/ only, leave data/ alone")
    ap.add_argument("--force", action="store_true", help="allow paths outside the project folder")
    a = ap.parse_args()
    if a.keep_logs and a.logs_only:
        sys.exit("--keep-logs and --logs-only cancel each other out")

    data, logs = Path(config.DATA_DIR), Path(config.LOGS_DIR)
    do_data = not a.logs_only
    do_logs = not a.keep_logs
    for label, p, active in (("data", data, do_data), ("logs", logs, do_logs)):
        if active and not inside_project(p) and not a.force:
            sys.exit(f"Refusing: {label} folder {p} is outside the project. Use --force if that is intended.")

    pycache = [p for p in ROOT.rglob("__pycache__") if ".venv" not in p.parts]

    print("This will:")
    if do_data:
        print(f"  - delete data/   ({size_mb(data):.1f} MB)  and re-create the starting notes, tickets and decoy secret")
    if do_logs:
        verb = "move to evidence/" if a.archive else "delete"
        print(f"  - {verb} logs/   ({size_mb(logs):.1f} MB, {len(list(logs.glob('*'))) if logs.exists() else 0} runs)")
    if not a.logs_only:
        print(f"  - delete {len(pycache)} __pycache__ folder(s)")
    if not a.yes and input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
        sys.exit("Cancelled.")

    if do_logs and logs.exists():
        if a.archive:
            dest = ROOT / "evidence" / datetime.now().strftime("%Y%m%d-%H%M%S")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(logs), str(dest))
            print(f"Logs archived to {dest}")
        else:
            shutil.rmtree(logs)
            print("Logs deleted.")
    if do_data:
        if data.exists():
            shutil.rmtree(data)
        seed.ensure()
        print("Data reset and re-seeded.")
    if not a.logs_only:
        for p in pycache:
            shutil.rmtree(p, ignore_errors=True)
    print("Done.")


if __name__ == "__main__":
    main()