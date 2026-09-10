/** Read-only interaction audit of the latest published FarmTact edition. */
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const origin = process.env.FARMTACT_BASE_URL || 'https://farmtact.fly.dev'
const reportPath = resolve(root, process.env.FARMTACT_BASELINE_REPORT || 'reports/v7/baseline_audit.json')
const screenshotDir = resolve(root, process.env.FARMTACT_BASELINE_SCREENSHOTS || 'apps/web/screenshots/v7-baseline')
const report = {
  started_at: new Date().toISOString(), origin, release: null, checks: [], failures: [], errors: [], screenshots: [],
  requests: { provider_capable_posts: [], numerical_posts: [], conversation_record_posts: [] },
  limitations: [
    'Responsive checks use headless Chromium emulation, not physical iOS or Android hardware.',
    'The software keyboard does not open in headless Chromium, so keyboard occlusion and native dictation remain unobserved.',
    'No message, council, invitation, planning run, scenario, acceptance, or provider request was submitted.',
    'Conversation response pacing and active-turn interruption were inspected in source and existing recorded evidence, not invoked live.',
  ],
}
const check = (name, pass, detail = '') => {
  const row = { name, pass: Boolean(pass), detail: String(detail).replace(/\s+/g, ' ').trim().slice(0, 900) }
  report.checks.push(row); if (!row.pass) report.failures.push(row)
}
const shot = async (page, width, name, fullPage = false) => {
  const path = resolve(screenshotDir, `${name}-${width}.png`)
  await page.screenshot({ path, fullPage, animations: 'disabled', caret: 'hide' })
  report.screenshots.push(relative(root, path))
}

await mkdir(dirname(reportPath), { recursive: true })
await mkdir(screenshotDir, { recursive: true })
const browser = await chromium.launch({ headless: true })
try {
  const request = await browser.newContext()
  const releaseResponse = await request.request.get(`${origin}/api/releases`)
  const releases = await releaseResponse.json()
  report.release = { latest: releases.latest, url: `${origin}/${releases.latest}/` }
  check('release registry identifies v6 as latest', releaseResponse.ok() && releases.latest === 'v6', JSON.stringify(report.release))
  await request.close()

  const context = await browser.newContext({ viewport: { width: 360, height: 844 }, hasTouch: true, reducedMotion: 'reduce' })
  const page = await context.newPage()
  page.on('pageerror', error => report.errors.push(`page: ${error.message}`))
  page.on('console', message => { if (message.type() === 'error' && !/429/.test(message.text())) report.errors.push(`console: ${message.text()}`) })
  page.on('request', request => {
    if (request.method() !== 'POST') return
    const path = new URL(request.url()).pathname
    const width = page.viewportSize()?.width || 0
    if (/\/conversations\/[^/]+\/(messages|invite|council)$/.test(path) || /planning-runs/.test(path)) report.requests.provider_capable_posts.push({ width, path })
    else if (/\/scenarios/.test(path)) report.requests.numerical_posts.push({ width, path })
    else if (/\/conversations$/.test(path)) report.requests.conversation_record_posts.push({ width, path })
  })
  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 })
    const response = await page.goto(`${origin}/v6/`, { waitUntil: 'networkidle', timeout: 60_000 })
    check(`${width}px v6 loads`, response?.status() === 200, response?.status())
    check(`${width}px no horizontal overflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), await page.evaluate(() => `${document.documentElement.scrollWidth}/${innerWidth}`))
    check(`${width}px reduced motion active`, await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches))
    await shot(page, width, 'farm-board', true)

    const bed = page.locator('.world-bed').first()
    await bed.scrollIntoViewIfNeeded(); await bed.click(); const bedDialog = page.locator('.game-panel[role="dialog"]:visible').last(); await bedDialog.waitFor()
    const bedText = await bedDialog.innerText()
    check(`${width}px selected bed exposes ask and experiment actions`, /Ask Mei/.test(bedText) && /Try a change/.test(bedText), bedText)
    await shot(page, width, 'selected-bed')
    await bedDialog.getByRole('button', { name: 'Ask Mei' }).click()
    const conversation = page.getByRole('dialog', { name: /Mei · Production/ }); await conversation.waitFor()
    await conversation.getByPlaceholder(/Ask Mei about this snapshot/).waitFor()
    const conversationText = await conversation.innerText()
    check(`${width}px conversation retains selected bed context`, /Current context: A1 · caixin/.test(conversationText), conversationText)
    check(`${width}px conversation offers targeted and council participation`, /Invite advisor/.test(conversationText) && /Convene council/.test(conversationText), conversationText)
    check(`${width}px conversation discloses device-keyboard voice option`, /Voice typing: use the microphone on your device keyboard/.test(conversationText), conversationText)
    check(`${width}px composer touch target is at least 44px`, await conversation.getByRole('button', { name: 'Send message' }).evaluate(node => node.getBoundingClientRect().height >= 44))
    check(`${width}px context has no removable selection controls`, await conversation.locator('[aria-label*="Remove"], .selection-chip, .context-chip').count() === 0)
    await shot(page, width, 'bed-conversation')
    await conversation.getByRole('button', { name: 'Close' }).click()

    await page.getByRole('button', { name: 'Scenario lab' }).click()
    const lab = page.getByRole('dialog', { name: 'Scenario lab' }); await lab.waitFor()
    const labText = await lab.innerText()
    check(`${width}px scenario lab exposes explicit staged workflow`, /Briefing/.test(labText) && /Assumptions/.test(labText) && /Compare/.test(labText), labText)
    check(`${width}px current controls omit bed reservation and order confirmation`, !/reserve bed|reservation interval|order confirmation/i.test(labText), labText)
    await shot(page, width, 'scenario-lab')
    await lab.getByRole('button', { name: 'Close' }).click()

    check(`${width}px audit did not submit provider-capable actions`, report.requests.provider_capable_posts.filter(item => item.width === width).length === 0)
    check(`${width}px audit did not submit numerical mutations`, report.requests.numerical_posts.filter(item => item.width === width).length === 0)
  }
  await context.close()
} catch (error) { report.errors.push(error.stack || String(error)) }
finally {
  report.finished_at = new Date().toISOString()
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  await browser.close()
}
console.log(JSON.stringify({ checks: report.checks.length, failures: report.failures, errors: report.errors, screenshots: report.screenshots.length, requests: report.requests }, null, 2))
if (report.failures.length || report.errors.length || report.requests.provider_capable_posts.length || report.requests.numerical_posts.length) process.exitCode = 1
