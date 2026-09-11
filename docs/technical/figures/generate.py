"""Generate report figures from source fixtures and explicit architecture annotations.

Run from any directory with the application requirements installed. SVG generation
uses the standard library. --png additionally uses documentation-only CairoSVG.
No database, network, solver, or provider call is made. No release evidence changes.
"""
from pathlib import Path
from html import escape
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from packages.fixtures import synthetic_farm
from packages.contracts import content_hash
from packages.models import forecast

OUT = Path(__file__).resolve().parent
INK = '#18332f'
MUTED = '#526b67'
GREEN = '#166956'
BLUE = '#315f98'
GOLD = '#b67120'

class SVG:
    def __init__(self, name, width, height, title, description):
        self.name = name
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
                      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#526b67"/></marker></defs>',
                      f'<rect width="{width}" height="{height}" fill="#fff"/>']
        self.text(40, 44, title, 26, weight='bold')
    def text(self, x, y, text, size=17, color=INK, weight='normal', anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(str(text))}</text>')
    def rect(self, x, y, w, h, fill='#eef5f1', stroke='#cadbd4', radius=10):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')
    def line(self, x1, y1, x2, y2, color=MUTED, arrow=False, dash=False):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2"' + (' marker-end="url(#arrow)"' if arrow else '') + (' stroke-dasharray="7 5"' if dash else '') + '/>')
    def box(self, x, y, w, h, title, lines, color='#eef5f1'):
        self.rect(x,y,w,h,fill=color)
        self.text(x+18,y+30,title,19,weight='bold')
        for i,t in enumerate(lines):self.text(x+18,y+59+25*i,t,16)
    def save(self):
        path=OUT / f'{self.name}.svg'
        path.write_text('\n'.join(self.parts+['</svg>'])+'\n')
        return path


def architecture():
    s=SVG('system-overview',1360,670,'FarmTact: numerical authority and optional AI interpretation',
          'Synthetic and imported farm snapshots feed local forecast, optimizer and simulation. Public context feeds the interface and optional DeepSeek interpretation. Only backend validation may accept simulation; no actual farm operations.')
    s.box(40,90,355,130,'Versioned farm inputs',['Synthetic reference / validated import','Orders · recipes · beds · resources','Cutoff, ownership and input hash'])
    s.box(465,90,400,130,'Local numerical pipeline',['EWMA demand + scheduled harvest','CP-SAT whole-bed schedules','Scenario simulation + constraint checks'])
    s.box(935,90,385,130,'Frozen results',['Lean · Balanced · Resilient','Quantities, ledgers and evidence refs','Persisted for comparison and replay'])
    s.line(395,155,465,155,arrow=True);s.line(865,155,935,155,arrow=True)
    s.box(40,300,355,140,'Public and curated context',['Weather · trade · climate · News','Crop knowledge / scientific references','Context only: no automatic forecast','or crop-growth input'],color='#eef3fa')
    s.box(465,300,400,140,'Explicit adviser action',['Server-only DeepSeek gateway','Role-specific interpretation of frozen','numbers and bounded evidence','Scripted research dialogue: zero calls'],color='#eef3fa')
    s.box(935,300,385,140,'Local evidence validation',['Schema + allowed references + values','Supported / unsupported / clarification','No model power to execute a plan'],color='#eef3fa')
    s.line(395,370,465,370,arrow=True);s.line(865,370,935,370,arrow=True)
    s.line(1127,220,1127,260);s.line(1127,260,665,260);s.line(665,260,665,300,arrow=True)
    s.box(465,510,855,100,'Simulation-only decision',['Main planning: backend policy. Research: explicit feasible current selection.','Stored work/results and isolated experiments; actual farm integrations disabled.'],color='#fcf4e8')
    s.line(1127,440,1127,510,arrow=True)
    s.text(40,640,'Figure 1. Source audit, 11 September 2026. Solid arrows show implemented information flow; no physiological model is implied.',15,MUTED)
    return s.save()


def growth(farm):
    s=SVG('growth-timeline',1360,610,'Plant development is a recipe calendar',
          'Four synthetic crop recipes show nursery duration, grow-out, harvest instant, sanitation interval and stock shelf-life. These are engineering assumptions, not measured growth curves.')
    s.text(40,78,'Illustrative common sow date = day 0. Existing batches retain their recorded dates.',17,MUTED)
    x0=255; scale=20; y0=140
    for d in range(0,51,5):
        x=x0+d*scale;s.line(x,115,x,440,color='#e0e8e4');s.text(x,465,d,15,anchor='middle')
    for i,r in enumerate(farm.recipes):
        y=y0+i*78; harvest=r.nursery_days+r.grow_days
        s.text(40,y+20,r.crop_id.replace('_',' ').title(),20,weight='bold')
        s.text(40,y+44,f'{float(r.marketable_kg_per_m2):.1f} kg/m² assumed',15,MUTED)
        s.rect(x0,y,r.nursery_days*scale,27,fill='#bcdac7',radius=0)
        s.rect(x0+r.nursery_days*scale,y,r.grow_days*scale,27,fill='#377968',radius=0)
        s.text(x0+r.nursery_days*scale/2,y+20,f'{r.nursery_days} d',14,anchor='middle')
        s.text(x0+(r.nursery_days+r.grow_days/2)*scale,y+20,f'{r.grow_days} d grow-out',15,color='#fff',anchor='middle')
        s.rect(x0+harvest*scale,y,r.sanitation_days*scale,27,fill='#e6bc76',radius=0)
        s.rect(x0+harvest*scale,y+34,r.shelf_life_days*scale,12,fill='#a8c5e7',radius=0)
        s.line(x0+harvest*scale,y-8,x0+harvest*scale,y+48,color=INK)
        s.text(x0+harvest*scale,y-14,f'Harvest d{harvest}',14,anchor='middle')
    s.text(750,495,'Days after sowing (calendar days)',17,anchor='middle')
    for x,c,label in [(40,'#bcdac7','Nursery'),(225,'#377968','Grow-out'),(430,'#e6bc76','Sanitation'),(650,'#a8c5e7','Stock shelf life')]:
        s.rect(x,518,25,15,fill=c,radius=0);s.text(x+36,531,label,16)
    s.text(40,566,'Figure 2. Continuous spans illustrate durations. Daily bed occupancy includes harvest + sanitation through that day.',15,MUTED)
    s.text(40,590,'The earliest next transplant is harvest + sanitation + 1 day. Shelf-life expiration is a separate inventory rule.',15,MUTED)
    return s.save()


def demand(farm):
    rows=sorted((h for h in farm.history if h.crop_id=='caixin'),key=lambda h:h.week)
    values=[float(h.ordered_kg) for h in rows]
    pred=[None]; state=values[0]
    for value in values[1:]:pred.append(state);state=.35*value+.65*state
    f=forecast(farm); last=state
    s=SVG('demand-baseline',1360,665,'Synthetic demand: observed fixture values and one-step EWMA',
          'Caixin fictional weekly demand versus the EWMA one-step prediction using only previous observations. Held-out weeks 7 through 12 match the historical evaluation design. A constant latest level is used for future weekly residual demand.')
    s.text(40,80,'Caixin · alpha = 0.35 · fabricated repeating history · no public/weather features',17,MUTED)
    x0=120; xstep=97; ytop=130; scale=40
    def y(v):return ytop+(35-v)*scale
    s.rect(x0+5.5*xstep,ytop,5.5*xstep,360,fill='#f6f0e5',stroke='none',radius=0)
    for v in range(26,36,2):
        s.line(x0,y(v),x0+11*xstep,y(v),color='#dce5e0');s.text(x0-15,y(v)+6,v,16,anchor='end')
    for i in range(12):s.text(x0+i*xstep,520,i+1,16,anchor='middle')
    for series,color in [(values,GREEN),(pred,BLUE)]:
        points=' '.join(f'{x0+i*xstep},{y(v)}' for i,v in enumerate(series) if v is not None)
        s.parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="3"/>')
        for i,v in enumerate(series):
            if v is not None:s.parts.append(f'<circle cx="{x0+i*xstep}" cy="{y(v)}" r="5" fill="{color}"/>')
    s.text(120,113,'kg / week',16);s.text(660,552,'Historical observation index',17,anchor='middle')
    s.line(120,587,160,587,color=GREEN);s.text(174,593,'Synthetic observations',16)
    s.line(455,587,495,587,color=BLUE);s.text(509,593,'One-step prediction',16)
    s.text(880,593,'Shading: held-out weeks 7–12',16,GOLD)
    s.text(40,632,f'Figure 3. Latest EWMA level = {last:.6f} kg/week. Future expected demand = bookings + max(0, level − weekly bookings).',15,MUTED)
    return s.save(), {'caixin_history_kg':values,'caixin_one_step_ewma_kg':pred,'latest_caixin_ewma_kg':last,'forecast_hash':content_hash(f)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--png',action='store_true');args=p.parse_args()
    farm=synthetic_farm(); demand_path,stats=demand(farm)
    paths=[architecture(),growth(farm),demand_path]
    (OUT/'data.json').write_text(json.dumps({'source_baseline':'a96025e','fixture_hash':content_hash(farm),'origin':'synthetic_demo','validation_status':'demo_only','recipes':[r.model_dump(mode='json') for r in farm.recipes],**stats},indent=2)+'\n')
    if args.png:
        import cairosvg
        for path in paths:cairosvg.svg2png(url=str(path),write_to=str(path.with_suffix('.png')))
    print('Generated 3 SVG figures and data.json'+(' plus 3 PNG figures' if args.png else '')+'. No external calls.')

if __name__=='__main__':main()
