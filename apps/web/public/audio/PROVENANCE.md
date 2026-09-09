# FarmTact audio provenance

All six WAV files in this directory are original, deterministic synthesizer output created for FarmTact. `scripts/generate_farm_audio.py` generates them from sine-wave oscillators and mathematical envelopes using only Python's standard library. The garden loop includes a quiet instrumental phrase, periodic breeze texture and three sparse bird-like chirps. It uses no recordings, samples, model output, external providers, or third-party licensed material.

Generation command: `python3 scripts/generate_farm_audio.py`

The loop is 16 seconds, mono, 22,050 Hz, signed 16-bit PCM. Its periodic components repeat over exactly 16 seconds and each discrete note reaches zero at its boundary, allowing gapless-capable browsers to repeat it without a waveform discontinuity.
