import json,wave
from pathlib import Path
from piper import PiperVoice, SynthesisConfig
import os
root=Path(__file__).resolve().parents[2];out=root/'output/demo-video/work';out.mkdir(parents=True,exist_ok=True)
voice=PiperVoice.load(os.environ.get('PIPER_MODEL','/tmp/farmtact-voice/en_US-lessac-high.onnx'))
for scene in json.loads((root/'scripts/demo_video/storyboard.json').read_text()):
    path=out/(scene['id']+'.wav')
    if not path.exists():
        with wave.open(str(path),'wb') as wav: voice.synthesize_wav(scene['text'],wav,syn_config=SynthesisConfig(length_scale=1.03))
    with wave.open(str(path)) as wav: duration=wav.getnframes()/wav.getframerate()
    print(scene['id'],round(duration,2),scene['seconds'],flush=True)
