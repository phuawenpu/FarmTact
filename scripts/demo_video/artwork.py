"""Create editorial frames and guide posters from real app screenshots."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parents[2]
FONT=Path('/usr/share/fonts/truetype/dejavu')
def font(size,bold=False):return ImageFont.truetype(str(FONT/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size)
def poster(slug,title,number,screenshot):
    im=Image.new('RGB',(1280,720),'#123b2b');d=ImageDraw.Draw(im)
    d.text((45,26),'FarmTact  /  Recorded app guide',font=font(24,True),fill='#c5ec83')
    d.text((45,70),f'{number:02d}  {title}',font=font(35,True),fill='#fff9eb')
    source=Image.open(screenshot).convert('RGB');source=source.crop((244,70,1280,790))
    shot=ImageOps.fit(source,(1190,510));im.paste(shot,(45,130));d=ImageDraw.Draw(im)
    d.rounded_rectangle((575,328,705,458),radius=65,fill='#153e2e',outline='#c5ec83',width=3)
    d.polygon([(626,360),(626,425),(673,392)],fill='#c5ec83')
    d.text((45,671),'Desktop + mobile  •  English narration & captions  •  Synthetic farm',font=font(21),fill='#f9f3e5')
    im.save(ROOT/f'apps/web/public/explainers/{slug}.png')
def plate(scene,index,path):
    im=Image.new('RGB',(2560,1440),'#102f25');d=ImageDraw.Draw(im)
    d.text((40,20),'FarmTact',font=font(40,True),fill='#c4eb70')
    d.text((290,28),'A real workflow, on two screens',font=font(26),fill='#e8eedc')
    d.text((40,78),'DESKTOP  /  1280 × 840',font=font(19,True),fill='#bfd4c6')
    d.text((1968,78),'MOBILE WEB  /  390 × 844',font=font(19,True),fill='#bfd4c6')
    d.rounded_rectangle((34,108,1866,1312),radius=10,fill='#79917c')
    d.rounded_rectangle((1962,108,2524,1312),radius=16,fill='#79917c')
    d.text((40,1320),f'{index+1:02d}  {scene["title"]}',font=font(24,True),fill='#c4eb70')
    d.text((2100,1323),'SYNTHETIC FARM',font=font(20,True),fill='#bfd4c6')
    im.save(path)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--screenshots',type=Path,default=Path('/tmp/farmtact-rehearsal-2'));a=p.parse_args()
    for n,(slug,title,scene) in enumerate([('observe-decide','From records to options','compare'),('council-evidence','How the Council earns trust','council'),('act-replan','From action to recovery','correction')],1):poster(slug,title,n,a.screenshots/f'desktop-{scene}.png')
