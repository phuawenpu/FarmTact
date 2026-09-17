import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';
import { writeFile } from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4196',report={base,checks:[],failures:[]};
const check=(name,pass)=>{report.checks.push({name,pass:!!pass});if(!pass)throw Error(name)};
const browser=await chromium.launch({headless:true});let page;
try{
 const context=await browser.newContext({viewport:{width:390,height:844},storageState:'/tmp/farmtact-v15-cards-storage.json'});page=await context.newPage();const posts=[];page.on('request',r=>{if(r.method()==='POST')posts.push(new URL(r.url()).pathname)});
 const get=path=>page.evaluate(async path=>{const r=await fetch('/api/v1'+path);if(!r.ok)throw Error('GET '+r.status);return r.json()},path),click=name=>page.getByRole('button',{name,exact:true}).filter({visible:true}).click();
 await page.goto(base);await page.locator('.ic-shell').waitFor();for(let i=0;i<8&&!await page.getByRole('button',{name:'More',exact:true}).isVisible();i++)await click('Back');await click('More');await click('Open tool');
 const sessions=await get('/planning-sessions'),before=sessions.sessions.find(s=>s.simulation?.days_executed>0);check('Existing accepted plan has real recorded execution prerequisite',before?.simulation?.completed_task_ids?.length>0&&Object.keys(before.simulation.harvest_lot_origins||{}).length>0);
 report.session_id=before.id;report.world_id=before.simulation.id;
 await click('Next');await click('Next');await click('Open');await page.getByText("Import saved settings", {exact:true}).click();await page.getByLabel('Planning assumptions JSON').fill(JSON.stringify({tentative_orders:[],future_demand:[],seasonal:[],order_changes:[],reservations:[],...before.assumptions}));await click('Review');await click('Create proposal');await page.getByRole('heading',{name:'Proposal and recalculation',exact:true}).waitFor();
 const proposalId=await page.locator('.integrated-tool__card').getAttribute('data-entity-id');await click('Apply & recalculate');
 let calculated;for(let i=0;i<150;i++){calculated=await get('/planning-sessions/'+before.id);if(calculated.status==='COMPLETED'&&calculated.result_id!==before.result_id)break;await page.waitForTimeout(2000)}
 check('Future-only local recalculation saves a new result',calculated.status==='COMPLETED'&&calculated.result_id!==before.result_id);
 await click('Back');await click('Back');await page.getByRole('button',{name:/Next/}).filter({visible:true}).click();await click('Open tool');for(let i=0;i<5;i++)await page.getByRole('button',{name:/Next/}).filter({visible:true}).click();await click('Open');
 for(let i=0;i<32&&!(await page.locator('.ir-card').innerText()).includes(proposalId);i++)await page.getByRole('button',{name:/Next/}).filter({visible:true}).click();check('Recovery approval card binds recalculated proposal',(await page.locator('.ir-card').innerText()).includes(proposalId));await click('Review approval');
 const approval=page.getByRole('button',{name:'Approve revision & create tasks',exact:true});check('Server exposes eligible current future-only approval',await approval.isEnabled());await approval.click();await approval.waitFor({state:'detached'});
 const after=await get('/planning-sessions/'+before.id),world=after.simulation;
 check('Approved replan retains simulation identity, clock and completed tasks',world.id===before.simulation.id&&world.clock_date===before.simulation.clock_date&&JSON.stringify(world.completed_task_ids)===JSON.stringify(before.simulation.completed_task_ids));
 check('Approved replan preserves inventory and harvest lot origins',JSON.stringify(world.inventory)===JSON.stringify(before.simulation.inventory)&&Object.entries(before.simulation.harvest_lot_origins).every(([lot,allocation])=>world.harvest_lot_origins[lot]===allocation));
 check('Replan does not change recorded physical totals',JSON.stringify(world.totals)===JSON.stringify(before.simulation.totals));
 const saved=await get(`/planning-sessions/${before.id}/results/${before.result_id}`);check('Executed source result remains replayable',saved.result_id===before.result_id&&saved.replay===true);
 check('Future-only card workflow submits no provider request',posts.every(path=>!path.endsWith('/review')&&!path.includes('/messages')&&!path.includes('/council')));report.mutations=posts;
}catch(e){report.failures.push(String(e));if(page)report.last_card=await page.locator('.ic-shell').innerText().catch(()=>null);process.exitCode=1}
finally{report.status=report.failures.length?'FAIL':'PASS';await browser.close();await writeFile('reports/v15/simulation-replan-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2))}
