import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';
import { writeFile } from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4196';
const report={base,status:'RUNNING',checks:[],failures:[]};
const check=(name,pass)=>{report.checks.push({name,pass:!!pass});if(!pass)throw Error(name)};
const browser=await chromium.launch({headless:true});let page;
try{
 const context=await browser.newContext({viewport:{width:390,height:844},storageState:`/tmp/farmtact-v15-scenarios-${new URL(base).port}.json`});
 page=await context.newPage();const mutations=[];page.on('request',r=>{if(r.method()==='POST')mutations.push(r.url())});
 const click=name=>page.getByRole('button',{name,exact:true}).filter({visible:true}).click();
 const get=path=>page.evaluate(async path=>{const r=await fetch('/api/v1'+path);if(!r.ok)throw Error('GET '+r.status);return r.json()},path);
 await page.goto(base);await page.locator('.ic-shell').waitFor();for(let i=0;i<6&&!await page.getByRole('button',{name:'More',exact:true}).isVisible();i++)await click('Back');await click('More');await click('Open tool');await click('Open');
 await page.getByRole('heading',{name:'Objectives and all demand',exact:true}).waitFor();
 const id=await page.locator('.integrated-tool__card').getAttribute('data-session-id'),session=await get('/planning-sessions/'+id);
 const facts=await page.locator('.integrated-tool__card').innerText();
 const total=session.farm.orders.reduce((n,o)=>n+Number(o.quantity_kg)-Number(o.cancelled_kg||0),0);
 check('Objectives show full confirmed total, tentative distinction and server horizon',facts.includes(total.toLocaleString(undefined,{maximumFractionDigits:3})+' kg')&&facts.includes('Tentative demand (separate from confirmed orders)')&&facts.includes(session.farm.horizon_days+' days'));
 await click('Review demand changes');await page.getByLabel('Planning assumptions JSON').waitFor();
 const draft={tentative_orders:[],future_demand:[],seasonal:[],order_changes:[],reservations:[],capacity:{cash_sgd:-1}};
 await page.getByLabel('Planning assumptions JSON').fill(JSON.stringify(draft));await click('Review');await click('Create proposal');await page.getByRole('heading',{name:'Proposal and recalculation',exact:true}).waitFor();await click('Apply & recalculate');await page.getByRole('alert').waitFor();
 check('Server rejects invalid capacity on apply and retains its draft without a revision change',(await page.locator('.integrated-tool__card').innerText()).includes('-1')&&(await get('/planning-sessions/'+id)).revision===session.revision);
 await click('Review assumptions');const order=session.farm.orders[0],grow=session.tactical_context.grow_space,day=order.due_date;
 const valid={...draft,capacity:{cash_sgd:Number(session.farm.resources.cash_sgd),nursery_sites:session.farm.resources.nursery_sites,labour_hours_per_week:Number(session.farm.resources.labour_hours_per_week)},tentative_orders:[{order_id:'v15-card-tentative',crop_id:order.crop_id,due_date:day,quantity_kg:1,status:'tentative'}],future_demand:[{crop_id:order.crop_id,start_date:day,end_date:day,percent:100}],seasonal:[{crop_id:order.crop_id,system:'sheltered_hydroponic',start_date:day,end_date:day,yield_percent:100,delay_days:0,reason:'Review existing baseline',provenance:'synthetic_assumption'}],order_changes:[{operation:'amend',order_id:order.id,quantity_kg:Number(order.quantity_kg)}],reservations:[{bed_id:grow.id,...grow.reservation_window}]};
 await page.getByLabel('Planning assumptions JSON').fill(JSON.stringify(valid));
 await click('Review');await click('Create proposal');await page.getByRole('heading',{name:'Proposal and recalculation',exact:true}).waitFor();
 const proposalId=await page.locator('.integrated-tool__card').getAttribute('data-entity-id'),workflow=await get('/farm-workflow'),proposal=workflow.proposals.find(p=>p.id===proposalId);
 check('Reviewed resource and demand proposal persists all supported assumption groups without applying',JSON.stringify(proposal?.changes?.[0]?.assumptions?.tentative_orders).includes('v15-card-tentative')&&proposal?.status==='draft'&&(await get('/planning-sessions/'+id)).revision===session.revision);
 await click('Back');await click('Back');for(let i=0;i<4;i++)await page.getByRole('button',{name:/Next/}).filter({visible:true}).click();await click('Open tool');await click('Open');
 const plans=(await get('/planning-sessions')).sessions.sort((a,b)=>Date.parse(b.updated_at)-Date.parse(a.updated_at)||b.id.localeCompare(a.id));
 const list=await page.locator('.integrated-tool__card').innerText();check('History lists newest plan with status, date and provenance',list.includes(plans[0].id)&&list.includes(plans[0].status)&&list.includes(plans[0].input_hash)&&list.includes('effective date'));
 await click('Read-only replay');await click('New attempt');await page.getByRole('heading',{name:'Review a new planning attempt',exact:true}).waitFor();
 check('Historical new attempt explicitly reviews current imported farm',(await page.locator('.integrated-tool__card').innerText()).includes('current imported farm'));
 const before=await get('/planning-sessions/'+plans[0].id);await click('Create new attempt');await page.getByRole('heading',{name:'Read-only saved replay',exact:true}).waitFor();
 const newId=await page.locator('.integrated-tool__card').getAttribute('data-entity-id');check('History new attempt creates a separate session and preserves saved replay',newId!==before.id&&JSON.stringify(await get('/planning-sessions/'+before.id))===JSON.stringify(before));
 check('Focused planning and history workflow makes no provider submission',mutations.every(p=>!p.includes('/messages')&&!p.includes('/review')&&!p.includes('/actual-discussion')));
}catch(e){report.failures.push(String(e));if(page)report.last_card=await page.locator('.ic-shell').innerText().catch(()=>null);process.exitCode=1}
finally{report.status=report.failures.length?'FAIL':'PASS';await browser.close();await writeFile('reports/v15/plan-history-gaps-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2))}
