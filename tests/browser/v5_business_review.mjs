/** Planning-only review of the live v4 business/gameplay baseline. No inference calls. */
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'

const base = (process.env.FARMTACT_BASE_URL || 'https://farmtact.fly.dev/v4').replace(/\/$/, '')
const reportPath = process.env.FARMTACT_V5_BUSINESS_REPORT || 'reports/v5/business_browser.json'
const shots = process.env.FARMTACT_V5_BUSINESS_SHOTS || 'apps/web/screenshots/v5-business'
const assignedState = process.env.FARMTACT_BROWSER_STATE
const report = {
  status: 'RUNNING', base_url: base, session_policy: assignedState
    ? 'One assigned returning v4 review tenant, reused across the full review; no new session admitted.'
    : 'One fresh browser context, reused across the full review.',
  inference_policy: 'No advisor message, invitation or council submission. Numerical experiment only.',
  checks: [], findings: [], failures: [], screenshots: [], page_errors: [], inference_requests: [], timings_ms: {},
}
const check = (name, pass, detail) => report.checks.push({ name, pass: Boolean(pass), detail })
const finding = (priority, id, observation, evidence) => report.findings.push({ priority, id, observation, evidence })
const json = async response => { if (!response.ok()) throw new Error(`API ${response.status()}: ${await response.text()}`); return response.json() }
const api = path => `${base}/api/v1${path}`
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))

await mkdir(shots, { recursive: true })
let browser
try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 360, height: 844 }, hasTouch: true, reducedMotion: 'reduce', ...(assignedState ? { storageState: assignedState } : {}) })
  await context.addInitScript(() => {
    const NativeAudio = window.Audio
    window.__businessReviewAudio = []
    window.Audio = function (...args) {
      const audio = new NativeAudio(...args)
      window.__businessReviewAudio.push(audio)
      return audio
    }
  })
  const page = await context.newPage()
  page.on('pageerror', error => report.page_errors.push(error.message))
  page.on('request', request => {
    if (request.method() === 'POST' && /\/conversations\/[^/]+\/(messages|invite|council)$/.test(new URL(request.url()).pathname)) report.inference_requests.push(request.url())
  })

  const opened = Date.now()
  await page.goto(`${base}/`, { waitUntil: 'networkidle' })
  await page.getByRole('group', { name: 'Farm map', exact: true }).waitFor()
  report.timings_ms.first_farm_ready = Date.now() - opened
  const cookies = await context.cookies()
  check(`${assignedState ? 'assigned' : 'fresh'} edition session is established`, cookies.some(cookie => cookie.name === 'farmtact_v4_session'), cookies.map(({ name, path }) => ({ name, path })))
  check('opening line states tap-based objective', await page.getByText('Tap a bed or visit an advisor to explore the plan.', { exact: true }).isVisible())
  check('first screen exposes resources and plan count', await page.getByRole('region', { name: 'Farm resources' }).count().catch(() => 0) || await page.getByLabel('Farm resources').isVisible())
  check('seven business roles are spatially visible', await page.locator('.world-advisor').count() === 7, await page.locator('.world-advisor__name').allTextContents())
  check('simulation time is explicitly a preview', await page.getByText('Preview only — this does not advance time or create observations.', { exact: true }).isVisible())
  const date = page.getByRole('slider', { name: 'Preview simulation date' })
  check('farm time has a bounded planning horizon', Number(await date.getAttribute('max')) > 0, { min: await date.getAttribute('min'), max: await date.getAttribute('max') })
  await date.focus(); await page.keyboard.press('End')
  check('keyboard can inspect the final planning date', await date.inputValue() === await date.getAttribute('max'))
  await page.getByRole('button', { name: 'Today', exact: true }).click()
  await page.screenshot({ path: `${shots}/novice-entry-360.png`, animations: 'disabled', fullPage: true }); report.screenshots.push(`${shots}/novice-entry-360.png`)

  // Audio must decode and advance after a deliberate user action; this checks audibility plumbing, not perceived loudness.
  const sound = page.getByRole('region', { name: 'Sound controls' }).first()
  await sound.getByRole('button', { name: 'Turn sound on' }).click()
  await pause(1300)
  const audioAfter = await page.evaluate(() => window.__businessReviewAudio.map(a => ({ path: new URL(a.src).pathname, duration: a.duration, currentTime: a.currentTime, paused: a.paused, volume: a.volume, readyState: a.readyState })))
  const music = audioAfter.find(item => item.path.endsWith('/audio/farm-garden-loop.wav'))
  check('background music decodes and its playhead advances', Boolean(music && Number.isFinite(music.duration) && music.duration > 5 && music.currentTime > .2 && !music.paused), music)
  check('default music level is gentle but nonzero', Boolean(music && music.volume === .2), music?.volume)
  await page.getByRole('button', { name: 'Data', exact: true }).filter({ visible: true }).first().click()
  await page.locator('.explorer-page').waitFor()
  await pause(250)
  const audioWithEffect = await page.evaluate(() => window.__businessReviewAudio.map(a => ({ path: new URL(a.src).pathname, currentTime: a.currentTime, volume: a.volume })))
  check('navigation effect is loaded and starts after sound opt-in', audioWithEffect.some(item => item.path.endsWith('/audio/navigate.wav') && item.currentTime > 0), audioWithEffect)

  const reference = await json(await context.request.get(api('/data-explorer/snapshots/reference')))
  check('data overview names history and planning horizon', await page.getByText('History → planning horizon', { exact: true }).isVisible())
  check('planning date and full date coverage are machine-readable', Boolean(reference.planning_date && reference.date_extent?.start && reference.date_extent?.end), { planning_date: reference.planning_date, date_extent: reference.date_extent })
  const shortage = reference.records.forecast.find(row => Number(row.expected_kg) > 0 && !reference.records.batches.some(batch => batch.date === row.date && batch.crop_id === row.crop_id))
  check('novice can find a future demand point without same-day scheduled harvest', Boolean(shortage), shortage)
  if (shortage) {
    await page.getByRole('combobox', { name: 'Crop filter', exact: true }).selectOption(shortage.crop_id)
    const point = page.locator('.explorer-chart [role="button"]').filter({ hasText: '' }).first()
    await point.focus(); await page.keyboard.press('Enter')
    check('keyboard chart inspection opens contributing records', await page.locator('.record-inspector').last().isVisible())
  }
  await page.screenshot({ path: `${shots}/evidence-390.png`, animations: 'disabled', fullPage: true }); report.screenshots.push(`${shots}/evidence-390.png`)

  // One realistic numerical shock, through the visible UI.
  await page.getByRole('button', { name: 'Farm', exact: true }).filter({ visible: true }).first().click()
  await page.getByRole('button', { name: 'Quest journal', exact: true }).click()
  const journal = page.getByRole('dialog', { name: 'Quest journal' })
  await journal.waitFor()
  const busyMarket = journal.locator('.quest-list article').filter({ has: page.getByRole('heading', { name: 'Busy market', exact: true }) })
  await busyMarket.getByRole('button', { name: /Start quest|Try again/ }).click()
  const lab = page.getByRole('dialog', { name: 'Scenario lab' })
  await lab.waitFor()
  check('scenario explains frozen branch and unchanged main farm', /main farm and its latest run remain unchanged/i.test(await lab.locator('.preview-note').innerText()))
  check('scenario declares numerical operation', await lab.getByText('Numerical · no inference', { exact: true }).isVisible())
  const demandInput = lab.getByRole('slider', { name: 'Market demand', exact: true })
  await demandInput.focus(); await page.keyboard.press('Home')
  for (let value = 50; value < 130; value += 1) await page.keyboard.press('ArrowRight')
  check('market demand shock is keyboard-adjustable to an exact value', await demandInput.inputValue() === '130')
  const runStarted = Date.now()
  await lab.getByRole('button', { name: 'Run experiment', exact: true }).click()
  await lab.getByRole('heading', { name: 'Inspect the trade-offs', exact: true }).waitFor({ timeout: 180000 })
  report.timings_ms.numerical_experiment_to_results = Date.now() - runStarted
  for (const policy of ['Lean', 'Balanced', 'Resilient']) {
    await lab.getByRole('button', { name: policy, exact: true }).click()
    check(`${policy} keeps baseline and branch under the same policy`, (await lab.locator('table caption').innerText()).startsWith(`${policy} policy`))
  }
  check('comparison exposes six decision outcomes', await lab.locator('.comparison-table tbody tr').count() === 6)
  check('debrief ties changes to the frozen baseline', /same policy with the frozen baseline/i.test(await lab.locator('.computed-debrief').innerText()))
  const deliveries = await lab.getByText(/delivery dates to inspect/).allTextContents()
  check('result points back to affected beds and delivery dates', deliveries.length > 0, deliveries)
  await page.screenshot({ path: `${shots}/tradeoffs-430.png`, animations: 'disabled', fullPage: true }); report.screenshots.push(`${shots}/tradeoffs-430.png`)

  // Persistence/replay/navigation assessment in the same session.
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('group', { name: 'Farm map', exact: true }).waitFor()
  await page.getByRole('button', { name: 'Scenario lab', exact: true }).click()
  const reopened = page.getByRole('dialog', { name: 'Scenario lab' })
  await reopened.getByRole('button', { name: /3.*Compare/ }).click()
  check('saved numerical branch survives reload', await reopened.locator('.branch-picker input[type=checkbox]').count() >= 1)
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: /^(Tools|Farm tools)$/ }).filter({ visible: true }).first().click()
  check('tools page explains replay does not infer again', await page.getByText(/Replay uses the stored result with zero new inference\./).count() > 0 || await page.getByText(/evidence-grounded run/).count() > 0)
  await page.getByRole('button', { name: 'Setup', exact: true }).filter({ visible: true }).first().click()
  check('setup makes synthetic status visible', await page.getByText(/synthetic/i).count() > 0)

  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 })
    await page.getByRole('button', { name: 'Farm', exact: true }).filter({ visible: true }).first().click()
    check(`${width}px has no page-level horizontal overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth })))
    const navButtons = page.locator(width < 700 ? '.thumb-nav button' : '.side-rail nav button')
    const sizes = await navButtons.evaluateAll(nodes => nodes.map(node => { const b = node.getBoundingClientRect(); return { width: b.width, height: b.height } }))
    check(`${width}px primary navigation remains touch-sized`, sizes.every(size => size.height >= 44 && (width >= 700 || size.width >= 44)), sizes)
    const image = `${shots}/responsive-${width}.png`
    await page.screenshot({ path: image, animations: 'disabled', fullPage: true }); report.screenshots.push(image)
  }

  check('complete review made no inference submission', report.inference_requests.length === 0, report.inference_requests)
  check('complete review has no uncaught page exception', report.page_errors.length === 0, report.page_errors)

  if (report.timings_ms.first_farm_ready > 3500) finding('high', 'BIZ-01', 'The first playable farm takes long enough to weaken a 90-second judge demonstration.', { milliseconds: report.timings_ms.first_farm_ready })
  if (report.timings_ms.numerical_experiment_to_results > 12000) finding('medium', 'BIZ-02', 'A single local numerical response interrupts the game loop for a noticeable interval.', { milliseconds: report.timings_ms.numerical_experiment_to_results })
  finding('high', 'BIZ-03', 'The shortage evidence and the scenario challenge live in separate rooms; the UI does not preserve a visible “this is the shortage I am solving” thread across the transition.', { evidence_room: 'Data → Overview/Records', action_room: 'Farm → Quest journal → Scenario lab' })
  finding('high', 'BIZ-04', 'The seven agents are visible, but the numerical scenario result jumps directly to policy metrics; the specialist disagreements central to Sumin’s business thesis are not visualized in this no-inference game loop.', { result_sections: ['before/after table', 'computed debrief', 'constraint details'] })
  finding('medium', 'BIZ-05', 'Planning time is biologically bounded and honestly labelled as preview-only, but scenario completion is immediate wall-clock computation with no in-world sequence from sowing through maturity and delivery.', { planning_horizon_days: await date.getAttribute('max'), preview_copy: 'does not advance time or create observations' })
  finding('medium', 'BIZ-06', 'Audio plumbing is functional when the native playhead advances, yet the 20% default loop and navigation cue provide no visible calibration or preview before the user commits to sound.', { music })
  finding('medium', 'BIZ-07', 'A first-time player is told to explore rather than given one explicit business objective, success condition, or recommended first quest on the farm screen.', { entry_copy: 'Tap a bed or visit an advisor to explore the plan.' })

  report.status = report.checks.some(item => !item.pass) ? 'REVIEW_FINDINGS' : 'PASS_WITH_FINDINGS'
  await context.close()
} catch (error) {
  report.status = 'FAIL'
  report.failures.push(error instanceof Error ? error.stack || error.message : String(error))
  process.exitCode = 1
} finally {
  if (browser) await browser.close()
  report.completed_at = new Date().toISOString()
  await mkdir(reportPath.slice(0, reportPath.lastIndexOf('/')) || '.', { recursive: true })
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, findings: report.findings.length, failures: report.failures.length, report: reportPath }))
}
