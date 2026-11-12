# Cisco MCP Scanner against the agent's MCP servers (offline 'static' scan of the exported tool list). No gateway needed.
#   .\tools\run_cisco.ps1          yara analyzer only
#   .\tools\run_cisco.ps1 -Llm     also the LLM analyzer (Ollama running)
param([switch]$Llm, [switch]$Control, [string]$Model = "openai/qwen2.5:7b-instruct")
$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "tool_env.ps1")

& $RepoPython tools\export_tools.py
if ($LASTEXITCODE -ne 0) { exit 1 }
if (-not $McpScanner) { throw "Cisco MCP scanner was not found. Set MCP_SCANNER or add mcp-scanner to PATH." }
$scanner = $McpScanner
$analyzers = "yara"
if ($Llm) {
  $env:MCP_SCANNER_LLM_API_KEY = "ollama"
  $env:MCP_SCANNER_LLM_BASE_URL = "http://localhost:11434/v1"
  $env:MCP_SCANNER_LLM_MODEL = $Model
  $analyzers = "yara,llm"
}
$tools = "tools\results\agent-tools.json"
if ($Control) { $tools = "tools\poisoned-tools.json"; Write-Host "POSITIVE CONTROL: scanning a tool list with a deliberately poisoned description (it SHOULD be flagged)" }
& $scanner --analyzers $analyzers --format table static --tools $tools
Write-Host "`nExpected by design: notes__delete_note, tickets__delete_ticket, notes__write_note and web__fetch_url are the risky tools."
Write-Host "Record which the scanner flagged, and any harmless tool it flagged (false alarm). Note the analyzers and model used."
