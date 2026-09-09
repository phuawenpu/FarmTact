import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'

const baseURL = 'https://farmtact.fly.dev'
const shotDir = new URL('../../../apps/web/screenshots/panel/review02/', import.meta.url).pathname
await fs.mkdir(shotDir, { recursive: true })

if (process.argv.includes('--retest')) {
  const localURL = 'http://127.0.0.1:8080'
  const saved = JSON.parse(await fs.readFile('/tmp/farmtact-explorer-saved-release.json', 'utf8'))
  const cookieValue = String(saved.cookie).replace(/^farmtact_session=/, '').split(';')[0]
  if (!cookieValue) throw new Error('Saved release session cookie is missing')
  const retestBrowser = await chromium.launch({ headless: true })
  const retestContext = await retestBrowser.newContext({ viewport: { width: 360, height: 800 }, hasTouch: true, isMobile: true })
  await retestContext.addCookies([{ name: 'farmtact_session', value: cookieValue, domain: '127.0.0.1', path: '/', httpOnly: true, sameSite: 'Lax' }])
  const retestPage = await retestContext.newPage()
  const results = []
  const capture = async (name, description) => {
    await retestPage.screenshot({ path: `${shotDir}${name}.png`, fullPage: false })
    results.push({ name, description, url: retestPage.url(), dateText: await retestPage.locator('body').innerText().then(t => t.match(/PLAN PREVIEW\s+\d+\s+Sept/)?.[0] ?? null) })
  }
  const exercise = async (prefix) => {
    await retestPage.goto(localURL, { waitUntil: 'networkidle', timeout: 60_000 })
    await capture(`${prefix}-default`, 'Default farm page')
    const startScroll = await retestPage.evaluate(() => scrollY)
    await retestPage.mouse.move(320, 650)
    await retestPage.mouse.down()
    await retestPage.mouse.move(320, 330, { steps: 8 })
    await retestPage.mouse.up()
    await retestPage.waitForTimeout(300)
    // This is a mouse-driven pointer drag, not native touchscreen/CDP scroll evidence.
    results.push({ action: `${prefix}-default-pointer-drag`, startScroll, endScroll: await retestPage.evaluate(() => scrollY), limitation: 'Not native touch scrolling evidence' })

    const moveFarm = retestPage.getByRole('button', { name: /Move farm/i }).first()
    if (!await moveFarm.count()) throw new Error('Move farm control missing')
    await moveFarm.click()
    await retestPage.waitForTimeout(250)
    await capture(`${prefix}-move-mode`, 'Farm movement mode after Move farm')

    const bedCandidates = retestPage.getByRole('button', { name: /^[A-D][1-4],/ })
    let bed = bedCandidates.first()
    for (let i = 0; i < await bedCandidates.count(); i++) {
      const candidate = bedCandidates.nth(i)
      const candidateBox = await candidate.boundingBox()
      if (candidateBox && candidateBox.x >= 0 && candidateBox.x + candidateBox.width <= (await retestPage.viewportSize()).width) { bed = candidate; break }
    }
    const before = await bed.boundingBox()
    if (!before) throw new Error('No bed available for direct drag')
    const bedName = await bed.getAttribute('aria-label')
    await retestPage.mouse.move(before.x + before.width / 2, before.y + before.height / 2)
    await retestPage.mouse.down()
    await retestPage.mouse.move(before.x + before.width / 2 + 90, before.y + before.height / 2 + 35, { steps: 5 })
    await retestPage.mouse.up()
    await retestPage.waitForTimeout(250)
    const after = await bed.boundingBox()
    results.push({ action: `${prefix}-direct-bed-drag`, bedName, before, after })

    const arrows = retestPage.getByRole('button').filter({ has: retestPage.locator('svg') })
    const arrowNames = await arrows.evaluateAll(els => els.map(e => e.getAttribute('aria-label')).filter(x => /move|pan|left|right|up|down/i.test(x || '')))
    for (const name of arrowNames.slice(0, 4)) await retestPage.getByRole('button', { name, exact: true }).click()
    results.push({ action: `${prefix}-arrow-controls`, arrowNames })

    const done = retestPage.getByRole('button', { name: /^(Done|Exit map movement)$/i })
    if (!await done.count()) throw new Error('Done control missing in movement mode')
    await done.click()
    await capture(`${prefix}-move-done`, 'Farm after arrow controls and Done')

    const b3 = retestPage.getByRole('button', { name: /^B3, Kailan/ }).first()
    await b3.click()
    await retestPage.waitForTimeout(250)
    results.push({ action: `${prefix}-deliberate-bed-tap`, dialog: await retestPage.getByRole('dialog').count() })
    await capture(`${prefix}-bed-tap`, 'Bed detail after deliberate tap')
    await retestPage.keyboard.press('Escape')

    const dateControlNames = await retestPage.locator('button').evaluateAll(els => els.map(e => e.getAttribute('aria-label') || e.textContent?.trim()).filter(x => /date|day|preview|week/i.test(x || '')))
    const previous = retestPage.getByRole('button', { name: /Previous|Earlier|Back one/i }).first()
    const next = retestPage.getByRole('button', { name: /Next|Later|Forward one/i }).first()
    const dates = []
    if (await next.count()) { await next.click(); dates.push((await retestPage.locator('body').innerText()).match(/PLAN PREVIEW\s+\d+\s+Sept/)?.[0] ?? null) }
    if (await previous.count()) { await previous.click(); dates.push((await retestPage.locator('body').innerText()).match(/PLAN PREVIEW\s+\d+\s+Sept/)?.[0] ?? null) }
    results.push({ action: `${prefix}-date-arrows`, dateControlNames, previous: await previous.count(), next: await next.count(), dates })
    await capture(`${prefix}-date-arrows`, 'Preview after Next and Previous date controls')
  }

  await exercise('09-mobile-local')
  await retestPage.setViewportSize({ width: 1280, height: 800 })
  await exercise('10-desktop-local')
  console.log(JSON.stringify(results, null, 2))
  await retestBrowser.close()
  process.exit(0)
}

const browser = await chromium.launch({ headless: true })
let storageState
try { storageState = JSON.parse(await fs.readFile('/tmp/farmtact-review02-state.json', 'utf8')) } catch {}
const context = await browser.newContext({ viewport: { width: 360, height: 800 }, hasTouch: true, isMobile: true, storageState })
const page = await context.newPage()
const log = []
const snap = async (name) => {
  await page.screenshot({ path: `${shotDir}${name}.png`, fullPage: false })
  log.push({ name, url: page.url(), text: (await page.locator('body').innerText()).slice(0, 8000) })
}
const buttons = async () => page.getByRole('button').allTextContents()

await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 60_000 })
await snap('01-mobile-home')
log.push({ mobileButtons: await buttons(), mobileLinks: await page.getByRole('link').allTextContents() })

// Exercise the visible farm map with direct taps, a drag gesture, and page scrolling.
const farmRegion = page.locator('main').first()
const box = await farmRegion.boundingBox()
if (box) {
  const a1Map = page.getByRole('button', { name: /^A1, Caixin/ }).first()
  const beforeDrag = await a1Map.boundingBox().catch(() => null)
  await page.mouse.click(box.x + box.width * 0.5, box.y + Math.min(box.height * 0.65, 500))
  await page.waitForTimeout(500)
  await snap('02-mobile-map-tap')
  await page.keyboard.press('Escape')
  await page.mouse.move(box.x + box.width * 0.72, box.y + Math.min(box.height * 0.65, 500))
  await page.mouse.down()
  await page.mouse.move(box.x + box.width * 0.25, box.y + Math.min(box.height * 0.65, 500), { steps: 8 })
  await page.mouse.up()
  await page.waitForTimeout(400)
  const afterDrag = await a1Map.boundingBox().catch(() => null)
  log.push({ mapDrag: { beforeDrag, afterDrag } })
  await snap('03-mobile-map-drag')
}

await page.mouse.wheel(0, 650)
await page.waitForTimeout(400)
await snap('04-mobile-scroll')

const a1 = page.getByRole('button', { name: /^A1, Caixin/ }).first()
if (await a1.count()) {
  await a1.click()
  await page.waitForTimeout(400)
  await snap('05-mobile-bed-a1')
  log.push({ bedA1: (await page.locator('body').innerText()).slice(-2500), dialogCount: await page.getByRole('dialog').count() })
  await page.keyboard.press('Escape')
}

const dateRange = page.locator('input[type="range"]').first()
if (await dateRange.count()) {
  const before = await dateRange.inputValue()
  const rangeBox = await dateRange.boundingBox()
  if (rangeBox) await page.touchscreen.tap(rangeBox.x + rangeBox.width * 0.65, rangeBox.y + rangeBox.height / 2)
  await page.waitForTimeout(400)
  const after = await dateRange.inputValue()
  await snap('05b-mobile-date-preview')
  log.push({ datePreview: { before, after, excerpt: (await page.locator('body').innerText()).slice(-1200) } })
}

log.push({ dateControls: await page.locator('button').evaluateAll(els => els.map(e => ({ text: e.textContent?.trim(), aria: e.getAttribute('aria-label'), title: e.getAttribute('title') })).filter(x => x.aria || x.title || /Today/.test(x.text || ''))) })

// Visit each bottom/top navigation destination once, preserving the same tenant/session.
for (const label of ['Farm', 'Plan', 'Briefing', 'Evidence']) {
  const control = page.getByRole('link', { name: new RegExp(`^${label}`, 'i') }).or(page.getByRole('button', { name: new RegExp(`^${label}`, 'i') })).first()
  if (await control.count()) {
    await control.click()
    await page.waitForTimeout(600)
    await snap(`05-mobile-nav-${label.toLowerCase()}`)
    log.push({ nav: label, buttons: await buttons() })
  }
}

// One permitted numerical scenario, using the normal visible planning control.
const numerical = page.getByRole('button', { name: /Plan with numerical tools/i })
if (!storageState && await numerical.count()) {
  await numerical.click()
  await page.waitForTimeout(12_000)
  await snap('06-mobile-numerical-result')
  log.push({ numericalResult: (await page.locator('body').innerText()).slice(0, 12_000), numericalButtons: await buttons() })
}

// Desktop uses the same context storage/session.
await page.setViewportSize({ width: 1280, height: 800 })
await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 60_000 })
await snap('07-desktop-home')
log.push({ desktopButtons: await buttons(), desktopLinks: await page.getByRole('link').allTextContents() })
await page.mouse.wheel(0, 700)
await page.waitForTimeout(400)
await snap('08-desktop-scroll')

console.log(JSON.stringify(log, null, 2))
await context.storageState({ path: '/tmp/farmtact-review02-state.json' })
await fs.chmod('/tmp/farmtact-review02-state.json', 0o600)
await browser.close()
