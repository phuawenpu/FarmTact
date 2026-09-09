import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const baseURL = 'https://farmtact.fly.dev'
const shotDir = resolve(root, 'apps/web/screenshots/panel/review01')
const runLog = { reviewed_at: new Date().toISOString(), baseURL, checks: [], observations: {}, screenshots: [], console_errors: [], page_errors: [], numerical_runs: 0, advisor_messages: 0 }
const check = (name, pass, detail) => runLog.checks.push({ name, pass, detail })
const capture = async (page, name) => { const path = resolve(shotDir, name); await page.screenshot({ path, animations: 'disabled', caret: 'hide' }); runLog.screenshots.push(`apps/web/screenshots/panel/review01/${name}`) }

await mkdir(shotDir, { recursive: true })
const browser = await chromium.launch({ headless: true })
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce', isMobile: true, hasTouch: true })
  const page = await context.newPage()
  page.on('console', message => { if (message.type() === 'error') runLog.console_errors.push(message.text()) })
  page.on('pageerror', error => runLog.page_errors.push(error.message))
  page.on('request', request => {
    if (request.method() !== 'POST') return
    const path = new URL(request.url()).pathname
    if (/\/scenarios\/[^/]+\/run$/.test(path)) runLog.numerical_runs += 1
    if (/\/conversations\/[^/]+\/messages$/.test(path)) runLog.advisor_messages += 1
  })

  await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 60_000 })
  const assets = await page.evaluate(() => performance.getEntriesByType('resource').map(entry => new URL(entry.name).pathname).filter(path => /\/assets\/index-.*\.(js|css)$/.test(path)))
  runLog.observations.assets = assets
  runLog.observations.mobile_title = await page.locator('h1').first().textContent()
  runLog.observations.mobile_resource_text = await page.getByLabel('Farm resources').innerText()
  runLog.observations.mobile_nav_labels = await page.locator('.thumb-nav button').allTextContents()
  check('mobile touch context is active', await page.evaluate(() => matchMedia('(pointer: coarse)').matches), { viewport: await page.evaluate(() => [innerWidth, innerHeight]) })
  check('farm is clearly labelled synthetic simulation', await page.getByText(/synthetic simulation/i).first().isVisible())
  check('mobile room navigation exposes six destinations', (await page.locator('.thumb-nav button').count()) === 6)
  check('mobile page has no horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth })))
  await capture(page, 'baseline-farm-mobile-390.png')

  await page.getByRole('button', { name: 'Scenario lab', exact: true }).click()
  const lab = page.getByRole('dialog', { name: 'Scenario lab' })
  await lab.waitFor()
  await lab.getByLabel('Challenge').selectOption('busy_market')
  await lab.getByRole('button', { name: 'Review assumptions' }).click()
  const demand = lab.getByRole('slider', { name: 'Market demand' })
  await demand.fill('135')
  runLog.observations.scenario_inputs = {
    challenge: await lab.getByLabel('Challenge').inputValue(),
    demand_percent: await demand.inputValue(),
    batch: await lab.getByLabel('Selected batch').inputValue(),
    crop: await lab.getByLabel('Demand crop').inputValue(),
  }
  await capture(page, 'busy-market-assumptions-mobile-390.png')
  await lab.getByRole('button', { name: 'Run experiment' }).click()
  await lab.getByText('Inspect the trade-offs').waitFor({ timeout: 90_000 })
  const table = lab.getByRole('table')
  runLog.observations.balanced_comparison = await table.innerText()
  runLog.observations.debrief = await lab.locator('.computed-debrief').first().innerText()
  runLog.observations.scenario_status = await lab.locator('.branch-cards article').first().innerText()
  check('one numerical scenario reached comparison', await table.isVisible() && (await lab.locator('.metric-delta').count()) >= 6)
  check('branch remains explicitly simulation only or infeasible', /simulation only|infeasible/i.test(runLog.observations.scenario_status))
  check('result identifies frozen snapshot and baseline', /Snapshot .*baseline/i.test(runLog.observations.scenario_status))
  await capture(page, 'busy-market-result-mobile-390.png')

  await lab.getByRole('button', { name: 'Ask an advisor about this branch' }).click()
  const advisor = page.getByRole('dialog', { name: /Asha · Planning chair/ })
  await advisor.waitFor()
  const input = advisor.getByLabel('Message Asha')
  await input.fill('For this 35% caixin demand increase, what should I prepare this week, and which limit should make me stop?')
  await input.press('Enter')
  await page.waitForFunction(() => document.querySelectorAll('.message-card--advisor').length > 0, null, { timeout: 90_000 })
  await page.waitForTimeout(750)
  const advisorCards = advisor.locator('.message-card--advisor')
  runLog.observations.advisor_reply = await advisorCards.last().innerText()
  check('advisor produced one visible grounded response', (await advisorCards.count()) > 0, runLog.observations.advisor_reply)
  await capture(page, 'advisor-response-mobile-390.png')
  await advisor.getByRole('button', { name: 'Close' }).click()

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 60_000 })
  check('desktop side rail exposes six destinations', (await page.locator('.side-rail nav button').count()) === 6)
  check('desktop page has no horizontal overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth })))
  await capture(page, 'baseline-farm-desktop-1280.png')
  await page.getByRole('button', { name: 'Farm tools', exact: true }).click()
  await page.getByText(/Plan options|Planning mission|Strategy/i).first().waitFor()
  runLog.observations.desktop_tools_heading = await page.locator('main h1, main h2').first().textContent()
  await capture(page, 'planning-tools-desktop-1280.png')

  check('exactly one numerical run was sent', runLog.numerical_runs === 1, runLog.numerical_runs)
  check('exactly one advisor message was sent', runLog.advisor_messages === 1, runLog.advisor_messages)
  check('no uncaught page errors', runLog.page_errors.length === 0, runLog.page_errors)
  runLog.status = runLog.checks.every(item => item.pass) ? 'PASS' : 'PARTIAL'
  await context.close()
} catch (error) {
  runLog.status = 'FAILED'
  runLog.failure = error instanceof Error ? error.stack || error.message : String(error)
} finally {
  await browser.close()
  await writeFile(resolve(shotDir, 'browser-observations.json'), `${JSON.stringify(runLog, null, 2)}\n`)
  process.stdout.write(`${JSON.stringify({ status: runLog.status, checks: runLog.checks, observations: runLog.observations, counters: { numerical_runs: runLog.numerical_runs, advisor_messages: runLog.advisor_messages }, failure: runLog.failure }, null, 2)}\n`)
}
if (runLog.status === 'FAILED') process.exitCode = 1
