"""Export the tool definitions of the agent's three MCP servers for the Cisco MCP Scanner (offline 'static' mode).

  python tools/export_tools.py       writes tools/results/agent-tools.json  ({"tools": [...]})
Run from the LocalAgent repo root. Starts each server over stdio, calls tools/list, and stops it again.
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config  # noqa: E402
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


def first(obj, *names):
    for n in names:
        v = getattr(obj, n, None)
        if v is not None:
            return v
    return None


async def main():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    tools = []
    with tempfile.TemporaryDirectory() as tmp:
        env = config.server_env(tmp)
        for name, script in config.SERVERS.items():
            params = StdioServerParameters(command=sys.executable, args=[str(script)], env=env, cwd=str(config.ROOT))
            with open(Path(tmp) / f"{name}.err", "w") as errf:
                async with stdio_client(params, errlog=errf) as (r, w):
                    async with ClientSession(r, w) as s:
                        await s.initialize()
                        for t in (await s.list_tools()).tools:
                            tools.append({"name": f"{name}__{t.name}", "description": t.description or "",
                                          "inputSchema": first(t, "input_schema", "inputSchema") or {"type": "object", "properties": {}}})
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "agent-tools.json").write_text(json.dumps({"tools": tools}, indent=2), encoding="utf-8")   # UTF-8 without BOM
    print(f"{len(tools)} tools -> tools/results/agent-tools.json")
    for t in tools:
        print("  ", t["name"])


asyncio.run(main())
