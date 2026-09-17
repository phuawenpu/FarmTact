import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4192';
const report={base,checks:[],failures:[],prerequisites:[]};
const check=(name,ok)=>{report.checks.push({name,pass:!!ok});if(!ok)throw Error(name)};
const browser=await chromium.launch({headless:true});let page;
try{
 const context=await browser.newContext({viewport:{width:430,height:900}});page=await context.newPage();
 await page.goto(base);await page.locator('.ic-shell').waitFor();
 const click=name=>page.getByRole('button',{name,exact:true}).click();
 const api=(path,body)=>page.evaluate(async({path,body})=>{const r=await fetch('/api/v1'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()}:{},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error(await r.text());return r.json()},{path,body});
 const poll=async(path,predicate)=>{for(let i=0;i<180;i++){const v=await api(path);if(predicate(v))return v;await page.waitForTimeout(500)}throw Error('Terminal state timeout: '+path)};
 // Real local numerical prerequisite lets the Waste Rescue UI inspect dated inventory.
 let session=(await api('/planning-sessions')).sessions.find(s=>s.workflow);
 if(!session.result){await api('/planning-sessions/'+session.id+'/calculate',{revision:session.revision});session=await poll('/planning-sessions/'+session.id,s=>s.result?.strategies?.length)}
 report.prerequisites.push('Calculated ordinary workflow through existing local API before opening experiments.');
 await click('More');for(let i=0;i<3;i++)await click('Next →');await click('Open tool');
 await click('Open');await click('Create scenario');await page.getByLabel('Name',{exact:true}).fill('V15 parent branch');
 await click('Review');const created=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/v1/scenarios');await click('Create frozen branch');const parent=await(await created).json();
 await click('Run locally');const done=await poll('/scenarios/'+parent.id,s=>s.status==='COMPLETED');check('parent scenario completes with frozen result',!!done.result);
 await click('Scenario actions');await click('Next');await click('Continue this branch');
 await page.getByLabel('Name',{exact:true}).fill('V15 child branch');await page.getByLabel('yield percent',{exact:true}).fill('95');await click('Review');
 const childResponse=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/api/v1/scenarios');await click('Create frozen branch');const child=await(await childResponse).json();check('continuation binds explicit parent identity',child.parent_scenario_id===parent.id);
 await click('Run locally');await poll('/scenarios/'+child.id,s=>s.status==='COMPLETED');
 await click('Scenario actions');await page.getByLabel('Compare with').selectOption(parent.id);const compared=page.waitForResponse(r=>new URL(r.url()).pathname.includes('/scenarios/compare'));await click('Compare compatible roots');const comparison=await(await compared).json();
 check('compatible scenario comparison completes inside card',await page.getByRole('heading',{name:'Recorded comparison',exact:true}).isVisible());check('comparison contains frozen branch identities',JSON.stringify(comparison).includes(parent.id)&&JSON.stringify(comparison).includes(child.id));
 // Return through the exact card trail; no new shell state or provider action.
 for(let i=0;i<12&&!await page.getByRole('heading',{name:'Scenarios & quests',exact:true}).isVisible().catch(()=>false);i++)await click('Back');
 await page.getByRole('heading',{name:'Scenarios & quests',exact:true}).waitFor();for(let i=0;i<3;i++)await click('Next');await click('Open');
 await page.getByLabel('Projected strategy').waitFor();const surplus=session.result.strategies.find(s=>Number(s.metrics.closing_stock_kg)>0);check('real calculation supplies dated surplus prerequisite',!!surplus);
 await page.getByLabel('Projected strategy').selectOption(surplus.id);
 const rescueResponse=page.waitForResponse(r=>new URL(r.url()).pathname.endsWith('/farm-workflow/waste-rescue'));await click('Compare rescue outcomes');const rescue=await(await rescueResponse).json();
 check('Waste Rescue binds selected result and strategy',rescue.binding?.strategy_id===surplus.id&&rescue.binding?.result_id===session.result_id);
 check('Waste Rescue compares all supported local options',rescue.scenarios?.length===3&&rescue.surplus_lots?.length>0);
 check('local experiments preserve main planning result', (await api('/planning-sessions/'+session.id)).result_id===session.result_id);
 report.status='PASS';
}catch(e){report.status='FAIL';report.failures.push(String(e.stack||e));if(page)report.page=(await page.locator('body').innerText()).slice(-3500);process.exitCode=1}
finally{await browser.close();await writeFile('reports/v15/scenarios-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2))}
