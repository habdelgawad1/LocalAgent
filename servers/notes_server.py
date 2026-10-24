"""Notes MCP server: read/write plain-text notes in a sandbox folder.

Baseline behaviour is what a developer would write on a first pass: join the requested name onto the
notes folder and go. With H_PATH_CHECK=1 the resolved path must stay inside the folder.
NOTE: the baseline does not stop '../' traversal. Run the lab inside a VM/container with nothing
sensitive on it.
"""
import os
from pathlib import Path

from common import audited, make_server, note

SANDBOX = Path(os.environ["AGENT_SANDBOX_DIR"]).resolve()
PATH_CHECK = os.environ.get("H_PATH_CHECK", "0") == "1"
MAX_READ = 100_000

mcp = make_server("notes")


def _resolve(name: str) -> Path:
    real = (SANDBOX / name).resolve()
    inside = real.is_relative_to(SANDBOX)
    note(requested=name, resolved_path=str(real), inside_sandbox=inside, path_check_enabled=PATH_CHECK)
    if PATH_CHECK and not inside:
        raise ValueError("path escapes the notes folder")
    return real


@mcp.tool()
@audited("notes")
def list_notes() -> str:
    """List the notes available in the notes folder."""
    names = sorted(p.relative_to(SANDBOX).as_posix() for p in SANDBOX.rglob("*") if p.is_file())
    note(count=len(names))
    return "\n".join(names) if names else "(no notes)"


@mcp.tool()
@audited("notes")
def read_note(name: str) -> str:
    """Read a note by file name, for example 'todo.txt'."""
    p = _resolve(name)
    if not p.is_file():
        raise FileNotFoundError(f"note not found: {name}")
    return p.read_text(encoding="utf-8", errors="replace")[:MAX_READ]


@mcp.tool()
@audited("notes")
def write_note(name: str, content: str) -> str:
    """Create or overwrite a note with the given content."""
    p = _resolve(name)
    existed = p.exists()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    note(overwrote=existed, bytes=len(content.encode("utf-8")))
    return f"{'Updated' if existed else 'Created'} note '{name}' ({len(content)} chars)"


@mcp.tool()
@audited("notes")
def delete_note(name: str) -> str:
    """Delete a note. This cannot be undone."""
    p = _resolve(name)
    if not p.is_file():
        raise FileNotFoundError(f"note not found: {name}")
    p.unlink()
    return f"Deleted note '{name}'"


if __name__ == "__main__":
    mcp.run(transport="stdio")
