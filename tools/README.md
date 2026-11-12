# External scanner integrations

This directory contains the four optional security-scanner integrations for LocalAgent. They are
separate from [`agent_tests/`](../agent_tests/), which contains the older gateway-based red-team
harness and its tool-specific scripts.

## Entry points

| File | Purpose | Output |
|---|---|---|
| `export_mcp_config.py` | Export LocalAgent's stdio MCP servers | `mcp_config.json` |
| `run_pip_audit.py` | Audit `requirements.lock` | `pip_audit/` |
| `run_mcp_scan.py` | Inspect or optionally remotely scan MCP config | `mcp_scan/` |
| `run_authlab.py` | Scan an HTTP/OAuth MCP endpoint | `mcp_authlab/` |
| `run_a2a_scan.py` | Optional A2A scanner placeholder | `a2a_scanner/` |
| `run_all.py` | Orchestrate available scanners and adapters | `findings_tools.json` |
| `adapters.py` | Normalize saved JSON into finding records | consumed by `run_all.py` |

Use the repository root as the working directory:

```text
python tools/run_all.py logs/<run>
python tools/export_mcp_config.py --run-dir logs/<run>
```

The scanners are installed in a separate virtual environment and are never imported by this
package. `mcp-scan inspect` is local-only; `mcp-scan scan` requires `--allow-remote`.

## Output layout

Each run keeps scanner evidence together:

```text
logs/<run>/
├── mcp_config.json
├── pip_audit/
├── mcp_scan/
├── mcp_authlab/
├── a2a_scanner/
└── findings_tools.json
```

The existing `findings.json` remains owned by `judge_lite.py`.
