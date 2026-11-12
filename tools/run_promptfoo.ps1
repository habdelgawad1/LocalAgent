# promptfoo red team against the LocalAgent gateway (gateway.py must be running).
$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "tool_env.ps1")
$py = $ToolPython
if (-not $py) { throw "Promptfoo Python was not found. Set TOOL_PYTHON to its interpreter." }

$env:REQUEST_TIMEOUT_MS = "900000"      # Qwen on CPU is slow
& $py tools\mark.py promptfoo
if ($LASTEXITCODE -ne 0) { exit 1 }
$cfg = "tools\promptfooconfig.agent.yaml"
if (Get-Command promptfoo -ErrorAction SilentlyContinue) { promptfoo redteam run -c $cfg --max-concurrency 1 }
else { npx promptfoo@latest redteam run -c $cfg --max-concurrency 1 }
& $py tools\score.py promptfoo
Write-Host "Now compare with promptfoo's own report:  promptfoo redteam report"
