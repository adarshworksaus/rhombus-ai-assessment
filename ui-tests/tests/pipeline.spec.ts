import { test, expect, chromium } from '@playwright/test';
test.describe.configure({ mode: 'serial' });

test('Rhombus workflow loads with pipeline controls', async () => {
  const browser = await chromium.connectOverCDP(
    'http://127.0.0.1:9222'
  );

  const context = browser.contexts()[0];

  const page = context.pages().find(
    p => p.url().includes('/workflow/5288')
  );

  if (!page) {
    throw new Error('Rhombus workflow 5288 is not open');
  }

  await expect(page).toHaveURL(/\/workflow\/5288/);

  await expect(
    page.getByTestId('run-pipeline')
  ).toBeVisible();

  await expect(
    page.getByRole('button', { name: 'Logs' })
  ).toBeVisible();

  await expect(
    page.getByRole('button', { name: /Data Input/ }).first()
  ).toBeVisible();

  await expect(
    page.getByRole('button', { name: /Data Output/ }).first()
  ).toBeVisible();

  await browser.close();
});

test('clean pipeline runs to completion', async () => {
  const browser = await chromium.connectOverCDP(
    'http://127.0.0.1:9222'
  );

  const context = browser.contexts()[0];

  const page = context.pages().find(
    p => p.url().includes('/workflow/5288')
  );

  if (!page) {
    throw new Error('Rhombus workflow 5288 is not open');
  }

  const runButton = page.getByTestId('run-pipeline');

  // Confirm pipeline is idle before starting.
  await expect(
    runButton.locator('svg.lucide-play')
  ).toBeVisible();

  await runButton.click();

  // Confirm a new execution actually started.
  await expect(
    runButton.locator('svg.lucide-square')
  ).toBeVisible();

  // Wait for this execution to finish naturally.
  await expect(
    runButton.locator('svg.lucide-play')
  ).toBeVisible({
    timeout: 120000,
  });

  // The workflow must still be usable after execution.
  await expect(runButton).toBeEnabled();

  await browser.close();
});

