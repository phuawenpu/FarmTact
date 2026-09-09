import { mkdir, writeFile, readFile } from 'node:fs/promises'
import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'

const base = 'https://farmtact.fly.dev'
const out = 'apps/web/screenshots/panel/review09'
const statePath = '/tmp/farmtact-review02-state.json'
const result = { checks: [], errors: [], screenshots: [], build_assets: [], facts: {}, requests: { scenarios: 0, advisor: 0 } }
const clean = value => String(value || '').replace(/\s+/g, ' ').trim()
const check = (name, pass, detail = '') => result.checks.push({ name, pass: Boolean(pass), detail: clean(detail).slice(0, 800) })
const snap = async (page, name) => {
  const path = `${out}/${name}.png`
  await page.screenshot({ path, animations: 'disabled', caret: 'hide' })
  result.screenshots.push(path)
}
const visibleLabels = async page => page.locator('button:visible, a:visible').evaluateAll(nodes => nodes.map(n => String(n.getAttribute('aria-label') || n.textContent || '').replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, 120))

await mkdir(out, { recursive: true })
const storageState = JSON.parse(await readFile(statePath, 'utf8'))
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, reducedMotion: 'reduce', storageState })
const page = await context.newPage()
page.on('pageerror', error => result.errors.push(`page: ${error.message}`))
page.on('console', msg => { if (msg.type() === 'error') result.errors.push(`console: ${msg.text()}`) })
page.on('request', request => {
  if (request.method() === 'POST' && request.url().endsWith('/api/v1/scenarios')) result.requests.scenarios++
  if (request.method() === 'POST' && /\/conversations\/[^/]+\/(messages|invite|council)/.test(request.url())) result.requests.advisor++
})

try {
  const response = await page.goto(base, { waitUntil: 'networkidle', timeout: 60_000 })
  check('live app responds', response?.status() === 200, response?.status())
  result.build_assets = (await page.locator('script[src],link[rel="stylesheet"]').evaluateAll(nodes => nodes.map(n => n.getAttribute('src') || n.getAttribute('href')).filter(Boolean))).filter(p => p.includes('/assets/'))
  result.facts.mobile_initial_text = clean(await page.locator('body').innerText()).slice(0, 5000)
  result.facts.mobile_initial_controls = await visibleLabels(page)
  check('mobile has no document overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => `${document.documentElement.scrollWidth}/${innerWidth}`))
  check('mobile touch targets at least 44px', await page.locator('button:visible, a:visible').evaluateAll(nodes => nodes.every(n => { const r = n.getBoundingClientRect(); return r.width >= 44 && r.height >= 44 })), 'all visible buttons and links')
  result.facts.mobile_small_targets = await page.locator('button:visible, a:visible').evaluateAll(nodes => nodes.map(n => { const r = n.getBoundingClientRect(); return { label: String(n.getAttribute('aria-label') || n.textContent || '').replace(/\s+/g, ' ').trim(), width: Math.round(r.width), height: Math.round(r.height) } }).filter(x => x.width < 44 || x.height < 44).slice(0, 30))
  await snap(page, 'mobile-390-home')

  await page.getByRole('button', { name: 'Quest journal', exact: true }).click()
  await page.waitForTimeout(300)
  result.facts.mobile_quest_text = clean(await page.locator('body').innerText()).slice(0, 5000)
  result.facts.mobile_quest_controls = await visibleLabels(page)
  await snap(page, 'mobile-390-quest-journal')
  await page.getByRole('button', { name: 'Start quest', exact: true }).first().click()
  await page.waitForTimeout(400)
  result.facts.mobile_quest_started_text = clean(await page.locator('body').innerText()).slice(-6000)
  result.facts.mobile_quest_started_controls = await visibleLabels(page)
  await snap(page, 'mobile-390-late-harvest-quest')
  await page.getByRole('button', { name: 'Review assumptions', exact: true }).click()
  await page.waitForTimeout(250)
  result.facts.mobile_review_text = clean(await page.locator('body').innerText()).slice(-5500)
  await snap(page, 'mobile-390-review-assumptions')

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.reload({ waitUntil: 'networkidle', timeout: 60_000 })
  result.facts.desktop_initial_text = clean(await page.locator('body').innerText()).slice(0, 5000)
  result.facts.desktop_initial_controls = await visibleLabels(page)
  check('desktop has no document overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => `${document.documentElement.scrollWidth}/${innerWidth}`))
  await snap(page, 'desktop-1280-home')
  await page.getByRole('button', { name: /^A1, Caixin, growing/ }).click()
  await page.waitForTimeout(250)
  result.facts.desktop_bed_text = clean(await page.locator('body').innerText()).slice(-5000)
  result.facts.desktop_bed_controls = await visibleLabels(page)
  await snap(page, 'desktop-1280-bed-a1')
  await page.getByRole('button', { name: 'Close', exact: true }).click()
  await page.getByRole('button', { name: 'Crop almanac', exact: true }).click()
  await page.waitForTimeout(250)
  result.facts.desktop_almanac_text = clean(await page.locator('body').innerText()).slice(-6500)
  result.facts.desktop_almanac_controls = await visibleLabels(page)
  await snap(page, 'desktop-1280-crop-almanac')
  await page.getByRole('button').filter({ hasText: /^Caixin/ }).first().click()
  await page.waitForTimeout(250)
  result.facts.desktop_caixin_text = clean(await page.locator('body').innerText()).slice(-7000)
  await snap(page, 'desktop-1280-caixin-evidence')
  const detailClose = page.getByRole('button', { name: 'Close', exact: true })
  if (await detailClose.count()) await detailClose.last().click()
  await page.getByRole('button', { name: 'Data', exact: true }).click()
  await page.waitForLoadState('networkidle')
  await page.getByText('Provenance', { exact: true }).waitFor({ timeout: 30_000 })
  result.facts.desktop_data_text = clean(await page.locator('body').innerText()).slice(0, 7500)
  result.facts.desktop_data_controls = await visibleLabels(page)
  await snap(page, 'desktop-1280-data-overview')
  check('no numerical scenario created', result.requests.scenarios === 0, JSON.stringify(result.requests))
  check('no advisor message sent', result.requests.advisor === 0, JSON.stringify(result.requests))
} catch (error) {
  result.errors.push(error.stack || String(error))
  await snap(page, 'failure').catch(() => {})
} finally {
  await writeFile(`${out}/observations.json`, JSON.stringify(result, null, 2) + '\n')
  await context.close().catch(() => {})
  await browser.close().catch(() => {})
}

console.log(JSON.stringify({ checks: result.checks, errors: result.errors, assets: result.build_assets, facts: result.facts, screenshots: result.screenshots, requests: result.requests }, null, 2))
if (result.errors.length) process.exitCode = 1
