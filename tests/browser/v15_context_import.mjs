import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';
import { writeFile } from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4196',report={base,checks:[],failures:[]};
const check=(name,pass)=>{report.checks.push({name,pass:!!pass});if(!pass)throw Error(name)};
const browser=await chromium.launch({headless:true});let page;
try{
 const context=await browser.newContext({viewport:{width:390,height:844},storageState:`/tmp/farmtact-v15-scenarios-${new URL(base).port}.json`});page=await context.newPage();let writes=0;page.on('request',r=>{if(r.method()==='POST')writes++});
 const click=name=>page.getByRole('button',{name,exact:true}).filter({visible:true}).click();
 await page.goto(base);await page.locator('.ic-shell').waitFor();for(let i=0;i<8&&!await page.getByRole('button',{name:'More',exact:true}).isVisible();i++)await click('Back');await click('More');await page.getByRole('button',{name:/Next/}).filter({visible:true}).click();await click('Open tool');
 for(let i=0;i<4;i++)await page.getByRole('button',{name:/Next/}).filter({visible:true}).click();await click('Open');await page.getByRole('button',{name:'Compare Waste Rescue',exact:true}).waitFor();
 const inventory=await page.locator('.ir-card').getAttribute('data-entity-id');await page.getByRole('button',{name:'Compare Waste Rescue',exact:true}).focus();const scroll=await page.evaluate(()=>window.scrollY);await click('Compare Waste Rescue');await page.getByRole('heading',{name:'Waste Rescue',exact:true}).waitFor();
 check('Inventory shortcut opens the actual Waste Rescue card directly',await page.getByRole('button',{name:'Compare rescue outcomes',exact:true}).isVisible());
 await click('Back');await page.getByRole('button',{name:'Compare Waste Rescue',exact:true}).waitFor();await page.waitForTimeout(100);
 check('Waste Rescue Back restores inventory identity, focus and position',(await page.locator('.ir-card').getAttribute('data-entity-id'))===inventory&&await page.getByRole('button',{name:'Compare Waste Rescue',exact:true}).evaluate(e=>e===document.activeElement)&&Math.abs(await page.evaluate(()=>window.scrollY)-scroll)<3);
 await click('Back');for(let i=0;i<4;i++)await page.getByRole('button',{name:/Previous/}).filter({visible:true}).click();await click('Open');await click('Review farm JSON');
 const farm=await page.evaluate(async()=>(await fetch('/api/v1/farms/demo-farm/snapshot')).json()),incoming={...farm,name:'Reviewed replacement; not saved'};
 await page.getByLabel('Farm JSON',{exact:true}).fill(JSON.stringify(incoming));await click('Review parsed farm');await page.getByRole('heading',{name:'Review farm import',exact:true}).waitFor();const text=await page.locator('.ir-card').innerText();
 check('Import review shows both current and incoming identities and cutoff',text.includes(farm.name)&&text.includes(incoming.name)&&text.includes(farm.cutoff)&&text.includes('Current imported farm')&&text.includes('Incoming farm'));
 check('Import review states counts, validation boundary and preserved history',['orders','beds','batches','inventory'].every(k=>text.toLowerCase().includes(k))&&text.includes('Full schema, crop, date and resource validation occurs on submit')&&text.includes('Existing plans, tasks and events remain'));
 await click('Back');const after=await page.evaluate(async()=>(await fetch('/api/v1/farms/demo-farm/snapshot')).json());check('Cancelling the reviewed transition preserves the exact current farm',JSON.stringify(after)===JSON.stringify(farm));
 check('Context navigation and import preview perform zero writes or inference',writes===0);
}catch(e){report.failures.push(String(e));if(page)report.last_card=await page.locator('.ic-shell').innerText().catch(()=>null);process.exitCode=1}
finally{report.status=report.failures.length?'FAIL':'PASS';await browser.close();await writeFile('reports/v15/context-import-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2))}
