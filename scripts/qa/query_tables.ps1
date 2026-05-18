$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot
$envFile = Join-Path $projectRoot '.env'
$envLines = Get-Content $envFile
$kLine = $envLines | Where-Object { $_ -match '^SUPABASE_SECRET_KEY=' } | Select-Object -First 1
if (-not $kLine) { Write-Error "SUPABASE_SECRET_KEY not found in .env"; exit 1 }
$k = $kLine -replace '^SUPABASE_SECRET_KEY=',''
$u = 'https://cdgcmcznmqykmzyovnmn.supabase.co'
$headers = @{ 'apikey' = $k; 'Authorization' = "Bearer $k" }

Write-Output "-- staging_vault (latest 5) --"
try { $s = Invoke-RestMethod -Uri "$u/rest/v1/staging_vault?select=*&order=created_at.desc&limit=5" -Method Get -Headers $headers -TimeoutSec 30; $s | ConvertTo-Json -Depth 5 | Write-Output } catch { Write-Output "staging_vault GET error: $($_.Exception.Message)" }

Write-Output "-- main_vault (latest 5) --"
try { $m = Invoke-RestMethod -Uri "$u/rest/v1/main_vault?select=*&order=created_at.desc&limit=5" -Method Get -Headers $headers -TimeoutSec 30; $m | ConvertTo-Json -Depth 5 | Write-Output } catch { Write-Output "main_vault GET error: $($_.Exception.Message)" }

Write-Output "-- audit_logs (latest 5) --"
try { $a = Invoke-RestMethod -Uri "$u/rest/v1/audit_logs?select=*&order=created_at.desc&limit=5" -Method Get -Headers $headers -TimeoutSec 30; $a | ConvertTo-Json -Depth 5 | Write-Output } catch { Write-Output "audit_logs GET error: $($_.Exception.Message)" }
