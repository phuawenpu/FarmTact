/** Actual UI capture in two independent synthetic sessions; never mocks API results. */
import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const root=resolve(new URL('../..',import.meta.url).pathname);
const rehearsal=process.env.REHEARSAL==='1';
const out=resolve(process.env.CAPTURE_DIR||`${root}/output/demo-video/work/capture`);
const base=process.env.BASE_URL||'http://127.0.0.1:8080';
const scenes=JSON.parse(await readFile(`${root}/scripts/demo_video/storyboard.json`));
await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const report={base,rehearsal,started:new Date().toISOString(),scenes:[],views:[],errors:[],providerRequests:[]};
const views=[];
for(const name of ['desktop','mobile']){
 const mobile=name==='mobile',size=mobile?{width:390,height:844}:{width:1280,height:840};
 const context=await browser.newContext({viewport:size,deviceScaleFactor:1,isMobile:mobile,hasTouch:mobile,reducedMotion:'no-preference',...(rehearsal?{}:{recordVideo:{dir:out,size}})});
 await context.addInitScript(({mobile})=>{
  addEventListener('DOMContentLoaded',()=>{
   const dot=document.createElement('div');dot.id='demo-cursor';dot.setAttribute('aria-hidden','true');
   dot.style.cssText='position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transform:translate(-80px,-80px);';
   dot.innerHTML=mobile?'':`<svg width="28" height="34" viewBox="0 0 28 34"><path d="M3 2L3 26L9 20L15 32L20 29L14 18L24 18Z" fill="#fffdf2" stroke="#173e2c" stroke-width="2"/></svg>`;
   document.body.append(dot);
   addEventListener('mousemove',e=>{dot.style.transform=`translate(${e.clientX}px,${e.clientY}px)`});
   const pulse=(x,y)=>{const ring=document.createElement('div');ring.style.cssText=`position:fixed;left:${x-18}px;top:${y-18}px;width:36px;height:36px;border:3px solid #edaa53;background:#edaa5333;border-radius:50%;pointer-events:none;z-index:2147483646;`;document.body.append(ring);ring.animate([{opacity:.9,transform:'scale(.6)'},{opacity:0,transform:'scale(1.8)'}],{duration:650}).onfinish=()=>ring.remove()};
   addEventListener(mobile?'touchstart':'mousedown',e=>{const p=mobile?e.touches[0]:e;pulse(p.clientX,p.clientY)},{passive:true});
  });
 },{mobile});
 context.setDefaultTimeout(40000);
 const started=Date.now(),page=await context.newPage();
 const view={name,mobile,context,page,started,size,focus:[],mouse:{x:70,y:70}};
 page.on('pageerror',e=>report.errors.push({view:name,error:e.message}));
 page.on('request',r=>{if(r.method()!=='GET'&&/\/conversations(?:\/|$)|\/planning-sessions\/[^/]+\/review$/.test(new URL(r.url()).pathname))report.providerRequests.push({view:name,path:new URL(r.url()).pathname})});
 page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/'))report.errors.push({view:name,status:r.status(),path:new URL(r.url()).pathname})});
 await page.goto(base,{waitUntil:'domcontentloaded'});await page.locator('.decision-guide').waitFor();
 await page.getByRole('button',{name:'Pause',exact:true}).click();
 views.push(view);
}
async function reveal(v,loc){
 await loc.waitFor({state:'visible'});
 await loc.evaluate(el=>el.scrollIntoView({behavior:'smooth',block:'center',inline:'nearest'}));
 await wait(rehearsal?350:1100);
}
async function move(v,x,y){
 if(v.mobile)return;
 const from={...v.mouse},steps=rehearsal?4:24;
 for(let i=1;i<=steps;i++){const t=i/steps,e=t*t*(3-2*t);await v.page.mouse.move(from.x+(x-from.x)*e,from.y+(y-from.y)*e);if(!rehearsal)await wait(14)}
 v.mouse={x,y};
}
async function click(v,loc){
 await reveal(v,loc);await loc.waitFor({state:'visible'});
 const b=await loc.boundingBox();await move(v,b.x+b.width*.5,b.y+b.height*.5);await wait(rehearsal?30:260);
 if(v.mobile)await loc.tap();else await loc.click();
 await wait(rehearsal?150:600);
}
async function focus(v,loc,zoom=1.35){await reveal(v,loc);const b=await loc.boundingBox();v.focus.push({time:(Date.now()-v.started)/1000,x:b.x+b.width/2,y:b.y+b.height/2,zoom});}
async function type(v,loc,text){await click(v,loc);await v.page.keyboard.press('ControlOrMeta+A');await v.page.keyboard.press('Backspace');await focus(v,loc);await loc.pressSequentially(text,{delay:rehearsal?2:70});await wait(rehearsal?50:900)}
const button=(v,name,scope)=> (scope||v.page).getByRole('button',{name,exact:true});
const dialog=v=>v.page.getByRole('dialog').filter({visible:true});
async function close(v){await v.page.keyboard.press('Escape');await wait(rehearsal?100:700)}
const actions={
 welcome:async v=>{await focus(v,v.page.locator('.decision-demo'),1);await click(v,button(v,'Next scene'));await wait(rehearsal?100:2600);await click(v,button(v,'Skip demo'));await reveal(v,v.page.locator('.decision-guide'))},
 farm:async v=>{await reveal(v,v.page.locator('.flow-observe'));await wait(rehearsal?100:1800);await reveal(v,v.page.locator('.living-board'));await focus(v,v.page.locator('.living-board'),1.1)},
 records:async v=>{await click(v,button(v,'Inbox'));await v.page.getByRole('dialog',{name:'Farm Inbox',exact:true}).waitFor();await focus(v,v.page.locator('.inbox-default'),1.25);await wait(rehearsal?100:4000);await reveal(v,v.page.locator('.sandbox-upload'));await wait(rehearsal?100:2000);await close(v)},
 calculate:async v=>{await click(v,button(v,'Compare planting plans',v.page.locator('.decision-guide')));await v.page.locator('.proposal-card').first().waitFor({timeout:180000});await reveal(v,v.page.locator('.decision-stage'));await focus(v,v.page.locator('.proposal-grid'),1.12)},
 compare:async v=>{const cards=v.page.locator('.proposal-card');await click(v,cards.filter({has:v.page.getByRole('heading',{name:'Balanced',exact:true})}));await wait(rehearsal?100:1600);await click(v,cards.filter({has:v.page.getByRole('heading',{name:'Resilient',exact:true})}));await wait(rehearsal?100:1600);await click(v,cards.filter({has:v.page.getByRole('heading',{name:'Balanced',exact:true})}));await focus(v,v.page.locator('.proposal-grid'),1.16)},
 council:async v=>{await reveal(v,v.page.locator('.cw-roster'));await wait(rehearsal?100:1800);await type(v,v.page.locator('.cw-discussion textarea'),'Which booked delivery is most exposed, and what crop timing limits our options?');await focus(v,v.page.locator('.cw-compose-actions'),1.3)},
 assumptions:async v=>{await click(v,button(v,'Adjust assumptions'));const d=v.page.getByRole('dialog',{name:'Challenge constraints and recalculate'});const demand=d.getByLabel('Expected demand',{exact:false});await click(v,demand);await focus(v,demand,1.35);for(let n=Number(await demand.inputValue());n<105;n++){await demand.press('ArrowRight');await wait(rehearsal?10:180)}if(await demand.inputValue()!=='105')throw Error('Expected demand not 105 percent');await reveal(v,d.locator('.proposal-review'));await focus(v,d.locator('.proposal-review'),1.25);await wait(rehearsal?100:1800);await click(v,d.getByRole('button',{name:'Calculate revised plans',exact:true}));await d.waitFor({state:'hidden'});await button(v,'Save simulation plan',v.page.locator('.decision-guide')).waitFor({timeout:180000});await v.page.waitForFunction(()=>{const b=[...document.querySelectorAll('.decision-guide button')].find(b=>b.textContent.trim()==='Save simulation plan');return b&&!b.disabled},null,{timeout:180000});await reveal(v,v.page.locator('.decision-stage'))},
 approve:async v=>{await click(v,button(v,'Save simulation plan',v.page.locator('.decision-guide')));const d=v.page.getByRole('dialog',{name:'Save simulation plan'});await d.waitFor();await focus(v,d,1.15);await wait(rehearsal?100:2200);await click(v,d.getByRole('button',{name:'Confirm simulation plan',exact:true}));await d.waitFor({state:'hidden'});await v.page.locator('.action-stage').waitFor();await reveal(v,v.page.locator('.action-stage'))},
 task:async v=>{const state=await v.page.evaluate(()=>fetch('/api/v1/farm-workflow').then(r=>r.json()));const proposal=[...state.proposals].reverse().find(x=>x.status==='approved');const tasks=state.tasks.filter(x=>x.proposal_id===proposal.id);v.task=tasks.find(x=>x.action==='harvest'&&Number(x.planned_quantity)>1)||tasks.find(x=>Number(x.planned_quantity)>1&&x.unit);if(!v.task)throw Error('No quantity task');await click(v,v.page.locator(`[data-task-id="${v.task.id}"]`));await reveal(v,v.page.locator('.task-result-panel'));await focus(v,v.page.locator('.task-result-panel'),1.2)},
 report:async v=>{await type(v,v.page.getByLabel(/Actual quantity/),String(Number(v.task.planned_quantity)-1));for(const c of await v.page.locator('.result-form').first().locator('input[type=checkbox]').all())await click(v,c);await type(v,v.page.getByLabel('Farmer note',{exact:true}),'Demo report: harvest one unit below plan. Review recovery.');await click(v,button(v,'Save reported result'));await v.page.getByLabel('Corrected quantity',{exact:true}).waitFor();await focus(v,v.page.locator('.correction-form'),1.2)},
 correction:async v=>{await type(v,v.page.getByLabel('Corrected quantity',{exact:true}),String(Number(v.task.planned_quantity)-.5));await type(v,v.page.getByLabel('Reason',{exact:true}),'Scale rechecked; corrected the demo reading.');await click(v,button(v,'Save auditable correction'));await wait(800);const current=await v.page.evaluate(id=>fetch('/api/v1/farm-workflow').then(r=>r.json()).then(s=>s.tasks.find(t=>t.id===id)),v.task.id);if(current.event_revision<2)throw Error('Correction not persisted');v.result={planned:v.task.planned_quantity,actual:current.actual_quantity,status:current.status,event_revision:current.event_revision};await reveal(v,v.page.locator('.recovery-stage'))},
 recovery:async v=>{await click(v,button(v,'Compare recovery plans',v.page.locator('.recovery-stage')));const d=v.page.getByRole('dialog',{name:'Challenge constraints and recalculate'});await d.waitFor();await focus(v,d.locator('.proposal-review'),1.2);await wait(rehearsal?100:2500);await close(v);await reveal(v,v.page.locator('.decision-guide'))},
 knowledge:async v=>{const nav=v.page.locator(v.mobile?'.thumb-nav':'.side-rail nav');await click(v,nav.getByRole('button',{name:'Crops',exact:true}));await v.page.getByRole('heading',{name:'Recipes with receipts.'}).waitFor();await reveal(v,v.page.getByRole('heading',{name:'Recipes with receipts.'}));await wait(rehearsal?100:1500);await type(v,v.page.getByPlaceholder('Search crop or local alias'),'Caixin');await click(v,v.page.locator('.crop-profile-card').first());await v.page.locator('.crop-modal').waitFor();await focus(v,v.page.locator('.crop-modal .metric-grid'),1.15);await wait(rehearsal?100:1500);await close(v);},
 guides:async v=>{const nav=v.page.locator(v.mobile?'.thumb-nav':'.side-rail nav');await click(v,nav.getByRole('button',{name:'Plan',exact:true}));await v.page.locator('.decision-guide').waitFor();await click(v,button(v,'How it works'));await v.page.getByRole('dialog',{name:'Three short guides'}).waitFor();await focus(v,v.page.locator('.explainer-item').first(),1.05);await wait(rehearsal?100:1500);await click(v,v.page.locator('.explainer-item').first().getByText('Transcript',{exact:true}));await wait(rehearsal?100:1200);await close(v)},
 finish:async v=>{await reveal(v,v.page.locator('.decision-guide'));await focus(v,v.page.locator('.decision-guide'),1);}
};
let failed=false;
try{
 for(const scene of scenes){
  const entry={...scene,views:{}};report.scenes.push(entry);console.log('SCENE',scene.id,flush());
  await Promise.all(views.map(async v=>{const start=Date.now();entry.views[v.name]={start:(start-v.started)/1000};await actions[scene.id](v);const actionEnd=Date.now();entry.views[v.name].actions=(actionEnd-start)/1000;if(!rehearsal)await wait(Math.max(0,scene.seconds*1000-(Date.now()-start)));entry.views[v.name].end=(Date.now()-v.started)/1000;await v.page.screenshot({path:`${out}/${v.name}-${scene.id}.png`});}));
  await writeFile(`${out}/timeline.json`,JSON.stringify(report,null,2));
 }
}catch(e){failed=true;report.errors.push({error:e.stack});console.error(e);for(const v of views)await v.page.screenshot({path:`${out}/${v.name}-failure.png`}).catch(()=>{})}
finally{
 for(const v of views){const video=v.page.video();const end=(Date.now()-v.started)/1000;await v.context.close();if(video)await video.saveAs(`${out}/${v.name}.webm`);report.views.push({name:v.name,size:v.size,focus:v.focus,end,result:v.result});}
 await browser.close();report.finished=new Date().toISOString();report.status=failed||report.errors.length?'FAIL':'PASS';await writeFile(`${out}/timeline.json`,JSON.stringify(report,null,2));console.log(report.status);if(failed)process.exitCode=1;
}
function flush(){return new Date().toISOString()}
