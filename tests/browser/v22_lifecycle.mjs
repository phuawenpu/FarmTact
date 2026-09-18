import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';

const root=resolve(new URL('../..',import.meta.url).pathname);
const base=(process.env.BASE_URL||'http://127.0.0.1:4199').replace(/\/$/,'');
const artifacts=process.env.ARTIFACT_DIR||'/tmp/v22-lifecycle';
const report={status:'RUNNING',base_url:base+(process.env.APP_PATH||'/'),checks:[],failures:[],page_errors:[],provider_requests:[],screenshots:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:!!pass,detail});console.log(`${pass?'PASS':'FAIL'} ${name}`);if(!pass)throw Error(`${name}: ${JSON.stringify(detail)}`)};
let browser,transport,page;
try{
 await mkdir(artifacts,{recursive:true});
 if(process.env.STAGED_SOURCE){
  if(base!=='http://127.0.0.1:4199')throw Error('Staged transport requires fixed loopback browser origin');
  ({stagedTransport:transport}=await import('./restored_staged_transport.mjs'));
  transport=await transport(process.env.STAGED_SOURCE);
 }
 browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:process.env.NORMAL_MOTION?'no-preference':'reduce',...(process.env.VIDEO_DIR?{recordVideo:{dir:process.env.VIDEO_DIR,size:{width:390,height:844}}}:{})});
 if(transport)await transport.attach(context);
 context.setDefaultTimeout(transport?180000:45000);
 page=await context.newPage();
 page.on('pageerror',error=>report.page_errors.push(error.message));
 page.on('request',request=>{if(request.method()!=='GET'&&/\/conversations(?:\/|$)|\/planning-sessions\/[^/]+\/review$/.test(new URL(request.url()).pathname))report.provider_requests.push([request.method(),request.url()])});
 await page.goto(report.base_url,{waitUntil:'domcontentloaded'});
 await page.locator('.decision-guide').waitFor({timeout:60000});
 const skip=page.getByRole('button',{name:'Skip demo',exact:true});if(await skip.isVisible().catch(()=>false))await skip.click();
 check('V22 guided decision entry is active',await page.locator(`[data-edition="${process.env.EXPECTED_EDITION||'v22'}"] .decision-guide`).count()===1);
 const first=page.locator('.decision-guide').getByRole('button',{name:'Compare planting plans',exact:true});
 if(await first.isVisible().catch(()=>false))await first.click();
 await page.locator('.proposal-card').first().waitFor({timeout:240000});
 check('actual numerical backend returns plan choices',await page.locator('.proposal-card').count()>=2);
 check('Council remains explicit and unsubmitted',await page.getByRole('button',{name:/Review these plans with Council|Review with Council/}).isVisible());

 await page.getByRole('button',{name:/Add or review records|Inbox/}).click();
 const inbox=page.getByRole('dialog',{name:/Farm Inbox/});await inbox.waitFor();
 const uploadName=`v22-lifecycle-${Date.now()}.csv`;
 await inbox.locator('.sandbox-upload input[type=file]').setInputFiles({name:uploadName,mimeType:'text/csv',buffer:Buffer.from('date,kind,amount,currency,reference\n2026-09-01,expense,18.75,SGD,V22-LIFECYCLE\n')});
 await inbox.getByRole('button',{name:'Upload candidate'}).click();
 const candidate=inbox.locator('.upload-review').filter({hasText:uploadName});await candidate.waitFor();
 await candidate.getByRole('button',{name:'Confirm reviewed fields'}).click();
 await inbox.getByText(new RegExp(`${uploadName} · confirmed`)).waitFor();
 check('record import remains review-before-authority',true);
 await page.getByRole('button',{name:/Close Farm Inbox/}).click();

 await page.getByRole('button',{name:'Adjust assumptions',exact:true}).click();
 const editor=page.getByRole('dialog',{name:'Challenge constraints and recalculate'});await editor.waitFor();
 await editor.getByLabel('Expected demand',{exact:false}).fill('105');
 await editor.getByRole('button',{name:'Calculate revised plans',exact:true}).click();
 await editor.waitFor({state:'hidden'});
 const saved=page.locator('.decision-guide').getByRole('button',{name:'Save simulation plan',exact:true});await saved.waitFor({timeout:240000});
 await page.waitForFunction(()=>{const button=[...document.querySelectorAll('button')].find(node=>node.textContent?.trim()==='Save simulation plan');return button&&!button.disabled},null,{timeout:240000});
 await saved.click();
 const approval=page.getByRole('dialog',{name:'Save simulation plan'});await approval.waitFor();
 check('approval names simulation boundary',/simulation/i.test(await approval.innerText()));
 await approval.getByRole('button',{name:'Confirm simulation plan',exact:true}).click();
 await approval.waitFor({state:'hidden'});
 const state=await page.evaluate(()=>fetch('/api/v1/farm-workflow').then(response=>response.json()));
 const approved=[...state.proposals].reverse().find(item=>item.status==='approved');
 const tasks=state.tasks.filter(item=>item.proposal_id===approved?.id);
 check('proposal recalculation and approval persist revision-bound tasks',Boolean(approved)&&tasks.length>0,{proposal:approved?.id,tasks:tasks.length});

 const target=tasks.find(item=>['pending','in_progress'].includes(item.status)&&Number(item.planned_quantity)>0&&item.unit)||tasks.find(item=>Number(item.planned_quantity)>0&&item.unit)||tasks[0];
 await page.locator(`[data-task-id="${target.id}"]`).click();
 const actual=page.getByLabel(/Actual quantity/);if(await actual.count())await actual.fill(String(Math.max(0,Number(target.planned_quantity||1)-1)));
 for(const checkbox of await page.locator('.result-form input[type=checkbox]').all())await checkbox.check();
 await page.getByLabel('Farmer note').fill('V22 lifecycle short result');
 await page.getByRole('button',{name:/Save reported result/}).click();
 await page.locator(`[data-task-id="${target.id}"]`).getByText('recovery_required').waitFor();
 const recovery=page.getByRole('button',{name:'Compare recovery plans',exact:true});
 check('reported exception offers future-only recovery',await recovery.isVisible()&&await page.getByText(/Keep completed work, change only the future/).isVisible());
 const corrected=Math.max(0,Number(target.planned_quantity||1)-.5);
 await page.getByLabel('Corrected quantity').fill(String(corrected));
 await page.getByLabel('Reason').fill('V22 scale reading correction');
 await page.getByRole('button',{name:'Save auditable correction',exact:true}).click();
 await page.reload({waitUntil:'domcontentloaded'});await page.locator('.decision-guide').waitFor();
 const durable=await page.evaluate(async id=>(await fetch('/api/v1/farm-workflow').then(response=>response.json())).tasks.find(item=>item.id===id),target.id);
 check('report and correction survive reload',durable?.event_revision>=2&&Number(durable.actual_quantity)===corrected,durable);

 await page.setViewportSize({width:1280,height:900});
 const nav=page.locator('.side-rail nav');
 for(const [label,scope] of [['Farm','Farm snapshot and main mission'],['Council research','Independent Council research'],['Farm tools',null],['Crops',null],['Data',null],['Outcomes','Recorded main-mission outcomes'],['Setup','Future planning snapshot']]){
  await nav.getByRole('button',{name:label,exact:true}).click();
  if(scope)await page.getByText(scope,{exact:true}).waitFor();else await page.locator('main h1, main h2').first().waitFor();
  check(`named room ${label} opens`,true);
 }
 await nav.getByRole('button',{name:'Plan',exact:true}).click();await page.locator('.decision-guide').waitFor();
 check('room tour returns to remembered guided plan',await page.locator(`[data-task-id="${target.id}"]`).count()===1);
 for(const width of [360,390,430,1280]){
  await page.setViewportSize({width,height:width===1280?900:844});
  const dimensions=await page.evaluate(()=>({body:document.body.scrollWidth,viewport:innerWidth}));check(`${width}px has no body overflow`,dimensions.body<=dimensions.viewport+1,dimensions);
  const image=resolve(artifacts,`lifecycle-${width}.png`);await page.screenshot({path:image,fullPage:true,animations:'disabled'});report.screenshots.push(image);
 }
 check('lifecycle submits no provider request',report.provider_requests.length===0,report.provider_requests);
 check('lifecycle has no page exceptions',report.page_errors.length===0,report.page_errors);
 report.status='PASS';await context.close();
}catch(error){report.status='FAIL';report.failures.push(error.stack||String(error));if(page)await page.screenshot({path:resolve(artifacts,'failure.png'),fullPage:true}).catch(()=>{});process.exitCode=1}
finally{
 if(transport)report.staged_transport=transport.evidence;
 if(browser)await browser.close();
 const output=resolve(process.env.REPORT_PATH||resolve(artifacts,'report.json'));await mkdir(resolve(output,'..'),{recursive:true});await writeFile(output,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,checks:report.checks.length,failures:report.failures.length}));
}
