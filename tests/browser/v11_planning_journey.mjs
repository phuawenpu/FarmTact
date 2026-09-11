/** Genuine V11 planning-session journey. It runs numerical work and never requests Council inference. */
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const base = (process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080').replace(/\/$/, '')
const app = `${base}/v11`
const reportPath = resolve(root, process.env.FARMTACT_BROWSER_REPORT || 'reports/v11/frontend-browser.json')
const report = { status: 'RUNNING', started_at: new Date().toISOString(), base_url: app, inference_policy: 'Numerical planning only; Council button is verified but never invoked.', checks: [], failures: [], screenshots: [] }
function check(name, pass, detail) { report.checks.push({ name, pass: Boolean(pass), ...(detail === undefined ? {} : { detail }) }); if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`) }
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
async function json(response) { if (!response.ok()) throw new Error(`${response.status()} ${await response.text()}`); return response.json() }
async function waitSession(request, id) { const until = Date.now() + 180000; let value; while (Date.now() < until) { value = await json(await request.get(`${app}/api/v1/planning-sessions/${id}`)); if (!['QUEUED','RUNNING'].includes(value.job?.status || '')) return value; await pause(750) } throw new Error(`session ${id} timed out at ${value?.job?.stage}`) }

await mkdir(dirname(reportPath), { recursive: true })
let browser
try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce', ...(process.env.FARMTACT_STORAGE_STATE ? { storageState: process.env.FARMTACT_STORAGE_STATE } : {}) })
  const page = await context.newPage(), errors = [], providerRequests = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => { if (/conversations|\/review$|deepseek|inference/i.test(request.url()) && request.method() !== 'GET') providerRequests.push({ method: request.method(), url: request.url() }) })
  await page.goto(app, { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: 'Plan the next crop cycle' }).waitFor()
  check('V11 opens on guided production planning', await page.getByRole('heading', { name: 'Plan the next crop cycle' }).isVisible())
  check('confirmed orders and expected demand are presented separately', await page.getByText('Confirmed customer orders', { exact: true }).isVisible() && await page.getByText(/Expected future demand/).first().isVisible())
  check('manual-style records disclose synthetic limits', await page.getByText('Record provenance and limits').isVisible())
  const previousSession = await page.locator('.records-section code').textContent()
  const newMissionResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/planning-sessions') && response.request().method() === 'POST')
  await page.getByRole('button', { name: /New mission from current records/ }).click()
  const freshSession = await json(await newMissionResponse)
  check('new mission uses current records without overwriting the saved session', !previousSession?.includes(freshSession.id))
  const calculateResponse = page.waitForResponse(response => response.url().includes('/api/v1/planning-sessions/') && response.url().endsWith('/calculate') && response.request().method() === 'POST')
  await page.getByRole('button', { name: /Calculate schedules/ }).click()
  let session = await json(await calculateResponse)
  await page.getByRole('heading', { name: 'Three feasible priorities' }).waitFor({ timeout: 180000 })
  session = await json(await context.request.get(`${app}/api/v1/planning-sessions/${session.id}`))
  check('numerical planning returns all three strategies', ['Lean','Balanced','Resilient'].every(name => session.result.strategies.some(item => item.name === name)))
  const metricVisibility = await Promise.all(['booked fulfillment','expired waste','remaining stock','simulated margin'].map(label => page.getByText(label, { exact: true }).first().isVisible()))
  check('comparison shows fulfillment waste stock and margin together', metricVisibility.every(Boolean), metricVisibility)
  check('Council is an explicit optional checkpoint', await page.getByRole('button', { name: /Review with Council/ }).isVisible())
  check('disruption controls start neutral', await page.getByRole('slider', { name: /Expected future demand/ }).inputValue() === '100' && await page.getByRole('slider', { name: /Seasonal yield assumption/ }).inputValue() === '100' && await page.getByRole('slider', { name: /Harvest delay/ }).inputValue() === '0')
  const advanceResponse = page.waitForResponse(response => response.url().includes('/api/v1/planning-sessions/') && response.url().endsWith('/advance') && response.request().method() === 'POST')
  await page.getByRole('button', { name: /Start · 1 day|\+1 day/ }).click()
  session = await json(await advanceResponse)
  check('simulation advance remains synthetic and disables operations', session.simulation?.simulation_only === true && session.simulation?.real_operations_enabled === false)
  const boardStages = await page.locator('.guided-farm-beds button').evaluateAll(nodes => nodes.map(node => node.getAttribute('aria-label')))
  check('farm board exposes actual schedule or simulation stages', boardStages.some(label => /nursery|growing|ready|future|empty|harvested/.test(label || '')), boardStages)
  await page.getByRole('slider', { name: /Expected future demand/ }).fill('130')
  await page.getByRole('slider', { name: /Seasonal yield assumption/ }).fill('85')
  await page.getByRole('slider', { name: /Harvest delay/ }).fill('4')
  await page.getByRole('button', { name: /Add a confirmed customer order/ }).click()
  await page.getByLabel('Quantity (kg)').fill('12')
  const disruptResponse = page.waitForResponse(response => response.url().includes('/api/v1/planning-sessions/') && response.url().endsWith('/disrupt') && response.request().method() === 'POST')
  await page.getByRole('button', { name: /Compare and replan/ }).click()
  session = await json(await disruptResponse)
  await page.getByRole('heading', { name: 'Keep the saved schedule or replan?' }).waitFor({ timeout: 180000 })
  session = await json(await context.request.get(`${app}/api/v1/planning-sessions/${session.id}`))
  check('changed demand remains distinct from explicit order edit', session.assumptions.future_demand[0].percent === 130 && Number(session.assumptions.order_changes[0].quantity_kg) === 12)
  check('seasonal assumption is dated and synthetic', session.assumptions.seasonal[0].yield_percent === 85 && session.assumptions.seasonal[0].delay_days === 4 && session.assumptions.seasonal[0].provenance === 'synthetic_assumption')
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: 'Keep the saved schedule or replan?' }).waitFor()
  check('same-condition comparison is shown', await page.getByText(/Every arm uses the same changed demand/).isVisible())
  const storedId = await page.evaluate(() => Object.entries(localStorage).find(([key]) => key.includes('planning-session'))?.[1])
  check('session selection survives reload', storedId === session.id, { storedId, sessionId: session.id })
  for (const width of [360,390,430,1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 })
    await page.waitForTimeout(100)
    const dimensions = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }))
    check(`${width}px journey has no body overflow`, dimensions.body <= dimensions.viewport + 1, dimensions)
    const clipped = await page.locator('.guided-hero h1,.guided-section h2,.guided-section header .button,.guided-strategy,.comparison-grid article,.disruption-submit .button').evaluateAll((nodes, viewport) => nodes.map(node => { const rect=node.getBoundingClientRect(); return { text:(node.textContent||'').trim().slice(0,60),left:rect.left,right:rect.right,width:rect.width } }).filter(item => item.left < -1 || item.right > Number(viewport) + 1), width)
    check(`${width}px primary headings, cards and actions are fully visible`, clipped.length === 0, clipped)
    const file = resolve(root, `apps/web/screenshots/v11-planning-${width}.png`); await page.screenshot({ path: file, animations: 'disabled', fullPage: true }); report.screenshots.push(file.slice(root.length + 1))
  }
  check('journey made no provider request', providerRequests.length === 0, providerRequests)
  check('journey has no page exceptions', errors.length === 0, errors)
  report.status = 'PASS'; await context.close()
} catch (error) { report.status = 'FAIL'; report.failures.push(error instanceof Error ? error.stack || error.message : String(error)) }
finally { if (browser) await browser.close(); report.completed_at = new Date().toISOString(); await writeFile(reportPath, `${JSON.stringify(report,null,2)}\n`); console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failures: report.failures.length, report: reportPath.slice(root.length+1) })); if (report.status !== 'PASS') process.exitCode = 1 }
