export type AudioEffect = 'navigate' | 'detail' | 'confirm' | 'complete' | 'error'

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
}

const DEFAULTS: AudioPreferences = {
  musicEnabled: true,
  effectsEnabled: true,
  musicVolume: 0.2,
  effectsVolume: 0.35,
}
const AUDIO_ROOT = '/audio/'
const listeners = new Set<() => void>()
const completedResults = new Set<string>()
const effectPlayers = new Map<AudioEffect, HTMLAudioElement>()
let editionKey = 'v2'
let preferences = DEFAULTS
let active = false
let blocked = false
let music: HTMLAudioElement | null = null
let lastEffectAt = 0
let lastEffect: AudioEffect | null = null
let configured = false
let snapshot: AudioState = { ...DEFAULTS, active: false, blocked: false, editionKey }

function storageKey(key = editionKey) { return `farmtact:${key}:audio:preferences` }
function clamp(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : fallback
}
function loadPreferences(key: string): AudioPreferences {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey(key)) || '{}') as Partial<AudioPreferences>
    return {
      musicEnabled: typeof saved.musicEnabled === 'boolean' ? saved.musicEnabled : DEFAULTS.musicEnabled,
      effectsEnabled: typeof saved.effectsEnabled === 'boolean' ? saved.effectsEnabled : DEFAULTS.effectsEnabled,
      musicVolume: clamp(saved.musicVolume, DEFAULTS.musicVolume),
      effectsVolume: clamp(saved.effectsVolume, DEFAULTS.effectsVolume),
    }
  } catch { return DEFAULTS }
}
function publish() {
  snapshot = { ...preferences, active, blocked, editionKey }
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
    music.addEventListener('error', () => { blocked = true; publish() })
  }
  music.volume = preferences.musicVolume
  return music
}
function ensureEffect(name: AudioEffect) {
  let player = effectPlayers.get(name)
  if (!player) {
    player = new Audio(source(name))
    player.preload = 'auto'
    player.addEventListener('error', () => { blocked = true; publish() })
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
  } catch {
    blocked = true
    active = false
  }
  publish()
}

export function configureAudioEdition(key: string) {
  if (configured && key === editionKey) return
  if (configured) stopAudioForNavigation()
  editionKey = key
  preferences = loadPreferences(key)
  configured = true
  publish()
}

export function getAudioState(): AudioState { return snapshot }
export function subscribeAudio(listener: () => void) { listeners.add(listener); return () => listeners.delete(listener) }

/** Must be called directly from a click/key activation. It is the only path that loads audio. */
export async function activateAudio() {
  active = true
  blocked = false
  publish()
  await startMusic()
}

export function deactivateAudio() {
  active = false
  music?.pause()
  for (const player of effectPlayers.values()) { player.pause(); player.currentTime = 0 }
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
  void player.play().then(() => { blocked = false; publish() }).catch(() => { blocked = true; publish() })
}

/** Plays a terminal result once even if polling and event streams report it repeatedly. */
export function playSimulationResult(resultId: string, outcome: 'complete' | 'error') {
  if (completedResults.has(resultId)) return
  completedResults.add(resultId)
  if (completedResults.size > 100) completedResults.delete(completedResults.values().next().value!)
  playAudioEffect(outcome)
}

export function stopAudioForNavigation() {
  deactivateAudio()
  music = null
  effectPlayers.clear()
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
