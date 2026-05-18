$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot
$envFile = Join-Path $projectRoot '.env'
$envLines = Get-Content $envFile
$kLine = $envLines | Where-Object { $_ -match '^SUPABASE_SECRET_KEY=' } | Select-Object -First 1
if (-not $kLine) { Write-Error "SUPABASE_SECRET_KEY not found in .env"; exit 1 }
$k = $kLine -replace '^SUPABASE_SECRET_KEY=',''
$u = 'https://cdgcmcznmqykmzyovnmn.supabase.co'
$headers = @{ 'apikey' = $k; 'Authorization' = "Bearer $k"; 'Prefer' = 'return=representation' }

$payload = @{ patient_id = 'PT-LIFECYCLE-MASTER-01'; status = 'pending' }
try {
    $r = Invoke-RestMethod -Uri "$u/rest/v1/staging_vault" -Method Post -Headers $headers -Body ($payload | ConvertTo-Json -Depth 5) -ContentType 'application/json' -TimeoutSec 30
    Write-Output "OK: $($r | ConvertTo-Json -Depth 5)"
} catch {
    Write-Output "ERROR: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        try { $text = $_.Exception.Response.GetResponseStream() | %{ (New-Object System.IO.StreamReader($_)).ReadToEnd() }; Write-Output "RESPONSE_BODY: $text" } catch { }
    }
}
