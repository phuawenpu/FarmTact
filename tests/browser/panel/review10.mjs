import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'
import crypto from 'node:crypto'
import { fileURLToPath } from 'node:url'

const base = 'https://farmtact.fly.dev'
const statePath = '/tmp/farmtact-review04-state.json'
const shotDir = fileURLToPath(new URL('../../../apps/web/screenshots/panel/review10/', import.meta.url))
await fs.mkdir(shotDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 430, height: 932 },
  hasTouch: true,
  isMobile: true,
  storageState: statePath,
})
const page = await context.newPage()
const result = { build: {}, checks: [], mobile: {}, desktop: {}, requests: { replayLoads: 0, scenarioRuns: 0, advisorMessages: 0 } }
const body = async () => (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim()
const snap = async (name) => page.screenshot({ path: `${shotDir}/${name}.png`, fullPage: false })
const record = (name, pass, detail = null) => result.checks.push({ name, pass, detail })
const clickRoom = async (name) => {
  const nav = page.getByRole('navigation', { name: 'FarmTact rooms' }).last()
  const button = name === 'Farm'
    ? nav.getByRole('button', { name: 'Farm', exact: true })
    : nav.getByRole('button', { name: new RegExp(name, 'i') })
  await button.click()
  await page.waitForTimeout(700)
  return body()
}

await page.goto(base, { waitUntil: 'networkidle', timeout: 60000 })
await page.locator('h1').first().waitFor({ timeout: 30000 })
const assets = []
for (const url of await page.locator('script[src],link[rel="stylesheet"]').evaluateAll(nodes => nodes.map(n => n.src || n.href).filter(Boolean))) {
  const response = await context.request.get(url)
  const bytes = await response.body()
  assets.push({ path: new URL(url).pathname, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), bytes: bytes.length })
}
result.build.assets = assets
result.mobile.farm = (await body()).slice(0, 7000)
result.mobile.rooms = await page.getByRole('navigation', { name: 'FarmTact rooms' }).last().getByRole('button').allTextContents()
record('mobile viewport and touch', (await page.viewportSize()).width === 430 && await page.evaluate(() => matchMedia('(pointer: coarse)').matches), await page.viewportSize())
record('prepared returning-demo disclosure visible', /synthetic|demo|simulation/i.test(result.mobile.farm))
await snap('01-mobile-farm')

result.mobile.tools = (await clickRoom('Tools')).slice(0, 5000)
result.requests.replayLoads += 1
await page.getByRole('button', { name: /Replay recorded demo/i }).click()
await page.getByText(/Shared recorded demo/i).first().waitFor({ timeout: 120000 })
await page.getByText(/strategies/i).first().waitFor({ timeout: 120000 })
result.mobile.replayedPlan = (await body()).slice(0, 12000)
await snap('02-mobile-plan')
record('recorded plan exposes demand and margin', /demand filled/i.test(result.mobile.replayedPlan) && /margin/i.test(result.mobile.replayedPlan))
const timelineButton = page.getByRole('button', { name: /Timeline/i }).first()
await timelineButton.click()
await page.getByRole('dialog').waitFor({ state: 'visible', timeout: 30000 }).catch(() => {})
result.mobile.timeline = (await body()).slice(0, 9000)
await page.getByRole('dialog').screenshot({ path: `${shotDir}/03-mobile-timeline.png` })
record('timeline exposes delivery or supply evidence', /deliver|harvest|supply|demand/i.test(result.mobile.timeline))
await page.getByRole('button', { name: 'Close' }).click()

result.mobile.outcomes = (await clickRoom('Outcomes')).slice(0, 10000)
await snap('04-mobile-outcomes')
record('outcomes exposes commercial evidence', /price|margin|revenue|cost|demand|deliver|supply/i.test(result.mobile.outcomes))

await page.setViewportSize({ width: 1280, height: 900 })
await page.evaluate(() => window.scrollTo(0, 0))
result.desktop.outcomes = (await body()).slice(0, 10000)
record('desktop viewport', (await page.viewportSize()).width === 1280, await page.viewportSize())
await snap('05-desktop-outcomes')

result.desktop.farm = (await clickRoom('Farm')).slice(0, 8000)
await snap('06-desktop-farm')
result.desktop.tools = (await clickRoom('Tools')).slice(0, 5000)
await page.getByRole('button', { name: /Timeline/i }).first().click()
await page.getByRole('dialog').waitFor({ state: 'visible', timeout: 30000 }).catch(() => {})
result.desktop.timeline = (await body()).slice(0, 10000)
await page.getByRole('dialog').screenshot({ path: `${shotDir}/07-desktop-timeline.png` })

console.log(JSON.stringify(result, null, 2))
await browser.close()
