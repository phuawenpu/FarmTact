import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'

const base = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const out = process.env.FARMTACT_AUDIO_REPORT || 'reports/edition_audio.json'
const report = { status: 'RUNNING', base, checks: [], errors: [], audio_requests: [] }
const check = (name, pass, detail) => { report.checks.push({ name, pass, detail }); if (!pass) throw Error(name) }
const browser = await chromium.launch()
let page
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } })
  await context.addInitScript(() => {
    if (!sessionStorage.getItem('farmtact-audio-test-started')) {
      localStorage.removeItem('farmtact:v2:audio:preferences')
      sessionStorage.setItem('farmtact-audio-test-started', '1')
    }
    let rejectNext = sessionStorage.getItem('farmtact-audio-rejection-tested') !== '1'
    window.__farmAudioTest = { plays: [], pauses: 0 }
    HTMLMediaElement.prototype.play = function () {
      window.__farmAudioTest.plays.push(new URL(this.src).pathname)
      if (rejectNext) { rejectNext = false; sessionStorage.setItem('farmtact-audio-rejection-tested', '1'); return Promise.reject(new DOMException('Test autoplay rejection', 'NotAllowedError')) }
      return Promise.resolve()
    }
    const originalPause = HTMLMediaElement.prototype.pause
    HTMLMediaElement.prototype.pause = function () { window.__farmAudioTest.pauses++; return originalPause.call(this) }
  })
  page = await context.newPage()
  page.on('request', request => { if (/\/audio\/.*\.wav$/.test(new URL(request.url()).pathname)) report.audio_requests.push(new URL(request.url()).pathname) })
  page.on('pageerror', error => report.errors.push(error.message))
  await page.goto(`${base}/v2`, { waitUntil: 'networkidle' })
  const controls = page.getByRole('region', { name: 'Sound controls' })
  await controls.waitFor()
  check('v2 starts silent without fetching audio', report.audio_requests.length === 0, [...report.audio_requests])
  check('master sound control is initially off', await controls.getByRole('button', { name: 'Turn sound on' }).getAttribute('aria-pressed') === 'false')
  check('mobile controls begin compact', await controls.getByRole('button', { name: 'Sound preferences' }).getAttribute('aria-expanded') === 'false' && await controls.getByLabel('Music volume').count() === 0)
  await controls.getByRole('button', { name: 'Sound preferences' }).click()
  check('music defaults to enabled at 20 percent', await controls.getByRole('button', { name: 'Music' }).getAttribute('aria-pressed') === 'true' && await controls.getByLabel('Music volume').inputValue() === '20')
  check('effects default to enabled at 35 percent', await controls.getByRole('button', { name: 'Effects' }).getAttribute('aria-pressed') === 'true' && await controls.getByLabel('Effects volume').inputValue() === '35')
  const boxes = await controls.getByRole('button').evaluateAll(nodes => nodes.map(node => node.getBoundingClientRect().height))
  check('all sound buttons meet the 44px touch target', boxes.every(height => height >= 44), boxes)

  await controls.getByRole('button', { name: 'Turn sound on' }).click()
  await controls.getByText('Sound could not start. Try again when you’re ready.').waitFor()
  check('a rejected play is nonblocking and offers retry', await controls.getByRole('button', { name: 'Retry sound' }).isVisible())
  await controls.getByRole('button', { name: 'Retry sound' }).click()
  await page.waitForTimeout(200)
  check('explicit retry activates music', await controls.getByRole('button', { name: 'Turn sound off' }).getAttribute('aria-pressed') === 'true')
  check('music is fetched only after deliberate activation from the frozen v2 path', report.audio_requests.some(path => path === '/v2/audio/farm-garden-loop.wav'), [...report.audio_requests])

  await controls.getByLabel('Music volume').fill('27')
  await controls.getByRole('button', { name: 'Effects' }).click()
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('farmtact:v2:audio:preferences')))
  check('v2 preferences use edition-scoped storage', stored.musicVolume === .27 && stored.effectsEnabled === false, stored)
  await page.reload({ waitUntil: 'networkidle' })
  const reloaded = page.getByRole('region', { name: 'Sound controls' })
  await reloaded.getByRole('button', { name: 'Sound preferences' }).click()
  check('reload restores preferences but stays silent', await reloaded.getByLabel('Music volume').inputValue() === '27' && await reloaded.getByRole('button', { name: 'Effects' }).getAttribute('aria-pressed') === 'false' && await reloaded.getByRole('button', { name: 'Turn sound on' }).isVisible())
  check('reload does not autoplay', (await page.evaluate(() => window.__farmAudioTest.plays.length)) === 0)

  await reloaded.getByRole('button', { name: 'Turn sound on' }).click()
  await reloaded.getByRole('button', { name: 'Effects' }).click()
  const playsBeforeNavigation = await page.evaluate(() => window.__farmAudioTest.plays.length)
  await page.getByRole('button', { name: 'Tools', exact: true }).click()
  await page.getByRole('button', { name: 'Tools', exact: true }).click()
  await page.waitForTimeout(100)
  const navigationPlays = await page.evaluate(start => window.__farmAudioTest.plays.slice(start).filter(path => path === '/v2/audio/navigate.wav'), playsBeforeNavigation)
  check('rapid duplicate navigation effects are throttled', navigationPlays.length === 1, navigationPlays)
  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')) })
  check('hidden pages pause audio', await page.evaluate(() => window.__farmAudioTest.pauses > 0))
  await page.route('**/v2/audio/navigate.wav', route => route.abort('failed'))
  await page.reload({ waitUntil: 'networkidle' })
  const failureControls = page.getByRole('region', { name: 'Sound controls' })
  await failureControls.getByRole('button', { name: 'Turn sound on' }).click()
  await page.getByRole('button', { name: 'Tools', exact: true }).click()
  await failureControls.getByText('Sound could not start. Try again when you’re ready.').waitFor()
  check('a missing effect asset reports a nonblocking audio error', await page.getByRole('main').isVisible())
  await page.unroute('**/v2/audio/navigate.wav')
  check('browser run has no uncaught page errors', report.errors.length === 0, report.errors)
  report.status = 'PASS'
} catch (error) {
  report.status = 'FAIL'; report.errors.push(String(error)); process.exitCode = 1
} finally {
  await browser.close(); await mkdir(out.slice(0, out.lastIndexOf('/')) || '.', { recursive: true }); await writeFile(out, JSON.stringify(report, null, 2) + '\n')
}
