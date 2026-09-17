import { readFile, writeFile } from 'node:fs/promises';
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';

const origin = (process.env.PUBLIC_URL || 'https://farmtact.fly.dev').replace(/\/$/, '');
const statePath = process.env.BROWSER_STATE;
const expectedEdition = String(process.env.EXPECTED_EDITION || 'v15').toLowerCase().replace(/^v?/, 'v');
if (!/^v(?:15|16)$/.test(expectedEdition)) throw new Error('EXPECTED_EDITION must be v15 or v16');
const reportPath = process.env.REPORT_PATH || `/tmp/farmtact-${expectedEdition}-public-verification.json`;
const editionNumber = expectedEdition.slice(1);
const cookieName = `farmtact_${expectedEdition}_session`;
const storagePrefix = `farmtact:${expectedEdition}:`;
const planningSessionKey = `${storagePrefix}planning-session`;
const argument = process.argv.find(value => value.startsWith('--expected-source='));
const expectedSource = process.env.EXPECTED_SOURCE || argument?.slice('--expected-source='.length) || process.argv[2];
if (!expectedSource || !/^[0-9a-f]{40}$/i.test(expectedSource)) throw new Error('EXPECTED_SOURCE or --expected-source=<40-character commit> is required');

if (!statePath) throw new Error('BROWSER_STATE must name a private authenticated Playwright state file');
const rawState = JSON.parse(await readFile(statePath, 'utf8'));
const sourceCookie = rawState.cookies?.find(cookie => cookie.name === cookieName);
if (!sourceCookie?.value) throw new Error('Private staged browser state has no FarmTact session cookie');
const publicState = {
  cookies: [{ ...sourceCookie, name: cookieName, domain: new URL(origin).hostname, path: '/', secure: true }],
  origins: [{ origin, localStorage: (rawState.origins || []).flatMap(item => item.localStorage || []).filter(item => item.name.startsWith(storagePrefix)) }],
};
const report = { started_at: new Date().toISOString(), origin, expected_source: expectedSource, checks: [], failures: [], widths: {} };
const check = (name, pass, detail = '') => { report.checks.push({ name, pass: Boolean(pass), detail }); if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`); };
const moduleEntry = html => [...html.matchAll(/<script[^>]+type=["']module["'][^>]+src=["']([^"']+\.js)["']/gi)].map(match => match[1])[0] || null;
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const probe = await browser.newContext({ storageState: publicState });
  const rootResponse = await probe.request.get(`${origin}/`), playResponse = await probe.request.get(`${origin}/play`);
  check('root and play respond successfully', rootResponse.ok() && playResponse.ok(), { root: rootResponse.status(), play: playResponse.status() });
  const rootEntry = moduleEntry(await rootResponse.text()), playEntry = moduleEntry(await playResponse.text());
  check('root and play serve the same built entry JavaScript', Boolean(rootEntry) && rootEntry === playEntry, { root_entry: rootEntry, play_entry: playEntry });
  const rootHealth = await probe.request.get(`${origin}/api/v1/health`), playHealth = await probe.request.get(`${origin}/api/v1/health`, { headers: { Referer: `${origin}/play` } });
  const healthA = await rootHealth.json(), healthB = await playHealth.json();
  check(`root and play health identify exact frozen V${editionNumber} source`, rootHealth.ok() && playHealth.ok() && healthA.edition === expectedEdition && healthB.edition === expectedEdition && healthA.source_commit === expectedSource && healthB.source_commit === expectedSource, { root: { edition: healthA.edition, source_commit: healthA.source_commit }, play: { edition: healthB.edition, source_commit: healthB.source_commit } });
  await probe.close();

  for (const width of [360, 390, 430, 1280]) {
    const context = await browser.newContext({ storageState: publicState, viewport: { width, height: width > 500 ? 900 : 844 }, reducedMotion: 'reduce' });
    const page = await context.newPage(), unsafeMethods = [], providers = [], errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    page.on('request', request => { if (/deepseek|openai|anthropic|provider|inference/i.test(request.url())) providers.push(new URL(request.url()).pathname); });
    await page.route('**/*', route => { const method = route.request().method(); if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) { unsafeMethods.push({ method, path: new URL(route.request().url()).pathname }); return route.abort('blockedbyclient'); } return route.continue(); });
    await page.goto(`${origin}/play`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
    await page.locator('.ic-shell').waitFor({ timeout: 30_000 });
    await page.locator('.ic-state').waitFor({ state: 'detached', timeout: 30_000 });
    await page.locator('.ic-card').waitFor({ state: 'visible', timeout: 30_000 });
    check(`${width}: exact V${editionNumber} integrated shell loads`, await page.locator(`.ic-shell[data-edition="${expectedEdition}"]`).count() === 1);
    check(`${width}: edition chooser and legacy interfaces are absent`, await page.locator('.edition-page,.edition-grid,.beginner-game,.guided-app,.tactical-console').count() === 0 && await page.getByRole('combobox', { name: /Choose FarmTact edition/i }).count() === 0);
    check(`${width}: saved current card is readable after loading settles`, await page.locator('.ic-state').count() === 0 && await page.locator('.ic-card').count() === 1 && (await page.locator('.ic-card').innerText()).trim().length > 20);
    check(`${width}: no horizontal overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth })));
    const remembered = await page.evaluate(key => localStorage.getItem(key), planningSessionKey);
    check(`${width}: saved V${editionNumber} planning session identity is retained`, Boolean(remembered), remembered || 'missing');
    const savedSession = await page.evaluate(async id => { const response = await fetch(`/api/v1/planning-sessions/${encodeURIComponent(id)}`); return { status: response.status, body: response.ok ? await response.json() : null }; }, remembered);
    check(`${width}: saved current session is readable`, savedSession.status === 200 && savedSession.body?.id === remembered, { status: savedSession.status, id: savedSession.body?.id });

    for (let i = 0; i < 10 && !(await page.getByRole('button', { name: 'More', exact: true }).filter({ visible: true }).isVisible().catch(() => false)); i++) {
      const back = page.getByRole('button', { name: 'Back', exact: true }).filter({ visible: true }).first(); if (await back.isVisible().catch(() => false)) await back.click(); else break;
    }
    const missionCard = page.locator('.ic-card');
    await page.waitForFunction(id => document.querySelector('.ic-card')?.getAttribute('data-session-id') === id, remembered, { timeout: 30_000 });
    check(`${width}: rendered mission card is bound to remembered session`, await missionCard.getAttribute('data-session-id') === remembered, { remembered, rendered: await missionCard.getAttribute('data-session-id') });
    check(`${width}: navigation normalization preserves remembered session`, await page.evaluate(({ key, id }) => localStorage.getItem(key) === id, { key: planningSessionKey, id: remembered }));
    await page.getByRole('button', { name: 'More', exact: true }).filter({ visible: true }).first().click();
    const previous = page.getByRole('button', { name: /Previous/ }).filter({ visible: true }).first();
    for (let i = 0; i < 6 && !(await previous.isDisabled()); i++) await previous.click();
    const names = [];
    for (let i = 0; i < 5; i++) { names.push((await page.locator('.ic-card h1').textContent())?.trim()); if (i < 4) await page.getByRole('button', { name: /Next/ }).filter({ visible: true }).first().click(); }
    check(`${width}: all five V${editionNumber} tools are readable`, JSON.stringify(names) === JSON.stringify(['Plan', 'Records & work', 'Knowledge & evidence', 'Experiments', 'History & preferences']), names);
    check(`${width}: tool card has no horizontal content overflow`, await page.locator('.ic-card').evaluate(node => node.scrollWidth <= node.clientWidth + 1), await page.locator('.ic-card').evaluate(node => ({ scrollWidth: node.scrollWidth, clientWidth: node.clientWidth })));
    await page.getByRole('button', { name: 'Open tool', exact: true }).click();
    await page.locator('.integrated-tool').waitFor();
    for (let i = 0; i < 7 && !(await page.getByRole('heading', { name: 'Saved plans', exact: true }).isVisible().catch(() => false)); i++) await page.getByRole('button', { name: 'Previous', exact: true }).click();
    await page.getByRole('button', { name: 'Open', exact: true }).click();
    const replay = page.getByRole('button', { name: 'Read-only replay', exact: true });
    await Promise.race([replay.waitFor(), page.getByText('No saved records', { exact: true }).waitFor()]);
    check(`${width}: saved plan replay is available`, await replay.isVisible().catch(() => false));
    await replay.click();
    await page.getByRole('heading', { name: 'Read-only saved replay', exact: true }).waitFor();
    check(`${width}: replay remains readable and explicitly read-only`, (await page.locator('.integrated-tool__card').innerText()).includes('Reading this card makes no provider calls or farm mutations.'));
    check(`${width}: replay card has no horizontal content overflow`, await page.locator('.integrated-tool__card').evaluate(node => node.scrollWidth <= node.clientWidth + 1), await page.locator('.integrated-tool__card').evaluate(node => ({ scrollWidth: node.scrollWidth, clientWidth: node.clientWidth })));
    check(`${width}: read-only verification attempted zero unsafe methods`, unsafeMethods.length === 0, unsafeMethods);
    check(`${width}: read-only verification made zero provider requests`, providers.length === 0, providers);
    check(`${width}: browser emitted no uncaught errors`, errors.length === 0, errors);
    report.widths[width] = { session_id: remembered, tool_names: names, unsafe_methods: unsafeMethods.length, provider_requests: providers.length, browser_errors: errors.length };
    await context.close();
  }
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL'; report.failures.push(error instanceof Error ? error.stack : String(error)); process.exitCode = 1;
} finally {
  report.finished_at = new Date().toISOString(); await browser?.close(); await writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
}
console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failures: report.failures }, null, 2));
