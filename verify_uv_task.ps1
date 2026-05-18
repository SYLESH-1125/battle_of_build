$ErrorActionPreference = 'Continue'
Set-Location (Join-Path $PSScriptRoot 'backend')
Write-Host "PWD: $PWD"
Write-Host "--- where task ---"
try { & where.exe task | ForEach-Object { Write-Host $_ } } catch { Write-Host "where.exe failed: $_" }
Write-Host "--- Get-Command task ---"
try { Get-Command task -ErrorAction SilentlyContinue | Format-List | Out-String | Write-Host } catch { Write-Host "Get-Command failed: $_" }
Write-Host "--- Running: uv run task serve ---"
try { & uv run task serve } catch { Write-Host "uv invocation failed: $_" }
