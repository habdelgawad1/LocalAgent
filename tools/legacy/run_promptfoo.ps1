# promptfoo red team against the LocalAgent gateway (gateway.py must be running).
$ErrorActionPreference = "Continue"
Set-Location "$PSScriptRoot\..\.."         # always run from the LocalAgent repo root
$py     = "C:\Users\nerme\AppData\Local\Python\pythoncore-3.14-64\python.exe"        # system Python 3.14 (has garak)
$venv   = Join-Path (Get-Location) ".venv\Scripts\python.exe"                         # repo venv (has mcp, openai)
$pyrit  = "C:\Users\nerme\Desktop\Coventry\GRAD\DVAI\pyrit-env\Scripts\python.exe"    # PyRIT environment
$memrun = "C:\Users\nerme\Desktop\Coventry\GRAD\Gemini"                               # folder with memrun go.mod

$env:REQUEST_TIMEOUT_MS = "900000"      # Qwen on CPU is slow
& $py tools\legacy\mark.py promptfoo
if ($LASTEXITCODE -ne 0) { exit 1 }
$cfg = "tools\legacy\promptfooconfig.agent.yaml"
if (Get-Command promptfoo -ErrorAction SilentlyContinue) { promptfoo redteam run -c $cfg --max-concurrency 1 }
else { npx promptfoo@latest redteam run -c $cfg --max-concurrency 1 }
& $py tools\legacy\score.py promptfoo
Write-Host "Now compare with promptfoo's own report:  promptfoo redteam report"
