import { Music2, SlidersHorizontal, Volume2, VolumeX, Waves } from 'lucide-react'
import { useEffect, useId, useState, useSyncExternalStore } from 'react'
import {
  activateAudio, configureAudioEdition, deactivateAudio, getAudioState,
  subscribeAudio, updateAudioPreferences,
} from '../lib/audio'
import './audio.css'

export function AudioControls({ editionKey }: { editionKey: string }) {
  useEffect(() => { configureAudioEdition(editionKey) }, [editionKey])
  const [expanded, setExpanded] = useState(false)
  const preferencesId = useId()
  const audio = useSyncExternalStore(subscribeAudio, getAudioState, getAudioState)
  const toggleMaster = () => { if (audio.active) deactivateAudio(); else void activateAudio() }

  return <section className="audio-controls" aria-label="Sound controls">
    <button className="audio-controls__master" type="button" onClick={toggleMaster}
      aria-pressed={audio.active} aria-label={audio.active ? 'Turn sound off' : audio.blocked ? 'Retry sound' : 'Turn sound on'}>
      {audio.active ? <Volume2 aria-hidden="true"/> : <VolumeX aria-hidden="true"/>}
      <span>{audio.active ? 'Sound on' : audio.blocked ? 'Retry sound' : 'Sound off'}</span>
    </button>
    <button className="audio-controls__expand" type="button" aria-expanded={expanded} aria-controls={preferencesId} onClick={() => setExpanded(value => !value)}><SlidersHorizontal aria-hidden="true"/><span>Sound preferences</span></button>
    {expanded && <div className="audio-controls__preferences" id={preferencesId}>
    <div className="audio-controls__channel">
      <button type="button" aria-pressed={audio.musicEnabled} onClick={() => updateAudioPreferences({ musicEnabled: !audio.musicEnabled })}>
        <Music2 aria-hidden="true"/><span>Music</span>
      </button>
      <label><span className="sr-only">Music volume</span><input type="range" min="0" max="100" value={Math.round(audio.musicVolume * 100)} aria-label="Music volume" onChange={event => updateAudioPreferences({ musicVolume: Number(event.target.value) / 100 })}/><output>{Math.round(audio.musicVolume * 100)}%</output></label>
    </div>
    <div className="audio-controls__channel">
      <button type="button" aria-pressed={audio.effectsEnabled} onClick={() => updateAudioPreferences({ effectsEnabled: !audio.effectsEnabled })}>
        <Waves aria-hidden="true"/><span>Effects</span>
      </button>
      <label><span className="sr-only">Effects volume</span><input type="range" min="0" max="100" value={Math.round(audio.effectsVolume * 100)} aria-label="Effects volume" onChange={event => updateAudioPreferences({ effectsVolume: Number(event.target.value) / 100 })}/><output>{Math.round(audio.effectsVolume * 100)}%</output></label>
    </div>
    </div>}
    {audio.blocked && <p role="status">Sound could not start. Try again when you’re ready.</p>}
  </section>
}
