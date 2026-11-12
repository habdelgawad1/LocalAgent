"""Shared standard-library helpers for external tool runners."""
from pathlib import Path
import shutil
import sys


def find_tool(name: str, aliases=()):
    """Return a console-script path from PATH or the active interpreter's Scripts directory."""
    for candidate_name in (name, *aliases):
        found = shutil.which(candidate_name)
        if found:
            return found
        candidate = Path(sys.executable).with_name(
            candidate_name + (".exe" if sys.platform == "win32" else "")
        )
        if candidate.exists():
            return str(candidate)
    return None
