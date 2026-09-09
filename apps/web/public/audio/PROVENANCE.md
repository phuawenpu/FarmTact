# FarmTact audio provenance

All nine WAV files in this directory are original, deterministic synthesizer output created for FarmTact. `scripts/generate_farm_audio.py` generates them from sine-wave oscillators and mathematical envelopes using only Python's standard library. The garden loop includes a varied instrumental phrase, periodic breeze texture and sparse bird-like chirps. The shortfall and withheld cues distinguish planning outcomes from completion and technical failure. It uses no recordings, samples, model output, external providers, or third-party licensed material.

Generation command: `python3 scripts/generate_farm_audio.py`

The loop is 64 seconds; all assets are mono, 44,100 Hz, signed 16-bit PCM. Files are deterministically normalised with peak headroom. The loop's periodic components repeat over exactly 64 seconds and each discrete note reaches zero at its boundary, allowing gapless-capable browsers to repeat it without a waveform discontinuity.
