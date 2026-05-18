Set-Location (Join-Path $PSScriptRoot 'backend')
Write-Host "Running: uv run .\task.cmd serve"
$proc = Start-Process -FilePath uv -ArgumentList 'run', '.\task.cmd', 'serve' -NoNewWindow -Wait -PassThru
Write-Host "Exit: $($proc.ExitCode)" 
