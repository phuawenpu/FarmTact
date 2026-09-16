"""Render deterministic, captioned farmer guides; no inference or external assets."""
import json
from pathlib import Path
import subprocess
import tempfile
import textwrap
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'apps/web/public/explainers'
GUIDES = {
    'observe-decide': [
        ('Start with reviewed records', 'Open the Farm Data Inbox. Try a synthetic example or upload your own records into this isolated sandbox. Preview the source before confirming extracted rows.'),
        ('Keep demand types separate', 'A market quote is a price signal. Tentative demand is uncertain. Only a confirmed order becomes a booked commitment. Review dates, crop, quantity and price before applying changes.'),
        ('Compare calculated options', 'Coverage compares deliveries with confirmed demand. Surplus is closing stock. Expiry is projected waste. Contribution margin subtracts modeled variable costs from revenue; it is not net profit.'),
        ('Apply a reviewed proposal', 'Challenge an assumption or edit a constraint. Review the proposal, then choose Apply & Recalculate. Local calculations produce new options. This does not approve a plan or create farm actions.'),
    ],
    'council-evidence': [
        ('Ask the relevant specialist', 'Seven roles cover demand, crops, weather, markets, capacity, farm planning and review. Ask about a constraint, challenge an assumption or compare an alternative strategy.'),
        ('Follow the evidence', 'Open each finding to inspect its source and tool activity. Validated means the claim passed its checks against this frozen planning result. It is not a guarantee of a real harvest.'),
        ('Respect missing information', 'Partial means some evidence or specialist findings are unavailable. Withheld advice failed checks or lacks support. Missing weather and market sources stay visible; the Council must not invent them.'),
        ('Approval stays explicit', 'Choose a feasible calculated strategy and inspect its assumptions. Approve & Create Actions records that revision in the sandbox. Later changes require a new reviewed proposal and approval.'),
    ],
    'act-replan': [
        ('Work from the approved revision', 'Each task identifies its crop or batch, location, due date and checklist. Tasks belong to the approved sandbox plan. The application does not operate equipment or contact buyers.'),
        ('Report what actually happened', 'Complete the checklist and record quantity with its unit. Keep accepted and rejected delivery quantities separate. Optional reviewed photos support observations; photos alone cannot establish yield.'),
        ('Verify differences honestly', 'Reported results update a labeled forecast. A short harvest or rejected delivery prompts recovery. User-reported results remain unverified. Corrections append an auditable event instead of erasing the original report.'),
        ('Replan while preserving work', 'Review the recovery proposal and recalculate future work. Completed and reported tasks retain their history. Waste Rescue compares dated surplus scenarios; a hypothetical sale is never treated as a confirmed order.'),
    ],
}
DURATION = 12
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')

def font(size, bold=False):
    return ImageFont.truetype(str(FONT_DIR / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)

def render(title, text, step):
    image = Image.new('RGB', (1280,720), '#173e2c')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((48,48,1232,672),radius=24,fill='#234d39')
    draw.text((96,85),'FarmTact V12  /  Singapore Demo Farm',font=font(28,True),fill='#cce986')
    draw.text((96,148),f'{step + 1} / 4',font=font(24,True),fill='#ffb197')
    for index,line in enumerate(textwrap.wrap(title,36)):
        draw.text((96,200+index*56),line,font=font(46,True),fill='#fff8e8')
    for index,line in enumerate(textwrap.wrap(text,65)):
        draw.text((96,335+index*41),line,font=font(29),fill='#e2ece4')
    draw.text((96,620),'Synthetic sandbox · real operations disabled',font=font(24),fill='#ffb197')
    return image

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    transcripts={}
    with tempfile.TemporaryDirectory(prefix='farmtact-media-') as directory:
        tmp=Path(directory)
        for slug,scenes in GUIDES.items():
            captions=['WEBVTT',''];concat=[]
            for index,(title,text) in enumerate(scenes):
                frame=tmp/f'{slug}-{index}.png';render(title,text,index).save(frame)
                if index==0:render(title,text,index).save(OUT/f'{slug}.png')
                clip=tmp/f'{slug}-{index}.mp4'
                subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i',str(frame),'-t',str(DURATION),'-r','24','-c:v','libx264','-preset','fast','-pix_fmt','yuv420p',str(clip)],check=True)
                concat.append(f"file '{clip}'")
                start=index*DURATION;end=start+DURATION
                stamp=lambda seconds:f'00:{seconds//60:02d}:{seconds%60:02d}.000'
                captions += [f'{stamp(start)} --> {stamp(end)}',title+'. '+text,'']
            manifest=tmp/f'{slug}.txt';manifest.write_text('\n'.join(concat)+'\n')
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(manifest),'-c','copy','-movflags','+faststart',str(OUT/f'{slug}.mp4')],check=True)
            (OUT/f'{slug}.vtt').write_text('\n'.join(captions))
            transcripts[slug]=[{'title':title,'text':text} for title,text in scenes]
    (OUT/'transcripts.json').write_text(json.dumps(transcripts,indent=2)+'\n')
    print('Generated three 48-second captioned guides and exact transcripts.')

if __name__=='__main__':main()
