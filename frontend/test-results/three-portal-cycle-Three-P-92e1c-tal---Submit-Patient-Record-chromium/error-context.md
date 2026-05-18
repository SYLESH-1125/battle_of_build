# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: three-portal-cycle.spec.ts >> Three-Portal Stitching Cycle >> 1. Doctor Portal - Submit Patient Record
- Location: MP_battle_of_build\memory-vault-mono\frontend\e2e\three-portal-cycle.spec.ts:12:7

# Error details

```
Error: locator.fill: Test ended.
Call log:
  - waiting for locator('input[placeholder*="PT-"]').first()

```

# Test source

```ts
  1   | import { test, expect, Page, Browser, BrowserContext } from "@playwright/test";
  2   | 
  3   | const BASE_URL = "http://localhost:3000";
  4   | 
  5   | let page: Page;
  6   | 
  7   | test.describe("Three-Portal Stitching Cycle", () => {
  8   |   test.beforeAll(async ({ browser }) => {
  9   |     // Global setup if needed
  10  |   });
  11  | 
  12  |   test("1. Doctor Portal - Submit Patient Record", async ({ page: testPage }) => {
  13  |     page = testPage;
  14  |     
  15  |     console.log("🏥 [TEST] Navigating to Doctor Dashboard...");
  16  |     await page.goto(`${BASE_URL}/dashboard`);
  17  |     await page.waitForLoadState("networkidle");
  18  | 
  19  |     // Fill in patient info
  20  |     const patientInput = page.locator('input[placeholder*="PT-"]').first();
> 21  |     await patientInput.fill("PT-UI-STITCH-99");
      |                        ^ Error: locator.fill: Test ended.
  22  | 
  23  |     // Fill in raw text (clinical note)
  24  |     const textInput = page.locator("textarea").first();
  25  |     await textInput.fill(
  26  |       "Patient presents with hypertension. BP 160/100. Prescribed Lisinopril 10mg daily."
  27  |     );
  28  | 
  29  |     // Submit
  30  |     const submitButton = page.locator("button").filter({ hasText: /Submit|Ingest/i });
  31  |     await submitButton.click();
  32  | 
  33  |     console.log("⏳ Waiting for submission confirmation...");
  34  |     await page.waitForTimeout(2000);
  35  | 
  36  |     console.log("✅ Record submitted for PT-UI-STITCH-99");
  37  |   });
  38  | 
  39  |   test("2. Worker Processing - Wait for Background Job", async ({ page: testPage }) => {
  40  |     page = testPage;
  41  |     
  42  |     console.log("🔄 [TEST] Waiting 15 seconds for background worker to process...");
  43  |     await page.waitForTimeout(15000);
  44  |     console.log("✅ Worker should have processed the record");
  45  |   });
  46  | 
  47  |   test("3. Admin Portal - Verify Record in Queue", async ({ page: testPage }) => {
  48  |     page = testPage;
  49  |     
  50  |     console.log("🏛️ [TEST] Navigating to Admin Dashboard...");
  51  |     await page.goto(`${BASE_URL}/admin`);
  52  |     await page.waitForLoadState("networkidle");
  53  | 
  54  |     // Wait for queue to load
  55  |     await page.waitForTimeout(2000);
  56  | 
  57  |     // Look for PT-UI-STITCH-99 in the sidebar
  58  |     const patientCard = page.locator("button").filter({ hasText: "PT-UI-STITCH-99" });
  59  |     await expect(patientCard).toBeVisible({ timeout: 10000 });
  60  | 
  61  |     console.log("✅ PT-UI-STITCH-99 found in admin queue");
  62  | 
  63  |     // Click to select
  64  |     await patientCard.click();
  65  |     await page.waitForTimeout(1000);
  66  | 
  67  |     // Verify comparison view is shown
  68  |     const comparisonHeader = page.locator("text=Before/After Clinical Data");
  69  |     await expect(comparisonHeader).toBeVisible();
  70  | 
  71  |     console.log("✅ Before/After comparison view displayed");
  72  | 
  73  |     // Click Approve button
  74  |     const approveButton = page.locator("button").filter({ hasText: /Approve/i });
  75  |     await approveButton.click();
  76  | 
  77  |     console.log("⏳ Waiting for approval processing...");
  78  |     await page.waitForTimeout(3000);
  79  | 
  80  |     console.log("✅ Record approved and committed");
  81  |   });
  82  | 
  83  |   test("4. Patient Portal - Generate QR Code", async ({ page: testPage }) => {
  84  |     page = testPage;
  85  |     
  86  |     console.log("🔐 [TEST] Navigating to Patient Portal...");
  87  |     await page.goto(`${BASE_URL}/patient`);
  88  |     await page.waitForLoadState("networkidle");
  89  | 
  90  |     // Fill in patient ID
  91  |     const patientInput = page.locator('input[placeholder*="PT-"]');
  92  |     await patientInput.fill("PT-UI-STITCH-99");
  93  | 
  94  |     // Click Access Vault
  95  |     const accessButton = page.locator("button").filter({ hasText: /Access Vault/i });
  96  |     await accessButton.click();
  97  | 
  98  |     console.log("⏳ Searching for patient vault...");
  99  |     await page.waitForTimeout(3000);
  100 | 
  101 |     // Verify vault status message
  102 |     const vaultStatus = page.locator("text=Vault Cryptographically Sealed");
  103 |     await expect(vaultStatus).toBeVisible({ timeout: 10000 });
  104 | 
  105 |     console.log("✅ Vault found and status displayed");
  106 | 
  107 |     // Verify QR code is rendered (canvas element)
  108 |     const qrCanvas = page.locator("canvas").first();
  109 |     await expect(qrCanvas).toBeVisible();
  110 | 
  111 |     console.log("✅ QR code successfully rendered");
  112 | 
  113 |     // Verify download button exists
  114 |     const downloadButton = page.locator("button").filter({ hasText: /Download QR/i });
  115 |     await expect(downloadButton).toBeVisible();
  116 | 
  117 |     console.log("✅ QR code download button available");
  118 |   });
  119 | 
  120 |   test("5. Verify Audit Trail", async ({ page: testPage }) => {
  121 |     page = testPage;
```