# PyRIT against the LocalAgent gateway (gateway.py must be running). Uses the pyrit-env Python by path.
$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "tool_env.ps1")
$py = $RepoPython
if (-not $PyritPython) { throw "PyRIT Python was not found. Set PYRIT_PYTHON to its interpreter." }

& $py tools\mark.py pyrit
if ($LASTEXITCODE -ne 0) { exit 1 }
& $PyritPython tools\pyrit_agent.py
& $py tools\score.py pyrit
