// Controlled transport failures; the real numerical/concurrency checks are separate.
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';
import { writeFile } from 'node:fs/promises';
const base = process.env.BASE_URL || 'http://127.0.0.1:4196';
const report = { base, fixture: 'Queued planning and lost cancellation response; no real mutation or inference', checks: [], failures: [] };
const check = (name, pass) => { report.checks.push({ name, pass }); if (!pass) throw Error(name); };
const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, storageState: `/tmp/farmtact-v15-scenarios-${new URL(base).port}.json` });
  const list = await (await context.request.get(`${base}/api/v1/planning-sessions`)).json();
  const original = await (await context.request.get(`${base}/api/v1/planning-sessions/${list.sessions.find(s => s.workflow).id}`)).json();
  let session = { ...original, result: null, result_id: null, selected_strategy_id: null, job: { id: 'controlled-job', status: 'QUEUED' } };
  const calls = [];
  const page = await context.newPage();
  await page.route('**/api/v1/planning-sessions**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    if (request.method() === 'POST') {
      calls.push({ path, key: request.headers()['idempotency-key'] });
      if (!path.endsWith('/cancel')) throw Error(`Unexpected mutation ${path}`);
      session = { ...session, job: { ...session.job, status: 'CANCELLED' } };
      if (calls.length === 1) return route.fulfill({ status: 503, json: { detail: 'Controlled response lost after cancellation committed' } });
    }
    return route.fulfill({ status: 200, json: path.endsWith('/planning-sessions') ? { sessions: [session] } : session });
  });
  await page.goto(base); await page.locator('.ic-shell').waitFor();
  const click = name => page.getByRole('button', { name, exact: true }).filter({ visible: true }).click();
  await click('More'); await click('Open tool'); await click('Open');
  await page.getByRole('button', { name: 'Review cancellation', exact: true }).waitFor();
  await click('Review cancellation');
  check('Cancellation has an explicit review before mutation', calls.length === 0);
  await click('Cancel active calculation');
  await page.getByRole('alert').filter({ hasText: 'Controlled response lost' }).waitFor();
  check('Uncertain cancellation retains its review without automatic retry', calls.length === 1 && await page.getByRole('heading', { name: 'Review calculation cancellation' }).isVisible());
  await click('Cancel active calculation');
  await page.getByRole('heading', { name: 'Objectives and all demand' }).waitFor();
  check('Cancellation retry retains the original idempotency key', calls.length === 2 && calls[0].key === calls[1].key && Boolean(calls[0].key));
  check('Confirmed cancellation enables a separate new local calculation', await page.getByRole('button', { name: 'Calculate locally', exact: true }).isVisible());
  check('No other mutation was attempted', calls.every(call => call.path === `/api/v1/planning-sessions/${session.id}/cancel`));
} catch (error) { report.failures.push(String(error)); process.exitCode = 1; }
finally { report.status = report.failures.length ? 'FAIL' : 'PASS'; await browser.close(); await writeFile('reports/v15/plan-recovery-browser.json', JSON.stringify(report, null, 2)); console.log(JSON.stringify(report, null, 2)); }
