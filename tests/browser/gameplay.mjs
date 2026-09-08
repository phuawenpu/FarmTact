import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const baseURL = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const screenshotDir = resolve(root, process.env.FARMTACT_GAMEPLAY_SCREENSHOT_DIR || 'apps/web/screenshots/gameplay')
const reportPath = resolve(root, process.env.FARMTACT_GAMEPLAY_REPORT || 'reports/gameplay_browser.json')
const report = { started_at: new Date().toISOString(), base_url: baseURL, checks: [], failures: [], console_errors: [], page_errors: [], screenshots: [], scenario_id: null }

function check(name, pass, detail) {
  report.checks.push({ name, pass, ...(detail === undefined ? {} : { detail }) })
  if (!pass) report.failures.push({ name, detail })
}

async function capture(page, filename) {
  const path = resolve(screenshotDir, filename)
  await page.screenshot({ path, animations: 'disabled', caret: 'hide' })
  report.screenshots.push(relative(root, path))
}

async function openButton(page, name) {
  const button = page.getByRole('button', { name }).first()
  await button.scrollIntoViewIfNeeded()
  await button.focus()
  await page.keyboard.press('Enter')
  return button
}

await mkdir(screenshotDir, { recursive: true })
let browser
try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' })
  const page = await context.newPage()
  page.on('console', message => { if (message.type() === 'error') report.console_errors.push(message.text()) })
  page.on('pageerror', error => report.page_errors.push(error.message))
  await page.goto(baseURL, { waitUntil: 'networkidle' })

  check('farm world is the homepage', await page.getByRole('region', { name: 'Interactive farm world' }).isVisible())
  check('world renders all 16 real beds', await page.locator('.world-bed').count() === 16, await page.locator('.world-bed').count())
  check('all six advisors are reachable', await page.locator('.world-advisor').count() === 6, await page.locator('.world-advisor').count())
  check('all eight farm facilities are tappable', await page.locator('.world-facility').count() === 8, await page.locator('.world-facility').count())
  check('mobile navigation exposes all six rooms', await page.locator('.thumb-nav button').count() === 6, await page.locator('.thumb-nav button').count())
  const smallTargets = await page.locator('.world-bed,.world-advisor,.world-facility,.world-chip,.world-controls button').evaluateAll(nodes => nodes.map(node => ({ label: node.getAttribute('aria-label') || node.textContent?.trim(), width: node.getBoundingClientRect().width, height: node.getBoundingClientRect().height })).filter(item => item.width < 44 || item.height < 44))
  check('scene touch targets are at least 44 pixels', smallTargets.length === 0, smallTargets)
  const occludedControls = await page.locator('.world-controls button').evaluateAll(nodes => nodes.map(node => { const box = node.getBoundingClientRect(); const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2); return { label: node.getAttribute('aria-label'), exposed: top === node || Boolean(top && node.contains(top)) } }).filter(item => !item.exposed))
  check('map controls are not occluded by mobile navigation', occludedControls.length === 0, occludedControls)

  const canvas = page.locator('.farm-world-canvas')
  const originalTransform = await canvas.getAttribute('style')
  await page.getByRole('button', { name: 'Zoom in' }).click()
  const buttonZoom = await canvas.getAttribute('style')
  check('zoom control changes the world transform', buttonZoom !== originalTransform)
  await page.getByRole('button', { name: 'Recenter farm' }).click()
  await page.locator('.farm-world-viewport').hover()
  const scrollBeforeWheel = await page.evaluate(() => scrollY)
  await page.mouse.wheel(0, -120)
  const wheelZoom = await canvas.getAttribute('style')
  check('mouse wheel zooms without scrolling the page', wheelZoom !== originalTransform && await page.evaluate(() => scrollY) === scrollBeforeWheel, { transform: wheelZoom, before: scrollBeforeWheel, after: await page.evaluate(() => scrollY) })
  const clearPoint = await page.locator('.farm-world-viewport').evaluate(node => {
    const box = node.getBoundingClientRect()
    for (let y = box.top + 70; y < box.bottom - 70; y += 30) for (let x = box.left + 20; x < box.right - 20; x += 30) {
      const target = document.elementFromPoint(x, y)
      if (target && !target.closest('button')) return { x, y }
    }
    return { x: box.left + box.width / 2, y: box.top + box.height / 2 }
  })
  await page.mouse.move(clearPoint.x, clearPoint.y)
  await page.mouse.down()
  await page.mouse.move(clearPoint.x + 50, clearPoint.y + 30, { steps: 4 })
  await page.mouse.up()
  check('pointer drag pans the world', (await canvas.getAttribute('style')) !== wheelZoom)
  await page.getByRole('button', { name: 'Recenter farm' }).click()

  const scrubber = page.getByRole('slider', { name: 'Preview simulation date' })
  const beforeBeds = await page.locator('.world-bed').evaluateAll(nodes => nodes.map(node => node.getAttribute('aria-label')))
  await scrubber.fill(String(await scrubber.getAttribute('max')))
  const afterBeds = await page.locator('.world-bed').evaluateAll(nodes => nodes.map(node => node.getAttribute('aria-label')))
  check('date scrubber previews scheduled changes', JSON.stringify(beforeBeds) !== JSON.stringify(afterBeds), { changed: afterBeds.filter((value, index) => value !== beforeBeds[index]).length })
  check('preview is explicitly non-observational', await page.getByText('Preview only — this does not advance time or create observations.').isVisible())

  const listLauncher = await openButton(page, 'Accessible farm list')
  const listDialog = page.getByRole('dialog', { name: 'Farm list' })
  check('accessible table lists all beds', await listDialog.locator('tbody tr').count() === 16, await listDialog.locator('tbody tr').count())
  await page.keyboard.press('Shift+Tab')
  check('dialog traps keyboard focus', await listDialog.evaluate(node => node.contains(document.activeElement)))
  await page.keyboard.press('Escape')
  check('dialog restores focus to launcher', await listLauncher.evaluate(node => node === document.activeElement))

  await openButton(page, 'Quest journal')
  const journal = page.getByRole('dialog', { name: 'Quest journal' })
  check('quest journal exposes four repeatable challenges', await journal.locator('.quest-list article').count() === 4)
  await page.keyboard.press('Escape')

  await openButton(page, 'Accessible farm list')
  const emptyBedRow = page.getByRole('dialog', { name: 'Farm list' }).locator('tbody tr').filter({ hasText: 'C1' })
  await emptyBedRow.getByRole('button', { name: 'Inspect' }).click()
  const emptyBed = page.getByRole('dialog', { name: 'C1' })
  check('empty plot remains explorable through the accessible farm list', await emptyBed.getByText('Unplanted bed').isVisible())
  await emptyBed.getByRole('button', { name: 'Try a change' }).click()
  const lab = page.getByRole('dialog', { name: 'Scenario lab' })
  await lab.waitFor()
  await lab.getByLabel('Challenge').selectOption('busy_market')
  const demandControl = lab.locator('.range-control').filter({ hasText: 'Market demand' }).locator('input')
  check('busy-market quest opens with relevant demand change', Number(await demandControl.inputValue()) !== 100, await demandControl.inputValue())
  const batchControl = lab.getByLabel('Selected batch')
  const actualBatchIds = await batchControl.locator('option').evaluateAll(options => options.map(option => option.value))
  check('empty plot falls back to an actual occupied batch', actualBatchIds.length > 0 && actualBatchIds.includes(await batchControl.inputValue()) && await batchControl.inputValue() !== 'batch-09', { selected: await batchControl.inputValue(), options: actualBatchIds })
  await demandControl.fill('130')
  check('all five bounded scenario controls are visible', await lab.locator('.range-control').count() === 5, await lab.locator('.range-control').count())
  const formReadability = await lab.evaluate(node => ({
    labels: [...node.querySelectorAll('.range-control b,.scenario-targets label')].map(label => ({ text: label.textContent?.trim(), fontSize: Number.parseFloat(getComputedStyle(label).fontSize) })),
    selects: [...node.querySelectorAll('.scenario-targets select')].map(select => ({ label: select.parentElement?.childNodes[0]?.textContent?.trim(), fontSize: Number.parseFloat(getComputedStyle(select).fontSize), height: select.getBoundingClientRect().height })),
  }))
  check('scenario form labels and selects remain readable on mobile', formReadability.labels.every(label => label.fontSize >= 11) && formReadability.selects.every(select => select.fontSize >= 11 && select.height >= 44), formReadability)
  await lab.getByRole('button', { name: 'Run experiment' }).click()
  await lab.getByText('Inspect the trade-offs').waitFor({ timeout: 60_000 })
  check('branch result names explicit policy', await lab.getByText('Compare the same policy', { exact: true }).isVisible())
  check('before-after table shows exact deltas', await lab.getByRole('table').isVisible() && await lab.locator('.metric-delta').count() >= 6)
  check('result exposes frozen snapshot association', await lab.getByText(/Snapshot .* baseline/i).isVisible())
  const scenarioResponse = await page.evaluate(async () => (await (await fetch('/api/v1/scenarios')).json()).scenarios[0])
  report.scenario_id = scenarioResponse?.id || null
  check('experiment persisted as an isolated completed branch', scenarioResponse?.status === 'COMPLETED' && scenarioResponse?.inference_calls === 0, { id: scenarioResponse?.id, status: scenarioResponse?.status, inference_calls: scenarioResponse?.inference_calls })
  check('empty-plot non-harvest quest creates a real branch with the fallback batch', scenarioResponse?.quest_id === 'busy_market' && actualBatchIds.includes(scenarioResponse?.controls?.batch_id), { quest_id: scenarioResponse?.quest_id, batch_id: scenarioResponse?.controls?.batch_id, valid_batch_ids: actualBatchIds })
  const branchReadability = await lab.locator('.branch-cards').evaluate(node => {
    const card = node.querySelector('article')
    const debrief = node.querySelector('.computed-debrief')
    const body = card?.querySelector('p:not(.kicker)')
    const buttons = [...node.querySelectorAll('button')]
    return {
      overflow: node.scrollWidth - node.clientWidth,
      container_width: node.clientWidth,
      card_width: card?.getBoundingClientRect().width || 0,
      body_font_size: body ? Number.parseFloat(getComputedStyle(body).fontSize) : 0,
      debrief_font_size: debrief ? Number.parseFloat(getComputedStyle(debrief).fontSize) : 0,
      button_heights: buttons.map(button => button.getBoundingClientRect().height),
    }
  })
  check('scenario debrief card is readable without mobile overflow', branchReadability.overflow <= 1 && branchReadability.card_width >= branchReadability.container_width - 1 && branchReadability.body_font_size >= 13 && branchReadability.debrief_font_size >= 13 && branchReadability.button_heights.every(height => height >= 44), branchReadability)
  await lab.getByRole('button', { name: 'Mark trade-offs inspected' }).click()
  await lab.getByRole('button', { name: 'Trade-off badge earned' }).waitFor()
  check('inspection earns the trade-off badge only after review', await lab.getByRole('button', { name: 'Trade-off badge earned' }).isDisabled())
  await capture(page, 'quest-comparison-390.png')

  await lab.getByRole('button', { name: 'Ask an advisor about this branch' }).click()
  const conversation = page.getByRole('dialog', { name: /Asha · Planning chair/ })
  await conversation.waitFor()
  check('interpretation stays attached to exact scenario branch', await conversation.getByText(new RegExp(`frozen branch ${String(report.scenario_id).slice(0, 8)}`)).isVisible())
  await conversation.getByRole('button', { name: 'Replay' }).waitFor({ state: 'visible' })
  await conversation.getByRole('button', { name: 'Replay' }).waitFor({ state: 'attached' })
  await page.waitForFunction(() => { const button = [...document.querySelectorAll('button')].find(node => node.textContent?.includes('Replay')); return button && !button.disabled })
  const inferenceBeforeReplay = await page.evaluate(async id => (await (await fetch(`/api/v1/conversations/${id}`)).json()).messages.length, (await page.evaluate(async () => (await (await fetch('/api/v1/conversations')).json()).conversations[0].id)))
  await conversation.getByRole('button', { name: 'Replay' }).click()
  await conversation.getByText(/Recorded replay/).waitFor()
  const latestConversation = await page.evaluate(async () => (await (await fetch('/api/v1/conversations')).json()).conversations[0])
  const inferenceAfterReplay = await page.evaluate(async id => (await (await fetch(`/api/v1/conversations/${id}`)).json()).messages.length, latestConversation.id)
  check('conversation replay adds no messages or paid calls', inferenceAfterReplay === inferenceBeforeReplay, { before: inferenceBeforeReplay, after: inferenceAfterReplay })
  check('typed follow-up and council controls remain available', await conversation.getByLabel('Message Asha').isVisible() && await conversation.getByRole('button', { name: 'Convene council' }).isVisible())
  await page.keyboard.press('Escape')

  await openButton(page, 'Scenario lab')
  const reopened = page.getByRole('dialog', { name: 'Scenario lab' })
  await reopened.getByRole('button', { name: /Compare/ }).first().click()
  check('completed branches remain revisitable', await reopened.getByText(scenarioResponse.name).first().isVisible())
  await page.keyboard.press('Escape')

  const reducedDuration = await page.locator('.world-bed').first().evaluate(node => getComputedStyle(node).animationDuration)
  check('reduced motion is honored', ['0.00001ms', '0.00001s', '1e-05s', '0s'].includes(reducedDuration), reducedDuration)
  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 })
    await page.goto(baseURL, { waitUntil: 'networkidle' })
    const dimensions = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }))
    check(`${width}px has no body overflow`, dimensions.body <= dimensions.viewport + 1, dimensions)
    if (width < 700) {
      const controlHits = await page.locator('.world-controls button').evaluateAll(nodes => {
        const navigation = document.querySelector('.thumb-nav')
        const navigationBox = navigation?.getBoundingClientRect()
        return nodes.map(node => {
          const box = node.getBoundingClientRect()
          const x = box.left + box.width / 2
          const y = box.top + box.height / 2
          const target = document.elementFromPoint(x, y)
          return {
            label: node.getAttribute('aria-label'),
            hit: target === node || Boolean(target && node.contains(target)),
            hit_element: target?.getAttribute('aria-label') || target?.tagName || null,
            bounds: { top: box.top, right: box.right, bottom: box.bottom, left: box.left },
            navigation_top: navigationBox?.top ?? null,
            above_navigation: Boolean(navigationBox && box.bottom <= navigationBox.top),
          }
        })
      })
      check(`${width}px all three map controls are coordinate-hittable above fixed navigation`, controlHits.length === 3 && controlHits.every(control => control.hit && control.above_navigation), controlHits)
    }
    await capture(page, `farm-world-${width}.png`)
  }
  check('no browser console errors', report.console_errors.length === 0, report.console_errors)
  check('no uncaught page errors', report.page_errors.length === 0, report.page_errors)
  await context.close()
} catch (error) {
  report.failures.push({ name: 'suite execution', detail: error instanceof Error ? error.stack || error.message : String(error) })
} finally {
  if (browser) await browser.close()
  report.completed_at = new Date().toISOString()
  report.status = report.failures.length ? 'FAIL' : 'PASS'
  await mkdir(dirname(reportPath), { recursive: true })
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
}

if (report.failures.length) {
  process.stderr.write(`${JSON.stringify(report.failures, null, 2)}\n`)
  process.exitCode = 1
}
