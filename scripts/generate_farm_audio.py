#!/usr/bin/env python3
"""Deterministically synthesize FarmTact's original PCM audio assets."""
from __future__ import annotations
import math, struct, wave
from pathlib import Path

RATE = 22_050
OUT = Path(__file__).resolve().parents[1] / "apps/web/public/audio"

def write(name: str, duration: float, sample):
    OUT.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for i in range(round(duration * RATE)):
        value = max(-1.0, min(1.0, sample(i / RATE)))
        frames += struct.pack("<h", round(value * 32767))
    with wave.open(str(OUT / name), "wb") as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(RATE); audio.writeframes(frames)

def tone(freq, t, start, length, gain=.1):
    x = t - start
    if not 0 <= x < length: return 0.0
    envelope = math.sin(math.pi * x / length) ** 2
    return gain * envelope * (math.sin(2*math.pi*freq*x) + .18*math.sin(4*math.pi*freq*x))

def garden(t):
    # The phrase and ambience are exactly 16 seconds periodic; notes meet at zero amplitude.
    notes = [261.63,329.63,392.0,329.63,293.66,349.23,440.0,349.23]
    music = sum(tone(freq, t, n*2, 1.72, .085) for n, freq in enumerate(notes))
    bass = sum(tone(freq/2, t, n*2, 1.9, .045) for n, freq in enumerate(notes))
    breeze = .012*math.sin(2*math.pi*t/16)*math.sin(2*math.pi*173*t)
    birds = tone(1312, t, 4.9, .15, .025)+tone(1568, t, 5.08, .12, .018)+tone(1175, t, 12.7, .14, .02)
    return music+bass+breeze+birds

def chime(freqs, duration=.34, gain=.13):
    def sample(t):
        env = math.sin(math.pi*t/duration)**2
        return gain*env*sum(math.sin(2*math.pi*f*t) for f in freqs)/len(freqs)
    return duration, sample

def main():
    write("farm-garden-loop.wav", 16, garden)
    for name, args in {
        "navigate": ([392, 523], .16, .10), "detail": ([523, 659], .22, .11),
        "confirm": ([440, 554, 659], .30, .13), "complete": ([523, 659, 784], .48, .14),
        "error": ([311, 277], .32, .09),
    }.items():
        duration, sample = chime(*args); write(f"{name}.wav", duration, sample)

if __name__ == "__main__": main()
