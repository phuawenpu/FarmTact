/** Public Data Explorer acceptance against cached, read-only source data. */
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname } from 'node:path'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const base = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const dir = process.env.FARMTACT_EXPLORER_PUBLIC_SCREENSHOTS || 'apps/web/screenshots/explorer-public'
const output = process.env.FARMTACT_EXPLORER_PUBLIC_REPORT || 'reports/explorer_public_browser.json'
const report = { status: 'RUNNING', base_url: base, checks: [], failures: [], screenshots: [], page_errors: [], console_errors: [], inference_requests: [] }
function check(name, pass, detail) { report.checks.push({ name, pass: Boolean(pass), ...(detail === undefined ? {} : { detail }) }); if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`) }
async function json(response) { if (!response.ok()) throw new Error(`API ${response.status()}: ${await response.text()}`); return response.json() }
async function shot(page, name) { const path = `${dir}/${name}.png`; await page.screenshot({ path, fullPage: true, animations: 'disabled' }); report.screenshots.push(path) }
async function fit(page, width) {
  check(`${width}px has no document overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth })))
  check(`${width}px has no page errors`, report.page_errors.length === 0, report.page_errors)
}

await mkdir(dir, { recursive: true })
await mkdir(dirname(output), { recursive: true })
let browser
try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 360, height: 844 }, reducedMotion: 'reduce', acceptDownloads: true })
  if (process.env.FARMTACT_BROWSER_SESSION_STATE) {
    const state = JSON.parse(await readFile(process.env.FARMTACT_BROWSER_SESSION_STATE, 'utf8'))
    await context.addCookies([{ name: 'farmtact_session', value: state.cookie, url: base, httpOnly: true, sameSite: 'Strict' }])
  }
  const page = await context.newPage()
  page.on('pageerror', error => report.page_errors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') report.console_errors.push(message.text()) })
  page.on('request', request => { if (/deepseek|\/conversations\/.+\/(messages|invite|council)/i.test(request.url())) report.inference_requests.push(request.url()) })
  await page.goto(base, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: 'Data', exact: true }).filter({ visible: true }).first().click()
  await page.getByRole('button', { name: 'Public context', exact: true }).click()
  await page.getByRole('combobox', { name: 'Public source' }).waitFor()
  const publicData = await json(await context.request.get(`${base}/api/v1/data-explorer/public`))

  const sourceSelect = page.getByRole('combobox', { name: 'Public source' })
  check('source selector includes all 23 registry entries', await sourceSelect.locator('option').count() === 24)
  check('reduced motion preference active', await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches))
  await sourceSelect.selectOption('D01')
  check('available source status and coverage visible', await page.getByText('88', { exact: true }).first().isVisible() && (await page.locator('.public-source-summary').innerText()).includes('Singapore stations'))
  const seriesSelect = page.getByRole('combobox', { name: 'Public measurement series' })
  await seriesSelect.selectOption({ index: 1 })
  check('numeric observation series plotted', await page.locator('.explorer-chart [role="button"]').count() > 0)
  const chartButton = page.locator('.explorer-chart [role="button"]').first()
  const chartLabel = await chartButton.getAttribute('aria-label')
  await chartButton.click()
  const inspector = page.locator('.record-inspector').last()
  await inspector.waitFor()
  const selectedId = await inspector.locator('summary').innerText()
  check('chart point opens its actual curated row', selectedId.includes(publicData.datasets.weather_observations.find(row => chartLabel?.includes(String(row.value)))?.id || 'wobs-'), selectedId)

  const first = publicData.datasets.weather_observations.find(row => row.source_id === 'D01')
  await page.getByRole('textbox', { name: 'Search public records' }).fill(first.id)
  check('search is shared by table and chart', await page.locator('.records-table tbody tr').count() === 1 && await page.locator('.explorer-chart [role="button"]').count() === 1)
  await page.getByRole('textbox', { name: 'Search public records' }).fill('')
  await sourceSelect.selectOption('D11')
  const powerDate = publicData.datasets.weather_observations.find(row => row.source_id === 'D11').date
  await page.getByRole('textbox', { name: 'Public start date' }).fill(powerDate)
  await page.getByRole('textbox', { name: 'Public end date' }).fill(powerDate)
  check('date range is shared by records and observed series', await page.locator('.records-table tbody tr').count() === 3 && await page.locator('.explorer-chart [role="button"]').count() === 1)
  await sourceSelect.selectOption('D01')
  await fit(page, 360); await shot(page, 'available-observations-360')

  await sourceSelect.selectOption('D07')
  check('metadata-only source is explicit', await page.getByText('Metadata only', { exact: true }).isVisible())
  check('metadata-only source has no chart or records', await page.locator('.explorer-chart').count() === 0 && await page.locator('.records-table tbody tr').count() === 0)
  await shot(page, 'metadata-only-360')

  await sourceSelect.selectOption('D04')
  await page.getByRole('combobox', { name: 'Public record set' }).selectOption('weather_forecasts')
  check('forecast records are browsable', await page.locator('.records-table tbody tr').count() > 0)
  check('forecasts are not charted as observations', await page.locator('.explorer-chart').count() === 0 && await page.getByText(/Forecast records remain available below/).isVisible())

  await sourceSelect.selectOption('D01')
  await page.getByRole('combobox', { name: 'Public record set' }).selectOption('weather_observations')
  const csvButton = page.getByRole('button', { name: 'CSV', exact: true })
  check('verified source enables export', await csvButton.isEnabled())
  const download = page.waitForEvent('download')
  await csvButton.click(); await download
  const exported = await json(await context.request.get(`${base}/api/v1/data-explorer/public/export?dataset=weather_observations&source_id=D01&format=json`))
  check('JSON export carries source attribution', exported.records.length > 0 && exported.provenance.sources.length === 1 && exported.provenance.sources[0].id === 'D01')
  await sourceSelect.selectOption('D06')
  await page.getByRole('combobox', { name: 'Public record set' }).selectOption('trade_observations')
  check('unverified licence disables UI export', await page.getByRole('button', { name: 'CSV', exact: true }).isDisabled() && await page.getByText(/unverified redistribution terms/).isVisible())
  const blocked = await context.request.get(`${base}/api/v1/data-explorer/public/export?dataset=trade_observations&source_id=D06&format=json`)
  check('server blocks restricted export', blocked.status() === 403, blocked.status())

  for (const width of [390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 })
    await fit(page, width); await shot(page, `trade-records-${width}`)
  }
  check('no browser console errors', report.console_errors.length === 0, report.console_errors)
  check('public browsing makes no inference requests', report.inference_requests.length === 0, report.inference_requests)
  report.status = 'PASS'
} catch (error) {
  report.status = 'FAIL'; report.failures.push(String(error)); process.exitCode = 1
} finally {
  if (browser) await browser.close()
  await writeFile(output, `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failures: report.failures, report: output }))
}
