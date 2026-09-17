import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { access, mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(new URL('../..', import.meta.url).pathname)
const base = (process.env.BASE_URL || 'http://127.0.0.1:4196').replace(/\/$/, '')
const storage = process.env.STORAGE_STATE || '/tmp/farmtact-v15-cards-storage.json'
const output = resolve(root, 'reports/v15/final-accessibility.json')
await access(storage)

const report = {
  status: 'RUNNING', base, storageSource: storage, checks: [], defects: [], limitations: [
    'ARIA and focus checks inspect Chromium DOM semantics; they do not claim testing with a real screen reader.',
    'The software-keyboard check emulates viewport occlusion while a form control is focused; it is not a physical mobile keyboard test.',
    'The offscreen check inspects persisted facts and animation lifecycle after scrolling; browser scheduling may differ on physical devices.'
  ], requests: { writes: [], provider: [] }, failures: []
}
const check = (name, pass, detail, defect = false) => {
  report.checks.push({ name, pass: Boolean(pass), detail })
  if (!pass && defect) report.defects.push({ name, detail })
}
let browser
try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ storageState: storage, viewport: { width: 390, height: 844 }, reducedMotion: 'no-preference' })
  const page = await context.newPage()
  page.on('request', request => {
    const path = new URL(request.url()).pathname
    if (!['GET', 'HEAD', 'OPTIONS'].includes(request.method())) report.requests.writes.push(`${request.method()} ${path}`)
    if (/deepseek|provider|inference/i.test(request.url())) report.requests.provider.push(`${request.method()} ${path}`)
  })
  await page.route('**/api/v1/**', route => ['GET', 'HEAD', 'OPTIONS'].includes(route.request().method()) ? route.continue() : route.abort('blockedbyclient'))
  await page.goto(`${base}/play`, { waitUntil: 'domcontentloaded' })
  await page.locator('.ic-shell').waitFor()
  const build = await page.locator('script[type=module]').first().getAttribute('src')
  report.build = build

  const saved = page.locator('.ic-saved-change')
  check('recorded event exposes persistent dated causal facts', await saved.count() === 1 && /Recorded simulation.*2026-09-14.*harvest kg.*delivered kg.*disposed kg/i.test((await saved.textContent()) || ''), await saved.textContent(), true)
  const scene = await page.locator('.ic-scene').evaluate(node => ({ label: node.getAttribute('aria-label'), text: node.textContent, date: node.querySelector('.ic-scene-head strong')?.textContent, modes: [...node.querySelectorAll('.ic-beds article')].slice(0, 8).map(n => n.textContent?.replace(/\s+/g, ' ').trim()) }))
  check('friendly scene semantics include mode date bed name crop and status', scene.label === 'Passive farm scene' && scene.date === '2026-09-14' && /Sandbox farm · real operations disabled/.test(await page.locator('.ic-heading').textContent() || '') && scene.modes.every(Boolean) && scene.modes.some(x => /A1.*Caixin.*harvested/i.test(x || '')) && scene.modes.some(x => /B1.*Caixin.*growing/i.test(x || '')), scene, true)

  const initialLive = await page.locator('.ic-transition').count()
  await page.waitForTimeout(1700)
  const settled = await page.locator('.ic-transition').count()
  const animations = await page.locator('.ic-beds article').evaluateAll(nodes => nodes.map(n => ({ name: getComputedStyle(n).animationName, state: getComputedStyle(n).animationPlayState })))
  check('normal-motion causal emphasis finishes and leaves persistent facts', initialLive === 1 && settled === 0 && animations.every(a => a.name === 'none') && await saved.count() === 1, { initialLive, settled, animations }, true)

  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.locator('.ic-shell').waitFor()
  const replayOnReload = await page.locator('.ic-transition').count()
  check('settled event does not announce or animate again on reload', replayOnReload === 0, { replayOnReload, event: await saved.textContent() }, true)
  await page.waitForTimeout(1700)

  const activeBefore = await page.locator('.ic-card').getAttribute('aria-label')
  await page.locator('.ic-card').focus()
  await page.keyboard.press('ArrowRight')
  await page.waitForFunction(label => document.querySelector('.ic-card')?.getAttribute('aria-label') !== label, activeBefore)
  const semantics = await page.evaluate(() => ({
    activeCards: document.querySelectorAll('.ic-card').length,
    liveCards: [...document.querySelectorAll('.ic-card')].map(n => ({ label: n.getAttribute('aria-label'), live: n.getAttribute('aria-live') })),
    statuses: [...document.querySelectorAll('[role=status]')].map(n => n.textContent?.replace(/\s+/g, ' ').trim()),
    focused: document.activeElement?.getAttribute('aria-label') || document.activeElement?.textContent?.replace(/\s+/g, ' ').trim()
  }))
  check('only the active card is exposed with a current polite label', semantics.activeCards === 1 && semantics.liveCards.length === 1 && semantics.liveCards[0].live === 'polite' && semantics.liveCards[0].label !== activeBefore, semantics, true)
  check('card change does not retain a stale accessible card name', Boolean(semantics.focused) && semantics.focused === semantics.liveCards[0].label, semantics, true)

  // Labelled viewport fixture: reset only the client-side "seen" marker for the real saved event,
  // add inert layout space, then move the real scene wholly offscreen while its finite emphasis runs.
  const expectedFacts = await saved.textContent()
  await page.evaluate(() => localStorage.removeItem('farmtact:v15:seen-scene-transition'))
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.locator('.ic-shell').waitFor()
  await page.locator('.ic-transition').waitFor()
  const fixtureStart = await page.evaluate(() => {
    const spacer = document.createElement('div'); spacer.id = 'v15-offscreen-layout-fixture'; spacer.setAttribute('aria-hidden', 'true'); spacer.style.height = '2400px'; document.body.append(spacer)
    window.scrollTo(0, document.documentElement.scrollHeight)
    const rect = document.querySelector('.ic-scene')?.getBoundingClientRect()
    return { top: rect?.top, bottom: rect?.bottom, viewport: innerHeight, transition: document.querySelector('.ic-transition')?.textContent, saved: document.querySelector('.ic-saved-change')?.textContent }
  })
  await page.waitForTimeout(1700)
  const fixtureEnd = await page.evaluate(() => {
    const rect = document.querySelector('.ic-scene')?.getBoundingClientRect(); const offscreen = Boolean(rect && rect.bottom < 0)
    const saved = document.querySelector('.ic-saved-change')?.textContent || ''
    const transition = Boolean(document.querySelector('.ic-transition'))
    window.scrollTo(0, 0); document.querySelector('#v15-offscreen-layout-fixture')?.remove()
    return { top: rect?.top, bottom: rect?.bottom, offscreen, transition, saved }
  })
  await page.waitForTimeout(100)
  const fixtureReturn = await page.evaluate(() => ({ transition: Boolean(document.querySelector('.ic-transition')), saved: document.querySelector('.ic-saved-change')?.textContent }))
  check('labelled offscreen viewport fixture settles the real event to identical persistent facts without replay', Boolean(fixtureStart.transition) && Number(fixtureStart.bottom) < 0 && fixtureEnd.offscreen && !fixtureEnd.transition && fixtureEnd.saved === expectedFacts && !fixtureReturn.transition && fixtureReturn.saved === expectedFacts, { fixture: 'inert 2400px aria-hidden layout spacer; client-only seen marker reset for the existing recorded event', fixtureStart, fixtureEnd, fixtureReturn }, true)

  const sizes = await page.locator('.ic-actions button:visible').evaluateAll(nodes => nodes.map(n => { const r = n.getBoundingClientRect(); return { label: n.textContent?.trim(), width: r.width, height: r.height, disabled: n.disabled } }))
  check('visible card controls meet the 44px target minimum', sizes.every(x => x.width >= 44 && x.height >= 44), sizes, true)

  // Open the existing preferences card and enable reduced motion using its real control.
  while (!await page.getByRole('button', { name: 'More', exact: true }).count()) await page.getByRole('button', { name: 'Back', exact: true }).last().click()
  await page.getByRole('button', { name: 'More', exact: true }).click()
  const historyCard = page.locator('.ic-card').filter({ hasText: 'History & preferences' })
  for (let i = 0; i < 4; i++) {
    const before = await page.locator('.ic-card').getAttribute('data-card-id')
    await page.locator('.ic-card').focus()
    await page.keyboard.press('ArrowRight')
    await page.waitForFunction(id => document.querySelector('.ic-card')?.getAttribute('data-card-id') !== id, before)
  }
  await historyCard.waitFor()
  await page.getByRole('button', { name: 'Open tool', exact: true }).click()
  const accessibility = page.locator('.integrated-tool__card').filter({ hasText: 'Accessibility & audio' })
  for (let i = 0; i < 4; i++) {
    const before = await page.locator('.integrated-tool__card').getAttribute('data-card-id')
    await page.locator('.integrated-tool__card').focus()
    await page.keyboard.press('ArrowRight')
    await page.waitForFunction(id => document.querySelector('.integrated-tool__card')?.getAttribute('data-card-id') !== id, before)
  }
  await accessibility.waitFor()
  await page.locator('.integrated-tool footer').getByRole('button', { name: 'Open', exact: true }).click()
  await page.getByLabel('Reduced motion').waitFor()
  const reduced = page.getByLabel('Reduced motion')
  if (!await reduced.isChecked()) await reduced.check()
  await page.waitForFunction(() => document.documentElement.dataset.reducedMotion === 'true')
  const reducedFacts = await page.evaluate(() => ({ stored: Object.entries(localStorage).filter(([k]) => k.includes('reduced-motion')), data: document.documentElement.dataset.reducedMotion, media: matchMedia('(prefers-reduced-motion: reduce)').matches }))
  check('existing motion preference persists an explicit immediate-facts mode', reducedFacts.data === 'true' && reducedFacts.stored.some(([,v]) => v === 'true'), reducedFacts, true)

  // Emulate keyboard occlusion by shrinking the visual viewport with the native checkbox focused.
  await reduced.focus()
  await page.setViewportSize({ width: 390, height: 500 })
  await reduced.scrollIntoViewIfNeeded()
  const keyboard = await reduced.evaluate(node => { const r = node.getBoundingClientRect(); return { focused: document.activeElement === node, top: r.top, bottom: r.bottom, innerHeight, documentWidth: document.documentElement.scrollWidth, viewportWidth: document.documentElement.clientWidth } })
  check('focused form control remains visible with simulated keyboard viewport', keyboard.focused && keyboard.top >= 0 && keyboard.bottom <= keyboard.innerHeight && keyboard.documentWidth <= keyboard.viewportWidth + 1, keyboard, true)

  check('read-only lifecycle audit sends no API write or provider request', report.requests.writes.length === 0 && report.requests.provider.length === 0, report.requests, true)
  report.status = report.defects.length ? 'FAIL' : 'PASS'
} catch (error) {
  report.status = 'ERROR'
  report.failures.push(error instanceof Error ? error.stack : String(error))
  process.exitCode = 1
} finally {
  await browser?.close()
  await mkdir(resolve(root, 'reports/v15'), { recursive: true })
  await writeFile(output, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
}
