import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { access, mkdir, readFile, writeFile } from 'node:fs/promises'
import { extname, resolve } from 'node:path'

const root = resolve(new URL('../..', import.meta.url).pathname)
const base = (process.env.BASE_URL || 'http://127.0.0.1:4196').replace(/\/$/, '')
const dist = '/tmp/farmtact-v15-first-use-review/apps/web/dist'
const storage = process.env.STORAGE_STATE || '/tmp/farmtact-v15-cards-storage.json'
const output = resolve(root, 'reports/v17/personas')
await Promise.all([access(resolve(dist, 'index.html')), access(storage), mkdir(output, { recursive: true })])

const mime = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json', '.wav': 'audio/wav', '.mp4': 'video/mp4', '.vtt': 'text/vtt' }
const browser = await chromium.launch({ headless: true })
const summary = {
  status: 'RUNNING', artifact: 'V15 a5ab2a8 exact preserved frontend bundle', frontendAsset: 'index-C89Jrp2Y.js', api: base,
  disclosure: 'Three AI heuristic personas reuse the same existing local acceptance tenant/session cookie. They are not independent humans, a fresh tenant study, or evidence of comprehension. Every API write is blocked.',
  rubric: ['Goal & Scope Definition', 'Architecture & Reasoning Loop', 'Tool Use & Integration', 'Autonomy & Human-in-the-Loop', 'Safety, Security & Guardrails', 'Observability & Evaluation', 'Platform & Tooling Usage'],
  personas: [], failures: []
}

async function makeContext(width) {
  const context = await browser.newContext({ storageState: storage, viewport: { width, height: width === 1280 ? 900 : 844 }, reducedMotion: 'reduce' })
  await context.route(`${base}/**`, async route => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname
    if (path.startsWith('/api/')) return ['GET', 'HEAD', 'OPTIONS'].includes(request.method()) ? route.continue() : route.abort('blockedbyclient')
    const file = resolve(dist, path === '/' || path === '/play' ? 'index.html' : `.${path}`)
    if (!file.startsWith(`${dist}/`) && file !== resolve(dist, 'index.html')) return route.abort()
    try { await route.fulfill({ body: await readFile(file), contentType: mime[extname(file)] || 'application/octet-stream' }) } catch { await route.abort() }
  })
  return context
}

async function runPersona({ id, label, width, journey, hypotheses, rubricMapping }) {
  const dir = resolve(output, id); await mkdir(dir, { recursive: true })
  const context = await makeContext(width), page = await context.newPage()
  const report = { id, label, viewport: { width, height: width === 1280 ? 900 : 844 }, status: 'RUNNING', observations: [], hypotheses, rubricMapping, requests: { writes: [], provider: [] }, errors: [], screenshots: [] }
  page.on('request', request => {
    const path = new URL(request.url()).pathname
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) report.requests.writes.push(`${request.method()} ${path}`)
    if (/deepseek|provider|inference/i.test(request.url())) report.requests.provider.push(`${request.method()} ${path}`)
  })
  page.on('pageerror', error => report.errors.push(error.message))
  const snap = async name => { const path = resolve(dir, `${name}.png`); await page.screenshot({ path, fullPage: true }); report.screenshots.push(`${name}.png`) }
  const observe = async (name, locator = page.locator('body')) => report.observations.push({ name, text: (await locator.innerText()).replace(/\n{3,}/g, '\n\n'), cardId: await page.locator('[data-card-id]:visible').first().getAttribute('data-card-id'), focus: await page.evaluate(() => ({ tag: document.activeElement?.tagName, text: document.activeElement?.textContent?.replace(/\s+/g, ' ').trim(), label: document.activeElement?.getAttribute('aria-label') })) })
  try {
    await page.goto(`${base}/play`, { waitUntil: 'domcontentloaded' }); await page.locator('.ic-shell').waitFor({ timeout: 45000 })
    await journey({ page, observe, snap, report })
    report.status = report.errors.length || report.requests.writes.length || report.requests.provider.length ? 'FAIL' : 'PASS'
  } catch (error) { report.status = 'ERROR'; report.errors.push(error instanceof Error ? error.stack : String(error)); try { await snap('failure') } catch {} }
  await writeFile(resolve(dir, 'walkthrough.json'), JSON.stringify(report, null, 2) + '\n')
  await context.close(); summary.personas.push({ id, label, status: report.status, observations: report.observations.length, screenshots: report.screenshots.length, writes: report.requests.writes, provider: report.requests.provider, errors: report.errors })
}

await runPersona({
  id: 'novice-mobile', label: 'AI persona: novice farm manager on mobile', width: 390,
  hypotheses: [
    'The unchanged objective and farm scene above both mission cards and tool cards may make the Tools index look like another planning step.',
    'Recorded batch, saved projection, preview and recorded simulation are precise but unfamiliar evidence categories for a first-time manager.',
    'Keep B3 available followed by Reserve B3 / unavailable may sound contradictory without a dated timeline.',
    'Continue may be interpreted as saving a strategy even though strategy cards are previews.'
  ],
  rubricMapping: {
    'Goal & Scope Definition': 'Objective and sandbox boundary are prominent; the immediate learning goal is less explicit when More opens.',
    'Autonomy & Human-in-the-Loop': 'Review before apply and disabled physical operations are visible checkpoints.',
    'Safety, Security & Guardrails': 'Sandbox and real-operations-disabled labels persist.',
    'Observability & Evaluation': 'Evidence type labels exist, but newcomer interpretation is a hypothesis requiring human testing.'
  },
  journey: async ({ page, observe, snap }) => {
    await observe('arrival: ordinary saved farm and situation card'); await snap('01-arrival')
    await page.locator('.ic-deck-nav button:last-child').click(); await observe('first calculated strategy preview'); await snap('02-strategy-preview')
    for (let i = 0; i < 3; i++) await page.locator('.ic-deck-nav button:last-child').click()
    await observe('B3 reservation card after strategy comparison'); await snap('03-b3-challenge')
    await page.getByRole('button', { name: 'Explain', exact: true }).click(); await observe('V15 deterministic B3 explanation'); await snap('04-b3-explanation')
    await page.getByRole('button', { name: 'Back', exact: true }).first().click(); await page.getByRole('button', { name: 'More', exact: true }).click(); await observe('More opens first of five tool cards'); await snap('05-tools-index')
    const toolTitles = []
    for (let i = 0; i < 5; i++) { toolTitles.push((await page.locator('.ic-card h1').textContent() || '').trim()); if (i < 4) await page.locator('.ic-deck-nav button:last-child').click() }
    await observe(`all tool purposes encountered: ${toolTitles.join(' | ')}`)
  }
})

await runPersona({
  id: 'expert-desktop', label: 'AI persona: expert production planner on desktop', width: 1280,
  hypotheses: [
    'Three strategies expose delivery, shortfall and cost, but only the explanation view supplies a signed comparison and only three allocations are sampled.',
    'V15 reservation explanation presents whole-proposal metric and allocation differences beneath a bed-07 statement, which can be overread as target-specific causality.',
    'The scene shows only 8 of 16 spaces, so a planner must rely on IDs and detail cards for off-screen affected beds.',
    'Tools contain deep records and experiments, but the five-card index does not expose current counts or pending work.'
  ],
  rubricMapping: {
    'Architecture & Reasoning Loop': 'Frozen input/result identities and deterministic local planning are visible; causal attribution in the V15 reservation explanation is too broad.',
    'Tool Use & Integration': 'Plan, Records, Knowledge, Experiments and History are reachable in one shell with typed card metadata.',
    'Autonomy & Human-in-the-Loop': 'Proposal review, recalculation, approval and inverse are explicit.',
    'Observability & Evaluation': 'Signed metrics, IDs and histories support audit, though first-view strategy detail is compressed.'
  },
  journey: async ({ page, observe, snap, report }) => {
    await observe('desktop baseline'); await snap('01-baseline')
    const strategies = []
    for (let i = 0; i < 3; i++) { await page.locator('.ic-deck-nav button:last-child').click(); strategies.push((await page.locator('.ic-card').innerText()).replace(/\n+/g, ' | ')); await snap(`0${i + 2}-strategy-${i + 1}`) }
    report.strategyCards = strategies
    await page.locator('.ic-deck-nav button:last-child').click(); await page.getByRole('button', { name: 'Explain', exact: true }).click(); await observe('reservation plan-wide differences'); await snap('05-reservation-explanation')
    report.reservationEvidence = await page.locator('.ic-explanation').innerText()
  }
})

await runPersona({
  id: 'architecture-judge', label: 'AI persona: skeptical agent architecture and evaluation judge using keyboard', width: 1280,
  hypotheses: [
    'The UI exposes canonical IDs and eligibility metadata in DOM attributes, but most architecture guarantees are invisible without reports or source inspection.',
    'Explain and replay correctly avoid provider calls; the interface could make the deterministic-versus-provider boundary more prominent before opening Knowledge.',
    'One active card and focus restoration support keyboard review, while deep tool cards use a second card-navigation component that must retain equivalent semantics.',
    'A polished golden path does not itself demonstrate tenant, stale-revision, concurrency or outage handling; those remain evaluation-artifact claims.'
  ],
  rubricMapping: {
    'Architecture & Reasoning Loop': 'Canonical card binding, frozen snapshots and explicit state transitions are inspectable.',
    'Tool Use & Integration': 'Tool adapters keep forms/transcripts inside cards and publish action authority/eligibility.',
    'Autonomy & Human-in-the-Loop': 'No provider call occurs until explicit Ask/Council submission; writes were blocked in this audit.',
    'Safety, Security & Guardrails': 'Sandbox boundary and server-owned eligibility are visible; adversarial guarantees require regression evidence.',
    'Observability & Evaluation': 'Replay, event identity and metadata are strong; human comprehension remains untested.',
    'Platform & Tooling Usage': 'Single shell and lazy integrated decks are coherent, with keyboard and swipe sharing card order.'
  },
  journey: async ({ page, observe, snap, report }) => {
    const card = page.locator('.ic-card'); await card.focus(); const first = await card.getAttribute('data-card-id'); await page.keyboard.press('ArrowRight'); await page.waitForFunction(id => document.querySelector('.ic-card')?.getAttribute('data-card-id') !== id, first)
    await observe('keyboard ArrowRight advances canonical card'); await snap('01-keyboard-card')
    report.cardMetadata = await card.evaluate(node => Object.fromEntries([...node.attributes].filter(a => a.name.startsWith('data-')).map(a => [a.name, a.value])))
    await page.getByRole('button', { name: 'Explain', exact: true }).focus(); await page.keyboard.press('Enter'); await observe('keyboard opens deterministic explanation'); await snap('02-deterministic-explain')
    await page.getByRole('button', { name: 'Back', exact: true }).first().focus(); await page.keyboard.press('Enter'); report.returnFocus = await page.evaluate(() => ({ tag: document.activeElement?.tagName, text: document.activeElement?.textContent?.trim() }))
    await page.getByRole('button', { name: 'More', exact: true }).focus(); await page.keyboard.press('Enter');
    for (let i = 0; i < 4; i++) { await page.locator('.ic-card').focus(); await page.keyboard.press('ArrowRight') }
    await observe('keyboard reaches History and preferences tool'); await snap('03-history-tool-card')
    await page.getByRole('button', { name: 'Open tool', exact: true }).focus(); await page.keyboard.press('Enter'); await page.locator('.integrated-tool').waitFor(); await observe('history opens in integrated card'); await snap('04-history-integrated')
  }
})

summary.status = summary.personas.every(row => row.status === 'PASS') ? 'PASS' : 'FAIL'
await writeFile(resolve(output, 'summary.json'), JSON.stringify(summary, null, 2) + '\n')
await browser.close()
console.log(JSON.stringify(summary, null, 2))
if (summary.status !== 'PASS') process.exitCode = 1
