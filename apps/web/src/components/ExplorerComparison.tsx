import { useState } from 'react'
import type { Scenario } from '../lib/game'
import type { Policy } from '../lib/explorer'
import type { Strategy, StrategyMetrics } from '../lib/types'

const metrics:Array<{key:keyof StrategyMetrics;label:string;unit:string}>=[
  {key:'shortfall_kg',label:'Delivery shortfall',unit:'kg'},
  {key:'waste_kg',label:'Waste',unit:'kg'},
  {key:'labour_hours',label:'Labour used',unit:'hours'},
  {key:'cost_sgd',label:'Cash spent',unit:'SGD'},
  {key:'margin_sgd',label:'Contribution margin',unit:'SGD'},
]
const fmt=(value:unknown)=>typeof value==='number'?value.toLocaleString('en-SG',{maximumFractionDigits:2}):'—'
const human=(key:string)=>key.replaceAll('_',' ')
const root=(s:Scenario)=>String(s.comparison_root||`farm:${s.baseline_hash}`)

function changes(s:Scenario){
  const descriptions:string[]=[]
  const generator=s.generator_settings as Record<string,number>|undefined
  const defaults:Record<string,number>={history_multiplier:1,history_trend:0,pattern_amplitude:1,orders_multiplier:1,price_multiplier:1}
  if(generator)for(const [key,value] of Object.entries(generator))if(value!==defaults[key])descriptions.push(`${human(key)}: ${fmt(value*100)}%`)
  const settings=s.forecast_settings as {alpha?:number}|undefined
  if(settings?.alpha!==undefined&&settings.alpha!==.35)descriptions.push(`EWMA alpha: ${settings.alpha} (reference 0.35)`)
  const c=s.controls
  if(c.delay_days)descriptions.push(`${c.batch_id}: harvest delayed ${c.delay_days} days`)
  if(c.yield_percent!==100)descriptions.push(`${c.batch_id}: yield ${c.yield_percent}%`)
  if(c.demand_percent!==100)descriptions.push(`${c.demand_crop_id}: demand ${c.demand_percent}%`)
  if(c.labour_percent!==100)descriptions.push(`Labour capacity ${c.labour_percent}%`)
  if(c.cash_percent!==100)descriptions.push(`Cash capacity ${c.cash_percent}%`)
  if(s.parent_scenario_id)descriptions.push(`Includes changes inherited from parent ${s.parent_scenario_id.slice(0,8)}. Inspect the frozen input differences below for the cumulative changes.`)
  return descriptions.length?descriptions:['Reference generator and forecast settings; no additional branch controls.']
}

function inputDifferences(s:Scenario){
  const before=s.baseline_snapshot as Record<string,unknown>|undefined, after=s.input_snapshot as Record<string,unknown>|undefined
  if(!before||!after)return []
  const result:Array<{dataset:string;record:string;field:string;before:unknown;after:unknown}>=[]
  for(const dataset of ['history','orders','batches','resources']){
    const old=dataset==='resources'?[before[dataset]]:before[dataset]
    const current=dataset==='resources'?[after[dataset]]:after[dataset]
    if(!Array.isArray(old)||!Array.isArray(current))continue
    current.forEach((value,index)=>{
      const row=value as Record<string,unknown>, original=old[index] as Record<string,unknown>|undefined
      if(!original)return
      for(const field of Object.keys(row))if(JSON.stringify(row[field])!==JSON.stringify(original[field]))result.push({dataset,record:String(row.id||row.crop_id&&`${row.crop_id} ${row.week}`||dataset),field,before:original[field],after:row[field]})
    })
  }
  return result
}

export function ExplorerComparison({scenarios,policy}:{scenarios:Scenario[];policy:Policy}) {
  const [evidence,setEvidence]=useState<string|null>(null)
  if(!scenarios.length)return null
  if(scenarios.length>3||scenarios.some(s=>s.status!=='COMPLETED')||new Set(scenarios.map(root)).size!==1||new Set(scenarios.map(s=>s.baseline_hash)).size!==1)return <p role="status">Complete and select up to three experiments from the same frozen baseline to compare them.</p>
  const baseline=(scenarios[0].baseline?.strategies||[]).find(s=>s.name===policy)
  if(!baseline)return <p role="status">The frozen baseline for this policy is unavailable.</p>
  const rows=scenarios.map(s=>({s,strategy:s.result?.strategies?.find(r=>r.name===policy)})).filter((value):value is {s:Scenario;strategy:Strategy}=>Boolean(value.strategy))
  const isPlayground=root(scenarios[0]).startsWith('playground:')
  const choose=(id:string)=>{setEvidence(id);window.setTimeout(()=>document.getElementById(`explorer-evidence-${id}`)?.scrollIntoView({behavior:'auto',block:'nearest'}),0)}
  return <section className="explorer-card explorer-wide">
    <p className="kicker">Numerical consequences · {policy}</p><h2>What changed against the baseline</h2>
    <p>{isPlayground?'The baseline is the original generated dataset, with default generator settings and EWMA alpha 0.35.':'The baseline is this main-farm experiment’s original frozen farm snapshot.'} Every column uses the {policy} policy over the same horizon. All outcomes are simulated.</p>
    <div className="table-scroll"><table className="explorer-comparison-table"><caption>{policy} · baseline and {rows.length} {rows.length===1?'branch':'branches'}</caption><thead><tr><th>Measure</th><th>Original baseline</th>{rows.map(({s})=><th key={s.id}>{s.name}</th>)}</tr></thead><tbody>
      {metrics.map(({key,label,unit})=><tr key={key}><th>{label} ({unit})</th><td>{fmt(baseline.metrics[key])}</td>{rows.map(({s,strategy})=>{const change=Number(strategy.metrics[key])-Number(baseline.metrics[key]);return <td key={s.id}><strong>{fmt(strategy.metrics[key])}</strong><br/><small>{change>0?'+':''}{fmt(change)} from baseline</small></td>})}</tr>)}
      <tr><th>Constraint violations</th><td>{baseline.violations.length}</td>{rows.map(({s,strategy})=><td key={s.id}><button className="text-button" style={{minHeight:44}} onClick={()=>choose(s.id)}>{strategy.violations.length} · {strategy.status==='FEASIBLE'?'Feasible':'Inspect infeasibility'}</button></td>)}</tr>
    </tbody></table></div>
    <div className="explorer-grid">{rows.map(({s,strategy})=>{
      const shortfall=Number(strategy.metrics.shortfall_kg)-Number(baseline.metrics.shortfall_kg)
      const waste=Number(strategy.metrics.waste_kg)-Number(baseline.metrics.waste_kg)
      const cost=Number(strategy.metrics.cost_sgd)-Number(baseline.metrics.cost_sgd)
      const margin=Number(strategy.metrics.margin_sgd)-Number(baseline.metrics.margin_sgd)
      const differences=inputDifferences(s)
      return <article key={s.id} style={{minWidth:0,paddingTop:16}}><h3>{s.name}</h3><details><summary style={{minHeight:44,padding:'10px 0',cursor:'pointer'}}>Changed assumptions</summary><ul>{changes(s).map((change,index)=><li key={index}>{change}</li>)}</ul></details>
        <p>{shortfall===0?'Delivery shortfall is unchanged':`Delivery shortfall ${shortfall<0?'falls':'rises'} by ${fmt(Math.abs(shortfall))} kg`}; waste {waste===0?'is unchanged':`${waste<0?'falls':'rises'} by ${fmt(Math.abs(waste))} kg`}. Cash spent {cost===0?'is unchanged':`${cost<0?'falls':'rises'} by SGD ${fmt(Math.abs(cost))}`}, while contribution margin {margin===0?'is unchanged':`${margin<0?'falls':'rises'} by SGD ${fmt(Math.abs(margin))}`}.</p>
        <p>This is a comparison of the frozen calculations, not proof that any one assumption caused a real farm outcome. {strategy.violations.length?'This policy violates a declared constraint and was not accepted as a feasible plan.':'The recorded constraint checks passed for this policy.'}</p>
        <button className="button button--cream" style={{minHeight:44}} onClick={()=>choose(s.id)}>Trace {s.name} to numerical evidence</button>
        <details id={`explorer-evidence-${s.id}`} open={evidence===s.id} onToggle={event=>{if(!event.currentTarget.open&&evidence===s.id)setEvidence(null)}} style={{paddingTop:12,overflowWrap:'anywhere'}}><summary style={{minHeight:44,cursor:'pointer'}}>Frozen evidence · {s.id.slice(0,8)}</summary><p>Input {s.input_hash}; baseline {s.baseline_hash}. Strategy {strategy.id}, {strategy.calculation_version}. Numeric metric fields below are the exact values used by the explanation.</p><pre style={{maxHeight:260,overflow:'auto',whiteSpace:'pre-wrap'}}>{JSON.stringify({baseline:baseline.metrics,scenario:strategy.metrics,violations:strategy.violations},null,2)}</pre>
        <details><summary style={{minHeight:44,cursor:'pointer'}}>Inspect {differences.length} cumulative input differences</summary><div className="table-scroll"><table><thead><tr><th>Dataset / record</th><th>Field</th><th>Baseline</th><th>Branch</th></tr></thead><tbody>{differences.map((d,index)=><tr key={index}><td>{d.dataset} · {d.record}</td><td>{human(d.field)}</td><td>{String(d.before)}</td><td>{String(d.after)}</td></tr>)}</tbody></table></div></details></details>
      </article>
    })}</div>
  </section>
}
