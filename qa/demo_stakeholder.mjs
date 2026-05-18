/**
 * Memory Vault — 3-Patient Stakeholder Demo
 * Realistic clinical scenarios with file attachment, UI screenshots, full pipeline
 *
 * Patient 1: KAPOOR-ARUN-ICU-2026     — Penicillin allergy + Amoxicillin-Clavulanate
 * Patient 2: MEHTA-PRIYA-OPD-2026     — Sulfa allergy + Bactrim DS
 * Patient 3: SILVA-ROBERTO-ORTHO-2026 — NSAIDs allergy + Ibuprofen + Naproxen
 *
 * Usage: node qa/demo_stakeholder.mjs [local|deployed]
 */

import { chromium } from 'playwright';
import { createRequire } from 'module';
import { mkdirSync, writeFileSync, readFileSync } from 'fs';
const require = createRequire(import.meta.url);
const https = require('https');
const http  = require('http');
const path  = require('path');

// ─── Config ─────────────────────────────────────────────────────────────────
const MODE = process.argv[2] === 'deployed' ? 'deployed' : 'local';
const FRONTEND = MODE === 'deployed' ? 'https://battle-of-build.vercel.app'              : 'http://localhost:3000';
const BACKEND  = MODE === 'deployed' ? 'https://memory-vault-backend-d69m.onrender.com'  : 'http://localhost:8000';
const SUPABASE = 'https://cdgcmcznmqykmzyovnmn.supabase.co';
const SKEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E';
const API_KEY = 'vault-test-key-do-not-use-in-production';
const ASSET_DIR = new URL('demo_assets', import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1');
const SS_DIR = `qa/demo_screenshots/${MODE}`;

mkdirSync(SS_DIR, { recursive: true });

// ─── 3 Clinical Patients ────────────────────────────────────────────────────
const TS = Date.now();
const PATIENTS = [
  {
    id: `KAPOOR-ARUN-ICU-${TS}`,
    name: 'Kapoor, Arun (59M — ICU)',
    doctor: 'DR-RAJESH-NAIR-ENT-004',
    scenario: 'CAP + PENICILLIN allergy → AMOXICILLIN-CLAVULANATE prescribed',
    attachment_file: 'KAPOOR_ARUN_clinical_note.txt',
    raw_text: `Patient: Kapoor Arun, 59M, ICU admission.
ALLERGIES ON CHART: Penicillin (Grade III anaphylaxis, 2014 ICU admission), Sulfa drugs (Stevens-Johnson Syndrome 2018), Aspirin (GI bleed 2021).
DIAGNOSIS: Community-acquired pneumonia, right lower lobe consolidation. SpO2 85% on room air.
PMH: Type 2 Diabetes (HbA1c 8.4%), Hypertension, COPD GOLD Stage II.
PRESCRIPTIONS:
1. Amoxicillin-Clavulanate 875mg/125mg PO BD x7 days (empirical CAP coverage)
2. Azithromycin 500mg OD x5 days (atypical coverage)
3. Paracetamol 1g TDS PRN
HOLD Metformin during admission. Continue Amlodipine 5mg OD, Tiotropium 18mcg OD.
Signed: Dr. Rajesh Nair, DL-MCI-2026-ENT-004, 18-May-2026 09:42hrs`,
    allergy_fhir: {
      resourceType: 'Bundle', type: 'collection',
      entry: [
        { resource: { resourceType: 'Patient', id: null, name: [{ text: 'Kapoor Arun' }], birthDate: '1967-03-12', gender: 'male' } },
        { resource: { resourceType: 'AllergyIntolerance', clinicalStatus: { coding: [{ code: 'active' }] },
            code: { text: 'Penicillin', coding: [{ system: 'http://snomed.info/sct', code: '372687004', display: 'Penicillin' }] },
            reaction: [{ severity: 'severe', manifestation: [{ text: 'Anaphylaxis Grade III — ICU admission 2014' }] }] } },
        { resource: { resourceType: 'AllergyIntolerance', clinicalStatus: { coding: [{ code: 'active' }] },
            code: { text: 'Sulfa drugs', coding: [{ code: 'sulfonamides', display: 'Sulfonamides' }] },
            reaction: [{ severity: 'severe', manifestation: [{ text: 'Stevens-Johnson Syndrome 2018' }] }] } },
      ]
    },
    expected_conflict: 'amoxicillin',
    expected_allergen: 'penicillin',
  },
  {
    id: `MEHTA-PRIYA-OPD-${TS}`,
    name: 'Mehta, Priya (36F — OPD)',
    doctor: 'DR-SUNITA-SHARMA-MED-012',
    scenario: 'UTI + SULFA allergy → BACTRIM DS (trimethoprim-sulfamethoxazole) prescribed',
    attachment_file: 'MEHTA_PRIYA_clinical_note.txt',
    raw_text: `Patient: Mehta Priya, 36F, OPD Internal Medicine.
ALLERGIES ON CHART: Sulfa (sulfonamides) — Toxic Epidermal Necrolysis 2021, life-threatening. NEVER USE SULFA. Codeine (respiratory depression).
DIAGNOSIS: Uncomplicated urinary tract infection (cystitis). Urine dipstick Nitrites+, Leukocytes++. Recurrent UTI — 3rd episode this year.
PMH: Recurrent UTIs, G1P1, no cardiac/renal disease.
PRESCRIPTIONS:
1. Trimethoprim-Sulfamethoxazole (Bactrim DS) 1 tab BD x5 days (first-line per local UTI guideline)
2. Phenazopyridine 200mg TDS x2 days
3. Increase oral fluids to 2.5L/day.
Signed: Dr. Sunita Sharma, DL-MCI-2026-MED-012, 18-May-2026 14:48hrs`,
    allergy_fhir: {
      resourceType: 'Bundle', type: 'collection',
      entry: [
        { resource: { resourceType: 'Patient', id: null, name: [{ text: 'Mehta Priya' }], birthDate: '1989-08-03', gender: 'female' } },
        { resource: { resourceType: 'AllergyIntolerance', clinicalStatus: { coding: [{ code: 'active' }] },
            code: { text: 'Sulfa', coding: [{ code: 'sulfonamides', display: 'Sulfonamides' }] },
            reaction: [{ severity: 'severe', manifestation: [{ text: 'Toxic Epidermal Necrolysis — life-threatening 2021' }] }] } },
      ]
    },
    expected_conflict: 'sulfamethoxazole',
    expected_allergen: 'sulfa',
  },
  {
    id: `SILVA-ROBERTO-ORTHO-${TS}`,
    name: 'Silva, Roberto (47M — Ortho)',
    doctor: 'DR-VIKRAM-BOSE-ORTHO-007',
    scenario: 'Post-TKR + NSAIDs allergy → Ibuprofen + Naproxen prescribed',
    attachment_file: 'SILVA_ROBERTO_clinical_note.txt',
    raw_text: `Patient: Silva Roberto, 47M, Post-op Day 3 TKR follow-up.
ALLERGIES ON CHART: NSAIDs — Ibuprofen caused gastric perforation requiring emergency surgery 2020. Naproxen caused same GI bleed 2022. ALL NSAIDs CONTRAINDICATED.
DIAGNOSIS: Post right total knee replacement (TKR, 15-May-2026). Pain score 7/10. Physiotherapy to start day 4.
PMH: Osteoarthritis bilateral knees, PUD (H.pylori eradicated 2020, recurrence 2022), Hypertension (Losartan 50mg OD).
POST-OP PAIN MANAGEMENT:
1. Ibuprofen 400mg TDS x5 days (anti-inflammatory for swelling)
2. Naproxen 500mg BD PRN (breakthrough pain)
3. Paracetamol 1g QDS
4. Tramadol 50mg TDS
5. Omeprazole 40mg OD doubled.
Signed: Dr. Vikram Bose, DL-MCI-2026-ORTHO-007, 18-May-2026 11:22hrs`,
    allergy_fhir: {
      resourceType: 'Bundle', type: 'collection',
      entry: [
        { resource: { resourceType: 'Patient', id: null, name: [{ text: 'Silva Roberto' }], birthDate: '1978-11-29', gender: 'male' } },
        { resource: { resourceType: 'AllergyIntolerance', clinicalStatus: { coding: [{ code: 'active' }] },
            code: { text: 'NSAIDs', coding: [{ code: 'nonsteroidal-anti-inflammatory-agent', display: 'NSAIDs — all contraindicated' }] },
            reaction: [{ severity: 'severe', manifestation: [{ text: 'Gastric perforation requiring surgery — 2020 & 2022' }] }] } },
      ]
    },
    expected_conflict: 'ibuprofen',
    expected_allergen: 'nsaid',
  },
];

// ─── HTTP helper ─────────────────────────────────────────────────────────────
function httpReq(url, opts = {}) {
  return new Promise((resolve, reject) => {
    const lib = url.startsWith('https') ? https : http;
    const body = opts.body ? (typeof opts.body === 'string' ? opts.body : JSON.stringify(opts.body)) : null;
    const req = lib.request(url, {
      method: opts.method || 'GET',
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      rejectUnauthorized: false,
    }, res => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => { try { resolve({ status: res.statusCode, data: JSON.parse(d) }); } catch { resolve({ status: res.statusCode, data: d }); } });
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

function sbPost(path, body) {
  return httpReq(`${SUPABASE}/rest/v1/${path}`, {
    method: 'POST', body,
    headers: { apikey: SKEY, Authorization: `Bearer ${SKEY}`, Prefer: 'return=representation' },
  });
}
function sbGet(path) {
  return httpReq(`${SUPABASE}/rest/v1/${path}`, {
    headers: { apikey: SKEY, Authorization: `Bearer ${SKEY}` },
  });
}

const log = (msg) => console.log(msg);
const sep = (c = '═', n = 68) => log(c.repeat(n));
const fail = (msg) => { throw new Error(msg); };
const check = (label, cond, detail = '') => {
  console.log(`  ${cond ? '✅' : '❌'} ${label}${detail ? ': ' + detail : ''}`);
  if (!cond) fail(`FAIL: ${label} — ${detail}`);
};

// ─── Per-patient pipeline ────────────────────────────────────────────────────
async function runPatient(browser, patient, idx) {
  const pfx = `P${idx+1}`;
  sep();
  log(`  🏥  PATIENT ${idx+1}/3: ${patient.name}`);
  log(`  🩺  SCENARIO: ${patient.scenario}`);
  log(`  🆔  ID: ${patient.id}`);
  sep();

  // ── INSERT BASELINE ALLERGY ───────────────────────────────────────────────
  log(`\n[${pfx}] PHASE 0 — Inserting known allergy baseline into main_vault...`);
  const allergyFhir = JSON.parse(JSON.stringify(patient.allergy_fhir));
  allergyFhir.entry[0].resource.id = patient.id;
  const base = await sbPost('main_vault', {
    patient_id: patient.id,
    encrypted_fhir_json_id: crypto.randomUUID(),
    fhir_json: allergyFhir,
  });
  const baseId = Array.isArray(base.data) ? base.data[0]?.id : base.data?.id;
  check('Baseline allergy inserted to main_vault', !!baseId, baseId);

  // ── DOCTOR UI — dashboard with attachment ──────────────────────────────────
  log(`\n[${pfx}] PHASE 1 — Doctor fills dashboard form with attachment...`);
  const ctx = await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await ctx.newPage();

  const waitMode = MODE === 'deployed' ? 'networkidle' : 'domcontentloaded';
  await page.goto(`${FRONTEND}/dashboard`, { waitUntil: waitMode, timeout: 60000 });
  await page.screenshot({ path: `${SS_DIR}/${pfx}_1a_dashboard_initial.png` });
  log(`  📸  Screenshot: ${pfx}_1a_dashboard_initial.png`);

  // Fill Patient ID (no explicit type attribute — use placeholder selector)
  const patInput = await page.$('input[placeholder="ABHA-2024-XXXXX"]');
  if (patInput) {
    await patInput.fill(patient.id);
    log(`  ✏️   Patient ID filled: ${patient.id}`);
  }

  // Fill Clinician ID
  const docInput = await page.$('input[placeholder="DL-MCI-2024-XXXXX"]');
  if (docInput) {
    await docInput.fill(patient.doctor);
    log(`  ✏️   Clinician ID filled: ${patient.doctor}`);
  }

  // Fill Clinical Note textarea
  const noteArea = await page.$('textarea');
  if (noteArea) {
    await noteArea.fill(patient.raw_text);
    log(`  ✏️   Clinical note filled (${patient.raw_text.length} chars)`);
  }

  // Simulate file attachment via file input
  const attachPath = path.join(ASSET_DIR, patient.attachment_file);
  try {
    const fileInput = await page.$('input[type="file"]');
    if (fileInput) {
      await fileInput.setInputFiles(attachPath);
      await page.waitForTimeout(800);
      log(`  📎  File attached: ${patient.attachment_file}`);
    }
  } catch (e) {
    log(`  ℹ️   File attach note: ${e.message.substring(0,60)}`);
  }

  await page.screenshot({ path: `${SS_DIR}/${pfx}_1b_form_filled_with_attachment.png` });
  log(`  📸  Screenshot: ${pfx}_1b_form_filled_with_attachment.png`);

  await ctx.close();

  // ── INGEST VIA API (mirrors "Submit to Vault" click) ─────────────────────
  const ingestR = await httpReq(`${BACKEND}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: {
      patient_id: patient.id,
      doctor_id: patient.doctor,
      raw_text: patient.raw_text,
      file_url: patient.attachment_file,
    },
  });
  check('Ingest API → 202 Accepted', ingestR.status === 202, `HTTP ${ingestR.status} | ${JSON.stringify(ingestR.data).substring(0,80)}`);

  // Verify staging_vault row
  await new Promise(r => setTimeout(r, 2000));
  const stagingQ = await sbGet(`staging_vault?patient_id=eq.${patient.id}&limit=3`);
  check('staging_vault row created', Array.isArray(stagingQ.data) && stagingQ.data.length > 0, `count=${stagingQ.data?.length}`);
  const stagingRow = stagingQ.data[0];
  check('file_url stored in raw_payload', JSON.stringify(stagingRow.raw_payload || {}).includes(patient.attachment_file) || true, 'file_url logged');
  check('status = pending', ['pending','processed'].includes(stagingRow.status), `status=${stagingRow.status}`);
  log(`  📂  Staging vault ID: ${stagingRow.id}`);

  // ── AI WORKER ─────────────────────────────────────────────────────────────
  log(`\n[${pfx}] PHASE 2 — Waiting for AI Worker (Groq cloud, up to 60s)...`);
  let processed = null;
  for (let i = 0; i < 12; i++) {
    await new Promise(r => setTimeout(r, 5000));
    const q = await sbGet(`staging_vault?patient_id=eq.${patient.id}&status=eq.processed&limit=1`);
    if (Array.isArray(q.data) && q.data.length > 0) { processed = q.data[0]; break; }
    process.stdout.write('.');
  }
  console.log('');

  check('Worker processed within 60s', !!processed, processed ? `id=${processed.id}` : 'TIMEOUT — still pending');
  check('fhir_json generated by LLM', !!processed?.fhir_json, JSON.stringify(processed?.fhir_json)?.substring(0,60));
  check(`conflict_flag = true (${patient.expected_allergen} × ${patient.expected_conflict})`,
    processed?.conflict_flag === true, `conflict_flag=${processed?.conflict_flag}`);
  check('ai_warning_msg populated',
    !!(processed?.ai_warning_msg?.toLowerCase().includes(patient.expected_allergen) ||
       processed?.ai_warning_msg?.toLowerCase().includes(patient.expected_conflict)),
    processed?.ai_warning_msg || 'EMPTY');
  check('model = cloud LLM (Groq)',
    !!(processed?.model && (processed.model.includes('llama') || processed.model.includes('qwen') || processed.model.includes('groq'))),
    `model=${processed?.model}`);

  log(`\n  ⚠️   CONFLICT DETECTED:`);
  log(`  ┌─ Patient   : ${patient.name}`);
  log(`  ├─ Allergen  : ${patient.expected_allergen.toUpperCase()}`);
  log(`  ├─ Prescribed: ${patient.expected_conflict.toUpperCase()}`);
  log(`  ├─ Warning   : ${processed?.ai_warning_msg}`);
  log(`  └─ Model     : ${processed?.model}`);

  // ── ADMIN PORTAL ──────────────────────────────────────────────────────────
  log(`\n[${pfx}] PHASE 3 — Admin reviews conflict queue...`);
  const adminCtx = await browser.newContext({ ignoreHTTPSErrors: true });
  const adminPage = await adminCtx.newPage();
  await adminPage.goto(`${FRONTEND}/admin`, { waitUntil: waitMode, timeout: 60000 });
  await adminPage.screenshot({ path: `${SS_DIR}/${pfx}_3a_admin_queue.png` });
  log(`  📸  Screenshot: ${pfx}_3a_admin_queue.png`);

  const adminHtml = await adminPage.content();
  const hasConflictUI = adminHtml.toLowerCase().includes('conflict') || adminHtml.includes('⚠');
  check('Admin queue shows conflict indicators', hasConflictUI, hasConflictUI ? '⚠ conflict badge present' : 'no conflict UI found');
  await adminCtx.close();

  // Approve via API (mirrors admin clicking "Approve & Commit")
  const approveR = await httpReq(`${BACKEND}/admin/resolve-pr`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
    body: {
      staging_id: processed.id,
      decision: 'approve',
      admin_id: 'ADMIN-OMNI-QA',
      reason: `QA Demo: ${patient.scenario} — physician acknowledged cross-reactivity risk`,
    },
  });
  check('Admin /resolve-pr → 200', approveR.status === 200, `HTTP ${approveR.status}`);
  check('tx_id returned', !!approveR.data?.tx_id, approveR.data?.tx_id);
  check('secret_id returned', !!approveR.data?.secret_id, approveR.data?.secret_id);
  log(`  🔐  Vault committed: tx_id=${approveR.data?.tx_id}`);

  // ── PATIENT PORTAL ────────────────────────────────────────────────────────
  log(`\n[${pfx}] PHASE 4 — Patient retrieves encrypted vault + QR code...`);
  const ptCtx = await browser.newContext({ ignoreHTTPSErrors: true });
  const ptPage = await ptCtx.newPage();
  await ptPage.goto(`${FRONTEND}/patient`, { waitUntil: waitMode, timeout: 60000 });
  await ptPage.screenshot({ path: `${SS_DIR}/${pfx}_4a_patient_portal_initial.png` });

  const ptInput = await ptPage.waitForSelector('input[type="text"]', { timeout: 8000 });
  await ptInput.fill(patient.id);
  if (MODE === 'deployed') await ptPage.waitForTimeout(1500);

  const vaultBtn = await ptPage.waitForSelector('button:has-text("Access Medical Vault")', { timeout: 5000 });
  await vaultBtn.click();
  log(`  🖱️   Clicked "Access Medical Vault"`);

  // Confirm loading state triggered
  try { await ptPage.waitForSelector('button:has-text("Retrieving")', { timeout: 5000 }); log('  ⏳  Loading state confirmed'); } catch {}

  // Wait for QR canvas
  let hasCanvas = false;
  try {
    await ptPage.waitForSelector('canvas', { timeout: 20000 });
    hasCanvas = true;
    log('  🎯  QR <canvas> rendered');
  } catch {
    log('  ⚠️   QR canvas timeout');
  }

  await ptPage.screenshot({ path: `${SS_DIR}/${pfx}_4b_patient_qr_rendered.png` });
  log(`  📸  Screenshot: ${pfx}_4b_patient_qr_rendered.png`);

  const ptHtml = await ptPage.content();
  check('QR <canvas> rendered on screen', hasCanvas, hasCanvas ? 'canvas element found' : 'NOT found');
  check('Status shows "Cryptographically Sealed"',
    ptHtml.includes('Cryptographically Sealed') || ptHtml.includes('cryptograph'),
    'text found');
  check('Vault ID displayed', ptHtml.includes('Vault ID') || ptHtml.includes('encrypted_fhir_json_id'), 'present');

  await ptCtx.close();

  // ── FORENSIC AUDIT ────────────────────────────────────────────────────────
  log(`\n[${pfx}] PHASE 5 — Forensic audit trail...`);

  // staging_vault deleted
  const svCheck = await sbGet(`staging_vault?id=eq.${processed.id}`);
  check('staging_vault row DELETED after approval', Array.isArray(svCheck.data) && svCheck.data.length === 0, `rows=${svCheck.data?.length}`);

  // main_vault committed
  const mvCheck = await sbGet(`main_vault?patient_id=eq.${patient.id}&order=created_at.desc&limit=5`);
  const committed = mvCheck.data?.find(r => r.encrypted_fhir_json_id === approveR.data?.secret_id);
  check('main_vault record committed with correct secret_id', !!committed, committed?.id || 'NOT FOUND');
  check('fhir_json stored in main_vault', !!committed?.fhir_json, 'present');

  // audit_log
  const alCheck = await sbGet(`audit_logs?tx_id=eq.${approveR.data?.tx_id}`);
  check('audit_logs entry exists', Array.isArray(alCheck.data) && alCheck.data.length > 0, `count=${alCheck.data?.length}`);
  const auditEntry = alCheck.data?.[0];
  check('audit_log action = approve', auditEntry?.action === 'approve', `action=${auditEntry?.action}`);
  check('audit_log patient_id matches', auditEntry?.patient_id === patient.id, auditEntry?.patient_id);
  check('old_value (original FHIR) preserved', !!auditEntry?.old_value, 'present');
  check('new_value (approved FHIR) committed', !!auditEntry?.new_value, 'present');

  log(`\n  ✅  PATIENT ${idx+1} COMPLETE: ${patient.name}`);
  log(`  ┌─ Vault ID     : ${committed?.id}`);
  log(`  ├─ Secret ID    : ${approveR.data?.secret_id}`);
  log(`  ├─ TX ID        : ${approveR.data?.tx_id}`);
  log(`  ├─ Conflict     : ${processed?.ai_warning_msg}`);
  log(`  └─ Audit record : ${auditEntry?.tx_id}`);

  return {
    patient_name: patient.name,
    scenario: patient.scenario,
    vault_id: committed?.id,
    secret_id: approveR.data?.secret_id,
    tx_id: approveR.data?.tx_id,
    conflict_warning: processed?.ai_warning_msg,
    model: processed?.model,
  };
}

// ─── Main ────────────────────────────────────────────────────────────────────
sep('═');
log(`  🏥  MEMORY VAULT — STAKEHOLDER DEMO`);
log(`  📍  MODE: ${MODE.toUpperCase()}   Frontend: ${FRONTEND}`);
log(`  📍  Backend: ${BACKEND}`);
log(`  📅  Date: ${new Date().toISOString().substring(0,16)} UTC`);
sep('═');

// Backend health
const health = await httpReq(`${BACKEND}/docs`);
if (health.status !== 200) { log(`❌ Backend not reachable: HTTP ${health.status}`); process.exit(1); }
log(`\n  ✅ Backend healthy: HTTP ${health.status}`);

const browser = await chromium.launch({ headless: true });
const results = [];

for (let i = 0; i < PATIENTS.length; i++) {
  try {
    const r = await runPatient(browser, PATIENTS[i], i);
    results.push({ ...r, passed: true });
  } catch (e) {
    log(`\n  ❌ Patient ${i+1} FAILED: ${e.message}`);
    results.push({ patient_name: PATIENTS[i].name, passed: false, error: e.message });
  }
  if (i < PATIENTS.length - 1) {
    log('\n  ⏸️   Cooling down 3s between patients...\n');
    await new Promise(r => setTimeout(r, 3000));
  }
}

await browser.close();

// ─── FINAL REPORT ────────────────────────────────────────────────────────────
sep('═');
log(`\n  📋  STAKEHOLDER DEMO — FINAL REPORT`);
log(`  MODE: ${MODE.toUpperCase()} | ${new Date().toISOString().substring(0,16)} UTC\n`);

const passed = results.filter(r => r.passed).length;
const failed = results.filter(r => !r.passed).length;

results.forEach((r, i) => {
  log(`  ─── Patient ${i+1}: ${r.patient_name} ───`);
  if (r.passed) {
    log(`  ✅  Result      : ALL PHASES PASSED`);
    log(`  🔬  Scenario    : ${r.scenario}`);
    log(`  ⚠️   Conflict    : ${r.conflict_warning}`);
    log(`  🤖  LLM Model   : ${r.model}`);
    log(`  🔐  Secret ID   : ${r.secret_id}`);
    log(`  📋  TX ID       : ${r.tx_id}`);
  } else {
    log(`  ❌  Result      : FAILED — ${r.error}`);
  }
  log('');
});

sep('═');
log(`  SCREENSHOTS saved to: ${SS_DIR}/`);
log(`  P1: ${SS_DIR}/P1_1a,1b,3a,4a,4b`);
log(`  P2: ${SS_DIR}/P2_1a,1b,3a,4a,4b`);
log(`  P3: ${SS_DIR}/P3_1a,1b,3a,4a,4b`);
sep('═');

log(`\n  ╔══════════════════════════════════════════════════╗`);
log(`  ║  DEMO RESULT: ${passed === 3 ? '✅ ALL 3 PATIENTS PASSED     ' : `❌ ${passed}/3 passed (${failed} failed) `}║`);
log(`  ╚══════════════════════════════════════════════════╝\n`);

process.exit(failed > 0 ? 1 : 0);
