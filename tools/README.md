# Security tool integrations

This directory contains every security-tool integration for LocalAgent. The newer scanner runners
are at its root; the older gateway-based red-team harness is retained under [`legacy/`](legacy/)
so there is one top-level location and no duplicate tool tree.

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

Legacy gateway harness:

| File | Purpose |
|---|---|
| `legacy/run.cmd` | Dispatch legacy PowerShell workflows |
| `legacy/start_gateway.ps1` | Start the LocalAgent gateway |
| `legacy/run_garak.ps1` | Run garak |
| `legacy/run_promptfoo.ps1` | Run promptfoo |
| `legacy/run_pyrit.ps1` | Run PyRIT |
| `legacy/run_cisco.ps1` | Run the legacy static MCP scanner |
| `legacy/run_memrun.ps1` | Run LLMrecon/memrun |
| `legacy/mark.py` + `legacy/score.py` | Mark and score gateway runs |

Use the repository root as the working directory:

```text
python tools/run_all.py logs/<run>
python tools/export_mcp_config.py --run-dir logs/<run>
tools\legacy\run.cmd start_gateway
tools\legacy\run.cmd run_garak
```

The scanners are installed in a separate virtual environment and are never imported by this
package. `mcp-scan inspect` is local-only; `mcp-scan scan` requires `--allow-remote`.
All commands are run from the repository root, write evidence under either `logs/<run>/` or
`tools/legacy/results/`, and leave `findings.json` owned by `judge_lite.py`.

## Output layout

Each new scanner run keeps evidence together:

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

Legacy gateway runs continue to use `tools/legacy/results/` for start marks and scanner reports,
while their ground-truth findings are calculated from the shared `logs/<run>/` trace by
`tools/legacy/score.py`.
