import { mkdir } from 'node:fs/promises'
import { chromium } from '../../../apps/web/node_modules/@playwright/test/index.mjs'

const base = process.env.FARMTACT_BASE_URL || 'https://farmtact.fly.dev'
const out = 'apps/web/screenshots/panel/review03'
const observations = { checks: [], errors: [], screenshots: [], texts: {} }
const note = (name, pass, detail) => observations.checks.push({ name, pass: Boolean(pass), detail })
const shot = async (page, name) => {
  const path = `${out}/${name}`
  await page.screenshot({ path, animations: 'disabled', caret: 'hide' })
  observations.screenshots.push(path)
}
const visibleButton = (page, name) => page.getByRole('button', { name, exact: true }).filter({ visible: true }).first()
const text = async locator => (await locator.innerText()).replace(/\s+/g, ' ').trim()

await mkdir(out, { recursive: true })
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 430, height: 932 },
  hasTouch: true,
  isMobile: true,
  reducedMotion: 'reduce',
})
const page = await context.newPage()
page.on('pageerror', error => observations.errors.push(`page: ${error.message}`))
page.on('console', message => { if (message.type() === 'error') observations.errors.push(`console: ${message.text()}`) })

try {
  const response = await page.goto(base, { waitUntil: 'networkidle', timeout: 60_000 })
  note('live root responds', response?.status() === 200, response?.status())
  const assets = await page.locator('script[src],link[rel="stylesheet"]').evaluateAll(nodes => nodes.map(n => n.getAttribute('src') || n.getAttribute('href')).filter(Boolean))
  observations.texts.build_assets = assets.filter(item => /assets\/.+-[A-Za-z0-9_-]+\.(js|css)/.test(item))
  observations.texts.mobile_heading = await text(page.locator('body').first()).then(value => value.slice(0, 700))
  await shot(page, 'mobile-430-board.png')

  const tools = page.getByRole('button', { name: /^(Farm tools|Tools)$/ }).filter({ visible: true }).first()
  note('mobile farm tools control visible', await tools.isVisible())
  await tools.click()
  await page.waitForTimeout(500)
  observations.texts.tools = (await text(page.locator('body'))).slice(0, 1200)
  await shot(page, 'mobile-430-tools.png')
  await page.goto(base, { waitUntil: 'networkidle', timeout: 60_000 })

  const scenarioButton = visibleButton(page, 'Scenario lab')
  await scenarioButton.click()
  const lab = page.getByRole('dialog', { name: 'Scenario lab' })
  await lab.waitFor()
  observations.texts.lab_initial = (await text(lab)).slice(0, 1800)
  const challenge = lab.getByRole('combobox', { name: 'Challenge', exact: true })
  if (await challenge.count()) await challenge.selectOption('short_handed_week')
  const labour = lab.getByRole('slider', { name: /^Available labour/ })
  const before = await labour.inputValue()
  await labour.focus()
  await page.keyboard.press('Home')
  const min = Number(await labour.getAttribute('min'))
  for (let i = min; i < 60; i++) await page.keyboard.press('ArrowRight')
  const after = await labour.inputValue()
  note('labour assumption changed through accessible slider', before !== after && Number(after) === 60, { before, after })
  await shot(page, 'mobile-430-assumption.png')

  const beforeMain = await page.locator('body').getAttribute('data-latest-run-id').catch(() => null)
  const created = page.waitForResponse(r => r.url().endsWith('/api/v1/scenarios') && r.request().method() === 'POST', { timeout: 30_000 })
  await lab.getByRole('button', { name: 'Run experiment', exact: true }).click()
  const createdResponse = await created
  note('one numerical scenario accepted by UI', createdResponse.status() === 201, createdResponse.status())
  await lab.getByRole('heading', { name: 'Inspect the trade-offs' }).waitFor({ timeout: 120_000 })
  observations.texts.result = (await text(lab)).slice(0, 3500)
  note('saved scenario exposes three policy choices', await lab.getByRole('button', { name: /^(Lean|Balanced|Resilient)$/ }).count() === 3)
  for (const policy of ['Lean', 'Balanced', 'Resilient']) {
    await lab.getByRole('button', { name: policy, exact: true }).click()
    const table = lab.locator('table').first()
    note(`${policy} policy table visible`, await table.isVisible(), (await text(table)).slice(0, 900))
  }
  await shot(page, 'mobile-430-scenario-result.png')
  const mark = lab.getByRole('button', { name: 'Mark trade-offs inspected', exact: true })
  if (await mark.count()) await mark.click()
  await page.keyboard.press('Escape')

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.reload({ waitUntil: 'networkidle', timeout: 60_000 })
  await shot(page, 'desktop-1280-board.png')
  const desktopScenario = visibleButton(page, 'Scenario lab')
  await desktopScenario.click()
  const desktopLab = page.getByRole('dialog', { name: 'Scenario lab' })
  await desktopLab.waitFor()
  observations.texts.desktop_lab = (await text(desktopLab)).slice(0, 2500)
  const compareStep = desktopLab.getByText('Compare', { exact: true }).first()
  await compareStep.click()
  const savedBranch = desktopLab.getByText(/Short-handed week ·/).first()
  note('saved numerical scenario survives reload and viewport change', await savedBranch.isVisible())
  await shot(page, 'desktop-1280-saved-scenario.png')
  await page.keyboard.press('Escape')
  const afterMain = await page.locator('body').getAttribute('data-latest-run-id').catch(() => null)
  note('main-plan DOM identity unchanged when exposed', beforeMain === afterMain, { beforeMain, afterMain })
} catch (error) {
  observations.errors.push(error.stack || String(error))
} finally {
  await context.close().catch(error => observations.errors.push(`teardown context: ${error.message}`))
  await browser.close().catch(error => observations.errors.push(`teardown browser: ${error.message}`))
}

console.log(JSON.stringify(observations, null, 2))
if (observations.errors.length) process.exitCode = 1
