import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'

const base = process.env.FARMTACT_BASE_URL || 'https://farmtact.fly.dev'
const out = process.env.FARMTACT_AUDIO_REPORT || 'reports/v5/audio_browser.json'
const shots = 'apps/web/screenshots/v5-audio'
const editions = ['v2', 'v4']
const report = { status: 'RUNNING', base, methodology: 'Native Chromium media state and Web Audio decoding; no claim of physical speaker/headphone listening.', editions: {}, errors: [] }
const browser = await chromium.launch()

async function reviewEdition(edition) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } })
  await context.addInitScript(() => {
    const NativeAudio = window.Audio
    window.__farmtactAudioElements = []
    window.Audio = function (...args) {
      const audio = new NativeAudio(...args)
      window.__farmtactAudioElements.push(audio)
      return audio
    }
  })
  const page = await context.newPage()
  const result = { checks: [], requests: [], console_errors: [], page_errors: [], decoded_assets: [] }
  const check = (name, pass, detail = null) => result.checks.push({ name, pass: Boolean(pass), detail })
  page.on('request', request => { const path = new URL(request.url()).pathname; if (path.includes('/audio/')) result.requests.push(path) })
  page.on('console', message => { if (message.type() === 'error') result.console_errors.push(message.text()) })
  page.on('pageerror', error => result.page_errors.push(error.message))
  try {
    await page.goto(`${base}/${edition}/`, { waitUntil: 'networkidle' })
    const controls = page.getByRole('region', { name: 'Sound controls' })
    await controls.waitFor()
    check('sound is opt-in', await controls.getByRole('button', { name: 'Turn sound on' }).getAttribute('aria-pressed') === 'false')
    check('no audio fetched before opt-in', result.requests.length === 0, [...result.requests])
    check('one visible control group on mobile', await controls.count() === 1)
    const masterBox = await controls.getByRole('button', { name: 'Turn sound on' }).boundingBox()
    check('master control meets 44 px touch target', masterBox && masterBox.height >= 44, masterBox)
    await page.screenshot({ path: `${shots}/${edition}-mobile-silent.png`, fullPage: true })

    await controls.getByRole('button', { name: 'Sound preferences' }).click()
    check('default music setting is 20 percent', await controls.getByLabel('Music volume').inputValue() === '20')
    check('default effects setting is 35 percent', await controls.getByLabel('Effects volume').inputValue() === '35')
    const sliderBoxes = await controls.locator('input[type=range]').evaluateAll(nodes => nodes.map(node => { const box = node.getBoundingClientRect(); return { width: box.width, height: box.height } }))
    check('mobile sliders have usable horizontal travel', sliderBoxes.every(box => box.width >= 100), sliderBoxes)
    await controls.getByLabel('Music volume').focus()
    await page.keyboard.press('ArrowRight')
    check('music volume is keyboard adjustable', await controls.getByLabel('Music volume').inputValue() === '21')
    await controls.getByLabel('Music volume').fill('20')
    await page.screenshot({ path: `${shots}/${edition}-mobile-preferences.png`, fullPage: true })

    await controls.getByRole('button', { name: 'Turn sound on' }).click()
    await page.waitForTimeout(900)
    const media = await page.evaluate(() => window.__farmtactAudioElements.map(a => ({ src: new URL(a.src).pathname, paused: a.paused, duration: a.duration, currentTime: a.currentTime, volume: a.volume, loop: a.loop, readyState: a.readyState, networkState: a.networkState, error: a.error?.message || null })))
    const music = media.find(item => item.src.endsWith('/farm-garden-loop.wav'))
    check('native audio element loaded and entered play state', Boolean(music && !music.paused && music.readyState >= 2), music)
    check('playhead advances after activation', Boolean(music && music.currentTime > 0), music)
    check('music element applies 0.20 software gain', Boolean(music && Math.abs(music.volume - .2) < .001), music)
    check('loop flag is set', Boolean(music?.loop), music)
    check('asset path is edition-pinned', Boolean(music?.src === `/${edition}/audio/farm-garden-loop.wav`), music)
    check('master exposes active state', await controls.getByRole('button', { name: 'Turn sound off' }).getAttribute('aria-pressed') === 'true')

    const decoded = await page.evaluate(async ({ edition, names }) => {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      const audioContext = new AudioContextClass()
      const rows = []
      for (const name of names) {
        const response = await fetch(`/${edition}/audio/${name}.wav`)
        const bytes = await response.arrayBuffer()
        let decoded = null
        let decodeError = null
        try {
          const buffer = await audioContext.decodeAudioData(bytes.slice(0))
          decoded = { duration: buffer.duration, sampleRate: buffer.sampleRate, channels: buffer.numberOfChannels, frames: buffer.length }
        } catch (error) { decodeError = String(error) }
        rows.push({ name, status: response.status, contentType: response.headers.get('content-type'), bytes: bytes.byteLength, decoded, decodeError })
      }
      await audioContext.close()
      return rows
    }, { edition, names: ['farm-garden-loop', 'navigate', 'detail', 'confirm', 'complete', 'error'] })
    result.decoded_assets = decoded
    check('all six WAV assets return and decode', decoded.every(row => row.status === 200 && row.contentType?.includes('audio') && row.decoded && !row.decodeError), decoded)

    const before = await page.evaluate(() => window.__farmtactAudioElements.map(a => ({ src: new URL(a.src).pathname, paused: a.paused })))
    await page.getByRole('button', { name: 'Tools', exact: true }).click()
    await page.waitForTimeout(250)
    const after = await page.evaluate(() => window.__farmtactAudioElements.map(a => ({ src: new URL(a.src).pathname, paused: a.paused, currentTime: a.currentTime, volume: a.volume })))
    check('navigation creates and starts an effect at 0.35 gain', after.some(item => item.src === `/${edition}/audio/navigate.wav` && item.volume === .35), { before, after })

    await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')) })
    check('backgrounding pauses all media', await page.evaluate(() => window.__farmtactAudioElements.every(a => a.paused)))
    await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => false }); document.dispatchEvent(new Event('visibilitychange')) })
    await page.waitForTimeout(250)
    check('returning to a visible page resumes opted-in music', await page.evaluate(() => window.__farmtactAudioElements.some(a => a.src.endsWith('/farm-garden-loop.wav') && !a.paused)))

    await controls.getByLabel('Effects volume').fill('44')
    const stored = await page.evaluate(edition => ({ selected: JSON.parse(localStorage.getItem(`farmtact:${edition}:audio:preferences`) || 'null'), keys: Object.keys(localStorage).filter(key => key.includes(':audio:preferences')) }), edition)
    check('preferences persist under this edition only', stored.selected?.effectsVolume === .44 && stored.keys.length === 1 && stored.keys[0] === `farmtact:${edition}:audio:preferences`, stored)

    await controls.getByRole('button', { name: 'Turn sound off' }).click()
    check('master off pauses all created media', await page.evaluate(() => window.__farmtactAudioElements.every(a => a.paused)))
    await page.reload({ waitUntil: 'networkidle' })
    check('reload stays silent', await page.getByRole('region', { name: 'Sound controls' }).getByRole('button', { name: 'Turn sound on' }).isVisible())

    if (edition === 'v4') {
      await page.setViewportSize({ width: 1280, height: 900 })
      await page.screenshot({ path: `${shots}/${edition}-desktop-silent.png`, fullPage: true })
      const desktopControls = page.getByRole('region', { name: 'Sound controls' })
      check('one visible control group on desktop', await desktopControls.count() === 1)
    }
    check('no uncaught page errors', result.page_errors.length === 0, result.page_errors)
  } finally {
    await context.close()
  }
  return result
}

try {
  await mkdir(shots, { recursive: true })
  for (const edition of editions) report.editions[edition] = await reviewEdition(edition)
  report.status = Object.values(report.editions).every(edition => edition.checks.every(check => check.pass)) ? 'PASS' : 'FAIL'
  if (report.status === 'FAIL') process.exitCode = 1
} catch (error) {
  report.status = 'FAIL'
  report.errors.push(String(error))
  process.exitCode = 1
} finally {
  await browser.close()
  await mkdir(out.slice(0, out.lastIndexOf('/')) || '.', { recursive: true })
  await writeFile(out, JSON.stringify(report, null, 2) + '\n')
}
