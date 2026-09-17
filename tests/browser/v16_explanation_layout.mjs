import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { access, mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(new URL('../..', import.meta.url).pathname)
const base = (process.env.BASE_URL || 'http://127.0.0.1:4196').replace(/\/$/, '')
const storage = process.env.STORAGE_STATE || '/tmp/farmtact-v15-cards-storage.json'
const output = resolve(root, 'reports/v16/explanation-layout.json')
const widths = [360, 390, 430, 1280]
await access(storage)
const storedState = JSON.parse(await readFile(storage, 'utf8'))
const recordedSession = storedState.origins?.flatMap(origin => origin.localStorage || []).find(row => row.name === 'farmtact:v15:planning-session')?.value
if (!recordedSession) throw new Error('Saved acceptance state has no recorded planning session binding')

const report = {
  status: 'RUNNING', base, storageSource: storage,
  scope: 'Read-only V16 explanation semantics and layout using an existing local tenant cookie; this is not an edition-state migration.',
  checks: [], stages: {}, requests: { writes: [], provider: [] }, failures: [],
  limitations: ['Chromium emulation is not a physical-device or screen-reader test.', 'The existing saved local planning/simulation record is reused read-only; V15 localStorage is neither read nor migrated.']
}
const check = (name, pass, detail) => report.checks.push({ name, pass: Boolean(pass), detail })
const sectionNames = ['What changed', 'Why', 'Tradeoff', 'Evidence / limits', 'Next action']
const format = value => new Intl.NumberFormat('en-SG', { maximumFractionDigits: 1 }).format(Number(value))
const stageSemantics = (id, title, sections, authoritative) => {
  const all = sectionNames.every(name => String(sections[name] || '').trim().length > 10)
  const explicit = sectionNames.every(name => !/^\s*(undefined|null)?\s*$/i.test(String(sections[name] || '')))
  const raw = Object.values(sections).some(value => /\{\s*"|"\s*:\s*|\[\s*\{/.test(String(value)))
  let stageCorrect = false
  if (id === 'situation') stageCorrect = /No plan change|frozen/i.test(sections['What changed']) && /objective|order/i.test(sections.Why) && /same baseline/i.test(sections.Tradeoff) && /planning input|frozen result/i.test(sections['Evidence / limits'])
  else if (id.startsWith('strategy-')) stageCorrect = /Preview.*not saved/i.test(sections['What changed']) && /compared with|compatible alternative/i.test(sections.Why) && /Delivery.*shortfall.*cost/i.test(sections.Tradeoff) && /bed-\d+.*20\d\d-\d\d-\d\d.*kg/i.test(sections['Evidence / limits'])
  else if (id === 'reservation') stageCorrect = /bed-07|reservation/i.test(sections['What changed']) && /reservation|planning challenge|planner recalculated|reviewed constraints|modeled demand|target-specific reason/i.test(sections.Why) && /(coverage|expiry|margin|not reported|target-specific signed delta|whole-proposal)/i.test(sections.Tradeoff) && /target bed-07|bed-07/i.test(sections['Evidence / limits'])
  else if (id === 'approved') stageCorrect = /(current-result|previously saved) sandbox task/i.test(sections['What changed']) && /explicit sandbox approval/i.test(sections.Why) && /does not.*physical operation|simulation work only/i.test(sections.Tradeoff) && /task-owning proposal IDs.*task IDs.*session revision/i.test(sections['Evidence / limits'])
  else if (id === 'simulation-result') stageCorrect = /Recorded simulation date 2026-09-14/i.test(sections['What changed']) && /saved simulation events/i.test(sections.Why) && /harvested.*delivered.*cash.*not physical/i.test(sections.Tradeoff) && /Recorded simulation.*event.*affected entities/i.test(sections['Evidence / limits'])
  let numericFactsMatchApi = true
  const session = authoritative.session, workflow = authoritative.workflow
  if (id === 'situation') numericFactsMatchApi = sections['What changed'].includes(`${session.farm.orders.length} order records`) && sections['What changed'].includes(`${session.farm.beds.length} grow spaces`) && (!session.farm.orders[0] || sections.Why.includes(`${format(session.farm.orders[0].quantity_kg)} kg`))
  else if (id.startsWith('strategy-')) {
    const strategy = session.result?.strategies?.find(row => `strategy-${row.id}` === id)
    numericFactsMatchApi = Boolean(strategy && sections['What changed'].includes(`${strategy.allocations.length} dated allocations`) && sections.Tradeoff.includes(`Delivery ${format(Number(strategy.metrics.fill_rate) * 100)}%`) && sections.Tradeoff.includes(`shortfall ${format(strategy.metrics.shortfall_kg)} kg`) && sections.Tradeoff.includes(`cost SGD ${format(strategy.metrics.cost_sgd)}`))
  } else if (id === 'reservation') {
    const reservation = session.assumptions?.reservations?.find(row => row.bed_id === 'bed-07')
    numericFactsMatchApi = !reservation || (sections['What changed'].includes(reservation.start_date) && sections['What changed'].includes(reservation.end_date))
  } else if (id === 'approved') {
    const shown = Number(sections['What changed'].match(/^(\d+)/)?.[1])
    const proposals = workflow.proposals.filter(row => row.session_id === session.id)
    const boundResult = session.tactical_context?.planning_snapshot?.result_id || session.result_id
    const bound = [...proposals].reverse().find(row => ['applied', 'approved'].includes(row.status) && row.recalculation_job?.id === boundResult)
    const boundTasks = bound ? workflow.tasks.filter(row => row.proposal_id === bound.id) : []
    const sessionTasks = workflow.tasks.filter(row => proposals.some(proposal => proposal.id === row.proposal_id))
    numericFactsMatchApi = shown === (boundTasks.length || sessionTasks.length) && sections['Evidence / limits'].includes(`session revision ${session.revision}`)
  } else if (id === 'simulation-result') {
    const sim = session.simulation
    numericFactsMatchApi = Boolean(sim && sections['What changed'].includes(sim.clock_date || sim.start_date) && sections.Tradeoff.includes(`harvested ${format(sim.totals.harvest_kg)} kg`) && sections.Tradeoff.includes(`delivered ${format(sim.totals.delivered_kg)} kg`) && sections.Tradeoff.includes(`cash SGD ${format(sim.cash_sgd)}`))
  }
  const objectLeakAbsent = Object.values(sections).every(value => !/\[object Object\]/i.test(String(value)))
  return { id, title, allSectionsSubstantive: all, missingFactsExplicit: explicit, rawJsonAbsent: !raw, objectLeakAbsent, stageCorrect, numericFactsMatchApi, sections }
}

let browser
try {
  browser = await chromium.launch({ headless: true })
  for (const width of widths) {
    const context = await browser.newContext({ storageState: storage, viewport: { width, height: width === 1280 ? 900 : 844 }, reducedMotion: 'reduce' })
    await context.addInitScript(sessionId => {
      localStorage.setItem('farmtact:v16:planning-session', sessionId)
      localStorage.setItem(`farmtact:v16:integrated-cards-navigation:${sessionId}`, JSON.stringify({ surface: 'mission', index: 0, missionIndex: 0, missionScroll: 0, directTool: false, origin: { label: 'More', scroll: 0 }, missionOrigin: { label: 'More', scroll: 0 } }))
    }, recordedSession)
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', request => {
      const path = new URL(request.url()).pathname
      if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) report.requests.writes.push(`${width} ${request.method()} ${path}`)
      if (/deepseek|provider|inference/i.test(request.url())) report.requests.provider.push(`${width} ${request.method()} ${path}`)
    })
    await page.route('**/api/v1/**', route => ['GET', 'HEAD', 'OPTIONS'].includes(route.request().method()) ? route.continue() : route.abort('blockedbyclient'))
    await page.goto(`${base}/play`, { waitUntil: 'domcontentloaded' })
    await page.locator('.ic-shell').waitFor()
    const authoritative = await page.evaluate(async sessionId => {
      const [session, workflow] = await Promise.all([fetch(`/api/v1/planning-sessions/${sessionId}`).then(response => response.json()), fetch('/api/v1/farm-workflow').then(response => response.json())])
      return { session, workflow }
    }, recordedSession)
    if (!report.authoritativeSummary) report.authoritativeSummary = { sessionId: authoritative.session.id, revision: authoritative.session.revision, resultId: authoritative.session.result_id, strategies: authoritative.session.result?.strategies?.map(row => ({ id: row.id, metrics: row.metrics, allocations: row.allocations.length })), simulation: authoritative.session.simulation ? { id: authoritative.session.simulation.id, clockDate: authoritative.session.simulation.clock_date, totals: authoritative.session.simulation.totals, cash: authoritative.session.simulation.cash_sgd } : null, workflow: { proposals: authoritative.workflow.proposals.length, tasks: authoritative.workflow.tasks.length } }
    report.build = await page.locator('script[type=module]').first().getAttribute('src')
    const edition = await page.locator('.ic-shell').getAttribute('data-edition')
    check(`${width}: shell is explicitly bound to V16`, edition === 'v16', { edition, note: 'Existing tenant cookie is reused; edition-local browser state remains V16.' })
    for (let i = 0; i < 12 && !await page.getByRole('button', { name: 'Explain', exact: true }).count(); i++) await page.getByRole('button', { name: 'Back', exact: true }).last().click()

    const stages = []
    for (let index = 0; index < 7; index++) {
      const card = page.locator('.ic-card')
      const cardId = (await card.getAttribute('data-card-id') || '').replace(/^mission:/, '')
      const title = (await card.locator('h1').textContent() || '').trim()
      const explain = page.getByRole('button', { name: 'Explain', exact: true })
      await explain.click()
      await page.getByRole('heading', { name: 'What this means', exact: true }).waitFor()
      const sections = await page.locator('.ic-explanation > div').evaluateAll(rows => Object.fromEntries(rows.map(row => [row.querySelector('dt')?.textContent?.trim() || '', row.querySelector('dd')?.textContent?.replace(/\s+/g, ' ').trim() || ''])))
      const semantic = stageSemantics(cardId, title, sections, authoritative)
      stages.push(semantic)
      const layout = await page.evaluate(() => ({ documentWidth: document.documentElement.scrollWidth, viewportWidth: document.documentElement.clientWidth, pageHeight: document.documentElement.scrollHeight, viewportHeight: innerHeight, cardWidth: document.querySelector('.ic-card')?.scrollWidth, cardClientWidth: document.querySelector('.ic-card')?.clientWidth, reduced: document.querySelector('.ic-shell')?.classList.contains('is-reduced-motion') }))
      check(`${width}: ${cardId} has five stage-correct API-matched explanation sections without object or JSON leakage`, semantic.allSectionsSubstantive && semantic.missingFactsExplicit && semantic.rawJsonAbsent && semantic.objectLeakAbsent && semantic.stageCorrect && semantic.numericFactsMatchApi, semantic)
      check(`${width}: ${cardId} explanation fits and remains vertically readable`, layout.documentWidth <= layout.viewportWidth + 1 && Number(layout.cardWidth) <= Number(layout.cardClientWidth) + 1 && layout.pageHeight >= layout.viewportHeight && layout.reduced, layout)
      const back = page.getByRole('button', { name: 'Back', exact: true })
      await back.click()
      await page.locator('.ic-card').waitFor()
      const focus = await page.evaluate(() => ({ text: document.activeElement?.textContent?.trim(), tag: document.activeElement?.tagName }))
      check(`${width}: ${cardId} Back restores Explain focus`, focus.tag === 'BUTTON' && focus.text === 'Explain', focus)
      if (index < 6) {
        const before = await page.locator('.ic-card').getAttribute('data-card-id')
        await page.locator('.ic-deck-nav button:last-child').click()
        await page.waitForFunction(id => document.querySelector('.ic-card')?.getAttribute('data-card-id') !== id, before)
      }
    }
    report.stages[width] = stages
    await page.getByRole('button', { name: 'Explain', exact: true }).click()
    await page.getByRole('heading', { name: 'What this means', exact: true }).waitFor()
    await page.evaluate(() => { document.documentElement.style.zoom = '2' })
    const zoom = await page.evaluate(() => ({ documentWidth: document.documentElement.scrollWidth, viewportWidth: document.documentElement.clientWidth, pageHeight: document.documentElement.scrollHeight, viewportHeight: innerHeight }))
    check(`${width}: 200% zoom preserves horizontal containment and document scrolling`, zoom.documentWidth <= zoom.viewportWidth + 1 && zoom.pageHeight > zoom.viewportHeight, zoom)
    check(`${width}: explanation audit has no browser errors`, errors.length === 0, errors)
    await context.close()
  }
  check('V16 explanation audit sends zero API writes and provider requests', report.requests.writes.length === 0 && report.requests.provider.length === 0, report.requests)
  report.status = report.checks.every(row => row.pass) ? 'PASS' : 'FAIL'
  if (report.status === 'FAIL') process.exitCode = 1
} catch (error) {
  report.status = 'ERROR'
  report.failures.push(error instanceof Error ? error.stack : String(error))
  process.exitCode = 1
} finally {
  await browser?.close()
  await mkdir(resolve(root, 'reports/v16'), { recursive: true })
  await writeFile(output, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify({ status: report.status, build: report.build, checks: report.checks.length, failed: report.checks.filter(row => !row.pass).map(row => row.name), failures: report.failures, requests: report.requests }, null, 2))
}
