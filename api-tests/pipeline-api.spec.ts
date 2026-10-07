import { test, expect, chromium, Page } from '@playwright/test';

const WORKFLOW_ID = '5288';
const API_BASE = 'https://api.rhombusai.com';

type AuthHeaders = {
  authorization: string;
  'x-org-id': string;
};

async function getAuthenticatedPage(): Promise<{
  browser: any;
  page: Page;
}> {
  const browser = await chromium.connectOverCDP(
    'http://127.0.0.1:9222'
  );

  const context = browser.contexts()[0];

  const page = context.pages().find(
    p => p.url().includes(`/workflow/${WORKFLOW_ID}`)
  );

  if (!page) {
    throw new Error(
      `Authenticated Rhombus workflow ${WORKFLOW_ID} is not open`
    );
  }

  return { browser, page };
}

async function captureAuthHeaders(
  page: Page
): Promise<AuthHeaders> {
  const target =
    `/api/dataset/analyzer/v2/projects/${WORKFLOW_ID}/nodes`;

  const requestPromise = page.waitForRequest(
    request =>
      request.url().includes(target) &&
      request.method() === 'GET'
  );

  // Reload causes Rhombus to make its normal authenticated API calls.
  await page.reload();

  const request = await requestPromise;
  const headers = request.headers();

  const authorization = headers['authorization'];
  const orgId = headers['x-org-id'];

  if (!authorization || !orgId) {
    throw new Error(
      'Could not capture Rhombus authentication headers'
    );
  }

  return {
    authorization,
    'x-org-id': orgId,
  };
}

async function directApiGet(
  page: Page,
  url: string,
  authHeaders: AuthHeaders
): Promise<{ status: number; body: string }> {
  return await page.evaluate(
    async ({ endpoint, headers }) => {
      const response = await fetch(endpoint, {
        method: 'GET',
        headers: {
          authorization: headers.authorization,
          'x-org-id': headers['x-org-id'],
        },
      });

      return {
        status: response.status,
        body: await response.text(),
      };
    },
    {
      endpoint: url,
      headers: authHeaders,
    }
  );
}

test.describe.configure({ mode: 'serial' });

test('GET workflow nodes returns pipeline configuration', async () => {
  const { browser, page } = await getAuthenticatedPage();

  const authHeaders = await captureAuthHeaders(page);

  const response = await directApiGet(
    page,
    `${API_BASE}/api/dataset/analyzer/v2/projects/${WORKFLOW_ID}/nodes`,
    authHeaders
  );

  expect(response.status).toBe(200);

  const body = JSON.parse(response.body);

  expect(body).toBeTruthy();

  await browser.close();
});

test('invalid workflow ID is rejected by backend', async () => {
  const { browser, page } = await getAuthenticatedPage();

  const authHeaders = await captureAuthHeaders(page);

  const invalidWorkflowId = '999999999';

  const response = await directApiGet(
    page,
    `${API_BASE}/api/dataset/analyzer/v2/projects/${invalidWorkflowId}/nodes`,
    authHeaders
  );

  expect(response.status).toBeGreaterThanOrEqual(400);
  expect(response.status).toBeLessThan(500);

  expect(response.body.length).toBeGreaterThan(0);

  await browser.close();
});
