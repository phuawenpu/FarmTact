import { lazy, Suspense, useState } from 'react'
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
 return <IntegratedCards renderTool={(tool,close)=><Suspense fallback={<p role="status">Opening cards…</p>}>
 {tool==='records'?<><div hidden={recovery}><Records onClose={close} onOpenPlan={()=>setRecovery(true)}/></div>{recovery&&<Plan onClose={()=>setRecovery(false)}/>}</>:tool==='knowledge'?<Knowledge onClose={close}/>:tool==='experiments'?(research?<Research onClose={()=>setResearch(false)}/>:<Experiments onClose={close} onResearch={()=>setResearch(true)}/>):tool==='plan'?<Plan onClose={close}/>:<History onClose={close}/>}
 </Suspense>}/>
}
