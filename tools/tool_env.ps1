# Shared portable environment for the PowerShell tool workflows.
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Find-Executable([string]$Name, [string]$EnvironmentVariable) {
    $configured = [Environment]::GetEnvironmentVariable($EnvironmentVariable)
    if ($configured -and (Test-Path $configured)) {
        return (Resolve-Path $configured).Path
    }
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    return $null
}

$RepoPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $RepoPython)) {
    $RepoPython = Find-Executable "python" "PYTHON"
}
$ToolPython = Find-Executable "python" "TOOL_PYTHON"
$PyritPython = Find-Executable "python" "PYRIT_PYTHON"
$MemrunRoot = [Environment]::GetEnvironmentVariable("MEMRUN_ROOT")
$McpScanner = Find-Executable "mcp-scanner" "MCP_SCANNER"

if (-not $RepoPython) {
    throw "Python was not found. Create .venv or set PYTHON to a Python executable."
}
