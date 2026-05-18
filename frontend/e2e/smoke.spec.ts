import { test } from '@playwright/test';

test('smoke: capture admin console logs', async ({ page }) => {
  const logs: string[] = [];

  page.on('console', (msg) => {
    const text = msg.text();
    const type = msg.type();
    const entry = `${type}: ${text}`;
    logs.push(entry);
    // also echo to stdout so runner captures them immediately
    console.log(`[playwright-console] ${entry}`);
  });

  page.on('pageerror', (err) => {
    const entry = `pageerror: ${err.message}`;
    logs.push(entry);
    console.log(`[playwright-pageerror] ${entry}`);
  });

  const ports = [3000, 3001];
  let loaded = false;
  for (const port of ports) {
    try {
      await page.goto(`http://localhost:${port}/admin`, { waitUntil: 'networkidle', timeout: 10000 });
      console.log(`PAGE_LOADED:http://localhost:${port}/admin`);
      loaded = true;
      break;
    } catch (e) {
      console.warn(`Failed to load http://localhost:${port}/admin: ${e}`);
    }
  }

  if (!loaded) {
    throw new Error('Unable to load /admin on ports 3000 or 3001');
  }

  // Give client JS a moment to run and emit console logs
  await page.waitForTimeout(3000);

  console.log('CONSOLE_LOGS_START');
  for (const l of logs) console.log(l);
  console.log('CONSOLE_LOGS_END');

  // Save a screenshot for debugging
  await page.screenshot({ path: 'e2e/smoke-admin-screenshot.png', fullPage: true });
  console.log('SCREENSHOT_SAVED:e2e/smoke-admin-screenshot.png');
});
