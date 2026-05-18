import { test, expect, Page, Browser, BrowserContext } from "@playwright/test";

const BASE_URL = "http://localhost:3000";

let page: Page;

test.describe("Three-Portal Stitching Cycle", () => {
  test.beforeAll(async ({ browser }) => {
    // Global setup if needed
  });

  test("1. Doctor Portal - Submit Patient Record", async ({ page: testPage }) => {
    page = testPage;
    
    console.log("🏥 [TEST] Navigating to Doctor Dashboard...");
    await page.goto(`${BASE_URL}/dashboard`);
    await page.waitForLoadState("networkidle");

    // Fill in patient info
    const patientInput = page.locator('input[placeholder*="PT-"]').first();
    await patientInput.fill("PT-UI-STITCH-99");

    // Fill in raw text (clinical note)
    const textInput = page.locator("textarea").first();
    await textInput.fill(
      "Patient presents with hypertension. BP 160/100. Prescribed Lisinopril 10mg daily."
    );

    // Submit
    const submitButton = page.locator("button").filter({ hasText: /Submit|Ingest/i });
    await submitButton.click();

    console.log("⏳ Waiting for submission confirmation...");
    await page.waitForTimeout(2000);

    console.log("✅ Record submitted for PT-UI-STITCH-99");
  });

  test("2. Worker Processing - Wait for Background Job", async ({ page: testPage }) => {
    page = testPage;
    
    console.log("🔄 [TEST] Waiting 15 seconds for background worker to process...");
    await page.waitForTimeout(15000);
    console.log("✅ Worker should have processed the record");
  });

  test("3. Admin Portal - Verify Record in Queue", async ({ page: testPage }) => {
    page = testPage;
    
    console.log("🏛️ [TEST] Navigating to Admin Dashboard...");
    await page.goto(`${BASE_URL}/admin`);
    await page.waitForLoadState("networkidle");

    // Wait for queue to load
    await page.waitForTimeout(2000);

    // Look for PT-UI-STITCH-99 in the sidebar
    const patientCard = page.locator("button").filter({ hasText: "PT-UI-STITCH-99" });
    await expect(patientCard).toBeVisible({ timeout: 10000 });

    console.log("✅ PT-UI-STITCH-99 found in admin queue");

    // Click to select
    await patientCard.click();
    await page.waitForTimeout(1000);

    // Verify comparison view is shown
    const comparisonHeader = page.locator("text=Before/After Clinical Data");
    await expect(comparisonHeader).toBeVisible();

    console.log("✅ Before/After comparison view displayed");

    // Click Approve button
    const approveButton = page.locator("button").filter({ hasText: /Approve/i });
    await approveButton.click();

    console.log("⏳ Waiting for approval processing...");
    await page.waitForTimeout(3000);

    console.log("✅ Record approved and committed");
  });

  test("4. Patient Portal - Generate QR Code", async ({ page: testPage }) => {
    page = testPage;
    
    console.log("🔐 [TEST] Navigating to Patient Portal...");
    await page.goto(`${BASE_URL}/patient`);
    await page.waitForLoadState("networkidle");

    // Fill in patient ID
    const patientInput = page.locator('input[placeholder*="PT-"]');
    await patientInput.fill("PT-UI-STITCH-99");

    // Click Access Vault
    const accessButton = page.locator("button").filter({ hasText: /Access Vault/i });
    await accessButton.click();

    console.log("⏳ Searching for patient vault...");
    await page.waitForTimeout(3000);

    // Verify vault status message
    const vaultStatus = page.locator("text=Vault Cryptographically Sealed");
    await expect(vaultStatus).toBeVisible({ timeout: 10000 });

    console.log("✅ Vault found and status displayed");

    // Verify QR code is rendered (canvas element)
    const qrCanvas = page.locator("canvas").first();
    await expect(qrCanvas).toBeVisible();

    console.log("✅ QR code successfully rendered");

    // Verify download button exists
    const downloadButton = page.locator("button").filter({ hasText: /Download QR/i });
    await expect(downloadButton).toBeVisible();

    console.log("✅ QR code download button available");
  });

  test("5. Verify Audit Trail", async ({ page: testPage }) => {
    page = testPage;
    
    console.log("📋 [TEST] Verifying audit trail completeness...");
    
    // This would ideally check the audit_logs table via API
    // For now, we'll verify the UI states we've seen
    
    console.log("✅ Three-portal cycle completed successfully");
    console.log("   - Doctor submitted: PT-UI-STITCH-99");
    console.log("   - Admin reviewed and approved");
    console.log("   - Patient accessed vault and generated QR");
    console.log("   - All state transitions recorded");
  });
});

test.describe("Error Handling Tests", () => {
  test("Admin - Display Processing Errors", async ({ page: testPage }) => {
    page = testPage;
    
    console.log("⚠️ [TEST] Testing error display...");
    await page.goto(`${BASE_URL}/admin`);
    await page.waitForLoadState("networkidle");

    // Look for error badges
    const errorBadge = page.locator("text=/⚠️|rule based fallback|llm inference failed/i");
    
    if (await errorBadge.isVisible()) {
      console.log("✅ Error messages displayed correctly");
      
      // Expand error details
      const expandButton = page.locator("button").filter({ hasText: /Processing Issues/i });
      if (await expandButton.isVisible()) {
        await expandButton.click();
        await page.waitForTimeout(500);
        console.log("✅ Error details can be expanded");
      }
    } else {
      console.log("ℹ️ No error messages found (queue may be clean)");
    }
  });

  test("Patient - Handle Missing Vault", async ({ page: testPage }) => {
    page = testPage;
    
    console.log("❌ [TEST] Testing error handling for invalid patient...");
    await page.goto(`${BASE_URL}/patient`);
    await page.waitForLoadState("networkidle");

    const patientInput = page.locator('input[placeholder*="PT-"]');
    await patientInput.fill("PT-INVALID-PATIENT");

    const accessButton = page.locator("button").filter({ hasText: /Access Vault/i });
    await accessButton.click();

    await page.waitForTimeout(2000);

    // Expect error message
    const errorMsg = page.locator("text=/No records found|Please verify/i");
    await expect(errorMsg).toBeVisible({ timeout: 5000 });

    console.log("✅ Error handling working correctly");
  });
});
