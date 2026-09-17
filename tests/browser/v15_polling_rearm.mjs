import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';
import {writeFile} from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4196',id=process.env.SESSION_ID;
if(!id||!process.env.STORAGE_STATE)throw Error('SESSION_ID and private STORAGE_STATE are required');
const report={status:'RUNNING',scope:'Read-only labelled RUNNING status overlay on a saved real session; verifies polling rearm after same-job tool return, not a new numerical job.',checks:[],failures:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)throw Error(name)};
let browser;
try{
 browser=await chromium.launch({headless:true});const context=await browser.newContext({storageState:process.env.STORAGE_STATE,viewport:{width:390,height:844}});
 await context.addInitScript(id=>{localStorage.setItem('farmtact:v15:planning-session',id);localStorage.removeItem(`farmtact:v15:integrated-cards-navigation:${id}`)},id);
 const page=await context.newPage();page.setDefaultTimeout(30000);let released=false,reads=0;const writes=[];
 page.on('request',r=>{if(r.method()!=='GET')writes.push(new URL(r.url()).pathname)});
 await page.route(`**/api/v1/planning-sessions/${id}`,async route=>{const response=await route.fetch(),body=await response.json();reads++;if(!released){body.job.status='RUNNING';body.job.stage='Controlled running receipt replay'}await route.fulfill({response,json:body})});
 await page.goto(`${base}/play`);await page.getByRole('button',{name:'Controlled running receipt replay',exact:true}).waitFor();
 check('running receipt renders before navigation',await page.locator('.ic-keys .is-primary').isDisabled());
 const click=name=>page.getByRole('button',{name,exact:true}).filter({visible:true}).first().click();
 await click('More');await click('Open tool');await page.locator('.integrated-tool').waitFor();await click('Back');await page.locator('.ic-path').waitFor();await click('Back');
 await page.getByRole('button',{name:'Controlled running receipt replay',exact:true}).waitFor();const before=reads;
 check('same running job survives completed tool load',await page.locator('.ic-card').getAttribute('data-session-id')===id&&await page.locator('.ic-keys .is-primary').isDisabled(),{reads:before});
 released=true;
 await page.waitForFunction(()=>{const b=document.querySelector('.ic-keys .is-primary');return b&&!b.disabled&&!b.textContent.includes('Controlled running')},null,{timeout:15000});
 check('a fresh poll resumes after tool return and reaches terminal state',reads>before&&await page.locator('.ic-card').getAttribute('data-session-id')===id,{before,after:reads});
 check('status overlay makes no writes or provider submissions',writes.length===0,writes);report.status='PASS';
}catch(e){report.status='FAIL';report.failures.push(String(e));process.exitCode=1}finally{await browser?.close();await writeFile(process.env.REPORT_PATH||'/tmp/farmtact-v15-poll-rearm.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2))}
