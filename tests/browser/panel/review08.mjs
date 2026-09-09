import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'
import fs from 'node:fs/promises'

const baseURL = 'https://farmtact.fly.dev'
const shotDir = new URL('../../../apps/web/screenshots/panel/review08/', import.meta.url).pathname
await fs.mkdir(shotDir, { recursive: true })

const auth = JSON.parse(await fs.readFile('/tmp/farmtact-explorer-release.json', 'utf8'))
const supplied = Array.isArray(auth.cookies) ? auth.cookies : (Array.isArray(auth) ? auth : [auth])
if (!supplied.some(x => x && x.name && x.value) && typeof auth.cookie === 'string') {
  const separator = auth.cookie.indexOf('=')
  if (separator > 0) supplied.push({ name: auth.cookie.slice(0, separator), value: auth.cookie.slice(separator + 1) })
  else supplied.push({ name: 'farmtact_session', value: auth.cookie })
}
const cookies = supplied.filter(x => x && x.name && x.value).map(x => ({
  name: x.name,
  value: x.value,
  domain: x.domain || 'farmtact.fly.dev',
  path: x.path || '/',
  secure: x.secure ?? true,
  httpOnly: x.httpOnly ?? true,
  sameSite: ['Strict', 'Lax', 'None'].includes(x.sameSite) ? x.sameSite : 'Lax',
}))
if (!cookies.length) throw new Error('Assigned session file did not contain a usable cookie')

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 360, height: 800 },
  hasTouch: true,
  isMobile: true,
  reducedMotion: 'reduce',
})
await context.addCookies(cookies)
const page = await context.newPage()
const observations = { build: {}, mobile: {}, desktop: {}, errors: [] }
page.on('pageerror', error => observations.errors.push(`pageerror: ${error.message}`))
page.on('console', msg => { if (msg.type() === 'error') observations.errors.push(`console: ${msg.text()}`) })
const snap = async name => page.screenshot({ path: `${shotDir}${name}.png`, fullPage: false })
const targetAudit = async () => page.locator('button, a, input, [role="button"]').evaluateAll(elements => elements.map(el => {
  const r = el.getBoundingClientRect()
  const style = getComputedStyle(el)
  return { label: (el.getAttribute('aria-label') || el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 90), tag: el.tagName, w: Math.round(r.width), h: Math.round(r.height), font: style.fontSize, display: style.display, visible: !!(r.width && r.height) }
}).filter(x => x.visible))

await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 60_000 })
observations.build.scripts = await page.locator('script[src]').evaluateAll(xs => xs.map(x => x.getAttribute('src')).filter(Boolean))
observations.build.styles = await page.locator('link[rel="stylesheet"]').evaluateAll(xs => xs.map(x => x.getAttribute('href')).filter(Boolean))
observations.mobile.authenticated = !/Start a private demo/i.test(await page.locator('body').innerText())
observations.mobile.reducedMotion = await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)
observations.mobile.motionAudit = await page.locator('body *').evaluateAll(elements => elements.map(el => {
  const s = getComputedStyle(el)
  return { tag: el.tagName, className: String(el.className || '').slice(0, 100), animation: s.animationDuration, transition: s.transitionDuration }
}).filter(x => x.animation !== '0s' || x.transition !== '0s').slice(0, 50))
observations.mobile.initialText = (await page.locator('body').innerText()).slice(0, 7000)
observations.mobile.targets = await targetAudit()
observations.mobile.overflow = await page.evaluate(() => ({ innerWidth, scrollWidth: document.documentElement.scrollWidth, innerHeight, scrollHeight: document.documentElement.scrollHeight }))
await snap('01-mobile-farm-360')

const accessibleBeds = page.getByRole('button', { name: /^[A-Z]\d+,/ })
observations.mobile.bedCount = await accessibleBeds.count()
if (await accessibleBeds.count()) {
  const bed = accessibleBeds.first()
  observations.mobile.bedName = await bed.getAttribute('aria-label') || await bed.innerText()
  await bed.tap()
  await page.waitForTimeout(300)
  observations.mobile.dialogAfterBedTap = await page.getByRole('dialog').count()
  observations.mobile.activeAfterBedTap = await page.evaluate(() => ({ tag: document.activeElement?.tagName, text: document.activeElement?.textContent?.trim().slice(0, 100), aria: document.activeElement?.getAttribute('aria-label') }))
  observations.mobile.bedDetailText = (await page.locator('body').innerText()).slice(-3500)
  await snap('02-mobile-bed-detail-360')
  await page.keyboard.press('Escape')
  await page.waitForTimeout(200)
  observations.mobile.dialogAfterEscape = await page.getByRole('dialog').count()
}

const range = page.locator('input[type="range"]').first()
if (await range.count()) {
  observations.mobile.dateBefore = await range.inputValue()
  await range.focus()
  await page.keyboard.press('ArrowRight')
  await page.waitForTimeout(250)
  observations.mobile.dateAfterKeyboard = await range.inputValue()
  observations.mobile.dateContext = (await page.locator('body').innerText()).slice(-2200)
  await snap('03-mobile-date-preview-360')
}
await page.mouse.wheel(0, 650)
await page.waitForTimeout(250)
observations.mobile.scrollY = await page.evaluate(() => scrollY)
await snap('04-mobile-scrolled-360')

await page.setViewportSize({ width: 1280, height: 800 })
await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 60_000 })
observations.desktop.initialText = (await page.locator('body').innerText()).slice(0, 7000)
observations.desktop.targets = await targetAudit()
observations.desktop.overflow = await page.evaluate(() => ({ innerWidth, scrollWidth: document.documentElement.scrollWidth, innerHeight, scrollHeight: document.documentElement.scrollHeight }))
await snap('05-desktop-farm-1280')

const focusTrail = []
for (let i = 0; i < 60; i++) {
  await page.keyboard.press('Tab')
  focusTrail.push(await page.evaluate(() => {
    const el = document.activeElement
    const r = el?.getBoundingClientRect()
    const s = el ? getComputedStyle(el) : null
    return { tag: el?.tagName, label: (el?.getAttribute('aria-label') || el?.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 100), x: Math.round(r?.x || 0), y: Math.round(r?.y || 0), outline: s?.outline, boxShadow: s?.boxShadow }
  }))
  if (/^[A-Z]\d+,/.test(focusTrail.at(-1).label)) break
}
observations.desktop.focusTrail = focusTrail
await snap('06-desktop-keyboard-focus-1280')

const focusedBed = focusTrail.findIndex(x => /^[A-Z]\d+,/.test(x.label))
if (focusedBed >= 0) {
  // Recreate the same tab position after the audit so Enter activation is deterministic.
  await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 60_000 })
  for (let i = 0; i <= focusedBed; i++) await page.keyboard.press('Tab')
  await page.keyboard.press('Enter')
  await page.waitForTimeout(250)
  observations.desktop.dialogAfterKeyboardBed = await page.getByRole('dialog').count()
  observations.desktop.activeInDialog = await page.evaluate(() => ({ tag: document.activeElement?.tagName, label: (document.activeElement?.getAttribute('aria-label') || document.activeElement?.textContent || '').trim().slice(0, 100) }))
  await snap('07-desktop-keyboard-bed-dialog-1280')
  await page.keyboard.press('Escape')
  observations.desktop.dialogAfterEscape = await page.getByRole('dialog').count()
}

await fs.writeFile(`${shotDir}observations.json`, JSON.stringify(observations, null, 2), { mode: 0o600 })
console.log(JSON.stringify({ screenshots: 7, mobileAuthenticated: observations.mobile.authenticated, bedCount: observations.mobile.bedCount, reducedMotion: observations.mobile.reducedMotion, errors: observations.errors.length }, null, 2))
await browser.close()
