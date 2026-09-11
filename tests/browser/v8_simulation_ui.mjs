import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const baseURL = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const appURL = `${baseURL.replace(/\/$/, '')}/v8`
const reportPath = resolve(root, process.env.FARMTACT_BROWSER_REPORT || 'reports/v8/ui-browser.json')
const screenshotPath = resolve(root, 'apps/web/screenshots/v8-recorded-simulation-390.png')
const terminal = new Set(['ACCEPTED_FOR_SIMULATION', 'REVIEW_WITHHELD', 'NO_FEASIBLE_PLAN', 'FAILED', 'CANCELLED', 'STALE_INPUT'])
const report = { started_at: new Date().toISOString(), base_url: appURL, execution_policy: 'numerical-only; no paid inference', checks: [], failures: [], console_errors: [], page_errors: [], http_errors: [], screenshots: [] }

function check(name, pass, detail) {
  report.checks.push({ name, pass, ...(detail === undefined ? {} : { detail }) })
  if (!pass) report.failures.push({ name, detail })
}

async function room(page, name) {
  const accessibleName = name === 'Farm tools' ? /^(Farm tools|Tools)$/ : new RegExp(`^${name}$`)
  await page.getByRole('button', { name: accessibleName }).filter({ visible: true }).first().click()
}

async function waitForRun(page) {
  const deadline = Date.now() + 120_000
  let run
  while (Date.now() < deadline) {
    run = await page.evaluate(async () => (await (await fetch('/api/v1/bootstrap')).json()).latest_run)
    if (run && terminal.has(run.status)) return run
    await page.waitForTimeout(350)
  }
  throw new Error(`planning run did not finish; last status ${run?.status || 'missing'}`)
}

await mkdir(dirname(reportPath), { recursive: true })
await mkdir(dirname(screenshotPath), { recursive: true })
let browser
try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } })
  const page = await context.newPage()
  const proxyEdition = async route => {
    const url = new URL(route.request().url())
    url.pathname = url.pathname.replace(/^\/v8(?=\/|$)/, '') || '/'
    const response = await route.fetch({ url: url.href })
    await route.fulfill({ response })
  }
  await context.route(/\/v8(?:\/|$)/, proxyEdition)
  page.on('console', message => { if (message.type() === 'error') report.console_errors.push(message.text()) })
  page.on('pageerror', error => report.page_errors.push(error.message))
  page.on('response', response => { if (response.status() >= 400) report.http_errors.push({ status: response.status(), url: response.url() }) })
  await page.goto(appURL, { waitUntil: 'domcontentloaded' })
  await page.getByRole('navigation', { name: 'FarmTact rooms' }).first().waitFor()

  await room(page, 'Farm tools')
  const firstPlanningAction = await page.locator('.hero-actions .button').first().innerText()
  check('council is the primary planning action', firstPlanningAction.includes('Plan with DeepSeek council'), firstPlanningAction)
  check('numerical-only planning remains explicit', await page.getByRole('button', { name: 'Plan with numerical tools' }).isVisible())
  check('configuration is disclosed separately', await page.getByText('Configured route', { exact: true }).isVisible() && await page.getByText('Last observed execution', { exact: true }).isVisible())
  await page.getByRole('button', { name: 'Plan with numerical tools' }).click()
  const run = await waitForRun(page)
  check('local mission accepted for simulation', run.status === 'ACCEPTED_FOR_SIMULATION', run.status)
  check('local mission made no council call', run.council_status === 'not_run', run.council_status)

  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.getByRole('slider', { name: 'Preview simulation date' }).waitFor()
  const refreshedRunId = await page.evaluate(async () => (await (await fetch('/api/v1/bootstrap')).json()).latest_run?.id)
  check('accepted mission survives page refresh and room changes', refreshedRunId === run.id, refreshedRunId)
  const preview = page.getByRole('slider', { name: 'Preview simulation date' })
  const farm = await page.evaluate(async () => (await (await fetch('/api/v1/bootstrap')).json()).farm)
  check('preview ends on final included horizon date', Number(await preview.getAttribute('max')) === farm.horizon_days - 1, await preview.getAttribute('max'))
  const sanitation = run.strategies.find(item => item.id === run.accepted_strategy_id)?.allocations
    .map(item => ({ ...item, days: Number(farm.recipe_calendar?.[item.recipe_id]?.sanitation_days || 0) }))
    .find(item => item.days > 0 && Math.round((Date.parse(`${item.harvest_date}T00:00:00Z`) - Date.parse(`${farm.planning_date}T00:00:00Z`)) / 86400000) + 1 < farm.horizon_days)
  if (sanitation) {
    const offset = Math.round((Date.parse(`${sanitation.harvest_date}T00:00:00Z`) - Date.parse(`${farm.planning_date}T00:00:00Z`)) / 86400000) + 1
    await preview.fill(String(offset))
    check('preview uses shared sanitation calendar', await page.locator('.world-bed[aria-label*="sanitation"]').count() > 0, { recipe_id: sanitation.recipe_id, offset })
  } else check('preview uses shared sanitation calendar', false, 'accepted plan had no in-horizon sanitation day')

  await room(page, 'Outcomes')
  let firstKey = '', secondKey = '', thirdKey = '', createAttempts = 0
  await page.route('**/api/v1/simulations', async route => {
    if (route.request().method() !== 'POST') return proxyEdition(route)
    createAttempts += 1
    const key = route.request().headers()['idempotency-key'] || ''
    if (createAttempts === 1) {
      firstKey = key
      return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'synthetic uncertain response' }) })
    }
    if (createAttempts === 2) {
      secondKey = key
      return route.fulfill({ status: 429, contentType: 'application/json', headers: { 'Retry-After': '1' }, body: JSON.stringify({ detail: 'synthetic transient limit' }) })
    }
    thirdKey = key
    return proxyEdition(route)
  })
  await page.getByRole('button', { name: 'Create recorded simulation' }).click()
  await page.getByRole('alert').waitFor()
  const retained = await page.evaluate(() => Object.values(sessionStorage).some(value => value.includes('/simulations')))
  check('5xx uncertainty retains pending operation', retained && Boolean(firstKey))

  await page.reload({ waitUntil: 'domcontentloaded' })
  await room(page, 'Outcomes')
  await page.getByRole('button', { name: 'Create recorded simulation' }).click()
  await page.getByRole('alert').waitFor()
  const retainedAfter429 = await page.evaluate(() => Object.values(sessionStorage).some(value => value.includes('/simulations')))
  check('429 keeps the same uncertain operation key', retainedAfter429 && firstKey === secondKey)

  await page.reload({ waitUntil: 'domcontentloaded' })
  await room(page, 'Outcomes')
  await page.getByRole('button', { name: 'Create recorded simulation' }).click()
  await page.getByText('Recorded through', { exact: true }).waitFor()
  check('reload retry reuses idempotency key', Boolean(firstKey) && firstKey === secondKey && secondKey === thirdKey)
  const clearedAfterSuccess = await page.evaluate(() => !Object.values(sessionStorage).some(value => value.includes('/simulations')))
  check('definitive success clears pending operation', clearedAfterSuccess)

  await page.getByRole('button', { name: 'Advance 1 day' }).click()
  await page.getByText('Not started', { exact: true }).waitFor({ state: 'detached' })
  check('one-day advance records clock', await page.locator('.simulation-events li').count() >= 2, await page.locator('.simulation-events li').count())
  check('future replan available with seven or more days', await page.getByRole('button', { name: 'Replan remaining days' }).isEnabled())
  await page.getByRole('button', { name: 'Replan remaining days' }).click()
  await page.getByText(/1 recorded replans/).waitFor({ timeout: 120_000 })
  check('future replan is recorded', await page.getByText(/1 recorded replans/).isVisible())
  await page.getByRole('button', { name: 'Advance 7 days' }).click()
  await page.getByRole('button', { name: 'Advance 7 days' }).waitFor()
  check('seven-day advance remains usable after replan', await page.locator('.simulation-events li').count() > 2)
  const totals = await page.locator('.simulation-totals').innerText()
  check('execution totals are visible', ['Inventory', 'Delivered', 'Harvested', 'Cash'].every(label => totals.includes(label)), totals)
  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 })
    const dimensions = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }))
    check(`${width}px simulation has no body overflow`, dimensions.body <= dimensions.viewport + 1, dimensions)
    const path = width === 390 ? screenshotPath : resolve(root, `apps/web/screenshots/v8-recorded-simulation-${width}.png`)
    await page.screenshot({ path, animations: 'disabled', caret: 'hide', fullPage: true })
    report.screenshots.push(path.slice(root.length + 1))
  }

  for (const horizon of [7, 56, 84]) {
    const horizonPage = await context.newPage()
    await horizonPage.route('**/v8/api/v1/bootstrap', async route => {
      const response = await route.fetch({ url: `${baseURL}/api/v1/bootstrap` })
      const payload = await response.json()
      payload.farm.horizon_days = horizon
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) })
    })
    await horizonPage.goto(appURL, { waitUntil: 'domcontentloaded' })
    const slider = horizonPage.getByRole('slider', { name: 'Preview simulation date' })
    await slider.waitFor()
    check(`${horizon}-day preview uses inclusive final index`, Number(await slider.getAttribute('max')) === horizon - 1, await slider.getAttribute('max'))
    await horizonPage.close()
  }

  await page.setViewportSize({ width: 390, height: 844 })
  await room(page, 'Setup')
  await page.route('**/api/v1/imports', route => route.request().method() === 'POST'
    ? route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ detail: 'definitive validation conflict' }) })
    : route.continue())
  await page.getByRole('button', { name: 'Load synthetic demo' }).click()
  await page.getByRole('alert').waitFor()
  const clearedAfter4xx = await page.evaluate(() => !Object.values(sessionStorage).some(value => value.includes('/imports')))
  check('definitive 4xx clears pending operation', clearedAfter4xx)
  check('no uncaught page errors', report.page_errors.length === 0, report.page_errors)
  const unexpectedHttp = report.http_errors.filter(item => !(
    (item.status === 503 && item.url.endsWith('/api/v1/simulations')) ||
    (item.status === 429 && item.url.endsWith('/api/v1/simulations')) ||
    (item.status === 409 && item.url.endsWith('/api/v1/imports')) ||
    (item.status === 404 && item.url.endsWith('/api/releases')) ||
    (item.status === 404 && /\/audio\//.test(item.url))
  ))
  check('no unexpected failed browser requests', unexpectedHttp.length === 0, unexpectedHttp)
  await context.close()
} catch (error) {
  report.failures.push({ name: 'suite execution', detail: error instanceof Error ? error.stack || error.message : String(error) })
} finally {
  if (browser) await browser.close()
  report.completed_at = new Date().toISOString()
  report.status = report.failures.length ? 'FAIL' : 'PASS'
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failures: report.failures.length, report: 'reports/v8/ui-browser.json' }))
  if (report.failures.length) process.exitCode = 1
}
