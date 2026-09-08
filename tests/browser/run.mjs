import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const baseURL = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const screenshotDir = resolve(root, 'apps/web/screenshots')
const reportPath = resolve(root, 'reports/browser.json')
const terminalStatuses = new Set(['ACCEPTED_FOR_SIMULATION', 'NO_FEASIBLE_PLAN', 'FAILED', 'CANCELLED', 'STALE_INPUT'])

const report = {
  started_at: new Date().toISOString(),
  base_url: baseURL,
  execution_policy: 'numerical-only browser missions; shared replay read-only; no paid council calls',
  checks: [],
  failures: [],
  console_errors: [],
  page_errors: [],
  screenshots: [],
  runs: {},
}

function check(name, pass, detail = undefined) {
  report.checks.push({ name, pass, ...(detail === undefined ? {} : { detail }) })
  if (!pass) report.failures.push({ name, detail })
}

async function visibleButton(page, name) {
  return page.getByRole('button', { name, exact: true }).filter({ visible: true }).first()
}

async function openRoomByKeyboard(page, name) {
  const button = await visibleButton(page, name)
  await button.focus()
  await page.keyboard.press('Enter')
  await page.waitForTimeout(80)
}

async function latestRun(page) {
  return page.evaluate(async () => {
    const response = await fetch('/api/v1/bootstrap')
    if (!response.ok) throw new Error(`bootstrap failed: ${response.status}`)
    const payload = await response.json()
    return payload.latest_run
  })
}

async function waitForLatestRun(page, expectedParent = undefined) {
  const deadline = Date.now() + 120_000
  let run = null
  while (Date.now() < deadline) {
    try {
      run = await latestRun(page)
      const parentMatches = expectedParent === undefined || run?.parent_run_id === expectedParent
      if (run && parentMatches && terminalStatuses.has(run.status)) return run
    } catch {
      // A Sprite service restart can briefly interrupt a poll; the idempotent run continues in the store.
    }
    await page.waitForTimeout(400)
  }
  throw new Error(`planning run did not finish; last status=${run?.status || 'missing'}`)
}

async function capture(page, filename) {
  const path = resolve(screenshotDir, filename)
  await page.screenshot({ path, animations: 'disabled', caret: 'hide' })
  report.screenshots.push(`apps/web/screenshots/${filename}`)
}

await mkdir(screenshotDir, { recursive: true })
let browser

try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } })
  const page = await context.newPage()
  page.on('console', message => {
    if (message.type() === 'error') report.console_errors.push(message.text())
  })
  page.on('pageerror', error => report.page_errors.push(error.message))

  const rootResponse = await page.goto(baseURL, { waitUntil: 'networkidle' })
  check('root serves application', rootResponse?.status() === 200, rootResponse?.status())
  check('DeepSeek mission action visible', await page.getByRole('button', { name: 'Plan with DeepSeek council' }).isVisible())
  check('numerical mission action visible', await page.getByRole('button', { name: 'Plan with numerical tools' }).isVisible())
  check('recorded replay action visible', await page.getByRole('button', { name: 'Replay recorded demo' }).isVisible())

  await page.getByRole('button', { name: 'Replay recorded demo' }).click()
  await page.getByText('Shared recorded demo').first().waitFor()
  check('shared replay visibly labelled', await page.getByText('This is a stored DeepSeek council result in replay mode. It is not current-time agent activity.').isVisible())
  check('shared replay has no replan action', await page.getByRole('button', { name: 'Simulate crop delay' }).count() === 0)
  check('shared replay has no worklist link', await page.getByRole('link', { name: /worklist/i }).count() === 0)
  check('shared replay leaves numerical mission available', await page.getByRole('button', { name: 'Plan with numerical tools' }).isVisible())
  const viewAll = page.getByRole('button', { name: 'View all' })
  await viewAll.focus()
  await page.keyboard.press('Enter')
  const councilDialog = page.getByRole('dialog', { name: 'Council findings' })
  await councilDialog.waitFor()
  check('shared replay exposes six stored advisor findings', await councilDialog.locator('.advisor-card').count() === 6)
  await page.keyboard.press('Escape')
  check('Escape closes council dialog', !(await councilDialog.isVisible()))
  await page.locator('.shared-replay-banner').scrollIntoViewIfNeeded()
  await capture(page, 'final-shared-replay-390.png')

  await page.getByRole('button', { name: 'Plan with numerical tools' }).click()
  const numericalRun = await waitForLatestRun(page)
  report.runs.numerical = { id: numericalRun.id, status: numericalRun.status, council_status: numericalRun.council_status }
  check('numerical mission accepted', numericalRun.status === 'ACCEPTED_FOR_SIMULATION', numericalRun.status)
  check('numerical mission skipped council', numericalRun.council_status === 'not_run', numericalRun.council_status)
  check('numerical mission returns three strategies', numericalRun.strategies?.length === 3, numericalRun.strategies?.length)
  check('Balanced selected automatically', numericalRun.strategies?.find(item => item.id === numericalRun.accepted_strategy_id)?.name === 'Balanced')
  await page.reload({ waitUntil: 'networkidle' })

  const currentFarm = await page.evaluate(async () => (await (await fetch('/api/v1/bootstrap')).json()).farm)
  const labourLabel = `Labour over ${currentFarm.horizon_days} days`
  const labourMeter = page.getByRole('meter', { name: labourLabel })
  check('labour is explicitly horizon-scoped', await labourMeter.isVisible())
  check('weekly labour label is absent', await page.getByText('Weekly labour', { exact: true }).count() === 0)
  check('labour meter uses full horizon capacity', Number(await labourMeter.getAttribute('aria-valuemax')) === currentFarm.resources.labour_hours_per_week * Math.ceil(currentFarm.horizon_days / 7))
  check('new sowing area avoids peak-occupancy claim', await page.getByText('New sowing area', { exact: true }).isVisible() && await page.getByText(/peak bed occupancy is validated separately/i).isVisible())
  await page.locator('.resource-panel').scrollIntoViewIfNeeded()
  await capture(page, 'final-plan-resources-390.png')

  const balanced = page.getByRole('button', { name: /Balanced/ }).first()
  await balanced.focus()
  await page.keyboard.press('Enter')
  const strategyDialog = page.getByRole('dialog', { name: 'Balanced strategy' })
  await strategyDialog.waitFor()
  await page.waitForTimeout(350)
  const worklistLink = strategyDialog.getByRole('link', { name: 'Download accepted worklist' })
  const worklistHref = await worklistLink.getAttribute('href')
  check('accepted strategy sheet exposes worklist', Boolean(worklistHref))
  const worklistResponse = worklistHref ? await context.request.get(`${baseURL}${worklistHref}`) : null
  const worklistText = worklistResponse ? await worklistResponse.text() : ''
  check('accepted worklist downloads', worklistResponse?.status() === 200, worklistResponse?.status())
  check('worklist is simulation-labelled CSV', worklistText.toLowerCase().includes('simulation') && worklistText.includes('crop'))
  await capture(page, 'final-balanced-sheet-390.png')
  await page.keyboard.press('Escape')
  check('Escape closes strategy dialog', !(await strategyDialog.isVisible()))

  const timelineButton = page.getByRole('button', { name: 'Timeline', exact: true })
  await timelineButton.focus()
  await page.keyboard.press('Enter')
  const timelineDialog = page.getByRole('dialog', { name: 'Harvest timeline' })
  await timelineDialog.waitFor()
  const tableButton = timelineDialog.getByRole('button', { name: 'Accessible table' })
  await tableButton.focus()
  await page.keyboard.press('Enter')
  check('timeline table alternative visible', await timelineDialog.getByRole('table').isVisible())
  check('timeline table includes allocations', await timelineDialog.locator('tbody tr').count() > 0)
  await capture(page, 'final-timeline-table-390.png')
  await page.keyboard.press('Escape')

  const eventsResponse = await context.request.get(`${baseURL}/api/v1/planning-runs/${encodeURIComponent(numericalRun.id)}/events`)
  const eventsText = await eventsResponse.text()
  check('terminal event stream is readable', eventsResponse.status() === 200 && eventsText.includes('run_started') && eventsText.includes('run_completed'), eventsResponse.status())

  const replanButton = page.getByRole('button', { name: 'Simulate crop delay' })
  await replanButton.scrollIntoViewIfNeeded()
  await replanButton.click()
  const replan = await waitForLatestRun(page, numericalRun.id)
  report.runs.replan = { id: replan.id, status: replan.status, council_status: replan.council_status, parent_run_id: replan.parent_run_id }
  check('crop-delay replan accepted', replan.status === 'ACCEPTED_FOR_SIMULATION', replan.status)
  check('replan remains numerical-only', replan.council_status === 'not_run', replan.council_status)
  check('replan is parent-linked', replan.parent_run_id === numericalRun.id)
  check('replan disruption is synthetic', replan.disruption?.origin === 'synthetic' && replan.disruption?.type === 'crop_delay')
  check('replan returns three strategies', replan.strategies?.length === 3, replan.strategies?.length)
  const staleWorklist = worklistHref ? await context.request.get(`${baseURL}${worklistHref}`) : null
  check('stale prior worklist is rejected', staleWorklist?.status() === 409, staleWorklist?.status())
  await page.reload({ waitUntil: 'networkidle' })
  await capture(page, 'final-disruption-390.png')

  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 })
    await page.goto(baseURL, { waitUntil: 'networkidle' })
    const dimensions = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }))
    check(`${width}px has no body overflow`, dimensions.body <= dimensions.viewport + 1, dimensions)
    await capture(page, `final-board-${width}.png`)
  }

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(baseURL, { waitUntil: 'networkidle' })
  await openRoomByKeyboard(page, 'Data')
  check('Data room renders current source cards', await page.locator('.source-card').count() >= 5, await page.locator('.source-card').count())
  check('Data room labels DeepSeek text capability', await page.getByText('DeepSeek text').isVisible())
  check('Data room humanizes public execution', await page.getByText('Public refresh').first().isVisible())
  await capture(page, 'final-data-390.png')

  await openRoomByKeyboard(page, 'Crops')
  const search = page.getByPlaceholder('Search crop or local alias')
  await search.fill('caixin')
  const cropCard = page.getByRole('button', { name: /Caixin/ }).first()
  await cropCard.focus()
  await page.keyboard.press('Enter')
  const cropDialog = page.getByRole('dialog', { name: 'Caixin profile' })
  await cropDialog.waitFor()
  await cropDialog.locator('.evidence-records article').first().waitFor({ timeout: 5_000 })
  check('crop detail loads evidence records', await cropDialog.locator('.evidence-records article').count() > 0)
  await cropDialog.locator('.evidence-records').scrollIntoViewIfNeeded()
  await capture(page, 'final-crop-evidence-390.png')
  await page.keyboard.press('Escape')
  check('Escape closes crop profile', !(await cropDialog.isVisible()))

  await openRoomByKeyboard(page, 'Outcomes')
  check('Outcomes labels demand fill correctly', await page.getByText('Demand filled').isVisible())
  check('owned run exposes worklist in Outcomes', await page.getByRole('link', { name: 'Download worklist' }).isVisible())
  await capture(page, 'final-outcomes-390.png')

  check('no browser console errors', report.console_errors.length === 0, report.console_errors)
  check('no uncaught page errors', report.page_errors.length === 0, report.page_errors)
  await context.close()
} catch (error) {
  report.failures.push({ name: 'suite execution', detail: error instanceof Error ? error.stack || error.message : String(error) })
} finally {
  if (browser) await browser.close()
  report.completed_at = new Date().toISOString()
  report.status = report.failures.length ? 'FAIL' : 'PASS'
  await mkdir(dirname(reportPath), { recursive: true })
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failures: report.failures.length, report: 'reports/browser.json' }))
  if (report.failures.length) process.exitCode = 1
}
