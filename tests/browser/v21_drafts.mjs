import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { runDraftChecks } from './v21_draft_checks.mjs';
const root=process.cwd();
const {chromium}=await import(pathToFileURL(resolve(root,'apps/web/node_modules/@playwright/test/index.mjs')));
const base=process.env.BASE_URL||'http://127.0.0.1:4199';
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('Draft UI runner is local-only');
const artifacts=process.env.ARTIFACT_DIR||'/tmp/v21-drafts';
const report={status:'RUNNING',test_kind:'local calculation + intercepted UI draft fixtures',backend_claims:'Real local creation/calculation only. Proposal and adviser acceptance/failure are intercepted UI fixtures, not backend acceptance evidence.',checks:[],failures:[],page_errors:[],real_backend_writes:[],blocked_writes:[],client_provider_requests:[],fixture_ui:null,draft_scope:'React memory within mounted V12 workspace; no reload/navigation persistence'};
const check=(name,pass,detail)=>{report.checks.push({name,pass:!!pass,detail});console.log(`${pass?'PASS':'FAIL'} ${name}`);if(!pass)throw Error(name);};
let browser,page;
try{
 await mkdir(artifacts,{recursive:true});
 browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});
 context.setDefaultTimeout(30000);
 page=await context.newPage();
 let session;
 page.on('pageerror',error=>report.page_errors.push(error.message));
 page.on('request',request=>{if(request.method()==='POST'&&/\/conversations(?:\/|$)|\/planning-sessions\/[^/]+\/review$/.test(new URL(request.url()).pathname))report.client_provider_requests.push(new URL(request.url()).pathname);});
 page.on('response',async response=>{if(response.ok()&&/\/planning-sessions(?:\/[^/?]+)?$/.test(new URL(response.url()).pathname)){try{const body=await response.json();if(body.id&&body.farm)session=body;}catch{}}});
 // This guard remains below the fixture route: no unhandled mutation/provider call
 // can escape to a backend. Only the initial ordinary session/calculation is real.
 await page.route('**/api/**',async route=>{
  const request=route.request(),method=request.method(),path=new URL(request.url()).pathname;
  if(method==='GET'||method==='HEAD')return route.fallback();
  if(method==='POST'&&(/\/planning-sessions$/.test(path)||/\/planning-sessions\/[^/]+\/calculate$/.test(path))){report.real_backend_writes.push({method,path});return route.fallback();}
  report.blocked_writes.push({method,path});
  return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Draft UI test blocked an unhandled mutation'})});
 });
 await page.goto(base+(process.env.APP_PATH||'/'),{waitUntil:'domcontentloaded'});
 await page.getByRole('heading',{name:/See the farm/}).waitFor();
 check('restored V12 experience is active',await page.locator(`[data-experience="v12"][data-edition="${process.env.EXPECTED_EDITION||'v21'}"]`).count()===1);
 await page.getByRole('button',{name:/Calculate options/}).click();
 await page.waitForFunction(()=>document.querySelectorAll('.proposal-card').length>=2,{},{timeout:240000});
 if(!session?.id)throw Error('No ordinary planning session observed');
 session=await page.evaluate(async id=>{const response=await fetch(`/api/v1/planning-sessions/${id}`);if(!response.ok)throw Error('Planning session read failed');return response.json();},session.id);
 check('local planner supplied ordinary calculated strategies',session.workflow===true&&session.result?.strategies?.length>=2);
 const realWritesAfterCalculation=report.real_backend_writes.length;
 report.fixture_ui=await runDraftChecks({page,session,check});
 check('all client provider-like requests were intercepted UI fixtures',report.client_provider_requests.every(path=>report.fixture_ui.writes.some(write=>write.path===path)),{count:report.client_provider_requests.length});

 // Scope assertions use only open/edit/close/navigation/reload, with no submit.
 const proposal=()=>page.getByRole('dialog',{name:'Challenge constraints and recalculate'});
 const open=async()=>{await page.getByRole('button',{name:'Apply & Recalculate',exact:true}).click();await proposal().waitFor();};
 const close=async()=>{await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});};
 const specialist=()=>page.getByRole('dialog',{name:'Ask a planning specialist'});
 const openSpecialist=async()=>{await page.getByRole('button',{name:'Ask this specialist',exact:true}).first().click();await specialist().waitFor();};
 const marker='V21 ephemeral draft scope marker';
 await open();await proposal().getByLabel('Expected demand',{exact:true}).fill('141');await close();
 await openSpecialist();await specialist().getByLabel('Question',{exact:true}).fill(marker);await close();
 const persisted=await page.evaluate(marker=>[localStorage,sessionStorage].some(storage=>Object.keys(storage).some(key=>(storage.getItem(key)||'').includes(marker))),marker);
 check('draft scope: unsent text is not persisted to browser storage',!persisted);
 await page.locator('.side-rail nav').getByRole('button',{name:'Crops',exact:true}).click();
 await page.getByRole('heading',{name:'Recipes with receipts.'}).waitFor();
 await page.locator('.side-rail nav').getByRole('button',{name:'Plan',exact:true}).click();
 await page.locator('.proposal-card').first().waitFor();
 await open();check('draft scope: navigating away and remounting resets proposal',await proposal().getByLabel('Expected demand',{exact:true}).inputValue()==='100');await close();
 await openSpecialist();check('draft scope: navigating away and remounting resets question',await specialist().getByLabel('Question',{exact:true}).inputValue()!==marker);
 await specialist().getByLabel('Question',{exact:true}).fill(marker);await close();
 await open();await proposal().getByLabel('Expected demand',{exact:true}).fill('143');await close();
 await page.reload({waitUntil:'domcontentloaded'});await page.locator('.proposal-card').first().waitFor();
 await open();check('draft scope: reload resets unsent proposal',await proposal().getByLabel('Expected demand',{exact:true}).inputValue()==='100');await close();
 await openSpecialist();check('draft scope: reload resets unsent question',await specialist().getByLabel('Question',{exact:true}).inputValue()!==marker);await close();
 check('draft checks made no additional real backend mutations',report.real_backend_writes.length===realWritesAfterCalculation,report.real_backend_writes);
 check('outer guard blocked no unexpected mutations',report.blocked_writes.length===0,report.blocked_writes);
 check('no page exceptions',report.page_errors.length===0,report.page_errors);
 report.status='PASS';
 await context.close();
}catch(error){report.status='FAIL';report.failures.push(error.stack||String(error));if(page)await page.screenshot({path:resolve(artifacts,'failure.png'),fullPage:true}).catch(()=>{});
}finally{
 if(browser)await browser.close();
 const output=resolve(process.env.REPORT_PATH||'/tmp/v21-drafts/report.json');
 await mkdir(resolve(output,'..'),{recursive:true});await writeFile(output,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,checks:report.checks.length,failures:report.failures}));
 if(report.status!=='PASS')process.exitCode=1;
}
