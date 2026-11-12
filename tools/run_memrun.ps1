# LLMrecon memory modules (memrun) against the LocalAgent gateway (gateway.py must be running).
param([int]$Runs = 3)
$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "tool_env.ps1")
$py = $ToolPython
if (-not $py) { throw "memrun Python was not found. Set TOOL_PYTHON to its interpreter." }
if (-not $MemrunRoot -or -not (Test-Path $MemrunRoot)) {
    throw "memrun repository was not found. Set MEMRUN_ROOT to its directory."
}

& $py tools\mark.py llmrecon
if ($LASTEXITCODE -ne 0) { exit 1 }
$out = Join-Path (Resolve-Path tools\results) "llmrecon_memrun.json"
Push-Location $MemrunRoot
go run ./cmd/memrun -bridge http://127.0.0.1:8800 -runs $Runs -out $out
Pop-Location
& $py tools\score.py llmrecon
Write-Host "memrun's own summary: $out ; compare its 'verified' counts with the ground truth above."
