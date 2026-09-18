/** Polling lifecycle UI fixture. Creates a real ordinary sandbox session, but
 * never calculates or submits provider work. Delayed/failed job reads are local
 * Playwright fixtures and do not claim backend job failure/recovery coverage. */
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const root = process.cwd();
const { chromium } = await import(pathToFileURL(resolve(root, 'apps/web/node_modules/@playwright/test/index.mjs')));
const base = process.env.BASE_URL || 'http://127.0.0.1:4199';
if (!['127.0.0.1', 'localhost'].includes(new URL(base).hostname)) throw Error('Polling UI test requires loopback origin');
const artifacts = process.env.ARTIFACT_DIR || '/tmp/v21-polling';
const report = {
  status: 'RUNNING',
  scope: 'Real sandbox bootstrap; delayed RUNNING/FAILED reads are intercepted UI fixtures. No numerical calculation, backend failure or provider call is induced.',
  checks: [], failures: [], page_errors: [], writes: [], blocked_writes: [], fixture: {},
};
const check = (name, pass, detail) => {
  report.checks.push({ name, pass: !!pass, detail });
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name}`);
  if (!pass) throw Error(name);
};
let browser, page, transport, releasePoll;
try {
  await mkdir(artifacts, { recursive: true });
  if (process.env.STAGED_SOURCE) {
    if (base !== 'http://127.0.0.1:4199') throw Error('Staged transport requires its fixed loopback origin');
    const { stagedTransport } = await import(pathToFileURL(resolve(root, 'tests/browser/restored_staged_transport.mjs')));
    transport = await stagedTransport(process.env.STAGED_SOURCE);
  }
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce' });
  if (transport) await transport.attach(context);
  context.setDefaultTimeout(transport ? 180000 : 30000);
  page = await context.newPage();
  let session, bootstrapFinished = false, workflowReads = 0;
  page.on('pageerror', error => report.page_errors.push(error.message));
  page.on('request', request => {
    const path = new URL(request.url()).pathname;
    if (request.method() === 'POST') report.writes.push(path);
    if (request.method() === 'GET' && /\/farm-workflow$/.test(path)) workflowReads++;
  });
  page.on('response', async response => {
    if (!bootstrapFinished && response.ok() && /\/planning-sessions(?:\/[^/?]+)?$/.test(new URL(response.url()).pathname)) {
      try { const body = await response.json(); if (body.id && body.farm) session = body; } catch { /* Not a session response. */ }
    }
  });
  // Only fresh-session creation may reach the backend; every later write fails.
  await page.route('**/api/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    if (['GET', 'HEAD'].includes(request.method())) return route.fallback();
    if (!bootstrapFinished && request.method() === 'POST' && /\/planning-sessions$/.test(path)) return route.fallback();
    report.blocked_writes.push({ method: request.method(), path });
    return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Polling test guard blocked an unexpected write' }) });
  });
  await page.goto(base + (process.env.APP_PATH || '/'), { waitUntil: 'domcontentloaded' });
  await page.getByRole('button', { name: /Calculate options/ }).waitFor();
  check('ordinary saved sandbox session is available', !!session?.farm && session.workflow === true);
  bootstrapFinished = true;
  const writesBefore = report.writes.length;
  const initialBeds = await page.locator('.living-board__beds').innerText();
  const snapshot = structuredClone(session);
  let mode = 'bootstrap', pollCount = 0, pending = 0, maximumPending = 0, notifyPoll;
  let pollSeen = new Promise(resolve => { notifyPoll = resolve; });
  let pollGate = new Promise(resolve => { releasePoll = resolve; });
  const fixtureSession = status => ({
    ...snapshot, status,
    job: { id: 'fixture-slow-calculation', kind: 'calculate', status, stage: status.toLowerCase(), ...(status === 'FAILED' ? { error: 'Fixture timeout' } : {}) },
  });
  await page.route(`**/api/v1/planning-sessions/${session.id}`, async route => {
    if (route.request().method() !== 'GET') return route.fallback();
    if (mode === 'bootstrap') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fixtureSession('RUNNING')) });
    pollCount++; pending++; maximumPending = Math.max(maximumPending, pending); notifyPoll();
    const gate = pollGate;
    try {
      await gate;
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fixtureSession('FAILED')) });
    } finally { pending--; }
  });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.farmer-flow').waitFor();
  mode = 'hold';
  await Promise.race([pollSeen, new Promise((_, reject) => setTimeout(() => reject(Error('No scheduled poll observed')), 15000))]);
  await page.waitForTimeout(6500);
  check('slow poll stays singular across more than three polling intervals', pollCount === 1 && pending === 1 && maximumPending === 1, { pollCount, pending, maximumPending, held_ms: 6500 });
  releasePoll();
  const alert = page.getByRole('alert').filter({ hasText: 'Your saved inputs remain available' });
  await alert.waitFor();
  check('failed fixture job explains saved-input recovery', (await alert.innerText()).includes('Your saved inputs remain available'));
  check('saved farm beds remain visible after failed calculation', (await page.locator('.living-board__beds').innerText()) === initialBeds);
  check('explicit Calculate retry is available', await page.getByRole('button', { name: /Calculate options/ }).isEnabled());
  const terminalPollCount = pollCount;
  await page.waitForTimeout(4000);
  check('terminal job stops polling', pollCount === terminalPollCount && pending === 0, { pollCount, pending });
  report.fixture.slow_terminal = { pollCount, maximumPending, held_ms: 6500 };

  // A second held read is released after leaving the workflow. Its response
  // must not refresh workflow state or replace the selected room.
  mode = 'bootstrap';
  pollCount = 0; maximumPending = 0;
  pollSeen = new Promise(resolve => { notifyPoll = resolve; });
  pollGate = new Promise(resolve => { releasePoll = resolve; });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.locator('.farmer-flow').waitFor();
  mode = 'hold';
  await Promise.race([pollSeen, new Promise((_, reject) => setTimeout(() => reject(Error('No disposal-fixture poll observed')), 15000))]);
  await page.locator('.side-rail nav').getByRole('button', { name: 'Crops', exact: true }).click();
  await page.getByRole('heading', { name: 'Recipes with receipts.' }).waitFor();
  const readsBeforeDisposedResponse = workflowReads;
  releasePoll();
  await page.waitForTimeout(1000);
  check('disposed poll response cannot refresh workflow or change room', workflowReads === readsBeforeDisposedResponse && await page.getByRole('heading', { name: 'Recipes with receipts.' }).isVisible() && await page.locator('.farmer-flow').count() === 0, { workflowReadsBefore: readsBeforeDisposedResponse, workflowReadsAfter: workflowReads });
  report.fixture.disposed = { pollCount, maximumPending };
  check('polling and failure recovery submit no automatic mutation', report.writes.length === writesBefore && report.blocked_writes.length === 0, { writesBefore, writesAfter: report.writes.length, blocked: report.blocked_writes });
  check('no calculation or provider request submitted', !report.writes.some(path => /\/calculate$|\/review$|\/conversations(?:\/|$)/.test(path)), report.writes);
  check('no page exceptions', report.page_errors.length === 0, report.page_errors);
  if (transport) check('exact staged transport has no failures', transport.evidence.failures.length === 0, transport.evidence.failures);
  report.status = 'PASS';
  await context.close();
} catch (error) {
  report.status = 'FAIL'; report.failures.push(error.stack || String(error));
  if (page) await page.screenshot({ path: resolve(artifacts, 'failure.png'), fullPage: true }).catch(() => {});
} finally {
  releasePoll?.();
  if (browser) await browser.close();
  if (transport) report.staged_transport = transport.evidence;
  const output = resolve(process.env.REPORT_PATH || '/tmp/v21-polling/report.json');
  await mkdir(resolve(output, '..'), { recursive: true });
  await writeFile(output, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failures: report.failures }));
  if (report.status !== 'PASS') process.exitCode = 1;
}
