import {useEffect,useRef,useState} from 'react'
import {editionPath,editionStorageKey} from '../lib/edition'
import './decision-guide.css'
const key=editionStorageKey('council-guidance-v2')
const scenes=[
 {title:'Start with a delivery question',body:'Inspect the crop, quantity and due date. Calculate alternatives from recorded inputs before choosing a plan.',roles:['ravi','mei'],labels:['Demand Planner','Crop Planner'],steps:['Dated order','Recorded crops','Calculate']},
 {title:'Compare different perspectives',body:'Ask Council explicitly. Read the relevant specialists, inspect their evidence and question the tradeoff. The Chair brings the recommendations together.',roles:['ben','lina','asha'],labels:['Resource Planner','Supply Planner','Chair'],steps:['Coverage','Expiry & cost','Your question']},
 {title:'Review before saving',body:'A candidate is only a preview. Review exact changes, calculate revised plans, then separately approve simulated tasks.',roles:['mei','asha'],labels:['Crop Planner','Chair'],steps:['Unsaved preview','Reviewed changes','Simulated tasks']},
 {title:'Report, compare and recover',body:'Save what was reported, compare it with the projection and review future recovery. Completed work stays in history.',roles:['lina','ravi'],labels:['Supply Planner','Demand Planner'],steps:['Reported result','Difference','Future recovery']},
]
function preferences(){try{return JSON.parse(localStorage.getItem(key)||'{}')}catch{return {}}}
export function DecisionGuide({title,detail,label,onAction,disabled,secondary,onSecondary}:{title:string;detail:string;label:string;onAction:()=>void;disabled:boolean;secondary?:string;onSecondary?:()=>void}){
 const [prefs,setPrefs]=useState<{demoDismissed?:boolean;hidden?:boolean}>(preferences)
 const [demo,setDemo]=useState(!prefs.demoDismissed),[step,setStep]=useState(0),[paused,setPaused]=useState(false)
 const [reduced,setReduced]=useState(()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches||localStorage.getItem(editionStorageKey('reduced-motion'))==='true')
 const dialog=useRef<HTMLDialogElement>(null),opener=useRef<HTMLElement|null>(null)
 const save=(next:typeof prefs)=>{setPrefs(next);try{localStorage.setItem(key,JSON.stringify({version:2,...next}))}catch{}}
 const close=()=>{setDemo(false);save({...prefs,demoDismissed:true});opener.current?.focus()}
 useEffect(()=>{document.documentElement.dataset.reducedMotion=String(reduced);try{localStorage.setItem(editionStorageKey('reduced-motion'),String(reduced))}catch{}},[reduced])
 useEffect(()=>{if(!demo)return;opener.current=document.activeElement as HTMLElement;dialog.current?.showModal();dialog.current?.querySelector<HTMLElement>('h2')?.focus();return()=>dialog.current?.close()},[demo])
 useEffect(()=>{if(!demo||paused||reduced||step===3)return;const timer=setTimeout(()=>setStep(value=>Math.min(3,value+1)),7500);return()=>clearTimeout(timer)},[demo,paused,reduced,step])
 const scene=scenes[step]
 return <>
 <section className="decision-guide" aria-label="Next decision">
  <div><p className="kicker">Current guided plan · Council workspace</p><h1>{title}</h1>{!prefs.hidden&&<p>{detail}</p>}<small>Synthetic farm · simulated tasks only</small></div>
  <div className="decision-guide-actions"><button className="button button--forest" disabled={disabled} onClick={onAction}>{label}</button>{secondary&&<button className="button button--cream" onClick={onSecondary}>{secondary}</button>}</div>
  <div className="decision-guide-preferences"><button className="text-button" onClick={()=>save({...prefs,hidden:!prefs.hidden})}>{prefs.hidden?'Show guidance':'Hide guidance'}</button><button className="text-button" onClick={()=>{setStep(0);setPaused(false);setDemo(true)}}>Replay demo</button><label><input type="checkbox" checked={reduced} onChange={e=>setReduced(e.target.checked)}/> Reduced motion</label></div>
 </section>
 {demo&&<dialog ref={dialog} className="decision-demo" onCancel={e=>{e.preventDefault();close()}} aria-labelledby="decision-demo-title">
  <p className="kicker">30-second introduction · {step+1} of 4</p><h2 id="decision-demo-title" tabIndex={-1}>Meet your farm Council</h2><p className="decision-demo-boundary">Illustration of the workflow—not your saved farm. No calculation or AI request runs in this demo.</p>
  <section className="decision-demo-scene" key={step} aria-live="polite"><h3>{scene.title}</h3><div className="decision-demo-roles">{scene.roles.map((role,index)=><div key={role}><img src={editionPath(`/art/advisors/${role}.svg`)} alt=""/><b>{scene.labels[index]}</b></div>)}</div><ol>{scene.steps.map(text=><li key={text}>{text}</li>)}</ol><p>{scene.body}</p></section>
  <div className="decision-demo-controls"><button className="button button--cream" onClick={close}>Skip demo</button><button className="button button--cream" disabled={step===0} onClick={()=>{setPaused(true);setStep(step-1)}}>Previous</button>{!reduced&&<button className="button button--cream" onClick={()=>setPaused(!paused)}>{paused?'Play':'Pause'}</button>}<button className="button button--forest" onClick={()=>step===3?close():(setPaused(true),setStep(step+1))}>{step===3?'Start planning':'Next scene'}</button></div>
 </dialog>}
 </>
}
export function SavedConsequence({identity,label,details}:{identity:string;label:string;details:string}){
 const seen=useRef(identity),[changed,setChanged]=useState(false)
 useEffect(()=>{if(seen.current===identity)return;seen.current=identity;setChanged(true);const timer=setTimeout(()=>setChanged(false),500);return()=>clearTimeout(timer)},[identity])
 return <p className={`decision-receipt ${changed?'is-new':''}`} role="status"><strong>{label}</strong> {details}</p>
}
