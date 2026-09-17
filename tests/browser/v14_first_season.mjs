/** Real browser journey: no intercepted planner results or manufactured outcomes. */
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';

const root = resolve(new URL('../..', import.meta.url).pathname);
const base = (process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:4190').replace(/\/$/, '');
const output = process.env.FARMTACT_REPORT || '/tmp/farmtact-v14-browser.json';
const evidence = { status: 'RUNNING', base, checks: [], screenshots: [], stages: [], failures: [] };
const check = (name, pass, detail) => {
  evidence.checks.push({ name, pass: Boolean(pass), ...(detail === undefined ? {} : { detail }) });
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`);
};
const browser = await chromium.launch({ headless: true });
let activePage;
await mkdir(resolve(root, 'apps/web/screenshots/v14'), { recursive: true });

async function shot(page, name) {
  const file = `apps/web/screenshots/v14/${name}.png`;
  await page.screenshot({ path: resolve(root, file), fullPage: true, animations: 'disabled' });
  evidence.screenshots.push(file);
}

try {
  for (const width of [360, 390, 430, 1280]) {
    const context = await browser.newContext({ viewport: { width, height: width > 500 ? 900 : 844 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    await page.goto(base + '/', { waitUntil: 'networkidle' });
    await page.getByTestId('beginner-shell').waitFor();
    check(`${width}: introduction has an obvious start`, await page.getByRole('button', { name: 'Start playing', exact: true }).isVisible());
    check(`${width}: illustrative animation is labelled`, (await page.locator('body').innerText()).includes('Illustrated example'));
    check(`${width}: no horizontal page overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    check(`${width}: no public version navigation`, !await page.locator('a[href*="/v1"], button[aria-label*="edition" i]').count());
    check(`${width}: farm is a noninteractive stage`, await page.getByTestId('beginner-scene').locator('button, a, input, [tabindex="0"]').count() === 0);
    await page.getByRole('button', { name: 'Next card', exact: true }).click();
    const title = await page.getByTestId('beginner-card').innerText();
    await page.getByTestId('beginner-card').focus();
    await page.keyboard.press('ArrowRight');
    check(`${width}: keyboard card navigation`, (await page.getByTestId('beginner-card').innerText()) !== title);
    await shot(page, `introduction-${width}`);
    await context.close();
  }

  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  activePage = page;
  let journey = null;
  const providerRequests = [], failedMutations = [], consoleErrors = [];
  page.on('pageerror', error => consoleErrors.push(String(error)));
  page.on('request', request => {
    if (request.method() === 'POST' && /\/conversations\/[^/]+\/(messages|invite|council)$|\/planning-sessions\/[^/]+\/review$/.test(new URL(request.url()).pathname)) providerRequests.push(request.url());
  });
  page.on('response', async response => {
    const path = new URL(response.url()).pathname;
    if (response.request().method() === 'POST' && response.status() >= 400) failedMutations.push({ path, status: response.status() });
    if (/\/beginner-journeys(?:\/[^/]+(?:\/actions)?)?$/.test(path) && response.ok()) {
      const body = await response.json().catch(() => null);
      if (body?.id && body?.stage) journey = body;
      else if (body?.journeys?.length) journey = body.journeys[0];
    }
  });
  await page.goto(base + '/', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Start playing', exact: true }).click();
  await page.waitForURL('**/play');
  await page.waitForFunction(() => document.querySelector('[data-testid="beginner-shell"]')?.getAttribute('data-stage') === 'START', null, { timeout: 30000 });
  for (let tries = 0; !journey && tries < 20; tries++) await page.waitForTimeout(100);
  check('starting creates a saved isolated lesson', Boolean(journey?.id));
  const firstId = journey.id;
  await shot(page, 'first-order-390');

  for (let step = 0; step < 35; step++) {
    await page.waitForFunction(() => {
      const node = document.querySelector('[data-testid="beginner-primary"]');
      return node && !node.disabled;
    }, null, { timeout: 120000 });
    for (let tries = 0; journey?.stage !== await page.getByTestId('beginner-shell').getAttribute('data-stage') && tries < 30; tries++) await page.waitForTimeout(100);
    const stage = journey?.stage;
    evidence.stages.push(stage);
    if (stage === 'COMPLETE') break;
    if (stage === 'CHOOSE_PLAN') {
      check('two or more actual choices are available', journey.choices.filter(x => x.eligible).length >= 2, journey.choices);
      await page.getByRole('button', { name: 'Next card', exact: true }).click();
      await shot(page, 'plan-preview-390');
    }
    if (stage === 'MAINTENANCE_DUE') {
      await page.reload({ waitUntil: 'networkidle' });
      check('reload resumes the maintenance checkpoint', journey?.id === firstId && journey?.stage === stage);
      await shot(page, 'maintenance-390');
    }
    const before = journey?.revision;
    process.stdout.write(`Action ${step}: ${stage} · ${await page.getByTestId('beginner-primary').innerText()}\n`);
    const [response] = await Promise.all([
      page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/actions'), { timeout: 30000 }),
      page.getByTestId('beginner-primary').click(),
    ]);
    check(`${stage}: action accepted`, response.ok(), response.ok() ? undefined : await response.text());
    await page.waitForFunction(({ before }) => {
      const shell = document.querySelector('[data-testid="beginner-shell"]');
      return shell && Number(shell.getAttribute('data-revision')) > before;
    }, { before }, { timeout: 120000 });
  }
  check('full season reaches debrief', journey?.stage === 'COMPLETE', journey);
  check('actual delivery fulfils the teaching objective', journey?.debrief?.objective_met === true, journey?.debrief);
  check('season used actual saved simulation events', journey?.timeline?.length > 0, journey?.timeline);
  check('journey makes zero automatic provider requests', providerRequests.length === 0, providerRequests);
  check('no failed gameplay mutations', failedMutations.length === 0, failedMutations);
  check('no uncaught browser errors', consoleErrors.length === 0, consoleErrors);
  await shot(page, 'delivery-debrief-390');
  await page.goto(base + '/', { waitUntil: 'networkidle' });
  check('returning player sees continue', await page.getByRole('button', { name: 'Continue my season', exact: true }).isVisible());
  await context.close();
  evidence.status = 'PASS';
} catch (error) {
  if (activePage && !activePage.isClosed()) await shot(activePage, 'failure-current');
  evidence.status = 'FAIL';
  evidence.failures.push(error.stack || String(error));
  process.exitCode = 1;
} finally {
  await browser.close();
  await writeFile(output, JSON.stringify(evidence, null, 2) + '\n');
  process.stdout.write(JSON.stringify(evidence, null, 2) + '\n');
}
