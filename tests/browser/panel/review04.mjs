import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import crypto from 'node:crypto'
import { fileURLToPath } from 'node:url'

const base = 'https://farmtact.fly.dev'
const shotDir = fileURLToPath(new URL('../../../apps/web/screenshots/panel/review04/', import.meta.url))
const statePath = '/tmp/farmtact-review04-state.json'
await fs.mkdir(shotDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
let prior
try { prior = JSON.parse(await fs.readFile(statePath, 'utf8')) } catch {}
const context = await browser.newContext({
  viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true,
  ...(prior ? { storageState: prior } : {}),
})
const page = await context.newPage()
const result = { checks: [], assets: [], mobile: {}, desktop: {}, requests: { scenarioRuns: 0, advisorMessages: 0 } }
const check = (name, pass, detail = null) => { result.checks.push({ name, pass, detail }); if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`) }
const bodyText = async () => (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim()

await page.goto(base, { waitUntil: 'networkidle', timeout: 60000 })
await page.locator('h1').first().waitFor({ timeout: 30000 })
for (const url of await page.locator('script[src],link[rel="stylesheet"]').evaluateAll(nodes => nodes.map(node => node.href || node.src).filter(Boolean))) {
  const response = await context.request.get(url)
  const bytes = await response.body()
  result.assets.push({ url: new URL(url).pathname, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length })
}
result.mobile.initialText = (await bodyText()).slice(0, 1800)
result.mobile.thumbNav = await page.getByRole('navigation', { name: 'FarmTact rooms' }).last().getByRole('button').allTextContents()
check('mobile touch viewport', (await page.viewportSize()).width === 390 && await page.evaluate(() => matchMedia('(pointer: coarse)').matches), await page.viewportSize())
check('mobile labels simulation scope', /synthetic simulation/i.test(result.mobile.initialText) && /Preview only/i.test(result.mobile.initialText))
await page.screenshot({ path: `${shotDir}/01-mobile-farm.png`, fullPage: false })

await page.getByRole('button', { name: /Scenario lab/i }).first().click()
const scenario = page.getByRole('dialog', { name: 'Scenario lab' })
await scenario.waitFor({ state: 'visible' })
await scenario.getByLabel('Challenge').selectOption('short_handed_week')
result.mobile.scenarioBrief = (await scenario.innerText()).replace(/\s+/g, ' ').slice(0, 1800)
check('scenario identifies frozen numerical branch', /Frozen-input numerical experiments/i.test(result.mobile.scenarioBrief) && /Numerical · no inference/i.test(result.mobile.scenarioBrief))
await scenario.screenshot({ path: `${shotDir}/02-mobile-scenario-assumptions.png` })
result.requests.scenarioRuns += 1
await scenario.getByRole('button', { name: /Run experiment/ }).click()
await scenario.getByRole('heading', { name: 'Inspect the trade-offs' }).waitFor({ timeout: 120000 })
await scenario.getByText(/Computed debrief · Balanced/).first().waitFor({ timeout: 120000 })
result.mobile.scenarioResult = (await scenario.innerText()).replace(/\s+/g, ' ').slice(0, 5000)
check('scenario returns same-policy baseline and delta', /baseline, branch outcome and computed change/i.test(result.mobile.scenarioResult) && /Δ/.test(result.mobile.scenarioResult))
await scenario.screenshot({ path: `${shotDir}/03-mobile-scenario-result.png` })

await scenario.getByRole('button', { name: /Ask an advisor about this branch/ }).first().click()
const conversation = page.getByRole('dialog').filter({ hasText: /Current context:/ }).first()
await conversation.waitFor({ state: 'visible', timeout: 30000 })
await conversation.locator('#advisor-message').fill('Which hard constraint should I inspect first, and which recorded reference supports that priority?')
result.requests.advisorMessages += 1
await conversation.getByRole('button', { name: 'Send message' }).click()
await conversation.getByText('Waiting for a bounded response…').waitFor({ state: 'hidden', timeout: 320000 }).catch(() => {})
await page.waitForTimeout(1500)
result.mobile.advisor = (await conversation.innerText()).replace(/\s+/g, ' ').slice(-5000)
check('advisor message preserved in transcript', /Which hard constraint should I inspect first/i.test(result.mobile.advisor), result.mobile.advisor.slice(-800))
await conversation.screenshot({ path: `${shotDir}/04-mobile-advisor.png` })
await conversation.getByRole('button', { name: 'Close' }).click()

await page.setViewportSize({ width: 1280, height: 900 })
await page.evaluate(() => window.scrollTo(0, 0))
result.desktop.farmText = (await bodyText()).slice(0, 2200)
check('desktop viewport', (await page.viewportSize()).width === 1280, await page.viewportSize())
await page.screenshot({ path: `${shotDir}/05-desktop-farm.png`, fullPage: false })
await page.getByRole('navigation', { name: 'FarmTact rooms' }).first().getByRole('button', { name: /Outcomes/ }).click()
await page.getByRole('heading', { name: /outcomes|results|No planning/i }).first().waitFor({ timeout: 30000 }).catch(() => {})
result.desktop.outcomes = (await bodyText()).slice(0, 5000)
await page.screenshot({ path: `${shotDir}/06-desktop-outcomes.png`, fullPage: false })
check('desktop provides persistent outcomes route', /Outcomes/i.test(result.desktop.outcomes))

await context.storageState({ path: statePath })
await fs.chmod(statePath, 0o600)
console.log(JSON.stringify(result, null, 2))
await browser.close()
