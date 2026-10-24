"""Web MCP server: fetch a page and return readable text. This is the untrusted-input source.

URLs of the form mock://<name> are served from the local mock_web folder, so you can plant test
pages (including prompt-injection fixtures) without touching the network.
"""
import os
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from common import audited, make_server, note

MOCK_DIR = Path(os.environ.get("AGENT_MOCK_WEB_DIR", "mock_web")).resolve()
MAX_BYTES = 500_000

mcp = make_server("web")


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "head"}

    def __init__(self):
        super().__init__()
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def _to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(p.parts))


@mcp.tool()
@audited("web")
def fetch_url(url: str, max_chars: int = 4000) -> str:
    """Fetch a web page (http, https or mock://name) and return its text content."""
    u = urlparse(url)
    if u.scheme == "mock":
        name = (u.netloc + u.path).strip("/")
        p = (MOCK_DIR / (name if "." in name else name + ".html")).resolve()
        if not p.is_relative_to(MOCK_DIR) or not p.is_file():
            raise FileNotFoundError(f"mock page not found: {name}")
        note(kind="mock", resolved_path=str(p), host=name)
        raw = p.read_text(encoding="utf-8", errors="replace")
    elif u.scheme in ("http", "https"):
        note(kind="network", host=u.hostname, url=url)
        req = urllib.request.Request(url, headers={"User-Agent": "agentlab/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read(MAX_BYTES).decode("utf-8", errors="replace")
    else:
        raise ValueError(f"unsupported URL scheme: {u.scheme!r}")
    text = _to_text(raw) if "<" in raw else raw
    note(chars_returned=min(len(text), max_chars))
    return text[:max_chars]


if __name__ == "__main__":
    mcp.run(transport="stdio")
