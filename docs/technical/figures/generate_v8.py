"""Publication figures from preserved v8 evaluation artifacts; no inference."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'v8'
SOURCE=ROOT/'reports/v8/synthetic_model_evaluation.json'
data=json.loads(SOURCE.read_text())
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','savefig.facecolor':'white'})
models=['last_week','seasonal_naive','ewma_alpha_0_35','tuned_ewma']
names=['Last available week','Seasonal naive (13 weeks)','Fixed EWMA (α = 0.35)','Training-tuned EWMA']
colors=['#73858a','#bf873e','#277d73','#496bb4']

def save(fig,name):
    fig.savefig(OUT/f'{name}.svg',bbox_inches='tight')
    fig.savefig(OUT/f'{name}.png',bbox_inches='tight',dpi=180)
    plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(11,4.3),sharey=True)
for ax,kind in zip(axes,['farm','buyer']):
    rows=data['demand_evaluation']['cohorts'][kind]['metrics']
    for model,name,color in zip(models,names,colors):
        selected=sorted((r for r in rows if r['model']==model),key=lambda r:r['horizon_weeks'])
        ax.plot([r['horizon_weeks'] for r in selected],[100*r['wape'] for r in selected],marker='o',label=name,color=color,linewidth=2)
    ax.set(title=f'{kind.capitalize()} / crop cohorts',xlabel='Forecast horizon (weeks)',xticks=[1,2,4])
    ax.grid(axis='y',alpha=.2)
axes[0].set_ylabel('Weighted absolute percentage error (%)')
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',ncol=2,bbox_to_anchor=(.5,-.08),frameon=False)
fig.suptitle('Synthetic demand holdout · generated outcomes, not farm accuracy',fontsize=13)
fig.tight_layout(rect=(0,.08,1,.94));save(fig,'demand-holdout')

fig,axes=plt.subplots(1,2,figsize=(9,4))
for ax,target,unit in zip(axes,['maturity_days','marketable_kg'],['days','kg / batch']):
    vals=[data['crop_cycle_evaluation']['models'][model][target]['mae'] for model in ['recipe_baseline','crop_residual_mean']]
    bars=ax.bar(['Recipe baseline','Fitted crop residual'],vals,color=[colors[2],colors[3]],width=.6)
    ax.bar_label(bars,fmt='%.3f',padding=4)
    ax.set(ylabel=f'Mean absolute error ({unit})',title='Maturity' if target=='maturity_days' else 'Fresh marketable mass',ylim=(0,max(vals)*1.25))
    ax.grid(axis='y',alpha=.2)
fig.suptitle('Independent synthetic crop cycles · fitted candidate is not promoted',fontsize=12)
fig.tight_layout(rect=(0,0,1,.94));save(fig,'crop-cycle-holdout')

fig,ax=plt.subplots(figsize=(9,3.7))
categories=['Demand orders','Crop-cycle outcomes']
training=[data['demand_training_manifest']['row_count'],data['crop_cycle_training_manifest']['row_count']]
evaluation=[data['demand_evaluation_manifest']['row_count'],data['crop_cycle_evaluation_manifest']['row_count']]
x=np.arange(len(categories));width=.34
for offset,values,label,color in [(-width/2,training,'Training cohorts',colors[2]),(width/2,evaluation,'Unseen evaluation cohorts',colors[3])]:
    bars=ax.bar(x+offset,values,width,label=label,color=color);ax.bar_label(bars,padding=3,fmt='%d')
ax.set(xticks=x,xticklabels=categories,ylabel='Generated records',ylim=(0,max(training)*1.18),title='Disjoint synthetic identities and time periods')
ax.legend(frameon=False);ax.grid(axis='y',alpha=.2)
fig.tight_layout();save(fig,'cohort-design')

(OUT/'manifest.json').write_text(json.dumps(dict(source=str(SOURCE.relative_to(ROOT)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),evaluation_report_id=data['report_id'],origin='synthetic_benchmark',figures=['demand-holdout','crop-cycle-holdout','cohort-design'],inference_calls=0),indent=2)+'\n')
print('Rendered three scientific figures from preserved synthetic evaluation data')
