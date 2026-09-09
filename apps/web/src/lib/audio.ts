export type AudioEffect = 'navigate' | 'detail' | 'confirm' | 'complete' | 'shortfall' | 'withheld' | 'error' | 'sound-test'

export type AudioPreferences = {
  musicEnabled: boolean
  effectsEnabled: boolean
  musicVolume: number
  effectsVolume: number
}

export type AudioState = AudioPreferences & {
  active: boolean
  blocked: boolean
  editionKey: string
  failure: string | null
}

const LEGACY_DEFAULTS: AudioPreferences = {
  musicEnabled: true,
  effectsEnabled: true,
  musicVolume: 0.2,
  effectsVolume: 0.35,
}
const AUDIBLE_DEFAULTS: AudioPreferences = {
  musicEnabled: true,
  effectsEnabled: true,
  musicVolume: 0.55,
  effectsVolume: 0.7,
}
const AUDIO_ROOT = '/audio/'
const listeners = new Set<() => void>()
const completedResults = new Set<string>()
const effectPlayers = new Map<AudioEffect, HTMLAudioElement>()
let editionKey = 'v2'
let preferences = LEGACY_DEFAULTS
let active = false
let blocked = false
let failure: string | null = null
let music: HTMLAudioElement | null = null
let lastEffectAt = 0
let lastEffect: AudioEffect | null = null
let configured = false
let snapshot: AudioState = { ...LEGACY_DEFAULTS, active: false, blocked: false, editionKey, failure: null }

function storageKey(key = editionKey) { return `farmtact:${key}:audio:preferences` }
function defaultsForEdition(key: string) {
  const match = /^v([1-9][0-9]*)$/.exec(key)
  return match && Number(match[1]) >= 5 ? AUDIBLE_DEFAULTS : LEGACY_DEFAULTS
}
function clamp(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : fallback
}
function loadPreferences(key: string): AudioPreferences {
  const defaults = defaultsForEdition(key)
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey(key)) || '{}') as Partial<AudioPreferences>
    return {
      musicEnabled: typeof saved.musicEnabled === 'boolean' ? saved.musicEnabled : defaults.musicEnabled,
      effectsEnabled: typeof saved.effectsEnabled === 'boolean' ? saved.effectsEnabled : defaults.effectsEnabled,
      musicVolume: clamp(saved.musicVolume, defaults.musicVolume),
      effectsVolume: clamp(saved.effectsVolume, defaults.effectsVolume),
    }
  } catch { return defaults }
}
function publish() {
  snapshot = { ...preferences, active, blocked, editionKey, failure }
  listeners.forEach(listener => listener())
}
function save() {
  try { localStorage.setItem(storageKey(), JSON.stringify(preferences)) } catch { /* storage is optional */ }
}
function source(name: string) { return `/${encodeURIComponent(editionKey)}${AUDIO_ROOT}${name}.wav` }
function ensureMusic() {
  if (!music) {
    music = new Audio(source('farm-garden-loop'))
    music.loop = true
    music.preload = 'auto'
    music.addEventListener('error', () => { blocked = true; failure = 'The background music could not load.'; publish() })
  }
  music.volume = preferences.musicVolume
  return music
}
function ensureEffect(name: AudioEffect) {
  let player = effectPlayers.get(name)
  if (!player) {
    player = new Audio(source(name))
    player.preload = 'auto'
    player.addEventListener('error', () => { blocked = true; failure = 'A sound effect could not load.'; publish() })
    effectPlayers.set(name, player)
  }
  player.volume = preferences.effectsVolume
  return player
}
async function startMusic() {
  if (!active || !preferences.musicEnabled || document.hidden) return
  try {
    await ensureMusic().play()
    blocked = false
    failure = null
  } catch {
    blocked = true
    active = false
    failure = 'Sound was blocked or no audio output was available.'
  }
  publish()
}

export function configureAudioEdition(key: string) {
  if (configured && key === editionKey) return
  if (configured) stopAudioForNavigation()
  editionKey = key
  preferences = loadPreferences(key)
  blocked = false
  failure = null
  configured = true
  publish()
}

export function getAudioState(): AudioState { return snapshot }
export function subscribeAudio(listener: () => void) { listeners.add(listener); return () => listeners.delete(listener) }

/** Must be called directly from a click/key activation. It is the only path that loads audio. */
export async function activateAudio() {
  active = true
  blocked = false
  failure = null
  publish()
  if (document.hidden) return
  const attempts: Array<{ channel: 'music' | 'effects', promise: Promise<unknown> }> = []
  if (preferences.musicEnabled) attempts.push({ channel: 'music', promise: ensureMusic().play() })
  if (preferences.effectsEnabled) {
    const test = ensureEffect('sound-test')
    test.currentTime = 0
    attempts.push({ channel: 'effects', promise: test.play() })
  }
  if (!attempts.length) return
  const results = await Promise.allSettled(attempts.map(attempt => attempt.promise))
  const passed = results.filter(result => result.status === 'fulfilled').length
  blocked = passed !== results.length
  active = passed > 0
  const failed = attempts.filter((_, index) => results[index].status === 'rejected').map(attempt => attempt.channel)
  failure = failed.length === 2 ? 'Music and effects could not play. Check device output and retry enabled sound.'
    : failed[0] === 'music' ? 'Music could not play. Effects remain available; retry enabled sound.'
    : failed[0] === 'effects' ? 'Effects could not play. Music remains available; retry enabled sound.' : null
  publish()
}

export function deactivateAudio() {
  active = false
  music?.pause()
  for (const player of effectPlayers.values()) { player.pause(); player.currentTime = 0 }
  blocked = false
  failure = null
  publish()
}

export function updateAudioPreferences(update: Partial<AudioPreferences>) {
  preferences = {
    musicEnabled: update.musicEnabled ?? preferences.musicEnabled,
    effectsEnabled: update.effectsEnabled ?? preferences.effectsEnabled,
    musicVolume: clamp(update.musicVolume, preferences.musicVolume),
    effectsVolume: clamp(update.effectsVolume, preferences.effectsVolume),
  }
  save()
  if (music) music.volume = preferences.musicVolume
  for (const player of effectPlayers.values()) player.volume = preferences.effectsVolume
  if (!preferences.musicEnabled) music?.pause()
  else void startMusic()
  if (!preferences.effectsEnabled) {
    for (const player of effectPlayers.values()) { player.pause(); player.currentTime = 0 }
  }
  publish()
}

export function playAudioEffect(name: AudioEffect) {
  if (!active || !preferences.effectsEnabled || document.hidden) return
  const now = performance.now()
  if (now - lastEffectAt < (lastEffect === name ? 450 : 120)) return
  lastEffectAt = now; lastEffect = name
  for (const player of effectPlayers.values()) { player.pause(); player.currentTime = 0 }
  const player = ensureEffect(name)
  void player.play().then(() => { blocked = false; failure = null; publish() }).catch(() => {
    blocked = true
    failure = 'A sound effect could not play. Try the sound test.'
    publish()
  })
}

/** Explicit diagnostic action. It respects both channel toggles and changes no preferences. */
export async function playSoundTest() {
  await activateAudio()
}

/** Plays a terminal result once even if polling and event streams report it repeatedly. */
export function playSimulationResult(resultId: string, outcome: 'complete' | 'shortfall' | 'withheld' | 'error') {
  if (completedResults.has(resultId)) return
  completedResults.add(resultId)
  if (completedResults.size > 100) completedResults.delete(completedResults.values().next().value!)
  playAudioEffect(outcome)
}

export function stopAudioForNavigation() {
  deactivateAudio()
  music = null
  effectPlayers.clear()
  failure = null
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      music?.pause()
      for (const player of effectPlayers.values()) player.pause()
    } else if (active) void startMusic()
  })
  window.addEventListener('pagehide', stopAudioForNavigation)
}
