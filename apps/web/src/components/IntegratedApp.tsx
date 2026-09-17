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
 const origin=useRef<{element:HTMLElement|null;scroll:number}|null>(null)
 const enter=(set:(value:boolean)=>void)=>{
  origin.current={element:document.activeElement as HTMLElement|null,scroll:window.scrollY};set(true)
 }
 const leave=(set:(value:boolean)=>void)=>{
  const previous=origin.current;set(false)
  window.dispatchEvent(new Event('farmtact-workflow-refresh'))
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
   if(previous?.element?.isConnected)previous.element.focus({preventScroll:true})
   if(previous)window.scrollTo(0,previous.scroll)
  }))
 }
 return <IntegratedCards renderTool={(tool,close)=><Suspense fallback={<p role="status">Opening cards…</p>}>
 {tool==='records'?<><div hidden={recovery}><Records onClose={close} onOpenPlan={()=>enter(setRecovery)}/></div>{recovery&&<Plan onClose={()=>leave(setRecovery)}/>}</>:tool==='knowledge'?<Knowledge onClose={close}/>:tool==='experiments'?<><div hidden={research}><Experiments onClose={close} onResearch={()=>enter(setResearch)}/></div>{research&&<Research onClose={()=>leave(setResearch)}/>}</>:tool==='plan'?<Plan onClose={close}/>:<History onClose={close}/>}
 </Suspense>}/>
}
