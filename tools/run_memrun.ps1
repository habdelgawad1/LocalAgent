# LLMrecon memory modules (memrun) against the LocalAgent gateway (gateway.py must be running).
param([int]$Runs = 3)
$ErrorActionPreference = "Continue"
Set-Location "$PSScriptRoot\.."            # always run from the LocalAgent repo root
$py     = "C:\Users\nerme\AppData\Local\Python\pythoncore-3.14-64\python.exe"        # system Python 3.14 (has garak)
$venv   = Join-Path (Get-Location) ".venv\Scripts\python.exe"                         # repo venv (has mcp, openai)
$pyrit  = "C:\Users\nerme\Desktop\Coventry\GRAD\DVAI\pyrit-env\Scripts\python.exe"    # PyRIT environment
$memrun = "C:\Users\nerme\Desktop\Coventry\GRAD\Gemini"                               # folder with memrun go.mod

& $py tools\mark.py llmrecon
if ($LASTEXITCODE -ne 0) { exit 1 }
$out = Join-Path (Resolve-Path tools\results) "llmrecon_memrun.json"
Push-Location $memrun
go run ./cmd/memrun -bridge http://127.0.0.1:8800 -runs $Runs -out $out
Pop-Location
& $py tools\score.py llmrecon
Write-Host "memrun's own summary: $out ; compare its 'verified' counts with the ground truth above."
