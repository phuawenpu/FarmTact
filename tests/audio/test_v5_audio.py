import array
import math
from pathlib import Path
import wave


AUDIO = Path(__file__).resolve().parents[2] / "apps/web/public/audio"
EXPECTED_DURATIONS = {
    "farm-garden-loop.wav": 64.0,
    "navigate.wav": 0.14,
    "detail.wav": 0.20,
    "confirm.wav": 0.30,
    "complete.wav": 0.48,
    "shortfall.wav": 0.48,
    "withheld.wav": 0.58,
    "error.wav": 0.34,
    "sound-test.wav": 0.38,
}


def read_audio(name):
    with wave.open(str(AUDIO / name), "rb") as source:
        metadata = (source.getnchannels(), source.getsampwidth(), source.getframerate(), source.getnframes())
        samples = array.array("h", source.readframes(source.getnframes()))
    return metadata, samples


def dbfs(value):
    return 20 * math.log10(value)


def test_audio_assets_have_expected_pcm_shape_and_duration():
    assert {path.name for path in AUDIO.glob("*.wav")} == set(EXPECTED_DURATIONS)
    for name, duration in EXPECTED_DURATIONS.items():
        (channels, width, rate, frames), samples = read_audio(name)
        assert (channels, width, rate) == (1, 2, 44_100)
        assert frames == round(duration * rate)
        assert len(samples) == frames


def test_audio_assets_are_audible_with_headroom_and_clean_boundaries():
    for name in EXPECTED_DURATIONS:
        _, samples = read_audio(name)
        peak = max(abs(value) for value in samples) / 32768
        rms = math.sqrt(sum((value / 32768) ** 2 for value in samples) / len(samples))
        target = -22 if name == "farm-garden-loop.wav" else -18
        assert abs(dbfs(rms) - target) <= 0.05
        assert dbfs(peak) <= -3
        assert samples[0] == samples[-1] == 0
        assert abs(sum(samples) / len(samples) / 32768) < 10 ** (-60 / 20)


def test_default_software_mix_is_no_longer_near_silent():
    for name in EXPECTED_DURATIONS:
        _, samples = read_audio(name)
        rms = math.sqrt(sum((value / 32768) ** 2 for value in samples) / len(samples))
        gain = 0.55 if name == "farm-garden-loop.wav" else 0.70
        effective = dbfs(rms * gain)
        assert effective >= (-27.25 if name == "farm-garden-loop.wav" else -21.2)


def test_loop_boundary_has_no_click_sized_step():
    _, samples = read_audio("farm-garden-loop.wav")
    transition = abs(samples[-1] - samples[0]) / 32768
    edge_steps = [abs(samples[index + 1] - samples[index]) / 32768 for index in range(1024)]
    edge_steps += [abs(samples[index + 1] - samples[index]) / 32768 for index in range(len(samples) - 1025, len(samples) - 1)]
    assert transition == 0
    assert max(edge_steps) < 10 ** (-45 / 20)
    window = 4_410
    start_rms = math.sqrt(sum((value / 32768) ** 2 for value in samples[:window]) / window)
    end_rms = math.sqrt(sum((value / 32768) ** 2 for value in samples[-window:]) / window)
    assert abs(dbfs(start_rms) - dbfs(end_rms)) < 1
