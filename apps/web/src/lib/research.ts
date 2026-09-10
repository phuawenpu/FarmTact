import { editionPath } from './edition'
import type { Farm, StrategyMetrics } from './types'

export type CouncilConcept = 'inline' | 'sheet' | 'cards'
export type SteeringMode = 'continuous' | 'checkpoints'
export type ResearchAction = 'say'|'select'|'propose'|'apply'|'discard'|'run'|'challenge'|'resolve'|'choose'|'configure'|'stop'|'next'
export interface ResearchMessage { id:string; speaker:string; text:string; refs:string[]; kind:string; input_version:number; created_at:string }
export interface ResearchProposal { operation:'reserve_bed'|'order_status'|'labour'; base_version:number; bed_id?:string; order_id?:string; start_date?:string|null; end_date?:string|null; confirmed?:boolean; labour_percent?:number }
export interface ResearchChallenge { status:'unresolved'|'evidence'|'corrected'|'reject'; text:string; input_version:number }
export interface ResearchStrategy { id:string; name:'Lean'|'Balanced'|'Resilient'; status:string; metrics:StrategyMetrics; allocations:Array<Record<string,unknown>>; violations:Array<Record<string,unknown>> }
export interface ResearchResult { version:number; status:string; input_hash:string; inputs:ResearchInputs; calculation?:{strategies:ResearchStrategy[]}; error?:string }
export interface ResearchInputs { reservations:Array<{bed_id:string;start_date:string;end_date:string}>; unconfirmed_order_ids:string[]; labour_percent:number }
export interface ResearchSession {
  id:string; revision:number; input_version:number; concept:CouncilConcept; steering:SteeringMode; selection_mode:'chips'|'cards'; animation:'static'|'transition';
  farm:Farm; inputs:ResearchInputs; selected_refs:string[]; proposal:ResearchProposal|null; challenge:ResearchChallenge|null; chosen:{version:number;policy:string;simulation_only:boolean}|null;
  messages:ResearchMessage[]; pending_turns:Array<{speaker:string;text:string;refs:string[]}>; results:ResearchResult[]; milestones:Record<string,boolean>; dialogue_mode:string; operational_execution:false
}
export interface ResearchReport { title:string; documents:Array<{title:string;markdown:string}>; sources:Array<{title:string;url:string}>; screenshots:Array<{title:string;url:string}> }
export interface ActualConversation { id:string; snapshot_ref?:string|{kind?:string;id?:string;hash?:string;version?:number}; tool_results?:Record<string,unknown>; messages:Array<{id:string;speaker:string;speaker_name?:string;content:string;validation_status?:string;interpretation_status?:string;tool_refs?:string[];evidence_refs?:string[]}>; last_request_status?:string|null }
export type ResearchActionBody = {action:ResearchAction;revision:number;text?:string;refs?:string[];operation?:ResearchProposal['operation'];bed_id?:string;order_id?:string;start_date?:string;end_date?:string;confirmed?:boolean;labour_percent?:number;policy?:'Lean'|'Balanced'|'Resilient';result_version?:number;concept?:CouncilConcept;steering?:SteeringMode;selection_mode?:'chips'|'cards';animation?:'static'|'transition';resolution?:ResearchChallenge['status'];advisor?:string}

async function call<T>(path:string, init?:RequestInit):Promise<T>{
  const response=await fetch(editionPath(`/api/v1/council-research${path}`),{...init,headers:{'Content-Type':'application/json',...init?.headers}})
  if(!response.ok){let detail='';try{detail=String((await response.json()).detail||'')}catch{};const error=Object.assign(new Error(detail||`Request failed (${response.status})`),{status:response.status});throw error}
  return response.json()
}
export const researchApi={
  list:()=>call<{sessions:Array<{id:string;created_at:string;concept:CouncilConcept;input_version:number;revision:number}>}>(''),
  create:(concept:CouncilConcept,steering:SteeringMode)=>call<ResearchSession>('',{method:'POST',headers:{'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({concept,steering})}),
  get:(id:string)=>call<ResearchSession>(`/${encodeURIComponent(id)}`),
  act:(id:string,body:ResearchActionBody)=>call<ResearchSession>(`/${encodeURIComponent(id)}/actions`,{method:'POST',headers:{'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify(body)}),
  report:()=>call<ResearchReport>('/report'),
  createActual:async(sessionId:string,version:number,advisor:string)=>{
    const response=await fetch(editionPath('/api/v1/conversations'),{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({advisor,snapshot_kind:'research',snapshot_id:sessionId,research_version:version})})
    if(!response.ok)throw new Error(String((await response.json().catch(()=>({}))).detail||`Request failed (${response.status})`));return response.json() as Promise<{id:string}>
  },
  sendActual:async(id:string,content:string)=>{
    const response=await fetch(editionPath(`/api/v1/conversations/${encodeURIComponent(id)}/messages`),{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({content})})
    if(!response.ok)throw new Error(String((await response.json().catch(()=>({}))).detail||`Request failed (${response.status})`))
  },
  getActual:async(id:string)=>{
    const response=await fetch(editionPath(`/api/v1/conversations/${encodeURIComponent(id)}`));if(!response.ok)throw new Error(`Conversation unavailable (${response.status})`);return response.json() as Promise<ActualConversation>
  },
}
