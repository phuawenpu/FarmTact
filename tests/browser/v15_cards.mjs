/** Actual integrated-card journey. Planner and workflow responses are never mocked. */
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { existsSync } from 'node:fs';
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';

const root = resolve(new URL('../..', import.meta.url).pathname);
const expectedEdition = String(process.env.EXPECTED_EDITION || 'v15').toLowerCase().replace(/^v?/, 'v');
if (!/^v(?:15|16)$/.test(expectedEdition)) throw new Error('EXPECTED_EDITION must be v15 or v16');
const editionNumber = expectedEdition.slice(1);
const planningSessionKey = `farmtact:${expectedEdition}:planning-session`;
const staged = process.env.STAGED_SOURCE ? await import('./v15_staged_transport.mjs').then(module => module.stagedTransport(process.env.STAGED_SOURCE)) : null;
const base = (staged ? 'http://127.0.0.1:4199' : process.env.BASE_URL || process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:4191').replace(/\/$/, '');
const reportDir = process.env.REPORT_DIR ? resolve(process.env.REPORT_DIR) : resolve(root, `reports/${expectedEdition}`);
const temporaryStorageState = process.env.STORAGE_STATE || `/tmp/farmtact-${expectedEdition}-cards-storage.json`;
const journeyWidth = Number(process.env.JOURNEY_WIDTH || 390), journeyHeight = journeyWidth > 500 ? 900 : 844;
const reportFile = process.env.REPORT_FILE || 'browser-cards.json';
const result = { status: 'RUNNING', base, width: journeyWidth, checks: [], failures: [], screenshots: [], video: null, mutations: [], providerRequests: [], ...(staged ? { stagedEvidence: staged.evidence } : {}) };
const check = (name, pass, detail) => {
  result.checks.push({ name, pass: Boolean(pass), ...(detail === undefined ? {} : { detail }) });
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`);
};
await mkdir(reportDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
let activePage;

async function shot(page, name) {
  if (name !== 'failure-current') check(`${name}: document fits the viewport`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  const path = resolve(reportDir, `${name}.png`);
  await page.screenshot({ path, fullPage: true, animations: 'disabled' });
  result.screenshots.push(process.env.REPORT_DIR ? path : `reports/${expectedEdition}/${name}.png`);
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
  let admissionFailure = null;
  page.on('response', async response => {
    if (/\/api\/v1\/bootstrap$/.test(new URL(response.url()).pathname) && response.status() === 429)
      admissionFailure = { status: 429, retryAfter: response.headers()['retry-after'], body: await response.text().catch(() => '') };
  });
  await page.goto(`${base}/play`, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  try { await page.locator('.ic-shell').waitFor({ timeout: 30_000 }); }
  catch (error) { if (admissionFailure) throw new Error(`Bootstrap admission blocked: ${JSON.stringify(admissionFailure)}`); throw error; }
  check(`shell declares ${expectedEdition}`, await page.locator(`.ic-shell[data-edition="${expectedEdition}"]`).count() === 1);
}

try {
  // Responsive read-only smoke: opening and browsing cards cannot mutate or invoke a provider.
  if (process.env.RESPONSIVE_SMOKE !== '0' && process.env.RESUME !== '1') {
    const responsiveContext = await browser.newContext({ viewport: { width: 360, height: 844 }, reducedMotion: 'reduce', ...(existsSync(temporaryStorageState) ? { storageState: temporaryStorageState } : {}) });
    if (staged) await staged.attach(responsiveContext);
    for (const width of [360, 390, 430, 1280]) {
    const page = await responsiveContext.newPage();
    await page.setViewportSize({ width, height: width > 500 ? 900 : 844 });
    const traffic = observe(page);
    await open(page);
    const mutationsAfterOpen = traffic.mutations.length;
    const parentCardTitle = await page.locator('.ic-card h1').innerText();
    const bedCount = await page.locator('.ic-beds article').count();
    check(`${width}: ordinary farm scene is not the four-bed lesson`, bedCount > 4, { bedCount });
    check(`${width}: objective retains an actual order`, /kg.+by \d{4}-\d{2}-\d{2}/i.test(await page.locator('.ic-heading').innerText()), await page.locator('.ic-heading').innerText());
    check(`${width}: exactly three contextual action keys`, await page.locator('.ic-keys > button').count() === 3);
    check(`${width}: page has no horizontal overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    const next = page.getByRole('button', { name: 'Next →' });
    if (await next.isEnabled()) await next.click();
    const originScroll = await page.evaluate(() => scrollY);
    await page.getByRole('button', { name: 'Explain' }).click();
    check(`${width}: deterministic explanation is available`, await page.getByRole('heading', { name: 'What this means' }).isVisible());
    const beforeExplainEnter = traffic.mutations.length;
    await page.locator('.ic-card').focus(); await page.keyboard.press('Enter');
    check(`${width}: Enter in explanation is read-only`, traffic.mutations.length === beforeExplainEnter && await page.getByRole('heading', { name: 'What this means' }).isVisible());
    await page.getByRole('button', { name: 'Back', exact: true }).click();
    check(`${width}: detail restores original action focus and scroll`, await page.evaluate(({ y }) => document.activeElement?.textContent?.trim() === 'Explain' && Math.abs(scrollY - y) <= 1, { y: originScroll }));
    await page.getByRole('button', { name: 'More', exact: true }).click();
    check(`${width}: five-card tool index`, (await page.locator('.ic-deck-nav').innerText()).includes('1 of 5'));
    check(`${width}: browsing made no mutation`, traffic.mutations.length === mutationsAfterOpen, traffic.mutations.slice(mutationsAfterOpen));
    check(`${width}: browsing made no provider request`, traffic.providers.length === 0, traffic.providers);
    check(`${width}: reduced motion disables animation`, await page.locator('.ic-beds').evaluate(node => getComputedStyle(node).animationName === 'none'));
    check(`${width}: no browser exception`, traffic.errors.length === 0, traffic.errors);
    await shot(page, `shell-${width}`);
    if (width === 390) {
      await page.getByRole('button', { name: 'Open tool' }).click();
      await page.locator('.integrated-tool').waitFor();
      await page.reload({ waitUntil: 'domcontentloaded' }); await page.locator('.integrated-tool').waitFor();
      check('390: reload restores the exact open tool without mutation', traffic.mutations.length === mutationsAfterOpen);
      await page.locator('.integrated-tool').getByRole('button', { name: 'Back', exact: true }).click();
    }
    await page.getByRole('button', { name: 'Back', exact: true }).click();
    await page.waitForFunction(() => document.activeElement?.textContent?.trim() === 'More');
    check(`${width}: tool index restores More focus and parent card`, await page.evaluate(() => document.activeElement?.textContent?.trim() === 'More') && (await page.locator('.ic-deck-nav').innerText()).includes('Farm plan'));
    check(`${width}: tool return preserves parent card identity`, (await page.locator('.ic-card h1').innerText()) === parentCardTitle);
      await page.close();
    }
    await responsiveContext.storageState({ path: temporaryStorageState });
    await responsiveContext.close();
  }

  const videoDir = resolve(reportDir, 'video');
  await mkdir(videoDir, { recursive: true });
  const context = await browser.newContext({ viewport: { width: journeyWidth, height: journeyHeight }, ...(existsSync(temporaryStorageState) ? { storageState: temporaryStorageState } : {}), recordVideo: { dir: videoDir, size: { width: journeyWidth, height: journeyHeight } } });
  if (staged) await staged.attach(context);
  const page = await context.newPage(); activePage = page;
  const traffic = observe(page);
  await open(page);
  if (process.env.FRESH_SESSION === '1') {
    const fresh = await page.evaluate(async ({ width, edition }) => {
      const response = await fetch('/api/v1/planning-sessions', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({ name: `V${edition} complete ${width}px journey`, workflow: true }) });
      if (!response.ok) throw new Error(await response.text());
      return response.json();
    }, { width: journeyWidth, edition: editionNumber });
    await page.evaluate(({ key, id }) => localStorage.setItem(key, id), { key: planningSessionKey, id: fresh.id });
    await context.storageState({ path: temporaryStorageState });
    await page.reload({ waitUntil: 'domcontentloaded' }); await page.locator('.ic-shell').waitFor();
    await page.waitForFunction(id => document.querySelector('.ic-card')?.getAttribute('data-session-id') === id && !document.querySelector('[role="status"]'), fresh.id, { timeout: 30_000 });
  }
  if (await page.locator('.integrated-tool').count()) await page.locator('.integrated-tool').getByRole('button', { name: 'Back', exact: true }).click();
  if ((await page.locator('.ic-deck-nav').innerText()).includes('Farm tools')) await page.getByRole('button', { name: 'Back', exact: true }).click();
  const card = page.locator('.ic-card');

  // Guide skip is persisted by the server and survives reload independently of planner revision.
  await page.getByRole('button', { name: 'Explain' }).click();
  const skip = page.getByRole('button', { name: 'Skip guide' });
  if (await skip.count()) {
    const sessionId = await card.getAttribute('data-session-id');
    const [guidanceResponse] = await Promise.all([
      page.waitForResponse(response => response.request().method() === 'POST' && /\/guidance$/.test(new URL(response.url()).pathname)),
      page.waitForResponse(response => response.request().method() === 'GET' && new URL(response.url()).pathname.endsWith(`/planning-sessions/${sessionId}`) && response.ok()),
      skip.click(),
    ]);
    check('guide skip mutation is accepted before reconciliation', guidanceResponse.ok(), { status: guidanceResponse.status() });
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
  await page.waitForTimeout(1200);

  // Calculate if this tenant has no saved ordinary result yet.
  const counterBeforePlan = await page.locator('.ic-deck-nav').innerText();
  if (/1 of 1\b/.test(counterBeforePlan)) {
    await page.locator('.ic-keys .is-primary').click();
    await page.waitForFunction(() => {
      const button = document.querySelector('.ic-deck-nav button:last-child');
      return button && !button.disabled;
    }, null, { timeout: 210_000 });
  }
  for (let i = 0; i < 8 && !await page.getByText('Preview—not saved', { exact: true }).count(); i++) {
    const previous = page.getByRole('button', { name: '← Previous' });
    if (await previous.isEnabled()) await previous.click(); else {
      const next = page.getByRole('button', { name: 'Next →' });
      if (await next.isEnabled()) await next.click(); else break;
    }
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
  for (let i = 0; i < 8 && !/Keep .+ available|is reserved/i.test(await card.locator('h1').innerText()); i++)
    await page.getByRole('button', { name: '← Previous' }).click();
  await page.getByRole('heading', { name: /Keep .+ available|is reserved/ }).waitFor();
  await shot(page, `reservation-before-review-${journeyWidth}`);

  // Proposal must be reviewed before apply; review replaces the active card content.
  const reviewButton = page.getByRole('button', { name: 'Review reservation' });
  if (await reviewButton.count()) {
    await reviewButton.click();
    await page.waitForFunction(() => /REVIEW BEFORE APPLYING/i.test(document.querySelector('.ic-card')?.textContent || ''), null, { timeout: 30_000 });
    check('reservation opens explicit review before apply', /REVIEW BEFORE APPLYING/i.test(await card.innerText()), await card.innerText());
    check('review retains one card and one three-key action area', await page.locator('.ic-card').count() === 1 && await page.locator('.ic-keys > button').count() === 3);
    await shot(page, `reservation-review-${journeyWidth}`);
    await page.getByRole('button', { name: 'Apply & recalculate' }).click();
    await page.getByRole('button', { name: 'Approve actions' }).waitFor({ timeout: 180_000 });
  }
  await page.getByRole('button', { name: 'Explain' }).click();
  const explanation = await card.innerText();
  check('saved recalculation explanation contains five structured facts and allocation evidence',
    ['What changed', 'Why', 'Tradeoff', 'Evidence / limits', 'Next action'].every(label => explanation.includes(label))
      && /bed-\d+/.test(explanation) && /\d{4}-\d{2}-\d{2}→\d{4}-\d{2}-\d{2}/.test(explanation), explanation);
  check('read/explain triggered no provider request', traffic.providers.length === 0, traffic.providers);
  await shot(page, `reservation-explanation-${journeyWidth}`);

  // Approval and inverse remain explicit, revision-bound operations.
  const inverseReview = page.getByRole('button', { name: 'Review inverse' });
  if (await inverseReview.count()) {
    await inverseReview.click();
    check('inverse has explicit review before mutation', await page.getByRole('heading', { name: 'Restore the grow space' }).isVisible());
    await page.getByRole('button', { name: 'Confirm inverse' }).click();
    await page.getByRole('button', { name: 'Review reservation' }).waitFor({ timeout: 180_000 });
    check('inverse recalculation restores reservation eligibility', true);
    await page.getByRole('button', { name: 'Review reservation' }).click();
    await page.waitForFunction(() => /REVIEW BEFORE APPLYING/i.test(document.querySelector('.ic-card')?.textContent || ''), null, { timeout: 30_000 });
    await page.getByRole('button', { name: 'Apply & recalculate' }).click();
    await page.getByRole('button', { name: 'Approve actions' }).waitFor({ timeout: 180_000 });
    await page.getByRole('button', { name: 'Approve actions' }).click();
    await page.waitForFunction(() => {
      const button = document.querySelector('.ic-deck-nav button:last-child'); return button && !button.disabled;
    }, null, { timeout: 60_000 });
    await page.getByRole('button', { name: 'Next →' }).click();
    await page.getByText(/sandbox task/i).first().waitFor({ timeout: 30_000 });
    check('approval creates persisted sandbox-only tasks', traffic.mutations.some(path => /\/approve-actions$/.test(path)));

    // Advance the approved simulation through the History cards, then return to the same shell.
    await page.getByRole('button', { name: 'More', exact: true }).click();
    for (let i = 0; i < 4; i++) await page.getByRole('button', { name: 'Next →' }).click();
    await page.getByRole('button', { name: 'Open tool' }).click();
    await page.getByRole('heading', { name: 'Saved plans' }).waitFor();
    await page.getByRole('button', { name: 'Open', exact: true }).click();
    await page.getByRole('button', { name: 'Read-only replay' }).click();
    await page.getByRole('button', { name: 'Saved versions' }).click();
    await page.getByRole('button', { name: 'Review time advance' }).click();
    await page.getByLabel('Days to advance').selectOption('7');
    const [advanceResponse] = await Promise.all([
      page.waitForResponse(response => response.request().method() === 'POST' && /\/planning-sessions\/[^/]+\/advance$/.test(new URL(response.url()).pathname) && response.ok(), { timeout: 60_000 }),
      page.getByRole('button', { name: 'Advance seven days' }).click(),
    ]);
    const advancedSession = await advanceResponse.json(); const advancedWorld = advancedSession.simulation;
    check('explicit History advance returns recorded simulation facts', advancedWorld.simulation_only === true && advancedWorld.clock_date && advancedWorld.beds?.length, advancedWorld);
    await page.getByRole('button', { name: 'Back', exact: true }).click(); // replay → list
    await page.getByRole('button', { name: 'Back', exact: true }).click(); // list → index
    await page.getByRole('button', { name: 'Back', exact: true }).click(); // history → tools
    await page.getByRole('button', { name: 'Back', exact: true }).click(); // tools → shell
    await page.waitForFunction(date => document.querySelector('.ic-scene-head strong')?.textContent === date, advancedWorld.clock_date, { timeout: 30_000 });
    const sceneText = await page.locator('.ic-scene').innerText();
    check('scene reloads recorded clock and server simulation bed state', sceneText.includes(advancedWorld.clock_date)
      && sceneText.toLowerCase().includes(String(advancedWorld.beds[0].stage).toLowerCase())
      && (!advancedWorld.beds[0].crop_id || sceneText.toLowerCase().includes(String(advancedWorld.beds[0].crop_id).replaceAll('_', ' ').toLowerCase())), { sceneText, bed: advancedWorld.beds[0] });
    check('recorded consequence transition remains factual and provider-free', /Recorded simulation/.test(sceneText) && traffic.providers.length === 0, sceneText);
  } else {
    await page.getByRole('button', { name: 'Back', exact: true }).click();
    const approve = page.getByRole('button', { name: 'Approve actions' });
    const alreadyHasTask = await page.getByRole('button', { name: 'Next →' }).isEnabled();
    if (!alreadyHasTask && await approve.count()) { await approve.click(); await page.waitForFunction(() => { const button=document.querySelector('.ic-deck-nav button:last-child');return button&&!button.disabled; }, null, { timeout: 60_000 }); }
    const next = page.getByRole('button', { name: 'Next →' }); if (await next.isEnabled()) await next.click();
    check('approved result records sandbox-only consequence', await page.getByText(/sandbox task/i).first().waitFor({ timeout: 30_000 }).then(() => true));

    await page.getByRole('button', { name: 'More', exact: true }).click();
    for (let i = 0; i < 4; i++) await page.getByRole('button', { name: 'Next →' }).click();
    await page.getByRole('button', { name: 'Open tool' }).click();
    await page.getByRole('heading', { name: 'Saved plans' }).waitFor();
    await page.getByRole('button', { name: 'Open', exact: true }).click();
    await page.getByRole('button', { name: 'Read-only replay' }).click(); await page.getByRole('button', { name: 'Saved versions' }).click(); await page.getByRole('button', { name: 'Review time advance' }).click();
    await page.getByLabel('Days to advance').selectOption('7');
    const [advanceResponse] = await Promise.all([page.waitForResponse(response => response.request().method() === 'POST' && /\/planning-sessions\/[^/]+\/advance$/.test(new URL(response.url()).pathname) && response.ok(), { timeout: 60_000 }), page.getByRole('button', { name: 'Advance seven days' }).click()]);
    const advancedSession = await advanceResponse.json(); const advancedWorld = advancedSession.simulation;
    await page.getByRole('button', { name: 'Back', exact: true }).click(); await page.getByRole('button', { name: 'Back', exact: true }).click(); await page.getByRole('button', { name: 'Back', exact: true }).click(); await page.getByRole('button', { name: 'Back', exact: true }).click();
    await page.waitForFunction(date => document.querySelector('.ic-scene-head strong')?.textContent === date, advancedWorld.clock_date, { timeout: 30_000 });
    const sceneText = await page.locator('.ic-scene').innerText();
    check('scene reloads recorded clock and server simulation bed state', sceneText.includes(advancedWorld.clock_date) && sceneText.toLowerCase().includes(String(advancedWorld.beds[0].stage).toLowerCase()), { sceneText, bed: advancedWorld.beds[0] });
    check('recorded consequence transition remains factual and provider-free', /Recorded simulation/.test(sceneText) && traffic.providers.length === 0, sceneText);
  }

  // 200% zoom remains document-scrollable without a nested card trap.
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  check('200% zoom uses document scrolling', await page.evaluate(() => document.documentElement.scrollHeight > innerHeight && getComputedStyle(document.querySelector('.ic-card')).overflowY !== 'scroll'));
  await page.evaluate(() => { document.documentElement.style.zoom = '1'; });
  await page.waitForTimeout(1700);
  check('normal-motion transition is finite', await page.locator('.ic-scene.is-transitioning').count() === 0);
  if (await page.locator('.ic-saved-change').count()) {
    const recordedFacts = await page.locator('.ic-saved-change').innerText();
    await page.emulateMedia({ reducedMotion: 'reduce' }); await page.reload({ waitUntil: 'domcontentloaded' }); await page.locator('.ic-shell').waitFor();
    check('reduced motion retains the same recorded consequence facts', (await page.locator('.ic-saved-change').innerText()) === recordedFacts && await page.locator('.ic-beds').evaluate(node => getComputedStyle(node).animationName === 'none'), recordedFacts);
    await shot(page, `recorded-consequence-reduced-${journeyWidth}`);
  }
  if (process.env.RESUME !== '1' || process.env.FRESH_SESSION === '1') {
    check('fresh journey persisted proposal apply inverse and approval mutations',
      traffic.mutations.some(path => /\/farm-workflow\/proposals$/.test(path))
        && traffic.mutations.some(path => /\/apply$/.test(path))
        && traffic.mutations.some(path => /\/inverse$/.test(path))
        && traffic.mutations.some(path => /\/approve-actions$/.test(path)), traffic.mutations);
  }
  check('full card journey made no automatic provider request', traffic.providers.length === 0, traffic.providers);
  check('no uncaught browser errors', traffic.errors.length === 0, traffic.errors);
  if (staged) {
    const health = await page.evaluate(async () => { const response = await fetch('/api/v1/health'); if (!response.ok) throw new Error(`Health ${response.status}`); return response.json(); });
    result.stagedHealth = { edition: health.edition || null, source_commit: health.source_commit || null, status: health.status || null };
    check('staged health matches the pinned source and expected edition', health.source_commit === process.env.STAGED_SOURCE && health.edition === expectedEdition, result.stagedHealth);
    check('staged private transport completed without failures', staged.evidence.failures.length === 0, staged.evidence.failures);
  }
  await shot(page, `journey-final-${journeyWidth}`);
  result.mutations = traffic.mutations; result.providerRequests = traffic.providers;
  const video = page.video();
  await context.storageState({ path: temporaryStorageState });
  await context.close();
  if (video) { result.video = await video.path(); }
  result.status = 'PASS';
} catch (error) {
  if (activePage && !activePage.isClosed()) await shot(activePage, 'failure-current').catch(() => {});
  result.status = 'FAIL'; result.failures.push(error?.stack || String(error)); process.exitCode = 1;
} finally {
  await browser.close();
  await writeFile(resolve(reportDir, reportFile), JSON.stringify(result, null, 2) + '\n');
  process.stdout.write(JSON.stringify(result, null, 2) + '\n');
}
