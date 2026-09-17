import { lazy, Suspense, useRef, useState } from 'react'
import IntegratedCards from './IntegratedCards'
const Records=lazy(()=>import('./IntegratedRecords').then(m=>({default:m.IntegratedRecords})))
const Knowledge=lazy(()=>import('./IntegratedKnowledge'))
const Experiments=lazy(()=>import('./IntegratedExperiments'))
const Plan=lazy(()=>import('./IntegratedPlan'))
const Research=lazy(()=>import('./IntegratedResearch'))
const History=lazy(()=>import('./IntegratedHistory'))
export default function IntegratedApp(){
 const [research,setResearch]=useState(false)
 const [recovery,setRecovery]=useState(false)
 const origin=useRef<{element:HTMLElement|null;scroll:number;label:string}|null>(null)
 const enter=(set:(value:boolean)=>void)=>{
  const element=document.activeElement as HTMLElement|null
  origin.current={element,scroll:window.scrollY,label:element?.textContent?.trim()||''};set(true)
 }
 const leave=(set:(value:boolean)=>void)=>{
  const previous=origin.current;set(false)
  const restore=()=>requestAnimationFrame(()=>requestAnimationFrame(()=>{
   if(!previous)return
   const target=previous.element?.isConnected?previous.element:Array.from(document.querySelectorAll<HTMLButtonElement>('.integrated-records button, .integrated-tool button')).find(button=>button.getClientRects().length>0&&button.textContent?.trim()===previous.label)
   target?.focus({preventScroll:true});window.scrollTo(0,previous.scroll)
  }))
  restore()
  if(set===setRecovery){
   // The refresh can replace the action node; restore against its saved label
   // after React commits the refreshed task, unless the reader moves on first.
   const cancel=()=>{window.removeEventListener('farmtact-workflow-refreshed',done);window.removeEventListener('pointerdown',cancel);window.removeEventListener('keydown',cancel)}
   const done=()=>{cancel();restore()}
   window.addEventListener('farmtact-workflow-refreshed',done,{once:true})
   window.addEventListener('pointerdown',cancel,{once:true});window.addEventListener('keydown',cancel,{once:true})
   window.dispatchEvent(new Event('farmtact-workflow-refresh'))
  }
 }
 return <IntegratedCards renderTool={(tool,close)=><Suspense fallback={<p role="status">Opening cards…</p>}>
 {tool==='records'?<><div hidden={recovery}><Records onClose={close} onOpenPlan={()=>enter(setRecovery)}/></div>{recovery&&<Plan onClose={()=>leave(setRecovery)}/>}</>:tool==='knowledge'?<Knowledge onClose={close}/>:tool==='experiments'?<><div hidden={research}><Experiments onClose={close} onResearch={()=>enter(setResearch)}/></div>{research&&<Research onClose={()=>leave(setResearch)}/>}</>:tool==='plan'?<Plan onClose={close}/>:<History onClose={close}/>}
 </Suspense>}/>
}
