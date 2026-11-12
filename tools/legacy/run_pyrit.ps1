# PyRIT against the LocalAgent gateway (gateway.py must be running). Uses the pyrit-env Python by path.
$ErrorActionPreference = "Continue"
Set-Location "$PSScriptRoot\..\.."         # always run from the LocalAgent repo root
$py     = "C:\Users\nerme\AppData\Local\Python\pythoncore-3.14-64\python.exe"        # system Python 3.14 (has garak)
$venv   = Join-Path (Get-Location) ".venv\Scripts\python.exe"                         # repo venv (has mcp, openai)
$pyrit  = "C:\Users\nerme\Desktop\Coventry\GRAD\DVAI\pyrit-env\Scripts\python.exe"    # PyRIT environment
$memrun = "C:\Users\nerme\Desktop\Coventry\GRAD\Gemini"                               # folder with memrun go.mod

& $py tools\legacy\mark.py pyrit
if ($LASTEXITCODE -ne 0) { exit 1 }
& $pyrit tools\legacy\pyrit_agent.py
& $py tools\legacy\score.py pyrit
