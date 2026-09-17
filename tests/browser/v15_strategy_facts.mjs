import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';
import { writeFile } from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4196',report={base,checks:[],failures:[]};
const check=(name,pass)=>{report.checks.push({name,pass:!!pass});if(!pass)throw Error(name)};
const browser=await chromium.launch({headless:true});
try{
 const context=await browser.newContext({viewport:{width:390,height:844},storageState:`/tmp/farmtact-v15-scenarios-${new URL(base).port}.json`});const page=await context.newPage();let writes=0;page.on('request',r=>{if(r.method()==='POST')writes++});
 const click=name=>page.getByRole('button',{name,exact:true}).filter({visible:true}).click();
 await page.goto(base);await page.locator('.ic-shell').waitFor();
 for(let i=0;i<8&&!await page.getByRole('button',{name:'More',exact:true}).isVisible();i++){if(await page.getByRole('button',{name:'Back',exact:true}).isVisible())await click('Back');else break}
 await click('More');await click('Open tool');await click('Next');await click('Open');await page.getByLabel('Compare strategy').waitFor();
 const id=await page.locator('.integrated-tool__card').getAttribute('data-session-id');const session=await page.evaluate(async id=>(await fetch('/api/v1/planning-sessions/'+id)).json(),id);
 for(const strategy of session.result.strategies){
  await page.getByLabel('Compare strategy').selectOption(strategy.id);const card=page.locator('.integrated-tool__card'),text=await card.innerText();
  check(strategy.name+' presents every server metric and projected preview label',Object.keys(strategy.metrics).every(key=>text.includes(key.replaceAll('_',' ')))&&text.includes('Preview—not saved'));
  check(strategy.name+' presents dated bed allocations and crop identities',strategy.allocations.every(a=>[a.bed_id,a.crop_id,a.transplant_date,a.harvest_date].filter(Boolean).every(value=>text.includes(String(value)))));
  check(strategy.name+' keeps the same frozen planning result binding',(await card.getAttribute('data-result-id'))===session.result_id);
 }
 check('All three supported strategies are inspectable',session.result.strategies.length===3&&new Set(session.result.strategies.map(s=>s.name)).size===3);
 await click('Back');await click('Back');
 await page.route('**/api/v1/planning-sessions',async route=>{const response=await route.fetch(),body=await response.json();const selected=body.sessions.find(s=>s.id===id);selected.result.strategies[0].status='INFEASIBLE';selected.result.strategies[0].violations=['Controlled fixture: insufficient nursery capacity'];await route.fulfill({response,json:body})});
 await click('Open tool');await click('Next');await click('Open');await page.getByLabel('Compare strategy').selectOption(session.result.strategies[0].id);
 const infeasibleText=await page.locator('.integrated-tool__card').innerText();
 check('Labelled infeasible-result fixture remains inspectable with explicit status and constraint reason',infeasibleText.includes('INFEASIBLE')&&infeasibleText.includes('Controlled fixture: insufficient nursery capacity')&&infeasibleText.includes('Only a feasible current result can be approved'));
 check('Comparing all schedules creates no farm mutation or inference',writes===0);
}catch(e){report.failures.push(String(e));process.exitCode=1}
finally{report.status=report.failures.length?'FAIL':'PASS';await browser.close();await writeFile('reports/v15/strategy-facts-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2))}
