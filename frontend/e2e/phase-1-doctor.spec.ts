import { test, expect, Page } from '@playwright/test';

test('PHASE 1: Doctor submits conflicting Amoxicillin prescription for patient with Penicillin allergy', async ({ page }) => {
  // Navigate to doctor dashboard
  await page.goto('http://localhost:3000/dashboard');
  
  // Wait for page to load
  await page.waitForLoadState('networkidle');
  
  // Find and fill patient ID field (placeholder: ABHA-2024-XXXXX)
  const patientIdInput = page.locator('input[placeholder="ABHA-2024-XXXXX"]');
  await expect(patientIdInput).toBeVisible();
  await patientIdInput.fill('PT-OMNI-MASTER-99');
  
  console.log('✅ Patient ID filled: PT-OMNI-MASTER-99');
  
  // Find and fill clinical note field
  const noteTextarea = page.locator('textarea[placeholder*="Paste triage summary"]');
  await expect(noteTextarea).toBeVisible();
  
  const clinicalNote = `Patient has severe ear infection. Prescribing Amoxicillin (penicillin-type antibiotic). Dosage: 500mg three times daily for 7 days. Patient reports new onset fever (101.2F) and severe otalgia. Tympanic membrane shows signs of infection. Will follow up in 3 days.`;
  
  await noteTextarea.fill(clinicalNote);
  
  console.log('✅ Clinical note filled with conflicting Amoxicillin prescription');
  
  // Find and click submit button (type=submit)
  const submitButton = page.locator('button[type="submit"]');
  await expect(submitButton).toBeVisible();
  
  console.log('📝 Clicking submit button...');
  await submitButton.click();
  
  // Wait for success or confirmation
  await page.waitForLoadState('networkidle');
  
  console.log('✅ PHASE 1 COMPLETE: Doctor submission recorded');
});
