import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';

const root = resolve(new URL('../..', import.meta.url).pathname);
const base = process.env.BASE_URL || 'http://127.0.0.1:4196';
const baselineId = process.env.BASELINE_SESSION || '6284489c14014f7c27430327199fdeae';
const alternateId = process.env.ALTERNATE_SESSION || 'f6da20ad6aec3f821b43ce1f31669cad';
const report = { status: 'RUNNING', base, baselineId, alternateId, checks: [], failures: [], requests: [], sessionReads: [] };
const check = (name, pass, detail) => {
  report.checks.push({ name, pass: Boolean(pass), detail });
  if (!pass) throw Error(`${name}: ${JSON.stringify(detail)}`);
};
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
const bounded = async (promise, label, ms = 45000) => {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(Error(`Timed out: ${label}`)), ms); })]); }
  finally { clearTimeout(timer); }
};
const applyObserved = deferred(), applyRelease = deferred(), workflowObserved = deferred(), workflowRelease = deferred(), calculateObserved = deferred(), calculateRelease = deferred();
let browser, closing = false, proposalId = '', jobId = '', terminal = null, workflowReceipt = null, armWorkflow = false, holdWorkflow = true, failRead = false, phase = 'baseline', calculateResponse;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, storageState: process.env.STORAGE_STATE || '/tmp/farmtact-v15-cards-storage.json' });
  const get = async path => { const response = await context.request.get(`${base}/api/v1${path}`); if (!response.ok()) throw Error(`${path}: ${response.status()}`); return response.json(); };
  const baseline = await get(`/planning-sessions/${baselineId}`), alternate = await get(`/planning-sessions/${alternateId}`);
  check('existing baseline and alternate require no session creation', Boolean(baseline.result_id) && baseline.workflow && alternate.status === 'DRAFT' && !alternate.result_id, { baseline: baseline.status, result: baseline.result_id, alternate: alternate.status });
  check('baseline has no reservation for the tested grow space', !(baseline.assumptions?.reservations || []).some(row => row.bed_id === baseline.tactical_context.grow_space.id));
  await context.addInitScript(id => {
    if (!sessionStorage.getItem('v15-reconciliation-initialized')) {
      localStorage.setItem('farmtact:v15:planning-session', id);
      localStorage.removeItem(`farmtact:v15:integrated-cards-navigation:${id}`);
      sessionStorage.setItem('v15-reconciliation-initialized', 'true');
    }
  }, baselineId);
  const page = await context.newPage();
  page.setDefaultTimeout(30000);
  page.on('request', request => { if (request.method() !== 'GET') report.requests.push({ method: request.method(), path: new URL(request.url()).pathname }); });
  await page.route('**/api/v1/**', async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    try {
      if (failRead && request.method() === 'GET' && path === `/api/v1/planning-sessions/${baselineId}`) {
        failRead = false;
        await route.fulfill({ status: 429, contentType: 'application/json', headers: { 'Retry-After': '17' }, body: JSON.stringify({ detail: 'Reconciliation test admission wait; saved session retained.' }) }); return;
      }
      const response = await route.fetch();
      if (request.method() === 'POST' && proposalId && path === `/api/v1/farm-workflow/proposals/${proposalId}/apply`) {
        const receipt = await response.json(); jobId = receipt.recalculation_job?.id;
        if (!jobId) throw Error('Apply did not return its exact recalculation job');
        applyObserved.resolve(receipt); await applyRelease.promise;
      }
      if (request.method() === 'POST' && path === `/api/v1/planning-sessions/${alternateId}/calculate`) {
        calculateResponse = await response.json(); calculateObserved.resolve(calculateResponse); await calculateRelease.promise;
      }
      if (request.method() === 'GET' && path === `/api/v1/planning-sessions/${baselineId}`) {
        const body = await response.json(); report.sessionReads.push({ phase, id: body.id, job: body.job?.id, status: body.job?.status, result: body.result_id });
        if (armWorkflow && body.id === baselineId && body.job?.id === jobId && body.job.status === 'COMPLETED' && body.result_id === jobId) terminal = body;
      }
      if (armWorkflow && holdWorkflow && terminal && request.method() === 'GET' && path === '/api/v1/farm-workflow') {
        const state = await response.json(), bound = state.proposals.find(row => row.id === proposalId && row.recalculation_job?.id === terminal.result_id);
        if (!bound?.explanation) throw Error('Terminal workflow lacks exact proposal explanation');
        workflowReceipt = bound; workflowObserved.resolve(); await workflowRelease.promise;
      }
      await route.fulfill({ response });
    } catch (error) { if (!closing) { report.failures.push(`Transport: ${String(error)}`); await route.abort().catch(() => {}); } }
  });
  const click = name => page.getByRole('button', { name, exact: true }).filter({ visible: true }).first().click();
  const mission = id => page.waitForFunction(value => document.querySelector('.ic-card')?.getAttribute('data-session-id') === value, id);
  const toolRoundtrip = async () => { await click('More'); await click('Open tool'); await page.locator('.integrated-tool').waitFor(); await click('Back'); await page.locator('.ic-path').waitFor(); await click('Back'); };
  await page.goto(`${base}/play`, { waitUntil: 'domcontentloaded' }); await mission(baselineId);
  check('visible baseline card is bound before any response is held', await page.locator('.ic-card').getAttribute('data-result-id') === baseline.result_id);
  for (let n = 0; n < 10 && !/Keep .+ available/.test(await page.locator('.ic-card h1').innerText()); n++) await click('Next →');
  await click('Review reservation'); await page.getByRole('button', { name: 'Apply & recalculate', exact: true }).waitFor();
  const state = await get('/farm-workflow');
  const proposal = state.proposals.filter(row => row.session_id === baselineId && row.status === 'draft').at(-1);
  if (!proposal) throw Error('UI did not create the reviewed reservation draft');
  proposalId = proposal.id;
  phase = 'held-apply'; await click('Apply & recalculate'); await bounded(applyObserved.promise, 'real Apply response'); armWorkflow = true;
  await click('Back'); phase = 'tool-return'; await toolRoundtrip();
  await bounded(workflowObserved.promise, 'exact terminal workflow response', 180000);
  const held = await page.evaluate(() => ({ session: document.querySelector('.ic-card')?.getAttribute('data-session-id'), result: document.querySelector('.ic-card')?.getAttribute('data-result-id'), busy: document.querySelector('.ic-keys .is-primary')?.textContent, disabled: document.querySelector('.ic-keys .is-primary')?.disabled }));
  check('terminal workflow barrier retains the exact visible previous result', held.session === baselineId && held.result === baseline.result_id && terminal.result_id !== baseline.result_id, { held, terminal: terminal.result_id, proposalId, jobId });
  check('pending mutation remains disabled through tool return', held.disabled && held.busy === 'Applying and recalculating', held);
  holdWorkflow = false; workflowRelease.resolve();
  await page.waitForFunction(id => document.querySelector('.ic-card')?.getAttribute('data-result-id') === id, terminal.result_id);
  check('terminal reconciliation cannot clear mutation-owned busy state', await page.locator('.ic-keys .is-primary').isDisabled() && await page.locator('.ic-keys .is-primary').innerText() === 'Applying and recalculating');
  applyRelease.resolve();
  await page.getByRole('button', { name: 'Approve actions', exact: true }).waitFor();
  await click('Explain'); const explanation = await page.locator('.ic-explanation').innerText();
  const reservation = proposal.changes[0].assumptions.reservations.find(row => row.bed_id === baseline.tactical_context.grow_space.id);
  check('explanation binds the exact completed proposal and result immediately', await page.locator('.ic-card').getAttribute('data-result-id') === jobId && workflowReceipt.id === proposalId && explanation.includes(workflowReceipt.explanation.why) && explanation.includes(reservation.bed_id) && explanation.includes(reservation.start_date) && explanation.includes(reservation.end_date) && !explanation.includes('Reason not available'), { proposalId, resultId: jobId, explanation });
  await click('Back'); armWorkflow = false;
  await page.evaluate(id => { localStorage.setItem('farmtact:v15:planning-session', id); localStorage.removeItem(`farmtact:v15:integrated-cards-navigation:${id}`); }, alternateId);
  phase = 'alternate'; await page.reload({ waitUntil: 'domcontentloaded' }); await mission(alternateId); await click('Calculate');
  await bounded(calculateObserved.promise, 'alternate Calculate response');
  check('held calculation receipt belongs to the intended alternate', calculateResponse.id === alternateId);
  await page.evaluate(id => localStorage.setItem('farmtact:v15:planning-session', id), baselineId); await toolRoundtrip(); await mission(baselineId);
  calculateRelease.resolve();
  await page.getByRole('button', { name: 'Approve actions', exact: true }).waitFor();
  check('late real mutation response preserves selected session and result', await page.locator('.ic-card').getAttribute('data-session-id') === baselineId && await page.locator('.ic-card').getAttribute('data-result-id') === jobId && await page.evaluate(() => localStorage.getItem('farmtact:v15:planning-session')) === baselineId);
  phase = 'admission'; failRead = true; await toolRoundtrip(); await page.getByRole('alert').waitFor();
  const alert = await page.getByRole('alert').innerText();
  check('429 retains the intended session and explicit recoverable error', alert.includes('Reconciliation test admission wait') && await page.locator('.ic-card').getAttribute('data-session-id') === baselineId && await page.evaluate(() => localStorage.getItem('farmtact:v15:planning-session')) === baselineId, alert);
  check('regression creates no sessions and submits no provider requests', report.requests.every(row => row.path !== '/api/v1/planning-sessions' && !/council|messages|research|inference/.test(row.path)), report.requests);
  if (report.failures.length) throw Error('Transport errors were recorded');
  report.status = 'PASS';
} catch (error) { report.status = 'FAIL'; report.failures.push(error instanceof Error ? error.stack : String(error)); process.exitCode = 1; }
finally {
  closing = true; applyRelease.resolve(); workflowRelease.resolve(); calculateRelease.resolve(); await browser?.close();
  await mkdir(resolve(root, 'reports/v15'), { recursive: true }); await writeFile(resolve(root, 'reports/v15/terminal-reconciliation-browser.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
}
