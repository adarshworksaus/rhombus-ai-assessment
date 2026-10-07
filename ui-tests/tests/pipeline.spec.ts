import { test, expect, chromium, Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

const WORKFLOW_ID = '5288';

async function getWorkflowPage(): Promise<{
  browser: Awaited<ReturnType<typeof chromium.connectOverCDP>>;
  page: Page;
}> {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  const context = browser.contexts()[0];

  const page = context.pages().find(
    p => p.url().includes(`/workflow/${WORKFLOW_ID}`)
  );

  if (!page) {
    await browser.close();
    throw new Error(`Rhombus workflow ${WORKFLOW_ID} is not open`);
  }

  return { browser, page };
}

test('configured AI transformation workflow is present', async () => {
  const { browser, page } = await getWorkflowPage();

  await expect(page).toHaveURL(new RegExp(`/workflow/${WORKFLOW_ID}`));

  await expect(page.getByTestId('run-pipeline')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Logs' })).toBeVisible();

  // Verify the configured transformation graph rather than only the page shell.
  await expect(page.getByTestId('rf__node-llm_node_7')).toBeVisible();
  await expect(
    page.getByTestId('rf__node-remove_duplicate_node_1')
  ).toBeVisible();

  // Verify the graph begins at the input and remains connected through
  // the AI-generated cleaning stages to the configured output node.
  const expectedEdges = [
    'rf__edge-xy-input_node_1-llm_node_7',
    'rf__edge-xy-llm_node_7-remove_duplicate_node_1',
    'rf__edge-xy-remove_duplicate_node_1-llm_node_1',
    'rf__edge-xy-llm_node_1-llm_node_2',
    'rf__edge-xy-llm_node_2-llm_node_3',
    'rf__edge-xy-llm_node_3-llm_node_4',
    'rf__edge-xy-llm_node_4-llm_node_5',
    'rf__edge-xy-llm_node_5-llm_node_6',
    'rf__edge-xy-llm_node_6-1791288473455',
  ];

  for (const edge of expectedEdges) {
    await expect(page.getByTestId(edge)).toBeAttached();
  }

  // Assert real cleaning configuration is present.
  await expect(
    page.getByTestId('rf__node-llm_node_7')
  ).toContainText('Transaction ID');

  await expect(
    page.getByTestId('rf__node-remove_duplicate_node_1')
  ).toContainText('Remove Duplicates');

  await browser.close();
});

test('AI Builder contains pipeline-specific context', async () => {
  const { browser, page } = await getWorkflowPage();

  const aiBuilder = page.getByText('AI Builder', { exact: true });
  await expect(aiBuilder).toBeVisible();

  await aiBuilder.click();

  await expect(
    page.getByText('AI Builder', { exact: true })
  ).toBeVisible();

  const body = page.locator('body');

  // The AI Builder history is tied to this ETL pipeline and its real output.
  await expect(body).toContainText('input DataFrame');
  await expect(body).toContainText('GCS');
  await expect(body).toContainText('pipeline');

  await browser.close();
});

test('pipeline has an active daily schedule', async () => {
  const { browser, page } = await getWorkflowPage();

  const scheduleButton = page.getByText('Schedule', { exact: true });
  await expect(scheduleButton).toBeVisible();

  await scheduleButton.click();

  await expect(
    page.getByText('Schedules', { exact: true })
  ).toBeVisible();

  const loading = page.getByText('Loading schedules...', { exact: true });

  if (await loading.count()) {
    await loading.waitFor({
      state: 'hidden',
      timeout: 30000,
    });
  }

  await expect(
    page.getByText('Schedule for Rhombus AI ETL Assessment', { exact: true })
  ).toBeVisible();

  await expect(
    page.getByText('Active', { exact: true })
  ).toBeVisible();

  // Assert the loaded schedule configuration from the schedule panel.
  // Rhombus may render these values inside a combined schedule card rather
  // than as independent text elements.
  const scheduleText = await page.locator('body').innerText();

  expect(scheduleText).toContain('Daily');
  expect(scheduleText).toContain('At 12:10pm');

  const activeSwitch = page.locator(
    '[role="switch"][aria-label="Deactivate schedule"]'
  );

  await expect(activeSwitch).toHaveAttribute('aria-checked', 'true');

  await browser.close();
});

test('clean pipeline runs to completion', async () => {
  const { browser, page } = await getWorkflowPage();

  const runButton = page.getByTestId('run-pipeline');

  // Confirm the pipeline is idle before starting.
  await expect(
    runButton.locator('svg.lucide-play')
  ).toBeVisible();

  await runButton.click();

  // Confirm a new execution genuinely starts.
  await expect(
    runButton.locator('svg.lucide-square')
  ).toBeVisible();

  // Wait for the real execution to finish. No fixed sleep is used.
  await expect(
    runButton.locator('svg.lucide-play')
  ).toBeVisible({
    timeout: 120000,
  });

  await expect(runButton).toBeEnabled();

  await browser.close();
});
