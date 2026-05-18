#!/usr/bin/env pwsh
# Root-level backend starter for PowerShell
# Run from repo root with: .\start-backend.ps1

$scriptDir = Split-Path -Parent (Get-Item $MyInvocation.MyCommand.Path).FullName
$backendDir = Join-Path $scriptDir "backend"

if (!(Test-Path $backendDir)) {
    Write-Error "Error: backend directory not found at $backendDir"
    exit 1
}

Write-Host "Starting backend from $backendDir..."
Write-Host ""

Set-Location $backendDir
& uv run python serve.py
