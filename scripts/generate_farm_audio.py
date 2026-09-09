#!/usr/bin/env python3
"""Deterministically synthesize FarmTact's original, offline game audio."""
from __future__ import annotations
import math, struct, wave
from pathlib import Path

RATE = 44_100
OUT = Path(__file__).resolve().parents[1] / "apps/web/public/audio"

def write(name: str, duration: float, sample, target_rms_db: float, peak_limit_db: float = -3.0):
    OUT.mkdir(parents=True, exist_ok=True)
    values = [max(-1.0, min(1.0, sample(i / RATE))) for i in range(round(duration * RATE))]
    # All oscillators have explicit zero endpoints. Normalise deterministically while
    # retaining headroom; browser channel gains then produce the intended mix level.
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    peak = max(abs(value) for value in values)
    rms_gain = 10 ** (target_rms_db / 20) / rms
    peak_gain = 10 ** (peak_limit_db / 20) / peak
    gain = min(rms_gain, peak_gain)
    frames = bytearray()
    for value in values:
        value = max(-1.0, min(1.0, value * gain))
        frames += struct.pack("<h", round(value * 32767))
    with wave.open(str(OUT / name), "wb") as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(RATE); audio.writeframes(frames)

def tone(freq, t, start, length, gain=.1):
    x = t - start
    if not 0 <= x < length: return 0.0
    envelope = math.sin(math.pi * x / length) ** 2
    return gain * envelope * (math.sin(2*math.pi*freq*x) + .18*math.sin(4*math.pi*freq*x))

def garden(t):
    # A 64-second periodic garden phrase. Midrange melody and gentle harmonics
    # remain present on small phone speakers; every event meets zero amplitude.
    notes = [
        392.00, 493.88, 587.33, 493.88, 440.00, 523.25, 659.25, 523.25,
        349.23, 440.00, 523.25, 659.25, 587.33, 493.88, 440.00, 392.00,
        392.00, 523.25, 659.25, 783.99, 659.25, 587.33, 523.25, 493.88,
        440.00, 554.37, 659.25, 554.37, 493.88, 440.00, 392.00, 349.23,
    ]
    note_index = min(len(notes) - 1, int(t // 2))
    melody = tone(notes[note_index], t, note_index * 2, 2.0, .10)
    warmth = tone(notes[note_index] / 2, t, note_index * 2, 2.0, .028)
    shimmer_index = int((t - .18) // 4)
    shimmer = tone(notes[::2][shimmer_index] * 2, t, shimmer_index * 4 + .18, 1.18, .018) if 0 <= shimmer_index < 16 else 0
    breeze = .010 * math.sin(2 * math.pi * t / 64) * math.sin(2 * math.pi * 720 * t)
    birds = sum(tone(freq, t, start, length, gain) for start, freq, length, gain in (
        (7.1, 1312, .18, .030), (7.34, 1568, .14, .022),
        (22.6, 1175, .19, .026), (38.2, 1397, .16, .026),
        (53.4, 1568, .15, .022), (53.61, 1760, .12, .018),
    ))
    return melody + warmth + shimmer + breeze + birds

def chime(freqs, duration=.34, gain=.13):
    def sample(t):
        env = math.sin(math.pi*t/duration)**2
        return gain*env*sum(math.sin(2*math.pi*f*t) for f in freqs)/len(freqs)
    return duration, sample

def sequence(notes, duration):
    def sample(t):
        return sum(tone(freq, t, start, length, gain) for start, length, freq, gain in notes)
    return duration, sample

def main():
    write("farm-garden-loop.wav", 64, garden, -22.0)
    for name, args in {
        "navigate": ([523, 659], .14, .10), "detail": ([659, 831], .20, .11),
        "confirm": ([440, 659, 880], .30, .13), "complete": ([523, 659, 784], .48, .14),
        "error": ([330, 294], .34, .10), "sound-test": ([523, 659, 784], .38, .13),
    }.items():
        duration, sample = chime(*args); write(f"{name}.wav", duration, sample, -18.0)
    for name, value in {
        "shortfall": sequence(((0, .20, 440, .12), (.22, .24, 370, .12)), .48),
        "withheld": sequence(((0, .18, 392, .11), (.20, .18, 494, .11), (.40, .16, 440, .10)), .58),
    }.items():
        duration, sample = value; write(f"{name}.wav", duration, sample, -18.0)

if __name__ == "__main__": main()
