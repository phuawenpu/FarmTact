import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const baseURL = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const screenshotDir = resolve(root, process.env.FARMTACT_SCREENSHOT_DIR || 'apps/web/screenshots/v6-crop-atlas')
const reportPath = resolve(root, process.env.FARMTACT_BROWSER_REPORT || 'reports/v6/crop_atlas_browser.json')
const expected = ['garlic_chives', 'sawtooth_coriander']
const result = {
  started_at: new Date().toISOString(), base_url: baseURL, checks: [], failures: [], errors: [], screenshots: [],
  limitations: [
    'Responsive checks use headless Chromium emulation, not physical iOS or Android hardware.',
    'One AI reviewer inspected colour and grayscale captures; the five-human recognition protocol has not been run.',
    'Illustrations are representative identifiers and do not verify cultivar, crop health, maturity or farm performance.',
  ],
}
const check = (name, pass, detail = '') => {
  const record = { name, pass: Boolean(pass), detail: String(detail).replace(/\s+/g, ' ').trim().slice(0, 600) }
  result.checks.push(record)
  if (!record.pass) result.failures.push(record)
}

await mkdir(screenshotDir, { recursive: true })
await mkdir(dirname(reportPath), { recursive: true })
const browser = await chromium.launch({ headless: true })

try {
  const authContext = await browser.newContext()
  const bootstrapResponse = await authContext.request.get(`${baseURL.replace(/\/$/, '')}/api/v1/bootstrap`)
  check('v6 synthetic farm bootstrap is available', bootstrapResponse.status() === 200, bootstrapResponse.status())
  const storageState = await authContext.storageState()
  if (new URL(baseURL).protocol === 'http:') {
    storageState.cookies = storageState.cookies.map(cookie => ({ ...cookie, secure: false }))
  }
  await authContext.close()
  for (const width of [360, 390, 430, 1280]) {
    const context = await browser.newContext({
      viewport: { width, height: width === 1280 ? 900 : 844 },
      hasTouch: width < 1280,
      isMobile: width < 1280,
      reducedMotion: 'reduce',
      storageState,
    })
    const page = await context.newPage()
    page.on('pageerror', error => result.errors.push(`${width}px page: ${error.message}`))
    page.on('console', message => { if (message.type() === 'error') result.errors.push(`${width}px console: ${message.text()}`) })
    const response = await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 60_000 })
    check(`${width}px application responds`, response?.status() === 200, response?.status())

    const cropNav = page.getByRole('button', { name: 'Crops', exact: true }).filter({ visible: true }).first()
    await cropNav.focus()
    await page.keyboard.press('Enter')
    const cards = page.locator('.crop-profile-card')
    await cards.first().waitFor()
    check(`${width}px shows twelve crop profiles`, await cards.count() === 12, await cards.count())
    check(`${width}px has no horizontal overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => `${document.documentElement.scrollWidth}/${innerWidth}`))
    check(`${width}px reduced-motion preference is active`, await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches))

    for (const image of await cards.locator('img').all()) {
      await image.scrollIntoViewIfNeeded()
      await image.evaluate(node => node.decode?.()).catch(() => {})
    }
    await page.evaluate(() => scrollTo(0, 0))

    for (const cropId of expected) {
      const image = page.locator(`.crop-profile-card img[src*="/${cropId}-ready.svg"]`)
      check(`${width}px ${cropId} uses mature original art`, await image.count() === 1, await image.getAttribute('src').catch(() => 'missing'))
      check(`${width}px ${cropId} image loaded`, await image.evaluate(node => node.complete && node.naturalWidth > 0).catch(() => false))
    }

    const screenshot = resolve(screenshotDir, `atlas-${width}.png`)
    await page.screenshot({ path: screenshot, animations: 'disabled', caret: 'hide', fullPage: true })
    result.screenshots.push(relative(root, screenshot))

    if (width === 390) {
      for (const { id, label, alias } of [
        { id: 'garlic_chives', label: /Garlic chives/i, alias: 'flat chives' },
        { id: 'sawtooth_coriander', label: /Sawtooth coriander/i, alias: 'culantro' },
      ]) {
        const search = page.getByPlaceholder('Search crop or local alias')
        await search.fill(alias)
        check(`${alias} search finds one profile`, await cards.count() === 1, await cards.count())
        const card = cards.first()
        check(`${id} search resolves expected label`, label.test(await card.innerText()), await card.innerText())
        await card.focus()
        await page.keyboard.press('Enter')
        const dialog = page.getByRole('dialog', { name: label })
        await dialog.waitFor()
        await dialog.getByText('Loading evidence profile…').waitFor({ state: 'hidden' })
        const text = await dialog.innerText()
        check(`${id} remains a knowledge profile`, text.includes('No planning recipe is available.'), text)
        check(`${id} exposes evidence`, /Evidence/.test(text) && /Open source/.test(text), text)
        const evidenceLinks = await dialog.locator('a[href^="https://"]').count()
        check(`${id} exposes two sourced evidence links`, evidenceLinks === 2, evidenceLinks)
        const profileScreenshot = resolve(screenshotDir, `${id}-profile-390.png`)
        await dialog.screenshot({ path: profileScreenshot, animations: 'disabled', caret: 'hide' })
        result.screenshots.push(relative(root, profileScreenshot))
        await dialog.evaluate(node => { node.scrollTop = node.scrollHeight })
        const evidenceScreenshot = resolve(screenshotDir, `${id}-evidence-390.png`)
        await dialog.screenshot({ path: evidenceScreenshot, animations: 'disabled', caret: 'hide' })
        result.screenshots.push(relative(root, evidenceScreenshot))
        await page.keyboard.press('Escape')
        check(`${id} dialog closes with Escape`, !(await dialog.isVisible()))
        await search.fill('')
      }
      await page.addStyleTag({ content: '.crop-profile-card__art { filter: grayscale(1); }' })
      const grayscale = resolve(screenshotDir, 'atlas-390-grayscale.png')
      await page.screenshot({ path: grayscale, animations: 'disabled', caret: 'hide', fullPage: true })
      result.screenshots.push(relative(root, grayscale))
    }
    await context.close()
  }
} catch (error) {
  result.errors.push(error.stack || String(error))
} finally {
  result.finished_at = new Date().toISOString()
  await writeFile(reportPath, `${JSON.stringify(result, null, 2)}\n`)
  await browser.close()
}

console.log(JSON.stringify({ checks: result.checks.length, failures: result.failures, errors: result.errors, screenshots: result.screenshots }, null, 2))
if (result.failures.length || result.errors.length) process.exitCode = 1
