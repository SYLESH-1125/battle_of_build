Set-Location (Join-Path $PSScriptRoot 'backend')
Write-Host "PWD: $PWD"
Write-Host "PYTHONHOME=$($env:PYTHONHOME)"
Write-Host "PYTHONPATH=$($env:PYTHONPATH)"
$path = $env:PATH
if ($path) { Write-Host "PATH (first 300 chars): $($path.Substring(0, [Math]::Min(300, $path.Length)))" } else { Write-Host "PATH is empty" }
Get-Command uv -ErrorAction SilentlyContinue | Format-List Source,Path | Out-Host
