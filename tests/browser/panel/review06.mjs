import { mkdir, writeFile, chmod, readFile } from 'node:fs/promises'
import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'

const base = process.env.FARMTACT_BASE_URL || 'https://farmtact.fly.dev'
const out = 'apps/web/screenshots/panel/review06'
const statePath = '/tmp/farmtact-review06-state.json'
const assignedStatePath = process.env.FARMTACT_ASSIGNED_SESSION || '/tmp/farmtact-fly-persistence.json'
const resumeSaved = process.env.FARMTACT_RESUME_SAVED === '1'
const resumeScenarioId = process.env.FARMTACT_RESUME_SCENARIO_ID || ''
const result = { checks: [], errors: [], screenshots: [], build_assets: [], facts: {}, requests: { scenarios: 0, advisor: 0 } }
const check = (name, pass, detail) => result.checks.push({ name, pass: Boolean(pass), detail })
const clean = value => String(value || '').replace(/\s+/g, ' ').trim()
const snap = async (page, name) => {
  const path = `${out}/${name}.png`
  await page.screenshot({ path, animations: 'disabled', caret: 'hide' })
  result.screenshots.push(path)
}
const click = async (page, name) => page.getByRole('button', { name, exact: true }).filter({ visible: true }).first().click()

await mkdir(out, { recursive: true })
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 430, height: 932 }, hasTouch: true, isMobile: true, reducedMotion: 'reduce' })
const assignedState = JSON.parse(await readFile(assignedStatePath, 'utf8'))
if (typeof assignedState.cookie !== 'string' || !assignedState.cookie) throw new Error('Assigned persisted session is unavailable')
await context.addCookies([{ name: 'farmtact_session', value: assignedState.cookie, url: base, httpOnly: true, sameSite: 'Strict' }])
const page = await context.newPage()
page.on('pageerror', error => result.errors.push(`page: ${error.message}`))
page.on('console', message => { if (message.type() === 'error') result.errors.push(`console: ${message.text()}`) })
page.on('request', request => {
  if (request.method() === 'POST' && request.url().endsWith('/api/v1/scenarios')) result.requests.scenarios += 1
  if (request.method() === 'POST' && /\/conversations\/[^/]+\/(messages|invite|council)/.test(request.url())) result.requests.advisor += 1
})

try {
  const response = await page.goto(base, { waitUntil: 'networkidle', timeout: 60_000 })
  check('live app responds', response?.status() === 200, response?.status())
  result.build_assets = (await page.locator('script[src],link[rel="stylesheet"]').evaluateAll(nodes => nodes.map(node => node.getAttribute('src') || node.getAttribute('href')).filter(Boolean))).filter(path => path.includes('/assets/'))
  await context.storageState({ path: statePath }); await chmod(statePath, 0o600)

  await click(page, 'Data')
  await page.getByRole('heading', { name: 'See every number behind the plan.' }).waitFor()
  check('mobile has no horizontal document overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1))
  result.facts.mobile_overview = clean(await page.locator('.explorer-page').innerText()).slice(0, 2600)
  await snap(page, 'mobile-430-forecast-overview')

  const snapshot = page.getByRole('combobox', { name: 'Dataset snapshot', exact: true })
  check('reference snapshot starts selected', await snapshot.inputValue() === 'reference', await snapshot.inputValue())
  const provenance = clean(await page.getByText('Provenance', { exact: true }).locator('..').innerText())
  result.facts.provenance = provenance
  check('provenance exposes cutoff and forecast version', /Cutoff/.test(provenance) && /Forecast/.test(provenance), provenance)

  const forecastPoint = page.getByRole('button', { name: /Expected Kg/ }).first()
  await forecastPoint.focus(); await page.keyboard.press('Enter')
  const inspector = page.locator('.record-inspector').last(); await inspector.waitFor()
  result.facts.forecast_record = clean(await inspector.innerText()).slice(0, 1800)
  check('forecast point opens contributing records', /input|order|history/i.test(result.facts.forecast_record), result.facts.forecast_record)
  await snap(page, 'mobile-430-forecast-record')

  let createdBody
  if (resumeSaved) {
    await page.waitForFunction(id => [...document.querySelectorAll('[aria-label="Dataset snapshot"] option')].some(node => node.value === `scenario:${id}` || (node.textContent || '').includes('Review06 evidence')), resumeScenarioId, { timeout: 30_000 })
    const options = await snapshot.locator('option').evaluateAll(nodes => nodes.map(node => ({ value: node.value, text: node.textContent || '' })))
    const option = options.find(item => item.value === `scenario:${resumeScenarioId}`) || options.find(item => item.value.startsWith('scenario:') && item.text.includes('Review06 evidence'))
    if (!option?.value.startsWith('scenario:')) throw new Error('Previously saved Review06 scenario was not found')
    await snapshot.selectOption(option.value)
    createdBody = { id: option.value.slice('scenario:'.length) }
    check('resumed previously saved numerical scenario', true, option.text)
  } else {
    await click(page, 'Generator')
    const history = page.getByRole('spinbutton', { name: 'Historical demand multiplier numeric value', exact: true })
    const alpha = page.getByRole('spinbutton', { name: 'Forecast smoothing alpha numeric value', exact: true })
    await history.fill('120'); await alpha.fill('0.65')
    await page.getByLabel('Saved dataset name', { exact: true }).fill(`Review06 evidence ${Date.now().toString(36)}`)
    await page.waitForTimeout(1000)
    check('bounded preview reflects changed controls', Number(await history.inputValue()) === 120 && Number(await alpha.inputValue()) === 0.65)
    result.facts.generator = clean(await page.locator('.generator-layout').innerText()).slice(0, 2400)
    await snap(page, 'mobile-430-forecast-assumptions')
    const created = page.waitForResponse(r => r.url().endsWith('/api/v1/scenarios') && r.request().method() === 'POST', { timeout: 30_000 })
    await click(page, 'Save dataset and run strategies')
    const creation = await created
    check('single numerical run accepted', creation.status() === 201, creation.status())
    createdBody = await creation.json()
    await page.waitForFunction(id => document.querySelector('[aria-label="Dataset snapshot"]')?.value === `scenario:${id}`, createdBody.id, { timeout: 180_000 })
    check('completed run opens its frozen dataset', await snapshot.inputValue() === `scenario:${createdBody.id}`, await snapshot.inputValue())
  }

  await click(page, 'Experiments')
  result.facts.mobile_result = clean(await page.locator('.explorer-page').innerText()).slice(0, 4200)
  await snap(page, 'mobile-430-strategy-result')

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.reload({ waitUntil: 'networkidle', timeout: 60_000 })
  await click(page, 'Data')
  await snapshot.selectOption(`scenario:${createdBody.id}`)
  await click(page, 'Overview')
  check('saved frozen dataset reloads on desktop', await snapshot.inputValue() === `scenario:${createdBody.id}`)
  await page.getByText('Provenance', { exact: true }).waitFor()
  result.facts.desktop_overview = clean(await page.locator('.explorer-page').innerText()).slice(0, 3200)
  await snap(page, 'desktop-1280-frozen-overview')
  await click(page, 'Experiments')
  await page.getByRole('button', { name: 'Compare selected', exact: true }).waitFor()
  await click(page, 'Compare selected')
  await page.getByRole('heading', { name: 'What changed against the baseline', exact: true }).waitFor()
  const table = page.locator('.explorer-comparison-table').first()
  result.facts.comparison = clean(await table.innerText()).slice(0, 3600)
  check('desktop comparison exposes six outcome rows', await table.locator('tbody tr').count() === 6, await table.locator('tbody tr').count())
  check('comparison includes constraints and economics', /constraint/i.test(result.facts.comparison) && /margin|cash/i.test(result.facts.comparison), result.facts.comparison)
  const trace = page.getByRole('button', { name: /^Trace .* to numerical evidence$/ }).first()
  await trace.click()
  const openEvidence = page.locator(`#explorer-evidence-${createdBody.id}`)
  await openEvidence.waitFor()
  result.facts.trace = clean(await openEvidence.innerText()).slice(0, 2400)
  check('result has inspectable numerical trace', await openEvidence.getAttribute('open') !== null && result.facts.trace.length > 80, result.facts.trace)
  await snap(page, 'desktop-1280-baseline-comparison')
  check('resume added no numerical run', resumeSaved ? result.requests.scenarios === 0 : result.requests.scenarios === 1, result.requests)
  check('no advisor message sent', result.requests.advisor === 0, result.requests)
} catch (error) {
  result.errors.push(error.stack || String(error))
  await snap(page, 'failure').catch(() => {})
} finally {
  await writeFile(`${out}/observations.json`, JSON.stringify(result, null, 2) + '\n')
  await context.close().catch(() => {})
  await browser.close().catch(() => {})
}

console.log(JSON.stringify({ checks: result.checks.length, failures: result.checks.filter(item => !item.pass), errors: result.errors, assets: result.build_assets, requests: result.requests }, null, 2))
if (result.errors.length || result.checks.some(item => !item.pass)) process.exitCode = 1
