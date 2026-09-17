import { useRef, type ReactNode } from 'react'
import type { FarmCard } from '../lib/cards'
import BoundCard from './BoundCard'
import './tool-card.css'
export type ToolAction = {label:string; run:()=>void; disabled?:boolean;disabledReason?:string;authority?:'local_navigation'|'server_mutation';eligibilitySource?:'local'|'server'}
export function ToolCard({title, children, onBack, primary, secondary, previous, next, position, busy, error, card}: {
 title:string;children:ReactNode;onBack:()=>void;primary?:ToolAction;secondary?:ToolAction;
 previous?:()=>void;next?:()=>void;position?:string;busy?:boolean;error?:string;card?:FarmCard
}) {
 const touch=useRef<{x:number;y:number}|null>(null)
 return <section className="integrated-tool" aria-label={title} onKeyDown={e=>{
   if((e.target as HTMLElement).closest('input,textarea,select,button,a'))return
   if(e.key==='ArrowRight'&&next){e.preventDefault();next()}
   if(e.key==='ArrowLeft'&&previous){e.preventDefault();previous()}
 }} onTouchStart={e=>{touch.current=(e.target as HTMLElement).closest('input,textarea,select,button,a')?null:{x:e.touches[0].clientX,y:e.touches[0].clientY}}} onTouchEnd={e=>{
   const from=touch.current;touch.current=null;if(!from)return
   const dx=e.changedTouches[0].clientX-from.x,dy=e.changedTouches[0].clientY-from.y
   if(Math.abs(dx)>65&&Math.abs(dx)>Math.abs(dy)*1.5){if(dx<0)next?.();else previous?.()}
 }}>
 {card?<BoundCard card={card} className="integrated-tool__card" tabIndex={0}><small>Sandbox · actual farm operations disabled</small><h2>{title}</h2>{children}</BoundCard>
 :<article className="integrated-tool__card" tabIndex={0}><small>Sandbox · actual farm operations disabled</small><h2>{title}</h2>{children}</article>}
 {error&&<p role="alert">{error}</p>}{busy&&<p role="status">Waiting for server confirmation…</p>}
 {(previous||next)&&<nav aria-label="Card navigation"><button onClick={previous} disabled={!previous}>Previous</button><span>{position}</span><button onClick={next} disabled={!next}>Next</button></nav>}
 <footer><button onClick={onBack}>Back</button>{primary&&<button className="primary" title={primary.disabledReason} disabled={busy||primary.disabled} onClick={primary.run}>{primary.label}</button>}{secondary&&<button title={secondary.disabledReason} disabled={busy||secondary.disabled} onClick={secondary.run}>{secondary.label}</button>}</footer>
 </section>
}
export function RecordFacts({value}:{value:unknown}) {
 if(value===null||value===undefined)return <p>Not available</p>
 if(typeof value!=='object')return <span>{String(value)}</span>
 if(Array.isArray(value))return <ul>{value.map((item,i)=><li key={i}><RecordFacts value={item}/></li>)}</ul>
 return <dl className="record-facts">{Object.entries(value).map(([key,item])=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd><RecordFacts value={item}/></dd></div>)}</dl>
}
