# Starts the agent gateway with the repo's venv. Leave this window open.
#   .\tools\start_gateway.ps1                      baseline
#   .\tools\start_gateway.ps1 -Hardened            hardened (matched pair)
param([switch]$Hardened)
$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "tool_env.ps1")

if ($Hardened) { $env:AGENT_HARDENED = "1" }
& $RepoPython gateway.py
