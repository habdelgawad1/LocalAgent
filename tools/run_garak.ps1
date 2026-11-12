# garak against the LocalAgent gateway (gateway.py must be running).
#   .\tools\run_garak.ps1            quick set (few prompts)
#   .\tools\run_garak.ps1 -Tier full adds the large probes (hours on CPU Qwen)
param([ValidateSet("quick","full")][string]$Tier = "quick")
$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "tool_env.ps1")
$py = $ToolPython
if (-not $py) { throw "Garak Python was not found. Set TOOL_PYTHON to its interpreter." }

$probes = "dan.Dan_11_0,goodside.Tag"
if ($Tier -eq "full") { $probes += ",latentinjection.LatentInjectionReport,encoding.InjectBase64" }
# keep only the probes this garak version actually has (names change between versions)
$have = & $py -m garak --list_probes 2>&1 | Out-String
$ok = @(); foreach ($p in $probes.Split(",")) { if ($have -match [regex]::Escape($p)) { $ok += $p } else { Write-Host "[skip] unknown probe in this garak version: $p" } }
if ($ok.Count -eq 0) { Write-Host "No valid probes. Run: python -m garak --list_probes"; exit 1 }
$probes = $ok -join ","
& $py tools\mark.py garak
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "garak probes: $probes   (Ctrl+C stops early; score.py still works on what ran)"
& $py -m garak --model_type rest -G tools\garak_agent.json --generations 1 --probes $probes
& $py tools\score.py garak
Write-Host "Now compare with garak's own report (path printed above: ...\garak_runs\*.report.jsonl)."
