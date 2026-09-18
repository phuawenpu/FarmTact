import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const base=(process.env.BASE_URL||'http://127.0.0.1:4199').replace(/\/$/,'');
const output=resolve(process.env.REPORT_PATH||'reports/v19/council-cards.json');
const report={status:'RUNNING',checks:[],mutations:[],provider_requests:[],failures:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)throw Error(`${name}: ${JSON.stringify(detail)}`)};
let browser;
try {
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
  const page=await context.newPage();
  page.on('request',request=>{if(request.method()!=='POST')return;const path=new URL(request.url()).pathname;report.mutations.push(path);if(/\/review$|\/conversations(?:\/|$)|\/invite$|\/council$/.test(path))report.provider_requests.push(path)});
  await page.goto(`${base}/play`,{waitUntil:'domcontentloaded'});
  await page.locator('.ic-shell').waitFor();
  if(await page.getByRole('button',{name:'Skip demonstration',exact:true}).count())await page.getByRole('button',{name:'Skip demonstration',exact:true}).click();
  const card=page.locator('.ic-card');
  const sessionId=await card.getAttribute('data-session-id');
  check('ordinary workflow session is bound to the opening card',Boolean(sessionId),sessionId);
  let session=await page.evaluate(async id=>(await fetch(`/api/v1/planning-sessions/${id}`)).json(),sessionId);
  if(!session.result?.strategies?.length){
    const response=await page.evaluate(async ({id,revision})=>{const r=await fetch(`/api/v1/planning-sessions/${id}/calculate`,{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({revision})});return {status:r.status,body:await r.json()};},{id:sessionId,revision:session.revision});
    check('local calculation request is accepted',response.status===202,{status:response.status});
    const deadline=Date.now()+180000;
    do { await page.waitForTimeout(700); session=await page.evaluate(async id=>(await fetch(`/api/v1/planning-sessions/${id}`)).json(),sessionId); } while(['QUEUED','RUNNING'].includes(session.status)&&Date.now()<deadline);
    check('local calculation completes',session.status==='COMPLETED',session.status);
    await page.reload({waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();
    if(await page.getByRole('button',{name:'Skip demonstration',exact:true}).count())await page.getByRole('button',{name:'Skip demonstration',exact:true}).click();
  }
  for(let i=0;i<8&&!await page.getByText('Preview—not saved',{exact:true}).count();i++){
    const next=page.getByRole('button',{name:'Next →',exact:true});if(await next.isDisabled())break;await next.click();
  }
  await page.getByText('Preview—not saved',{exact:true}).waitFor();
  const binding=JSON.parse(await card.getAttribute('data-council-binding')||'null');
  check('calculated strategy exposes an immutable Council binding',binding?.sessionId===sessionId&&binding?.resultId&&binding?.revision===session.revision&&binding.providerSubmissionRequired===true,binding);
  check('calculated strategy presents a layered decision brief',await page.locator('.ic-decision-brief').count()===1&&await page.getByText('Decision details',{exact:true}).count()===1,await card.innerText());
  check('strategy preserves the three-action card row',JSON.stringify(await page.locator('.ic-keys button').allTextContents())===JSON.stringify(['Explain','Ask Council about this plan','More']),await page.locator('.ic-keys button').allTextContents());
  await page.screenshot({path:'reports/v19/council-decision-brief-390.png',fullPage:true});
  const beforeBrowse=report.mutations.length;
  await page.getByRole('button',{name:'Explain',exact:true}).click();await page.getByRole('heading',{name:'What this means',exact:true}).waitFor();await page.getByRole('button',{name:'Back',exact:true}).click();
  await page.getByRole('button',{name:'More',exact:true}).click();await page.getByRole('button',{name:'Back',exact:true}).click();
  check('brief reading and tool browsing make no provider request',report.mutations.length===beforeBrowse&&report.provider_requests.length===0,{mutations:report.mutations,provider:report.provider_requests});
  await page.getByRole('button',{name:'Ask Council about this plan',exact:true}).click();
  await page.getByRole('heading',{name:'Review the frozen alternatives',exact:true}).waitFor({timeout:30000});
  check('Council opens only through its explicit primary action',report.provider_requests.filter(path=>/\/review$/.test(path)).length===1,report.provider_requests);
  const councilActions=JSON.parse(await page.locator('.ik-card').getAttribute('data-card-actions')||'[]');
  check('Council card retains a back action and advisory review action',councilActions.some(action=>action.label==='Back')&&councilActions.some(action=>action.label==='Review with Council'),councilActions);
  await context.close();report.status='PASS';
} catch(error) { report.status='FAIL';report.failures.push(error instanceof Error?error.stack:String(error));process.exitCode=1; }
finally { if(browser)await browser.close();await mkdir(resolve(output,'..'),{recursive:true});await writeFile(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report)); }
