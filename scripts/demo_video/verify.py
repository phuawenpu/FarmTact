"""Validate final exported media, not just container headers."""
from pathlib import Path
import json,subprocess,hashlib,re
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'output/demo-video';REPORT=ROOT/'reports/demo-video'
checks=[]
def check(name,ok,detail=None):
    checks.append({'name':name,'passed':bool(ok),'detail':detail})
    if not ok:raise AssertionError(name)
def probe(path):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))
def main():
    files=json.loads((OUT/'media-manifest.json').read_text());allstats=[]
    for item in files:
        path=ROOT/item['file'];data=probe(path);seconds=float(data['format']['duration']);video=next(s for s in data['streams'] if s['codec_type']=='video');audio=next(s for s in data['streams'] if s['codec_type']=='audio')
        check(f'{path.name}: under 100 MB',0<path.stat().st_size<100_000_000,path.stat().st_size)
        check(f'{path.name}: H.264/AAC',video['codec_name']=='h264' and audio['codec_name']=='aac')
        check(f'{path.name}: SHA-256 matches',hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'])
        decoded=subprocess.run(['ffmpeg','-hide_banner','-v','error','-threads','2','-i',str(path),'-f','null','-'],capture_output=True,text=True)
        check(f'{path.name}: full audio/video decode',decoded.returncode==0 and not decoded.stderr,decoded.stderr)
        raw=path.read_bytes();check(f'{path.name}: fast-start metadata',raw.find(b'moov')<raw.find(b'mdat'))
        volume=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-vn','-af','volumedetect','-f','null','-'],capture_output=True,text=True)
        peak=re.search(r'max_volume: ([-\d.]+) dB',volume.stderr);mean=re.search(r'mean_volume: ([-\d.]+) dB',volume.stderr)
        check(f'{path.name}: audible nonclipping narration',peak and mean and -35<float(mean[1])<-8 and -10<float(peak[1])<0,{'peak_db':peak[1] if peak else None,'mean_db':mean[1] if mean else None})
        allstats.append({'file':item['file'],'duration':seconds,'size':path.stat().st_size})
        if path.parent==OUT:check('Master lasts at least five minutes and about five minutes',300<=seconds<=360,seconds)
        caption=path.with_suffix('.vtt');text=caption.read_text();check(f'{path.name}: nonempty WebVTT',text.startswith('WEBVTT') and text.count('-->')>=8)
    capture=json.loads((OUT/'capture-evidence.json').read_text());check('Actual recorded UI journey passed',capture['status']=='PASS' and not capture['errors']);check('No fabricated/provider requests',not capture['providerRequests'])
    for view in capture['views']:check(f'{view["name"]}: short result and correction persisted',view['result']['status']=='recovery_required' and view['result']['event_revision']>=2,view['result'])
    REPORT.mkdir(exist_ok=True,parents=True);(REPORT/'media-verification.json').write_text(json.dumps({'status':'PASS','checks':checks,'files':allstats},indent=2)+'\n');print(json.dumps({'status':'PASS','checks':len(checks),'files':allstats},indent=2))
if __name__=='__main__':main()
