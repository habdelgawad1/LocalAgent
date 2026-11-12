# Starts the agent gateway with the repo's venv. Leave this window open.
#   .\tools\start_gateway.ps1                      baseline
#   .\tools\start_gateway.ps1 -Hardened            hardened (matched pair)
param([switch]$Hardened)
$ErrorActionPreference = "Continue"
Set-Location "$PSScriptRoot\.."             # always run from the LocalAgent repo root
$py     = "C:\Users\nerme\AppData\Local\Python\pythoncore-3.14-64\python.exe"        # system Python 3.14 (has garak)
$venv   = Join-Path (Get-Location) ".venv\Scripts\python.exe"                         # repo venv (has mcp, openai)
$pyrit  = "C:\Users\nerme\Desktop\Coventry\GRAD\DVAI\pyrit-env\Scripts\python.exe"    # PyRIT environment
$memrun = "C:\Users\nerme\Desktop\Coventry\GRAD\Gemini"                               # folder with memrun go.mod

if ($Hardened) { $env:AGENT_HARDENED = "1" }
& $venv gateway.py
