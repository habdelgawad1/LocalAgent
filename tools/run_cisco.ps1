# Cisco MCP Scanner against the agent's MCP servers (offline 'static' scan of the exported tool list). No gateway needed.
#   .\tools\run_cisco.ps1          yara analyzer only
#   .\tools\run_cisco.ps1 -Llm     also the LLM analyzer (Ollama running)
param([switch]$Llm, [switch]$Control, [string]$Model = "openai/qwen2.5:7b-instruct")
$ErrorActionPreference = "Continue"
Set-Location "$PSScriptRoot\.."            # always run from the LocalAgent repo root
$py     = "C:\Users\nerme\AppData\Local\Python\pythoncore-3.14-64\python.exe"        # system Python 3.14 (has garak)
$venv   = Join-Path (Get-Location) ".venv\Scripts\python.exe"                         # repo venv (has mcp, openai)
$pyrit  = "C:\Users\nerme\Desktop\Coventry\GRAD\DVAI\pyrit-env\Scripts\python.exe"    # PyRIT environment
$memrun = "C:\Users\nerme\Desktop\Coventry\GRAD\Gemini"                               # folder with memrun go.mod

& $venv tools\export_tools.py
if ($LASTEXITCODE -ne 0) { exit 1 }
$scanner = "C:\Users\nerme\.local\bin\mcp-scanner.exe"
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
