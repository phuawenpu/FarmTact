import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const origin = (process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080').replace(/\/$/, '')
const edition = (process.env.FARMTACT_EDITION || '').replace(/^\/+|\/+$/g, '')
const url = `${origin}${edition ? `/${edition}/` : '/'}`
const reportPath = resolve(root, process.env.FARMTACT_SEVEN_AGENT_REPORT || 'reports/seven_agents_browser.json')
const browserState = process.env.FARMTACT_BROWSER_STATE
const savedState = browserState ? JSON.parse(await readFile(browserState, 'utf8')) : null
const storageState = savedState?.cookies ? savedState : savedState?.cookie ? { cookies: [{ name: edition ? `farmtact_${edition}_session` : 'farmtact_session', value: savedState.cookie, domain: new URL(url).hostname, path: edition ? `/${edition}/` : '/', httpOnly: true, secure: new URL(url).protocol === 'https:', sameSite: 'Strict' }], origins: [] } : undefined
const report = { url, checks: [], failures: [], screenshots: [] }
const check = (name, pass, detail) => { report.checks.push({ name, pass, detail }); if (!pass) report.failures.push({ name, detail }) }
const browser = await chromium.launch({ headless: true })

try {
  for (const width of [360, 390, 430, 1280]) {
    const page = await browser.newPage({ viewport: { width, height: width < 700 ? 844 : 900 }, reducedMotion: 'reduce', ...(storageState ? { storageState } : {}) })
    let inferencePosts = 0
    page.on('request', request => { if (request.method() === 'POST' && /\/conversations\/[^/]+\/(messages|invite|council)$/.test(new URL(request.url()).pathname)) inferencePosts++ })
    await page.goto(url, { waitUntil: 'networkidle' })
    const world = page.getByRole('group', { name: 'Farm map' })
    await world.waitFor()
    const agents = page.locator('.world-advisor')
    check(`${width}px map shows seven advisors`, await agents.count() === 7, await agents.count())
    const names = await agents.locator('.world-advisor__name b').allTextContents()
    check(`${width}px roster has exact seven names`, ['Ravi','Hana','Idris','Mei','Lina','Ben','Asha'].every(name => names.includes(name)), names)
    await page.getByRole('button', { name: /^Talk to Idris, Market/ }).click()
    const panel = page.getByRole('dialog', { name: 'Idris · Market' })
    await panel.waitFor()
    const signals = panel.getByLabel('Market community signals')
    await signals.waitFor()
    check(`${width}px market panel states feed status and count`, /Connected feeds\s*0/i.test(await signals.innerText()) && /Observations\s*0/i.test(await signals.innerText()), await signals.innerText())
    const switcher = panel.getByLabel('Advisor shortcuts')
    check(`${width}px selector contains seven advisors`, await switcher.locator('button').count() === 7, await switcher.locator('button').count())
    const box = await switcher.boundingBox()
    check(`${width}px selector stays usable`, Boolean(box && box.height >= 58), box)
    await panel.locator('.panel-loading').waitFor({ state: 'hidden', timeout: 10_000 }).catch(() => {})
    const shot = resolve(root, `apps/web/screenshots/seven-agents-${width}.png`)
    await page.screenshot({ path: shot, animations: 'disabled' }); report.screenshots.push(shot.slice(root.length + 1))
    const lina = switcher.getByRole('button', { name: 'Talk to Lina' })
    await lina.focus(); await page.keyboard.press('Enter')
    await page.getByRole('dialog', { name: 'Lina · Supply Chain' }).waitFor()
    check(`${width}px keyboard activates the seventh advisor`, await page.getByRole('dialog', { name: 'Lina · Supply Chain' }).isVisible(), 'Lina opened with Enter')
    check(`${width}px browsing advisors sends no inference request`, inferencePosts === 0, inferencePosts)
    await page.close()
  }
} catch (error) {
  report.failures.push({ name: 'browser journey', detail: error instanceof Error ? error.stack : String(error) })
} finally {
  await browser.close(); await mkdir(dirname(reportPath), { recursive: true }); await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
}

if (report.failures.length) process.exitCode = 1
else console.log(JSON.stringify({ checks: report.checks.length, url, screenshots: report.screenshots }, null, 2))
