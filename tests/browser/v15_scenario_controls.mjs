// Explicit transport fixtures exercise durable queued/cancel/retry/error cards.
// Numerical/domain behavior is covered separately by the real V15 scenario suite
// and the full PostgreSQL regression; no provider or real farm mutation is sent.
import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4196';
const report={base,fixture:'Controlled scenario transport states, not real numerical results',checks:[],failures:[]};
const check=(name,ok)=>{report.checks.push({name,pass:!!ok});if(!ok)throw Error(name)};
const browser=await chromium.launch({headless:true});let page;
try{
 const context=await browser.newContext({viewport:{width:360,height:850}});page=await context.newPage();
 let scenario={id:'v15-controlled-queued',name:'Controlled queued scenario',status:'RUNNING',run_key:'v15-original-run',quest_id:'late_harvest',controls:{delay_days:1,yield_percent:100,demand_percent:100,labour_percent:100,cash_percent:100,batch_id:'B1'},input_hash:'controlled-frozen-input',attempt_count:1};
 const calls=[];
 await page.route('**/api/v1/scenarios**',async route=>{const r=route.request(),u=new URL(r.url());if(r.method()==='POST')calls.push({path:u.pathname,key:r.headers()['idempotency-key']});let payload;
  if(u.pathname.endsWith('/compare'))return route.fulfill({status:409,json:{detail:'Branches must share the same frozen baseline'}});
  if(u.pathname.endsWith('/cancel'))scenario={...scenario,status:'CANCELLED'};
  if(u.pathname.endsWith('/retry'))scenario={...scenario,status:'QUEUED',attempt_count:2};
  if(u.pathname==='/api/v1/scenarios')payload={scenarios:[scenario,{...scenario,id:'other-root',name:'Unrelated root'}]};else payload=scenario;
  await route.fulfill({status:200,json:payload});
 });
 await page.route('**/api/v1/quests/late_harvest/inspect',route=>{calls.push({path:new URL(route.request().url()).pathname,body:route.request().postDataJSON()});return route.fulfill({status:200,json:{id:'late_harvest',status:'inspected',outcome:'controlled recorded outcome',scenario_id:scenario.id}})});
 await page.goto(base);await page.locator('.ic-shell').waitFor();const click=name=>page.getByRole('button',{name,exact:true}).click();
 await click('More');for(let i=0;i<3;i++)await click('Next →');await click('Open tool');await click('Open');await click('Inspect scenario');
 check('queued scenario remains inspectable with refresh',await page.getByRole('button',{name:'Refresh result',exact:true}).isVisible());
 await click('Scenario actions');await click('Next');await click('Next');await click('Cancel calculation');await page.getByRole('button',{name:'Scenario actions',exact:true}).waitFor();
 check('explicit cancellation sends one bound mutation',calls.filter(c=>c.path.endsWith('/cancel')).length===1);
 await click('Scenario actions');for(let i=0;i<3;i++)await click('Next');await click('Retry interrupted calculation');await page.getByRole('button',{name:'Scenario actions',exact:true}).waitFor();
 check('retry retains original run idempotency key',calls.find(c=>c.path.endsWith('/retry'))?.key==='v15-original-run');
 await click('Scenario actions');for(let i=0;i<4;i++)await click('Next');await click('Inspect quest outcome');await page.getByRole('heading',{name:'Recorded comparison',exact:true}).waitFor();
 check('quest inspection binds exact frozen scenario',calls.find(c=>c.path.includes('/quests/'))?.body.scenario_id===scenario.id);
 await click('Back');for(let i=0;i<4;i++)await click('Previous');await page.getByLabel('Compare with').selectOption('other-root');await click('Compare compatible roots');
 await page.getByRole('alert').waitFor();check('incompatible comparison retains card with server reason',await page.getByRole('alert').textContent()==='Branches must share the same frozen baseline');
 check('read-only incompatible comparison adds no mutation',calls.length===3);
 report.status='PASS';
}catch(e){report.status='FAIL';report.failures.push(String(e.stack||e));if(page)report.page=(await page.locator('body').innerText()).slice(-2500);process.exitCode=1}
finally{await browser.close();await writeFile('reports/v15/scenario-controls-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2))}
