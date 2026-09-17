/** Actual V15 integrated-card journey. Planner and workflow responses are never mocked. */
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';

const root = resolve(new URL('../..', import.meta.url).pathname);
const base = (process.env.BASE_URL || process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:4191').replace(/\/$/, '');
const reportDir = resolve(root, 'reports/v15');
const result = { status: 'RUNNING', base, checks: [], failures: [], screenshots: [], video: null, mutations: [], providerRequests: [] };
const check = (name, pass, detail) => {
  result.checks.push({ name, pass: Boolean(pass), ...(detail === undefined ? {} : { detail }) });
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`);
};
await mkdir(reportDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
let activePage;

async function shot(page, name) {
  const path = resolve(reportDir, `${name}.png`);
  await page.screenshot({ path, fullPage: true, animations: 'disabled' });
  result.screenshots.push(`reports/v15/${name}.png`);
}

function observe(page) {
  const mutations = [], providers = [], errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  page.on('request', request => {
    if (request.method() !== 'POST') return;
    const path = new URL(request.url()).pathname;
    mutations.push(path);
    if (/\/conversations(?:\/|$)|\/review$|\/invite$|\/council$/.test(path)) providers.push(path);
  });
  return { mutations, providers, errors };
}

async function open(page) {
  await page.goto(`${base}/play`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.locator('.ic-shell').waitFor({ timeout: 30_000 });
}

try {
  // Responsive read-only smoke: opening and browsing cards cannot mutate or invoke a provider.
  for (const width of [360, 390, 430, 1280]) {
    const context = await browser.newContext({ viewport: { width, height: width > 500 ? 900 : 844 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const traffic = observe(page);
    await open(page);
    const mutationsAfterOpen = traffic.mutations.length;
    const bedCount = await page.locator('.ic-beds article').count();
    check(`${width}: ordinary farm scene is not the four-bed lesson`, bedCount > 4, { bedCount });
    check(`${width}: objective retains an actual order`, /kg.+by \d{4}-\d{2}-\d{2}/i.test(await page.locator('.ic-heading').innerText()), await page.locator('.ic-heading').innerText());
    check(`${width}: exactly three contextual action keys`, await page.locator('.ic-keys > button').count() === 3);
    check(`${width}: page has no horizontal overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    const next = page.getByRole('button', { name: 'Next →' });
    if (await next.isEnabled()) await next.click();
    await page.getByRole('button', { name: 'Explain' }).click();
    check(`${width}: deterministic explanation is available`, await page.getByRole('heading', { name: 'What this means' }).isVisible());
    await page.getByRole('button', { name: 'Back', exact: true }).click();
    await page.getByRole('button', { name: 'More', exact: true }).click();
    check(`${width}: five-card tool index`, (await page.locator('.ic-deck-nav').innerText()).includes('1 of 5'));
    check(`${width}: browsing made no mutation`, traffic.mutations.length === mutationsAfterOpen, traffic.mutations.slice(mutationsAfterOpen));
    check(`${width}: browsing made no provider request`, traffic.providers.length === 0, traffic.providers);
    check(`${width}: reduced motion disables animation`, await page.locator('.ic-beds').evaluate(node => getComputedStyle(node).animationName === 'none'));
    check(`${width}: no browser exception`, traffic.errors.length === 0, traffic.errors);
    await shot(page, `shell-${width}`);
    await context.close();
  }

  const videoDir = resolve(reportDir, 'video');
  await mkdir(videoDir, { recursive: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, recordVideo: { dir: videoDir, size: { width: 390, height: 844 } } });
  const page = await context.newPage(); activePage = page;
  const traffic = observe(page);
  await open(page);
  const card = page.locator('.ic-card');

  // Guide skip is persisted by the server and survives reload independently of planner revision.
  await page.getByRole('button', { name: 'Explain' }).click();
  const skip = page.getByRole('button', { name: 'Skip guide' });
  if (await skip.count()) {
    await Promise.all([
      page.waitForResponse(response => response.request().method() === 'POST' && /\/guidance$/.test(new URL(response.url()).pathname) && response.ok()),
      skip.click(),
    ]);
    await page.reload({ waitUntil: 'domcontentloaded' }); await page.locator('.ic-shell').waitFor();
    await page.getByRole('button', { name: 'Explain' }).click();
    check('server guidance skip resumes after reload', await page.getByRole('button', { name: 'Skip guide' }).count() === 0);
    await page.getByRole('button', { name: 'Back', exact: true }).click();
  } else {
    await page.getByRole('button', { name: 'Back', exact: true }).click();
    check('previously skipped guide remains skipped', true);
  }
  if ((await page.locator('.ic-deck-nav').innerText()).includes('Farm tools'))
    await page.getByRole('button', { name: 'Back', exact: true }).click();
  const dismiss = page.getByRole('button', { name: 'Dismiss' });
  if (await dismiss.count()) await dismiss.click();

  // Calculate if this tenant has no saved ordinary result yet.
  for (let i = 0; i < 12; i++) {
    if (await page.getByText('Preview—not saved', { exact: true }).count()) break;
    const calculate = page.getByRole('button', { name: 'Calculate', exact: true });
    if (await calculate.count()) { await calculate.click(); await page.waitForTimeout(1000); continue; }
    const next = page.getByRole('button', { name: 'Next →' });
    if (await next.isEnabled()) {
      const title = await card.locator('h1').innerText();
      await next.click();
      await page.waitForFunction(value => document.querySelector('.ic-card h1')?.textContent !== value, title);
    } else break;
  }
  await page.getByText('Preview—not saved', { exact: true }).waitFor({ timeout: 180_000 });

  // Keyboard and swipe change selection without a planning/workflow mutation.
  const beforeBrowse = traffic.mutations.length;
  await card.focus(); const beforeTitle = await card.locator('h1').innerText();
  await page.keyboard.press('ArrowRight');
  check('ArrowRight changes the active card', (await card.locator('h1').innerText()) !== beforeTitle);
  const box = await page.locator('.ic-deck').boundingBox();
  if (box) {
    await page.mouse.move(box.x + box.width * .8, box.y + box.height / 2);
    await page.mouse.down(); await page.mouse.move(box.x + box.width * .2, box.y + box.height / 2, { steps: 8 }); await page.mouse.up();
  }
  check('keyboard and swipe do not mutate farm/planner state', traffic.mutations.length === beforeBrowse, traffic.mutations.slice(beforeBrowse));

  // All three policies are selectable cards from the same saved calculation.
  const names = new Set();
  for (let i = 0; i < 8 && await page.getByRole('button', { name: '← Previous' }).isEnabled(); i++)
    await page.getByRole('button', { name: '← Previous' }).click();
  for (let i = 0; i < 8; i++) {
    const title = await card.locator('h1').innerText();
    if (/ plan$/.test(title)) names.add(title.replace(/ plan$/, ''));
    const next = page.getByRole('button', { name: 'Next →' });
    if (await next.isDisabled()) break;
    await next.click();
  }
  check('Lean Balanced and Resilient are all available', ['Lean', 'Balanced', 'Resilient'].every(name => names.has(name)), [...names]);
  await page.getByRole('heading', { name: /Keep .+ available|is reserved/ }).waitFor();
  await shot(page, 'reservation-before-review-390');

  // Proposal must be reviewed before apply; review replaces the active card content.
  const reviewButton = page.getByRole('button', { name: 'Review reservation' });
  if (await reviewButton.count()) {
    await reviewButton.click();
    check('reservation opens explicit review before apply', /REVIEW BEFORE APPLYING/i.test(await card.innerText()), await card.innerText());
    check('review retains one card and one three-key action area', await page.locator('.ic-card').count() === 1 && await page.locator('.ic-keys > button').count() === 3);
    await shot(page, 'reservation-review-390');
    await page.getByRole('button', { name: 'Apply & recalculate' }).click();
    await page.getByRole('button', { name: 'Approve actions' }).waitFor({ timeout: 180_000 });
  }
  await page.getByRole('button', { name: 'Explain' }).click();
  const explanation = await card.innerText();
  check('saved recalculation explanation contains why tradeoff and evidence', /Why \/ tradeoff/.test(explanation) && /Evidence \/ limits/.test(explanation) && /→/.test(explanation), explanation);
  check('read/explain triggered no provider request', traffic.providers.length === 0, traffic.providers);
  await shot(page, 'reservation-explanation-390');

  // Approval and inverse remain explicit, revision-bound operations.
  const inverseReview = page.getByRole('button', { name: 'Review inverse' });
  if (await inverseReview.count()) {
    await inverseReview.click();
    check('inverse has explicit review before mutation', await page.getByRole('heading', { name: 'Restore the grow space' }).isVisible());
    await page.getByRole('button', { name: 'Confirm inverse' }).click();
    await page.getByRole('button', { name: 'Review reservation' }).waitFor({ timeout: 180_000 });
    check('inverse recalculation restores reservation eligibility', true);
  } else {
    await page.getByRole('button', { name: 'Back', exact: true }).click();
    const approve = page.getByRole('button', { name: 'Approve actions' });
    if (await approve.count()) await approve.click();
    check('approved result records sandbox-only consequence', await page.getByText(/sandbox task/i).first().waitFor({ timeout: 60_000 }).then(() => true));
  }

  // 200% zoom remains document-scrollable without a nested card trap.
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  check('200% zoom uses document scrolling', await page.evaluate(() => document.documentElement.scrollHeight > innerHeight && getComputedStyle(document.querySelector('.ic-card')).overflowY !== 'scroll'));
  await page.evaluate(() => { document.documentElement.style.zoom = '1'; });
  await page.waitForTimeout(1700);
  check('normal-motion transition is finite', await page.locator('.ic-scene.is-transitioning').count() === 0);
  check('full card journey made no automatic provider request', traffic.providers.length === 0, traffic.providers);
  check('no uncaught browser errors', traffic.errors.length === 0, traffic.errors);
  await shot(page, 'journey-final-390');
  result.mutations = traffic.mutations; result.providerRequests = traffic.providers;
  const video = page.video();
  await context.close();
  if (video) { result.video = await video.path(); }
  result.status = 'PASS';
} catch (error) {
  if (activePage && !activePage.isClosed()) await shot(activePage, 'failure-current').catch(() => {});
  result.status = 'FAIL'; result.failures.push(error?.stack || String(error)); process.exitCode = 1;
} finally {
  await browser.close();
  await writeFile(resolve(reportDir, 'browser-cards.json'), JSON.stringify(result, null, 2) + '\n');
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
}
