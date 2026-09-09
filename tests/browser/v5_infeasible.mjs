/**
 * Intercepted UI contract test for an infeasible numerical scenario.
 *
 * The farm/bootstrap response and application bundle are real. Scenario and quest
 * responses are deliberately mocked so this test can exercise NO_FEASIBLE_PLAN
 * deterministically without running the planner, worker, database writes, or an
 * advisor. Every mocked result carries a visible label in the rendered UI.
 */
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const baseURL = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080/v5'
const storageState = process.env.FARMTACT_BROWSER_STATE || '/tmp/farmtact-v5-browser-state.json'
const screenshotDir = resolve(root, process.env.FARMTACT_INFEASIBLE_SCREENSHOT_DIR || 'apps/web/screenshots/v5-infeasible')
const reportPath = resolve(root, process.env.FARMTACT_INFEASIBLE_REPORT || 'reports/v5/infeasible_browser.json')
const fixtureLabel = '[MOCK NUMERICAL RESULT]'
const report = {
  started_at: new Date().toISOString(),
  base_url: baseURL,
  fixture_policy: 'The application and bootstrap are real. Scenario and quest APIs are intercepted; no planner, worker, database mutation, or advisor is used.',
  checks: [], failures: [], screenshots: [], intercepted: { scenarios: [], quests: [], news: [], conversations: [], providers: [] },
}

function check(name, pass, detail) {
  report.checks.push({ name, pass: Boolean(pass), ...(detail === undefined ? {} : { detail }) })
  if (!pass) report.failures.push({ name, detail })
}

function same(value) { return JSON.stringify(value) }

function json(route, payload, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(payload) })
}

function metrics(fillRate, margin, waste, shortfall, labour, cost) {
  return { fill_rate: fillRate, margin_sgd: margin, waste_kg: waste, shortfall_kg: shortfall, labour_hours: labour, cost_sgd: cost }
}

const baselineMetrics = metrics(0.71, 3400, 88, 260, 74, 1710)
const policyFixtures = [
  {
    policy: 'Lean',
    metrics: metrics(0.49, 2280, 42, 510, 61, 920),
    violation: { constraint_code: 'cash_limit', entity_id: 'farm_budget', required: 1900, available: 700, unit: 'SGD', severity: 'error' },
  },
  {
    policy: 'Balanced',
    metrics: metrics(0.57, 2510, 64, 430, 92, 1160),
    violation: { constraint_code: 'labour_capacity', entity_id: 'week_3', required: 92, available: 16, unit: 'hours', severity: 'error' },
  },
  {
    policy: 'Resilient',
    metrics: metrics(0.63, 2190, 103, 350, 86, 1380),
    violation: { constraint_code: 'area_capacity', entity_id: 'growing_beds', required: 520, available: 180, unit: 'm2', severity: 'error' },
  },
]

function comparisons() {
  return policyFixtures.map(item => ({
    policy: item.policy,
    baseline_strategy_id: `baseline-${item.policy.toLowerCase()}`,
    scenario_strategy_id: `fixture-${item.policy.toLowerCase()}`,
    baseline_status: 'FEASIBLE',
    scenario_status: 'INFEASIBLE',
    baseline_metrics: baselineMetrics,
    scenario_metrics: item.metrics,
    deltas: Object.fromEntries(Object.keys(item.metrics).map(key => [key, item.metrics[key] - baselineMetrics[key]])),
    violations: [item.violation],
  }))
}

function makeQuests() {
  return [
    ['late_harvest', 'Late harvest', 'Mei', 'Change a selected batch delay and expected yield.'],
    ['busy_market', 'Busy market', 'Ravi', 'Change simulated demand for an existing crop.'],
    ['short_handed_week', 'Short-handed week', 'Ben', 'Change the available weekly labour.'],
    ['tight_budget', 'Tight budget', 'Ben', 'Change the available cash without changing the main farm.'],
  ].map(([id, name, advisor, description]) => ({
    id, name, title: name, advisor_id: advisor.toLowerCase() === 'mei' ? 'mei' : advisor.toLowerCase() === 'ravi' ? 'ravi' : 'ben',
    description, status: 'available', badges: [], experiment_ids: [], inspected_ids: [],
  }))
}

function fixtureFor(width) {
  const scenarioId = `mock-infeasible-${width}`
  const fixtureName = `${fixtureLabel} Infeasible tight-budget branch`
  const quests = makeQuests()
  const scenarios = []
  const state = { scenarioId, fixtureName, quests, scenarios, scenarioPosts: [], questPosts: [] }

  const completed = body => ({
    id: scenarioId,
    name: fixtureName,
    status: 'COMPLETED',
    simulation_status: 'NO_FEASIBLE_PLAN',
    accepted_strategy_id: null,
    acceptance: null,
    inference_calls: 0,
    quest_id: body.quest_id || 'tight_budget',
    parent_scenario_id: null,
    source_conversation_id: null,
    controls: body.controls,
    input_hash: `mock-input-${width}-frozen`,
    baseline_hash: `mock-baseline-${width}-frozen`,
    affected_bed_ids: ['bed-a1', 'bed-a2'],
    affected_deliveries: [{ crop_id: 'caixin', due_date: '2026-09-16', order_id: 'mock-delivery-1' }],
    data_mode: 'synthetic_demo', execution_mode: 'test', warnings: [],
    baseline: { status: 'ACCEPTED_FOR_SIMULATION', metrics: baselineMetrics },
    result: { status: 'NO_FEASIBLE_PLAN', accepted_strategy_id: null },
    policy_comparisons: comparisons(),
    created_at: '2026-09-08T00:00:00Z', completed_at: '2026-09-08T00:00:01Z',
  })

  state.scenarioRoute = async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname.replace(/^\/v5(?=\/api\/)/, ''), method = request.method()
    let body = null
    if (method === 'POST') { try { body = request.postDataJSON() } catch { body = null } }
    report.intercepted.scenarios.push({ width, method, path, body })
    if (path === '/api/v1/scenarios' && method === 'GET') return json(route, { scenarios })
    if (path === '/api/v1/scenarios' && method === 'POST') {
      state.scenarioPosts.push(body)
      const draft = { ...completed(body), status: 'DRAFT', simulation_status: undefined, policy_comparisons: undefined }
      scenarios.splice(0, scenarios.length, draft)
      return json(route, draft, 201)
    }
    if (path === '/api/v1/scenarios/compare' && method === 'GET') return json(route, { baseline: scenarios[0]?.baseline || {}, scenarios })
    const match = path.match(/^\/api\/v1\/scenarios\/([^/]+)(?:\/(run))?$/)
    if (!match) return json(route, { detail: 'Unknown fixture scenario route' }, 404)
    if (match[1] !== scenarioId) return json(route, { detail: 'Scenario not found' }, 404)
    if (method === 'POST' && match[2] === 'run') {
      const value = completed(state.scenarioPosts.at(-1))
      scenarios.splice(0, scenarios.length, value)
      const quest = quests.find(item => item.id === value.quest_id)
      quest.status = 'experiment_complete'; quest.experiment_ids = [scenarioId]; quest.badges = ['Experiment explorer']
      return json(route, value, 202)
    }
    if (method === 'GET' && !match[2]) return json(route, scenarios[0])
    return json(route, { detail: 'Method not allowed' }, 405)
  }

  state.questRoute = async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname.replace(/^\/v5(?=\/api\/)/, ''), method = request.method()
    let body = null
    if (method === 'POST') { try { body = request.postDataJSON() } catch { body = null } }
    report.intercepted.quests.push({ width, method, path, body })
    if (path === '/api/v1/quests' && method === 'GET') return json(route, { quests })
    const match = path.match(/^\/api\/v1\/quests\/([^/]+)\/inspect$/)
    if (match && method === 'POST') {
      state.questPosts.push(body)
      if (match[1] !== 'tight_budget' || body?.scenario_id !== scenarioId) return json(route, { detail: 'Fixture quest mismatch' }, 409)
      const quest = quests.find(item => item.id === 'tight_budget')
      quest.status = 'completed'; quest.inspected_ids = [scenarioId]; quest.badges = ['Experiment explorer', 'Tradeoff discovered']
      return json(route, quest)
    }
    return json(route, { detail: 'Unknown fixture quest route' }, 404)
  }
  return state
}

async function capture(page, filename) {
  const path = resolve(screenshotDir, filename)
  await page.screenshot({ path, animations: 'disabled', caret: 'hide' })
  report.screenshots.push(relative(root, path))
}

async function runViewport(browser, width) {
  const height = width === 1280 ? 900 : 844
  const context = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce', storageState })
  const fixture = fixtureFor(width)
  const pageErrors = [], consoleErrors = [], browserRequests = [], responseErrors = []
  const providerPattern = /(?:api\.deepseek\.com|deepseek)/i
  await context.route('**/api/v1/scenarios**', route => fixture.scenarioRoute(route))
  await context.route('**/api/v1/quests**', route => fixture.questRoute(route))
  await context.route('**/api/v1/news**', route => {
    report.intercepted.news.push({ width, method: route.request().method(), url: route.request().url() })
    return json(route, { status: 'not_recorded', records: [], sources: [], total: 0, frozen: true, decision_id: fixture.scenarioId, summary: `${fixtureLabel} News evidence is unavailable for this intercepted branch.` })
  })
  await context.route('**/api/v1/conversations**', route => {
    report.intercepted.conversations.push({ width, method: route.request().method(), url: route.request().url() })
    return json(route, { detail: 'Advisor calls are outside this numerical fixture' }, 503)
  })
  await context.route('**://api.deepseek.com/**', route => {
    report.intercepted.providers.push({ width, url: route.request().url() })
    return route.abort('blockedbyclient')
  })
  const page = await context.newPage()
  page.on('pageerror', error => pageErrors.push(error.message))
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()) })
  page.on('response', response => { if (response.status() >= 400) responseErrors.push({ status: response.status(), path: new URL(response.url()).pathname }) })
  page.on('request', request => {
    const url = request.url()
    browserRequests.push(url)
    if (providerPattern.test(url)) report.intercepted.providers.push({ width, url })
  })

  await page.goto(baseURL, { waitUntil: 'networkidle' })
  const before = await page.evaluate(async () => (await fetch('/v5/api/v1/bootstrap')).json())
  check(`${width}px uses the real bootstrap farm`, await page.getByText(before.farm.name, { exact: true }).first().isVisible(), before.farm.name)

  await page.getByRole('button', { name: 'Quest journal', exact: true }).first().click()
  const journal = page.getByRole('dialog', { name: 'Quest journal' })
  const tightBudget = journal.locator('.quest-list article').filter({ hasText: 'Tight budget' })
  await tightBudget.getByRole('button', { name: 'Start quest', exact: true }).click()
  const lab = page.getByRole('dialog', { name: 'Scenario lab' })
  await lab.waitFor()
  check(`${width}px opening the numerical lab makes no advisor call`, report.intercepted.conversations.filter(item => item.width === width).length === 0)
  check(`${width}px lab identifies local numerical work`, await lab.getByText('Numerical · no inference', { exact: true }).isVisible())

  const cash = lab.getByRole('spinbutton', { name: 'Available cash numeric value', exact: true })
  await cash.fill('50')
  check(`${width}px tight-budget assumption is editable`, await cash.inputValue() === '50', await cash.inputValue())
  await lab.getByRole('button', { name: 'Run experiment', exact: true }).click()
  await lab.getByRole('heading', { name: 'Inspect the trade-offs', exact: true }).waitFor()
  const branch = lab.locator('.branch-cards article').filter({ hasText: fixture.fixtureName })
  await branch.waitFor()

  check(`${width}px fixture is visibly labelled as mocked numerical output`, await branch.getByText(fixtureLabel, { exact: false }).isVisible())
  check(`${width}px completed branch retains NO_FEASIBLE_PLAN state`, fixture.scenarios[0]?.status === 'COMPLETED' && fixture.scenarios[0]?.simulation_status === 'NO_FEASIBLE_PLAN', fixture.scenarios[0] && { status: fixture.scenarios[0].status, simulation_status: fixture.scenarios[0].simulation_status })
  check(`${width}px uses a friendly infeasible label`, await branch.getByText('Infeasible result', { exact: true }).isVisible() && await lab.getByText('NO_FEASIBLE_PLAN', { exact: true }).count() === 0)
  check(`${width}px infeasible result has no horizontal document overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth })))
  const branchControls = await branch.locator('button,summary').evaluateAll(nodes => nodes.map(node => { const box=node.getBoundingClientRect(); return { label:(node.textContent||'').trim(), height:box.height, width:box.width } }))
  check(`${width}px blocked-result controls remain touch-sized`, branchControls.every(control => control.height >= 40), branchControls)
  check(`${width}px explicitly allows learning from infeasibility`, await lab.getByText('Learning counts even when infeasible', { exact: true }).isVisible())
  check(`${width}px has no inspection badge before review`, await branch.getByRole('button', { name: 'Mark trade-offs inspected', exact: true }).isVisible() && await branch.getByRole('button', { name: 'Trade-off badge earned', exact: true }).count() === 0)

  const balancedPerspective = lab.getByRole('region', { name: 'Computed numerical perspectives for Balanced' })
  await balancedPerspective.waitFor()
  check(`${width}px actual positive shortfall warns rather than supports`, await balancedPerspective.locator('.perspective-card').filter({ hasText: 'Ravi · Demand' }).getByText('warns', { exact: true }).isVisible())
  const asha = balancedPerspective.locator('.perspective-card').filter({ hasText: 'Asha · Planner' })
  const ashaEvidence = asha.getByText('Evidence used', { exact: true })
  await ashaEvidence.click()
  const ashaText = (await asha.innerText()).replace(/\s+/g, ' ')
  check(`${width}px blocked planner evidence is structured`, !ashaText.includes('[object Object]') && /labour capacity.*week 3.*92 hours required.*16 hours available/i.test(ashaText), ashaText)

  for (const item of policyFixtures) {
    await lab.getByRole('button', { name: item.policy, exact: true }).click()
    const details = branch.locator('details').filter({ hasText: 'constraint issue' })
    if (!(await details.evaluate(node => node.open))) await details.locator('summary').click()
    const constraintText = (await details.textContent())?.replace(/\s+/g, ' ').trim() || ''
    const expectedParts = [item.violation.constraint_code.replaceAll('_', ' '), String(item.violation.required), String(item.violation.available), item.violation.unit, 'required', 'available']
    check(`${width}px ${item.policy} shows required, available, and unit`, expectedParts.every(part => constraintText.includes(part)), { constraintText, expectedParts })
    check(`${width}px ${item.policy} outcome is visibly infeasible`, await lab.locator('.comparison-table td.is-warning').count() >= 6)
  }

  await branch.getByRole('button', { name: 'Mark trade-offs inspected', exact: true }).click()
  const earned = branch.getByRole('button', { name: 'Trade-off badge earned', exact: true })
  await earned.waitFor()
  check(`${width}px infeasible inspection earns and locks the badge`, await earned.isDisabled())
  check(`${width}px inspection targets the exact completed branch`, fixture.questPosts.length === 1 && fixture.questPosts[0]?.scenario_id === fixture.scenarioId, fixture.questPosts)
  await branch.scrollIntoViewIfNeeded()
  await capture(page, `infeasible-${width}.png`)

  await lab.getByRole('button', { name: 'Close', exact: true }).click()
  await page.getByRole('button', { name: 'Quest journal', exact: true }).first().click()
  const reopened = page.getByRole('dialog', { name: 'Quest journal' }).locator('.quest-list article').filter({ hasText: 'Tight budget' })
  await reopened.getByText('Trade-off finder', { exact: true }).waitFor()
  check(`${width}px journal records experiment completion`, await reopened.getByText('Experiment complete', { exact: true }).isVisible() && await reopened.getByText('Experimenter', { exact: true }).isVisible())
  check(`${width}px journal records inspected trade-off badge`, await reopened.getByText('Trade-off finder', { exact: true }).isVisible() && await reopened.getByRole('button', { name: 'Try again', exact: true }).isVisible())

  const after = await page.evaluate(async () => (await fetch('/v5/api/v1/bootstrap')).json())
  check(`${width}px mocked branch leaves the main farm unchanged`, same(after.farm) === same(before.farm))
  check(`${width}px mocked branch leaves the latest main run unchanged`, same(after.latest_run) === same(before.latest_run))
  check(`${width}px made no conversation or provider request`, report.intercepted.conversations.filter(item => item.width === width).length === 0 && report.intercepted.providers.filter(item => item.width === width).length === 0, { conversations: report.intercepted.conversations.filter(item => item.width === width), providers: report.intercepted.providers.filter(item => item.width === width) })
  check(`${width}px scenario and quest writes stayed inside route fixtures`, fixture.scenarioPosts.length === 1 && fixture.questPosts.length === 1, { scenarioPosts: fixture.scenarioPosts.length, questPosts: fixture.questPosts.length })
  check(`${width}px browser has no page exceptions`, pageErrors.length === 0, pageErrors)
  const substantiveConsoleErrors = consoleErrors.filter(message => !/^Failed to load resource: the server responded with a status of 404/.test(message))
  check(`${width}px browser has no substantive console errors`, substantiveConsoleErrors.length === 0, { consoleErrors, responseErrors })
  check(`${width}px loaded bootstrap over the real API`, browserRequests.some(url => new URL(url).pathname.endsWith('/api/v1/bootstrap')))
  await context.close()
}

await mkdir(screenshotDir, { recursive: true })
let browser
try {
  browser = await chromium.launch({ headless: true })
  for (const width of [360, 1280]) await runViewport(browser, width)
} catch (error) {
  report.failures.push({ name: 'suite execution', detail: error instanceof Error ? error.stack || error.message : String(error) })
} finally {
  if (browser) await browser.close()
  report.completed_at = new Date().toISOString()
  report.status = report.failures.length ? 'FAIL' : 'PASS'
  await mkdir(dirname(reportPath), { recursive: true })
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
}

process.stdout.write(`${JSON.stringify({ status: report.status, checks: report.checks.length, failures: report.failures.length, report: relative(root, reportPath) })}\n`)
if (report.failures.length) process.exitCode = 1
