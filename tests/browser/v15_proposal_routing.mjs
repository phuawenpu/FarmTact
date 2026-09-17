import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';

const root=resolve(new URL('../..',import.meta.url).pathname),base=(process.env.BASE_URL||'http://127.0.0.1:4196').replace(/\/$/,'');
const report={status:'RUNNING',base,checks:[],failures:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)throw Error(`${name}: ${JSON.stringify(detail)}`)};
async function open(storageState){const context=await browser.newContext({viewport:{width:390,height:844},storageState});const page=await context.newPage();await page.goto(`${base}/play`,{waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();return {context,page}}
async function mission(page){for(let i=0;i<18;i++){if(await page.getByRole('button',{name:'More',exact:true}).isVisible().catch(()=>false))return;const back=page.getByRole('button',{name:'Back',exact:true}).filter({visible:true}).first();if(!await back.count())break;await back.click()}throw Error('Mission did not restore from saved navigation')}
async function state(page){return page.evaluate(async()=>({sessions:await fetch('/api/v1/planning-sessions').then(r=>r.json()),workflow:await fetch('/api/v1/farm-workflow').then(r=>r.json())}))}

let browser;
try{
  browser=await chromium.launch({headless:true});
  const mixed=await open('/tmp/farmtact-v15-scenarios-4196.json'),writes=[];
  mixed.page.on('request',request=>{if(!['GET','HEAD','OPTIONS'].includes(request.method()))writes.push(`${request.method()} ${new URL(request.url()).pathname}`)});
  const mixedState=await state(mixed.page),sessionId=mixedState.sessions.sessions[0]?.id||mixedState.sessions.sessions.at(-1)?.id;
  const mixedDrafts=mixedState.workflow.proposals.filter(item=>item.status==='draft'&&item.changes?.[0]?.assumptions?.capacity&&item.changes[0].assumptions.reservations?.length);
  check('fixture contains a mixed general draft with a reservation',mixedDrafts.length>0,mixedDrafts.map(item=>item.id));
  await mission(mixed.page);
  check('mixed draft does not force reservation review',!await mixed.page.getByText('Review before applying',{exact:true}).count()&&!/Reserve bed-/i.test(await mixed.page.locator('.ic-card').innerText()),await mixed.page.locator('.ic-card').innerText());
  const before=writes.length;await mixed.page.getByRole('button',{name:'More',exact:true}).click();await mixed.page.getByRole('button',{name:'Next →',exact:true}).click();await mixed.page.getByRole('button',{name:'Open tool',exact:true}).click();await mixed.page.getByRole('button',{name:'Back',exact:true}).filter({visible:true}).first().click();
  check('browsing tools with a mixed draft sends no mutation',writes.length===before,{sessionId,writes});await mixed.context.close();

  const saved=await open('/tmp/farmtact-v15-cards-storage.json');await mission(saved.page);const savedState=await state(saved.page),approved=savedState.workflow.proposals.find(item=>item.status==='approved'&&item.inverse_changes?.[0]?.assumptions&&Object.keys(item.inverse_changes[0].assumptions).length>0);
  check('fixture contains a frozen applied reservation proposal',Boolean(approved),approved?.id);
  for(let i=0;i<14&&!/is reserved/i.test(await saved.page.locator('.ic-card h1').innerText().catch(()=>''));i++)await saved.page.getByRole('button',{name:'Next →',exact:true}).click();
  const cardText=await saved.page.locator('.ic-card').innerText();
  check('applied reservation remains recognized from frozen before state',/is reserved/i.test(cardText)&&/saved recalculation includes this reservation/i.test(cardText),cardText);
  check('saved reservation barrier remains visible',await saved.page.locator('.ic-reservation-barrier').isVisible(),await saved.page.locator('.ic-scene').innerText());await saved.context.close();
  report.status='PASS';
}catch(error){report.status='FAIL';report.failures.push(error instanceof Error?error.stack:String(error));process.exitCode=1}finally{await browser?.close();await mkdir(resolve(root,'reports/v15'),{recursive:true});await writeFile(resolve(root,'reports/v15/proposal-routing-browser.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2))}
