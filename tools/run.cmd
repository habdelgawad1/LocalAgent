@echo off
rem Runs a script from this folder without the PowerShell execution-policy prompt.
rem   tools\run.cmd start_gateway
rem   tools\run.cmd run_garak
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0%~1.ps1" %2 %3 %4 %5
