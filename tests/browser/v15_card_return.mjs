import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';
import { writeFile } from 'node:fs/promises';
const base = process.env.BASE_URL || 'http://127.0.0.1:4196';
const report = { base, checks: [], failures: [] };
const check = (name, pass) => { report.checks.push({ name, pass }); if (!pass) throw Error(name); };
let page;
const browser = await chromium.launch({ headless: true });
try {
  // Reuse the separately created local scenario tenant; this test only reads it.
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, storageState: `/tmp/farmtact-v15-scenarios-${new URL(base).port}.json` });
  page = await context.newPage();
  page.on('console', msg => { if(msg.type() === 'error') console.log(msg.text()); });
  let writes = 0;
  page.on('request', request => { if (request.method() === 'POST') writes++; });
  await page.goto(base); await page.locator('.ic-shell').waitFor();
  const click = name => page.getByRole('button', { name, exact: true }).filter({ visible: true }).click();
  for(let i=0;i<6&&!await page.getByRole('button',{name:'More',exact:true}).isVisible();i++)await click('Back');
  await click('More'); await click('Open tool');
  const capture = async () => {
    await page.getByRole('button', { name: 'Open', exact: true }).scrollIntoViewIfNeeded();
    await page.getByRole('button', { name: 'Open', exact: true }).focus();
    await page.waitForTimeout(100);
    return page.evaluate(() => window.scrollY);
  };
  const planScroll = await capture();
  await click('Open'); await page.getByRole('heading', { name: 'Objectives and all demand' }).waitFor();
  await click('Review demand changes'); await page.getByText('Import saved settings',{exact:true}).waitFor(); await click('Back');
  await page.getByRole('heading', { name: 'Objectives and all demand' }).waitFor(); await page.waitForTimeout(100);
  check('Demand editor Back restores the originating objective and action focus', await page.getByRole('button', { name: 'Review demand changes', exact: true }).evaluate(e => e === document.activeElement));
  await click('Back'); await page.waitForTimeout(100);
  check('Plan Back restores original action focus', await page.getByRole('button', { name: 'Open', exact: true }).evaluate(e => e === document.activeElement));
  check('Plan Back restores scroll', Math.abs(await page.evaluate(() => window.scrollY) - planScroll) < 3);
  await click('Back');
  await page.locator('.ic-path').waitFor();
  for (let i = 0; i < 4; i++) await page.getByRole('button', { name: /Next/ }).filter({ visible: true }).click();
  await page.locator('.ic-path').filter({ hasText: 'History & preferences' }).waitFor();
  await click('Open tool');
  const historyScroll = await capture();
  await click('Open'); await click('Read-only replay');
  await page.getByRole('heading', { name: 'Read-only saved replay' }).waitFor();
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await click('Back'); await page.waitForTimeout(100);
  check('History replay Back restores replay action focus', await page.getByRole('button', { name: 'Read-only replay', exact: true }).evaluate(e => e === document.activeElement));
  await click('Back'); await page.waitForTimeout(100);
  check('History list Back restores Open focus', await page.getByRole('button', { name: 'Open', exact: true }).evaluate(e => e === document.activeElement));
  check('History list Back restores original scroll', Math.abs(await page.evaluate(() => window.scrollY) - historyScroll) < 3);
  check('Reading and returning performs zero writes', writes === 0);
} catch (error) { report.failures.push(String(error)); if(page) report.last_card = await page.locator('.ic-shell').innerText().catch(() => 'unavailable'); process.exitCode = 1; }
finally { report.status = report.failures.length ? 'FAIL' : 'PASS'; await browser.close(); await writeFile('reports/v15/card-return-browser.json', JSON.stringify(report, null, 2)); console.log(JSON.stringify(report, null, 2)); }
