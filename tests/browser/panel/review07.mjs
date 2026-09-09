import { mkdir, writeFile, readFile } from 'node:fs/promises'
import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'

const base = 'https://farmtact.fly.dev'
const out = 'apps/web/screenshots/panel/review07'
const assigned = '/tmp/farmtact-gameplay-release-first-attempt.json'
const result = { checks: [], errors: [], screenshots: [], assets: [], facts: {}, requests: { scenarios: 0, advisor: 0 } }
const clean = value => String(value || '').replace(/\s+/g, ' ').trim()
const check = (name, pass, detail = '') => result.checks.push({ name, pass: Boolean(pass), detail: clean(detail).slice(0, 1200) })
const snap = async (page, name) => {
  const path = `${out}/${name}.png`
  await page.screenshot({ path, animations: 'disabled', caret: 'hide' })
  result.screenshots.push(path)
}
const visibleText = async page => clean(await page.locator('body').innerText()).slice(0, 9000)

await mkdir(out, { recursive: true })
const session = JSON.parse(await readFile(assigned, 'utf8'))
if (typeof session.cookie !== 'string' || !session.cookie) throw new Error('Assigned returning-demo session is unavailable')

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, reducedMotion: 'reduce' })
await context.addCookies([{ name: 'farmtact_session', value: session.cookie, url: base }])
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
  result.assets = (await page.locator('script[src],link[rel="stylesheet"]').evaluateAll(nodes => nodes.map(node => node.getAttribute('src') || node.getAttribute('href')).filter(Boolean))).filter(path => path.includes('/assets/'))
  check('returning demo is authenticated', !/start your farm|create demo/i.test(await visibleText(page)))
  check('mobile has no horizontal document overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => `${document.documentElement.scrollWidth}/${innerWidth}`))
  result.facts.mobile_home = await visibleText(page)
  await snap(page, 'mobile-390-home')

  const zoneButton = page.getByRole('button', { name: /Zone|Nursery|Hydro|Bench|Rack/i }).filter({ visible: true }).first()
  if (await zoneButton.count()) {
    result.facts.zone_button = clean(await zoneButton.getAttribute('aria-label') || await zoneButton.innerText())
    await zoneButton.click()
    await page.waitForTimeout(500)
    result.facts.mobile_zone = await visibleText(page)
    await snap(page, 'mobile-390-zone-detail')
    check('farm object opens a detail layer', result.facts.mobile_zone !== result.facts.mobile_home, result.facts.zone_button)
    const close = page.getByRole('button', { name: /close|back/i }).filter({ visible: true }).first()
    if (await close.count()) await close.click()
  } else check('farm object opens a detail layer', false, 'No visible zone-like button found')

  const outcomes = page.getByRole('button', { name: 'Outcomes', exact: true }).filter({ visible: true }).first()
  if (await outcomes.count()) {
    await outcomes.click(); await page.waitForTimeout(600)
    result.facts.mobile_outcomes = await visibleText(page)
    await snap(page, 'mobile-390-outcomes')
    check('outcomes expose business metrics', /fill|margin|waste|yield|kg|resource/i.test(result.facts.mobile_outcomes), result.facts.mobile_outcomes)
  }

  const data = page.getByRole('button', { name: 'Data', exact: true }).filter({ visible: true }).first()
  await data.click(); await page.getByRole('heading', { name: 'See every number behind the plan.' }).waitFor({ timeout: 20_000 })
  await page.getByText('Loading provenance…', { exact: true }).waitFor({ state: 'hidden', timeout: 20_000 }).catch(() => {})
  result.facts.mobile_data = await visibleText(page)
  await snap(page, 'mobile-390-data-evidence')
  check('data view labels provenance and freshness', /provenance/i.test(result.facts.mobile_data) && /cutoff|fresh|retriev|forecast/i.test(result.facts.mobile_data), result.facts.mobile_data)

  const experiments = page.getByRole('button', { name: 'Experiments', exact: true }).filter({ visible: true }).first()
  await experiments.click(); await page.waitForTimeout(800)
  result.facts.mobile_experiments = await visibleText(page)
  await snap(page, 'mobile-390-experiments')
  check('experiments show alternatives or saved runs', /lean|balanced|resilient|scenario|baseline|compare/i.test(result.facts.mobile_experiments), result.facts.mobile_experiments)

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.reload({ waitUntil: 'networkidle', timeout: 60_000 })
  result.facts.desktop_home = await visibleText(page)
  await snap(page, 'desktop-1280-home')
  check('desktop farm renders without overflow', await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => `${document.documentElement.scrollWidth}/${innerWidth}`))

  const missions = page.getByRole('button').filter({ hasText: 'Planning tools' }).filter({ visible: true }).first()
  if (await missions.count()) {
    result.facts.mission_button = clean(await missions.getAttribute('aria-label') || await missions.innerText())
    await missions.click(); await page.waitForTimeout(700)
    result.facts.desktop_mission = await visibleText(page)
    await snap(page, 'desktop-1280-decision')
    check('decision view connects plan to evidence or constraints', /strategy|constraint|evidence|accepted|simulation|resource/i.test(result.facts.desktop_mission), result.facts.desktop_mission)
  } else check('decision view connects plan to evidence or constraints', false, 'No visible mission or strategy button found')

  check('review made no numerical mutation', result.requests.scenarios === 0, JSON.stringify(result.requests))
  check('review sent no advisor message', result.requests.advisor === 0, JSON.stringify(result.requests))
} catch (error) {
  result.errors.push(error.stack || String(error))
  await snap(page, 'failure').catch(() => {})
} finally {
  await writeFile(`${out}/observations.json`, JSON.stringify(result, null, 2) + '\n')
  await context.close().catch(() => {})
  await browser.close().catch(() => {})
}

console.log(JSON.stringify({ checks: result.checks, errors: result.errors, assets: result.assets, requests: result.requests }, null, 2))
if (result.errors.length) process.exitCode = 1
