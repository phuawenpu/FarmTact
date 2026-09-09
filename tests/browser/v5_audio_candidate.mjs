import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { execFileSync } from 'node:child_process'
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const base = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const edition = process.env.FARMTACT_AUDIO_EDITION || 'v5'
const out = process.env.FARMTACT_AUDIO_REPORT || 'reports/v5/audio_candidate.json'
const storageState = process.env.FARMTACT_BROWSER_STATE || '/tmp/farmtact-v5-browser-state.json'
const screenshot = 'apps/web/screenshots/v5-audio/v5-candidate-controls.png'
const report = { status: 'RUNNING', base, edition, checks: [], errors: [], requests: [] }
const check = (name, pass, detail = null) => { report.checks.push({ name, pass: Boolean(pass), detail }); if (!pass) throw new Error(name) }
const browser = await chromium.launch()
const compilationDir = await mkdtemp(join(tmpdir(), 'farmtact-v5-audio-'))

try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, storageState, bypassCSP: true })
  await context.addInitScript(() => {
    const NativeAudio = window.Audio
    window.__v5Audio = []
    let rejectFirst = true
    window.Audio = function (...args) {
      const audio = new NativeAudio(...args)
      window.__v5Audio.push(audio)
      const nativePlay = audio.play.bind(audio)
      audio.play = function () {
        if (rejectFirst) { rejectFirst = false; return Promise.reject(new DOMException('V5 retry check', 'NotAllowedError')) }
        return nativePlay()
      }
      return audio
    }
  })
  const page = await context.newPage()
  page.on('request', request => { const path = new URL(request.url()).pathname; if (path.includes('/audio/')) report.requests.push(path) })
  page.on('pageerror', error => report.errors.push(error.message))
  await page.goto(`${base}/${edition}/`, { waitUntil: 'networkidle' })
  const controls = page.getByRole('region', { name: 'Sound controls' })
  await controls.waitFor()
  check('v5 begins silent', await controls.getByRole('button', { name: 'Turn sound on' }).isVisible() && report.requests.length === 0)
  check('silent-start explanation is visible', await controls.getByText('Sound starts off on every visit.').isVisible())
  await controls.getByRole('button', { name: 'Sound preferences' }).click()
  const originalStorage = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage).filter(([key]) => key.includes(':audio:preferences'))))
  const initialLevels = { music: await controls.getByLabel('Music volume').inputValue(), effects: await controls.getByLabel('Effects volume').inputValue() }
  check('audible v5 defaults are exposed when no preference was saved', originalStorage['farmtact:v5:audio:preferences'] ? true : initialLevels.music === '55' && initialLevels.effects === '70', initialLevels)
  const boxes = await controls.locator('button,input[type=range]').evaluateAll(nodes => nodes.map(node => { const box = node.getBoundingClientRect(); return { tag: node.tagName, width: box.width, height: box.height } }))
  check('buttons and actual slider inputs are at least 44 px high', boxes.every(box => box.height >= 44), boxes)
  await controls.getByLabel('Music volume').focus()
  const keyboardBefore = Number(await controls.getByLabel('Music volume').inputValue())
  await page.keyboard.press(keyboardBefore < 100 ? 'ArrowRight' : 'ArrowLeft')
  check('volume slider responds to keyboard', Number(await controls.getByLabel('Music volume').inputValue()) !== keyboardBefore)
  await controls.getByLabel('Effects volume').fill('68')
  const scopedStorage = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage).filter(([key]) => key.includes(':audio:preferences'))))
  check('preference write is edition-scoped', JSON.parse(scopedStorage['farmtact:v5:audio:preferences']).effectsVolume === .68 && Object.entries(originalStorage).every(([key, value]) => key === 'farmtact:v5:audio:preferences' || scopedStorage[key] === value), scopedStorage)
  await page.screenshot({ path: screenshot, fullPage: true })

  await controls.getByRole('button', { name: 'Turn sound on' }).click()
  await controls.getByText(/Music could not play/).waitFor()
  check('partial playback failure stays visible and recoverable while collapsed', await controls.getByText('Sound issue').isVisible() && await controls.getByRole('button', { name: 'Turn sound off' }).isVisible() && await controls.getByRole('button', { name: 'Retry enabled sound' }).isVisible())
  await controls.getByRole('button', { name: 'Retry enabled sound' }).click()
  await page.waitForTimeout(100)
  check('explicit retry clears error and starts both channels', await controls.getByText('Sound is active for this visit.').isVisible() && await page.evaluate(() => window.__v5Audio.filter(a => !a.paused).length >= 2))
  check('v5 requests edition-pinned music and test', report.requests.includes(`/${edition}/audio/farm-garden-loop.wav`) && report.requests.includes(`/${edition}/audio/sound-test.wav`), report.requests)
  const nativeState = await page.evaluate(() => window.__v5Audio.map(audio => ({ path: new URL(audio.src).pathname, paused: audio.paused, currentTime: audio.currentTime, duration: audio.duration, volume: audio.volume, readyState: audio.readyState, loop: audio.loop })))
  const music = nativeState.find(row => row.path.endsWith('/farm-garden-loop.wav'))
  const test = nativeState.find(row => row.path.endsWith('/sound-test.wav'))
  check('music has real decode, advancing playhead, loop and configured gain', music && !music.paused && music.readyState >= 2 && music.currentTime > 0 && music.duration === 64 && music.loop && Math.abs(music.volume - Number(await controls.getByLabel('Music volume').inputValue()) / 100) < .001, music)
  check('sound test entered native play state at configured gain', test && test.readyState >= 2 && test.duration === .38 && Math.abs(test.volume - .68) < .001, test)

  await controls.getByRole('button', { name: 'Effects', exact: true }).click()
  const testPlayersBeforeDisabledActivation = await page.evaluate(() => window.__v5Audio.filter(audio => audio.src.endsWith('/sound-test.wav')).length)
  await controls.getByRole('button', { name: 'Turn sound off' }).click()
  await controls.getByRole('button', { name: 'Turn sound on' }).click()
  await page.waitForTimeout(100)
  const testPlayersAfterDisabledActivation = await page.evaluate(() => window.__v5Audio.filter(audio => audio.src.endsWith('/sound-test.wav')).length)
  check('persisted effects-off is respected by master activation', testPlayersAfterDisabledActivation === testPlayersBeforeDisabledActivation && await controls.getByRole('button', { name: 'Effects test off' }).isDisabled(), { before: testPlayersBeforeDisabledActivation, after: testPlayersAfterDisabledActivation })
  check('effects-off preference remains persisted', await page.evaluate(() => JSON.parse(localStorage.getItem('farmtact:v5:audio:preferences')).effectsEnabled === false))
  await controls.getByRole('button', { name: 'Effects', exact: true }).click()

  const decoded = await page.evaluate(async edition => {
    const context = new AudioContext()
    const output = []
    for (const name of ['farm-garden-loop','navigate','detail','confirm','complete','shortfall','withheld','error','sound-test']) {
      const response = await fetch(`/${edition}/audio/${name}.wav`)
      const data = await response.arrayBuffer()
      const buffer = await context.decodeAudioData(data.slice(0))
      output.push({ name, status: response.status, duration: buffer.duration, sampleRate: buffer.sampleRate, channels: buffer.numberOfChannels })
    }
    await context.close()
    return output
  }, edition)
  check('all semantic assets decode', decoded.length === 9 && decoded.every(row => row.status === 200 && row.sampleRate === 44100 && row.channels === 1), decoded)

  execFileSync('apps/web/node_modules/.bin/tsc', ['apps/web/src/lib/audio.ts', '--target', 'ES2022', '--module', 'ES2022', '--lib', 'ES2022,DOM', '--skipLibCheck', '--outDir', compilationDir], { stdio: 'pipe' })
  const compiled = await readFile(join(compilationDir, 'audio.js'), 'utf8')
  await page.addScriptTag({ type: 'module', content: `${compiled}\nwindow.__v5EventAudio={configureAudioEdition,activateAudio,playSimulationResult,deactivateAudio};` })
  await page.waitForFunction(() => Boolean(window.__v5EventAudio))
  const eventStart = await page.evaluate(() => window.__v5Audio.length)
  await page.evaluate(async () => { window.__v5EventAudio.configureAudioEdition('v5'); await window.__v5EventAudio.activateAudio() })
  for (const outcome of ['complete', 'shortfall', 'withheld', 'error']) {
    await page.evaluate(outcome => window.__v5EventAudio.playSimulationResult(`fixture-${outcome}`, outcome), outcome)
    await page.waitForTimeout(150)
  }
  await page.evaluate(() => window.__v5EventAudio.playSimulationResult('fixture-complete', 'complete'))
  await page.waitForTimeout(150)
  const eventPaths = await page.evaluate(start => window.__v5Audio.slice(start).map(audio => new URL(audio.src).pathname), eventStart)
  for (const outcome of ['complete', 'shortfall', 'withheld', 'error']) check(`${outcome} result maps to exactly one semantic player`, eventPaths.filter(path => path === `/v5/audio/${outcome}.wav`).length === 1, eventPaths)
  check('polling duplicate creates no second result player', eventPaths.filter(path => path === '/v5/audio/complete.wav').length === 1, eventPaths)
  await page.evaluate(() => window.__v5EventAudio.deactivateAudio())

  await page.evaluate(() => { Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')) })
  check('hidden tab pauses every player', await page.evaluate(() => window.__v5Audio.every(audio => audio.paused)))
  await controls.getByRole('button', { name: 'Turn sound off' }).click()
  await page.reload({ waitUntil: 'networkidle' })
  check('reload remains opt-in', await page.getByRole('region', { name: 'Sound controls' }).getByRole('button', { name: 'Turn sound on' }).isVisible())
  check('browser run has no uncaught errors', report.errors.length === 0, report.errors)
  report.status = 'PASS'
  await context.close()
} catch (error) {
  report.status = 'FAIL'
  report.errors.push(String(error))
  process.exitCode = 1
} finally {
  await browser.close()
  await rm(compilationDir, { recursive: true, force: true })
  await mkdir(out.slice(0, out.lastIndexOf('/')) || '.', { recursive: true })
  await writeFile(out, JSON.stringify(report, null, 2) + '\n')
}
