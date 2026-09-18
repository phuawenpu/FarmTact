// Run from the repository root. Uses a fresh disposable public sandbox.
// Only sandbox session creation and one numerical calculation are allowed writes.
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs';

const base = 'https://farmtact.fly.dev';
const expected = 'b980180dbb49a5261e43ee1d8e4916cc24457d7f';
const out = resolve('reports/v21/usability-review');
await mkdir(out, { recursive: true });
const report = { reviewed_at: new Date().toISOString(), scope: 'Fresh public V21 sandbox; no inference or plan approval', checks: [], observations: {}, screenshots: [], writes: [], blocked: [], page_errors: [] };
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'no-preference' });
const page = await context.newPage();
page.setDefaultTimeout(30000);
const check = (name, pass, detail) => { report.checks.push({ name, pass: !!pass, detail }); if (!pass) throw Error(name); };
const shot = async (name, fullPage = false) => { await page.waitForTimeout(400); await page.screenshot({ path: resolve(out, `${name}.png`), fullPage, animations: 'disabled' }); report.screenshots.push(`${name}.png`); };
const geometry = () => page.evaluate(() => ({ viewport: { width: innerWidth, height: innerHeight }, scrollY, pageHeight: document.body.scrollHeight, headings: [...document.querySelectorAll('main h2')].map(e => ({ text: e.textContent, y: Math.round(e.getBoundingClientRect().top + scrollY) })), actions: [...document.querySelectorAll('.farmer-flow button')].filter(e => /Calculate options|Inbox|Apply & Recalculate|Approve & Create Actions/.test(e.textContent)).map(e => ({ text: e.textContent.trim(), y: Math.round(e.getBoundingClientRect().top + scrollY), disabled: e.disabled })) }));
await context.route('**/api/**', async route => {
  const r = route.request(), path = new URL(r.url()).pathname;
  if (['GET', 'HEAD'].includes(r.method())) return route.continue();
  const allowed = r.method() === 'POST' && (/\/council-research$/.test(path) || /\/planning-sessions$/.test(path) || /\/planning-sessions\/[^/]+\/calculate$/.test(path));
  const safePath = path.replace(/\/[a-f0-9-]{20,}(?=\/|$)/g, '/:id');
  (allowed ? report.writes : report.blocked).push({ method: r.method(), path: safePath });
  if (allowed) return route.continue();
  return route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ detail: 'Review harness: this mutation was not submitted.' }) });
});
page.on('pageerror', e => report.page_errors.push(e.message));
try {
  const health = await context.request.get(`${base}/api/v1/health`);
  const identity = await health.json();
  report.identity = { edition: identity.edition, source_commit: identity.source_commit };
  check('Public health matches frozen V21 source', identity.edition === 'v21' && identity.source_commit === expected);
  await page.goto(base, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: /See the farm/ }).waitFor();
  check('V21 renders restored V12 workspace', await page.locator('[data-experience="v12"][data-edition="v21"]').count() === 1);
  await page.evaluate(() => scrollTo(0, 0));
  report.observations.initial = await geometry();
  await shot('01-mobile-first-viewport');
  await shot('02-mobile-initial-page', true);
  const before = await page.locator('.living-board').innerText();
  report.observations.initial_board = before;
  await page.locator('.flow-rail button').filter({ hasText: 'Replan' }).click();
  check('Unavailable Replan explains prerequisite', await page.getByText('Calculate options first. No farm change has been made.').isVisible());
  check('Rail never invents completed stages', await page.locator('.flow-rail .is-done').count() === 0);
  check('Rail focuses calculation guidance', await page.locator('.flow-callout').evaluate(e => document.activeElement === e));
  const calculate = page.getByRole('button', { name: /Calculate options/ });
  await shot('03-calculate-guidance');
  const started = Date.now();
  await calculate.click();
  console.log('Numerical calculation submitted in fresh review sandbox.');
  await page.locator('.proposal-card').first().waitFor({ timeout: 240000 });
  report.observations.calculation_seconds = (Date.now() - started) / 1000;
  check('Three numerical plans returned', await page.locator('.proposal-card').count() === 3);
  report.observations.calculated = await geometry();
  report.observations.proposals = await page.locator('.proposal-card').allInnerTexts();
  report.observations.council_before_submission = await page.locator('.council-room').innerText();
  for (const name of ['Lean', 'Resilient']) {
    await page.locator('.proposal-card').filter({ hasText: name }).click();
    const board = await page.locator('.living-board').getAttribute('data-preview-strategy');
    check(`${name} board and brief use same preview`, !!board && board === await page.locator('.v12-plan-brief').getAttribute('data-preview-strategy'));
    check(`${name} remains explicitly unsaved`, await page.getByText(/Selecting a candidate changes this preview only/).isVisible());
  }
  const schedule = page.locator('.v12-plan-brief details');
  await schedule.locator('summary').click();
  report.observations.schedule_rows = await schedule.locator('li').count();
  await page.locator('.flow-rail button').filter({ hasText: 'Decide' }).click();
  check('Decide scrolls and focuses real section', await page.locator('.decision-stage').evaluate(e => document.activeElement === e && e.getBoundingClientRect().top < innerHeight));
  await shot('04-mobile-plan-comparison');
  const opener = page.getByRole('button', { name: 'Apply & Recalculate', exact: true });
  await opener.click();
  const dialog = page.getByRole('dialog', { name: /Challenge constraints/ });
  report.observations.proposal_editor = await dialog.innerText();
  check('Proposal heading receives focus', await dialog.locator('h2').evaluate(e => document.activeElement === e));
  await shot('05-mobile-proposal-editor');
  await page.keyboard.press('Escape');
  check('Escape returns focus to opener', await opener.evaluate(e => document.activeElement === e));
  await page.getByRole('button', { name: /Inbox/ }).click();
  report.observations.inbox = await page.getByRole('dialog').innerText();
  await shot('06-mobile-inbox');
  await page.getByRole('button', { name: 'Open manual entry' }).click();
  report.observations.manual_entry_labels = await page.getByRole('dialog').locator('label').allInnerTexts();
  await page.keyboard.press('Escape');
  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 });
    await page.evaluate(() => scrollTo(0, 0));
    const dims = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }));
    check(`${width}px no page horizontal overflow`, dims.body <= dims.viewport + 1, dims);
    if (width === 390 || width === 1280) await shot(`07-planned-${width}`, true);
  }
  // Inspect existing sections without submitting their actions.
  for (const room of ['Farm', 'Council research', 'Farm tools', 'Crops', 'Data', 'Outcomes', 'Setup']) {
    await page.locator('.side-rail nav').getByRole('button', { name: room, exact: true }).click();
    await page.waitForTimeout(1200);
    if (room === 'Council research') await page.getByRole('button', { name: 'Ask council for a plan', exact: true }).waitFor();
    report.observations[`room_${room}`] = (await page.locator('main').innerText()).slice(0, 8500);
    await shot(`08-room-${room.toLowerCase().replaceAll(' ', '-')}`);
    if (room === 'Data') {
      await page.getByRole('button', { name: 'Public context', exact: true }).click();
      await page.waitForTimeout(1200);
      report.observations.public_context=(await page.locator('main').innerText()).slice(0,16000);
      await shot('09-public-context', true);
    }
  }
  await page.goto(`${base}/play`, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: /See the farm/ }).waitFor();
  check('/play also renders V21', await page.locator('[data-edition="v21"]').count() === 1);
  check('No page exceptions', report.page_errors.length === 0);
  report.status = 'PASS';
} catch (error) {
  report.status = 'INCOMPLETE';
  report.failure = String(error);
  await shot('failure', true).catch(() => {});
} finally {
  await writeFile(resolve(out, 'walkthrough.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, blocked: report.blocked, failure: report.failure }));
  if (report.status !== 'PASS') process.exitCode = 1;
}
