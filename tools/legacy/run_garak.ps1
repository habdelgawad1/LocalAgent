# garak against the LocalAgent gateway (gateway.py must be running).
#   .\tools\legacy\run_garak.ps1            quick set (few prompts)
#   .\tools\legacy\run_garak.ps1 -Tier full adds the large probes (hours on CPU Qwen)
param([ValidateSet("quick","full")][string]$Tier = "quick")
$ErrorActionPreference = "Continue"
Set-Location "$PSScriptRoot\..\.."         # always run from the LocalAgent repo root
$py     = "C:\Users\nerme\AppData\Local\Python\pythoncore-3.14-64\python.exe"        # system Python 3.14 (has garak)
$venv   = Join-Path (Get-Location) ".venv\Scripts\python.exe"                         # repo venv (has mcp, openai)
$pyrit  = "C:\Users\nerme\Desktop\Coventry\GRAD\DVAI\pyrit-env\Scripts\python.exe"    # PyRIT environment
$memrun = "C:\Users\nerme\Desktop\Coventry\GRAD\Gemini"                               # folder with memrun go.mod

$probes = "dan.Dan_11_0,goodside.Tag"
if ($Tier -eq "full") { $probes += ",latentinjection.LatentInjectionReport,encoding.InjectBase64" }
# keep only the probes this garak version actually has (names change between versions)
$have = & $py -m garak --list_probes 2>&1 | Out-String
$ok = @(); foreach ($p in $probes.Split(",")) { if ($have -match [regex]::Escape($p)) { $ok += $p } else { Write-Host "[skip] unknown probe in this garak version: $p" } }
if ($ok.Count -eq 0) { Write-Host "No valid probes. Run: python -m garak --list_probes"; exit 1 }
$probes = $ok -join ","
& $py tools\legacy\mark.py garak
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "garak probes: $probes   (Ctrl+C stops early; score.py still works on what ran)"
& $py -m garak --model_type rest -G tools\legacy\garak_agent.json --generations 1 --probes $probes
& $py tools\legacy\score.py garak
Write-Host "Now compare with garak's own report (path printed above: ...\garak_runs\*.report.jsonl)."
