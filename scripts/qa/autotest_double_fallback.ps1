# Autotest: double-fallback simulation (no Redis, no local LLM)
# Usage: powershell -NoProfile -File .\scripts\qa\autotest_double_fallback.ps1

$projectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $projectRoot

$envFile = Join-Path $projectRoot '.env'
$envLines = Get-Content $envFile
$kLine = $envLines | Where-Object { $_ -match '^SUPABASE_SECRET_KEY=' } | Select-Object -First 1
if (-not $kLine) { Write-Error "SUPABASE_SECRET_KEY not found in .env"; exit 1 }
$k = $kLine -replace '^SUPABASE_SECRET_KEY=',''

$u = 'https://cdgcmcznmqykmzyovnmn.supabase.co'
$headers = @{ 'apikey' = $k; 'Authorization' = "Bearer $k"; 'Prefer' = 'return=representation' }

# 1) Insert staging row
$st = @{
    patient_id = 'PT-LIFECYCLE-MASTER-01'
    raw_payload = @{ text = 'Patient presents with high blood pressure. Prescribed Lisinopril 10mg daily.' }
    fallback_reason = 'redis_unavailable'
    status = 'pending'
}
$body = $st | ConvertTo-Json -Depth 10
$r = Invoke-RestMethod -Uri "$u/rest/v1/staging_vault" -Method Post -Headers $headers -Body $body -ContentType 'application/json' -TimeoutSec 30
Write-Output "STAGING_INSERTED:$($r[0].id)"
$id = $r[0].id

# 2) Patch as processed (simulate worker + cloud LLM result)
$processed = @{
    fhir_json = @{ resourceType = 'Bundle'; entry = @( @{ resource = @{ resourceType = 'AllergyIntolerance'; note = @( @{ text = 'Patient allergic to ACE inhibitors; Lisinopril conflict detected.' } ) } } ) }
    conflict_flag = $true
    ai_warning_msg = 'CONFLICT DETECTED: Patient is allergic to ACE Inhibitors (Lisinopril). Prior prescription found in medical history.'
    model = 'groq'
    status = 'processed'
}
$body2 = $processed | ConvertTo-Json -Depth 10
$r2 = Invoke-RestMethod -Uri "$u/rest/v1/staging_vault?id=eq.$id" -Method Patch -Headers $headers -Body $body2 -ContentType 'application/json' -TimeoutSec 30
Write-Output "STAGING_UPDATED:$($r2[0].id):$($r2[0].status)"

# 3) Add main_vault entry (simulate admin commit)
$vault_id = [guid]::NewGuid().ToString()
$postMain = @{ patient_id = 'PT-LIFECYCLE-MASTER-01'; encrypted_fhir_json_id = $vault_id }
$r3 = Invoke-RestMethod -Uri "$u/rest/v1/main_vault" -Method Post -Headers $headers -Body ($postMain | ConvertTo-Json -Depth 5) -ContentType 'application/json' -TimeoutSec 30
Write-Output "MAIN_INSERTED:$($r3[0].id):enc_id=$vault_id"

# 4) Delete staging row
Invoke-RestMethod -Uri "$u/rest/v1/staging_vault?id=eq.$id" -Method Delete -Headers $headers -TimeoutSec 30
Write-Output "STAGING_DELETED:$id"

# 5) Insert audit log
$tx = [guid]::NewGuid().ToString()
$audit = @{
    tx_id = $tx
    staging_id = $id
    admin_id = 'qa-automation'
    patient_id = 'PT-LIFECYCLE-MASTER-01'
    action_type = 'approve'
    old_value = $null
    new_value = $processed.fhir_json
    reason = 'Auto-approve for test: Lisinopril conflict handled'
}
$r4 = Invoke-RestMethod -Uri "$u/rest/v1/audit_logs" -Method Post -Headers $headers -Body ($audit | ConvertTo-Json -Depth 10) -ContentType 'application/json' -TimeoutSec 30
Write-Output "AUDIT_INSERTED:$($r4[0].id):tx=$tx"

# 6) Verify inserts
$verifyMain = Invoke-RestMethod -Uri "$u/rest/v1/main_vault?patient_id=eq.PT-LIFECYCLE-MASTER-01&select=id,encrypted_fhir_json_id" -Method Get -Headers @{ 'apikey' = $k; 'Authorization' = "Bearer $k" } -TimeoutSec 30
Write-Output "MAIN_ROWS:$($verifyMain | ConvertTo-Json -Depth 5)"
$verifyAudit = Invoke-RestMethod -Uri "$u/rest/v1/audit_logs?tx_id=eq.$tx&select=id,tx_id,created_at,reason" -Method Get -Headers @{ 'apikey' = $k; 'Authorization' = "Bearer $k" } -TimeoutSec 30
Write-Output "AUDIT_ROWS:$($verifyAudit | ConvertTo-Json -Depth 5)"
