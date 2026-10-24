"""Connects to the MCP servers over stdio, exposes their tools to the model, routes tool calls."""
import hashlib
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import config


def _first(obj, *names):
    """mcp 1.x uses camelCase fields (inputSchema, isError); mcp 2.x uses snake_case."""
    for n in names:
        v = getattr(obj, n, None)
        if v is not None:
            return v
    return None


class MCPHub:
    def __init__(self, servers: dict, env: dict, run_dir, log):
        self.servers = servers
        self.env = env
        self.run_dir = run_dir
        self.log = log
        self.routes: dict = {}      # full tool name -> (server, tool, session)
        self.schemas: list = []     # OpenAI-style tool definitions
        self._stack: AsyncExitStack | None = None

    async def __aenter__(self):
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        try:
            for name, script in self.servers.items():
                errf = open(self.run_dir / f"server_{name}.stderr", "w", encoding="utf-8")
                self._stack.callback(errf.close)
                params = StdioServerParameters(command=sys.executable, args=[str(script)],
                                               env=self.env, cwd=str(config.ROOT))
                read, write = await self._stack.enter_async_context(stdio_client(params, errlog=errf))
                session = await self._stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                listed = await session.list_tools()
                described = []
                for t in listed.tools:
                    full = f"{name}__{t.name}"
                    desc = t.description or ""
                    schema = _first(t, "input_schema", "inputSchema") or {"type": "object", "properties": {}}
                    self.routes[full] = (name, t.name, session)
                    self.schemas.append({"type": "function", "function": {
                        "name": full, "description": desc, "parameters": schema}})
                    described.append({"tool": full, "description": desc,
                                      "description_sha256": hashlib.sha256(desc.encode()).hexdigest(),
                                      "input_schema": schema})
                # Descriptions are logged with hashes so a changed ('rug-pulled') description is detectable.
                self.log.event("mcp_server_connected", server=name, script=str(script), tools=described)
        except BaseException:
            await self._stack.aclose()
            raise
        return self

    async def __aexit__(self, *exc):
        if self._stack:
            await self._stack.aclose()

    async def call(self, full_name: str, args: dict):
        """Returns (text_for_model, is_error, raw_content_list)."""
        server, tool, session = self.routes[full_name]
        res = await session.call_tool(tool, args)
        parts, raw = [], []
        for c in getattr(res, "content", None) or []:
            raw.append(c.model_dump() if hasattr(c, "model_dump") else str(c))
            if getattr(c, "type", "") == "text":
                parts.append(c.text)
            else:
                parts.append(f"[{getattr(c, 'type', 'content')} content omitted]")
        return "\n".join(parts), bool(_first(res, "is_error", "isError")), raw
