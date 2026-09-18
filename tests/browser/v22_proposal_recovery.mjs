import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const root=process.cwd();
const {chromium}=await import(pathToFileURL(resolve(root,'apps/web/node_modules/@playwright/test/index.mjs')));
const base=process.env.BASE_URL||'http://127.0.0.1:4199';
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('Proposal recovery verification is local-only');
const report={status:'RUNNING',scope:'fully intercepted local UI fixture; zero backend or provider requests',checks:[],failures:[],fixture_writes:[],provider_requests:[],unexpected_api:[],screenshots:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:!!pass,detail});console.log(`${pass?'PASS':'FAIL'} ${name}`);if(!pass)throw Error(name);};
let browser,page;
try{
 browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:900},reducedMotion:'reduce'});context.setDefaultTimeout(45000);
 const fixture=JSON.parse(await readFile(process.env.V22_UI_FIXTURE||'/tmp/v22-ui-fixture.json','utf8'));
 const session=fixture.session,workflow=fixture.workflow;
 const planningDate=session.farm.planning_date||session.farm.cutoff.slice(0,10),bed=session.farm.beds[0],crop=session.farm.orders[0]?.crop_id||'caixin';
 const day=value=>{const date=new Date(`${planningDate}T00:00:00Z`);date.setUTCDate(date.getUTCDate()+value);return date.toISOString().slice(0,10)};
 const strategy=(id,name,delivered,margin)=>({id,name,status:'FEASIBLE',description:`${name} fixture`,metrics:{fill_rate:delivered/100,booked_requested_kg:100,booked_delivered_kg:delivered,waste_kg:4,margin_sgd:margin,closing_stock_kg:2,harvest_kg:delivered,shortfall_kg:100-delivered,cost_sgd:200,labour_hours:10,area_m2:Number(bed.area_m2)},allocations:[{id:`${id}-cycle`,bed_id:bed.id,crop_id:crop,sow_date:day(1),transplant_date:day(8),harvest_date:day(29),area_m2:Number(bed.area_m2),expected_kg:delivered}],weekly:[],violations:[],assumptions:[]});
 const resultId='fixture-v22-calculated-result';
 Object.assign(session,{revision:2,status:'COMPLETED',stage:'review',result_id:resultId,selected_strategy_id:'balanced-fixture',job:{id:resultId,status:'COMPLETED',kind:'calculate'},result:{id:resultId,strategies:[strategy('lean-fixture','Lean',70,700),strategy('balanced-fixture','Balanced',82,820),strategy('resilient-fixture','Resilient',90,900)]}});
 Object.assign(workflow,{phase:'decision',revision:2,proposals:[],tasks:[]});
 await context.addInitScript(id=>localStorage.setItem('farmtact:v22:planning-session',id),session.id);
 page=await context.newPage();
 page.on('request',request=>{const path=new URL(request.url()).pathname;if(request.method()==='POST'&&/\/conversations|\/review$/.test(path))report.provider_requests.push(path);});
 let serverStatus='draft',createCount=0,applyCount=0,createdBody;
 const proposal={id:'fixture-v22-recovery-proposal',session_id:'',base_revision:0,proposal_revision:1,status:'draft',selected_strategy_id:'',calculated_metrics:{},recalculation_job:null};
 await page.route('**/api/**',async route=>{
  const request=route.request(),path=new URL(request.url()).pathname,method=request.method();
  const json=body=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  if(method==='GET'&&path.endsWith('/bootstrap'))return json(fixture.bootstrap);
  if(method==='GET'&&path.endsWith(`/planning-sessions/${session.id}`))return json(session);
  if(method==='GET'&&path.endsWith('/farm-workflow'))return json({...workflow,proposals:[...workflow.proposals.filter(item=>item.id!==proposal.id),...(createCount?[{...proposal,status:serverStatus}]:[])]});
  if(method==='GET'&&path.endsWith('/conversations'))return json({conversations:[],next_before:null});
  if(method==='GET'&&path.endsWith('/data-explorer/snapshots'))return json({snapshots:[]});
  if(method==='POST'&&path.endsWith('/farm-workflow/proposals')){
   createCount++;createdBody=request.postDataJSON();proposal.session_id=createdBody.session_id;proposal.base_revision=createdBody.base_revision;proposal.selected_strategy_id=createdBody.selected_strategy_id;report.fixture_writes.push({kind:'create',body:createdBody});
   return route.fulfill({status:201,contentType:'application/json',body:JSON.stringify(proposal)});
  }
  if(method==='POST'&&path.endsWith(`/farm-workflow/proposals/${proposal.id}/apply`)){
   applyCount++;report.fixture_writes.push({kind:'apply',body:request.postDataJSON()});serverStatus='applied';
   return route.abort('failed');
  }
  report.unexpected_api.push({method,path});return route.abort('blockedbyclient');
 });

 await page.goto(base,{waitUntil:'domcontentloaded'});
 await page.locator('.decision-guide h1').waitFor();
 const skip=page.getByRole('button',{name:'Skip demo',exact:true});if(await skip.isVisible().catch(()=>false))await skip.click();
 await page.locator('.proposal-card').first().waitFor();

 await page.getByRole('button',{name:'Adjust assumptions',exact:true}).click();
 let dialog=page.getByRole('dialog',{name:'Challenge constraints and recalculate'});await dialog.waitFor();
 await dialog.getByLabel('Expected demand',{exact:false}).fill('127');
 await dialog.getByLabel('Add an order to this scenario').check();
 const order=dialog.locator('.proposal-order-fields');
 await order.locator('label').filter({hasText:/^Customer \/ order reference/}).locator('input').fill('RECOVERY-ORIGINAL');
 await order.locator('label').filter({hasText:/^Quantity/}).locator('input').fill('14');
 await dialog.getByRole('button',{name:'Calculate revised plans',exact:true}).click();
 await dialog.getByText('Revised-plan submission needs reconciliation').waitFor();
 check('fixture created and attempted exactly one proposal',createCount===1&&applyCount===1,{createCount,applyCount});
 check('lost apply response leaves original fields locked',await dialog.getByLabel('Expected demand',{exact:false}).isDisabled()&&await order.locator('input').first().isDisabled());
 const pending=await page.evaluate(()=>Object.entries(localStorage).filter(([key])=>key.includes('pending-proposal-apply')).map(([key,value])=>({key,value:JSON.parse(value)})));
 check('pending receipt records exact proposal, base, result and inputs',pending.length===1&&pending[0].value.proposal.id==='fixture-v22-recovery-proposal'&&pending[0].value.baseRevision===createdBody.base_revision&&pending[0].value.resultId&&pending[0].value.draft.orderReference==='RECOVERY-ORIGINAL'&&pending[0].value.assumptions.order_changes[0].quantity_kg===14,pending);
 // A conflicting ordinary draft cannot alter the frozen recovery receipt.
 await page.evaluate(()=>{for(const key of Object.keys(localStorage))if(key.includes('v22-drafts:proposals')){const rows=JSON.parse(localStorage.getItem(key)||'[]');for(const row of rows)if(row?.[1]){row[1].orderReference='CHANGED-SHOULD-NOT-SUBMIT';row[1].demand=51;}localStorage.setItem(key,JSON.stringify(rows));}});
 await page.reload({waitUntil:'domcontentloaded'});await page.locator('.proposal-card').first().waitFor({timeout:60000});
 await page.getByRole('button',{name:'Adjust assumptions',exact:true}).click();dialog=page.getByRole('dialog',{name:'Challenge constraints and recalculate'});await dialog.waitFor();
 const restoredOrder=dialog.locator('.proposal-order-fields').locator('label').filter({hasText:/^Customer \/ order reference/}).locator('input');
 check('reload restores exact pending fields instead of changed ordinary draft',await dialog.getByLabel('Expected demand',{exact:false}).inputValue()==='127'&&await restoredOrder.inputValue()==='RECOVERY-ORIGINAL');
 check('pending recovery never auto-applies on mount',createCount===1&&applyCount===1,{createCount,applyCount});
 const screenshot='/tmp/v22-proposal-recovery/reconcile-readability.png';await mkdir(resolve(screenshot,'..'),{recursive:true});await page.screenshot({path:screenshot,fullPage:true,animations:'disabled'});report.screenshots.push(screenshot);
 await dialog.getByRole('button',{name:'Resume / reconcile saved proposal',exact:true}).click();
 await dialog.waitFor({state:'hidden'});
 check('durably applied proposal reconciles without duplicate create or apply',createCount===1&&applyCount===1,{createCount,applyCount});
 check('successful reconciliation clears pending receipt',await page.evaluate(()=>!Object.keys(localStorage).some(key=>key.includes('pending-proposal-apply'))));
 check('changed draft fields were never submitted',report.fixture_writes.every(write=>!JSON.stringify(write).includes('CHANGED-SHOULD-NOT-SUBMIT')),report.fixture_writes);
 check('recovery made no provider request',report.provider_requests.length===0,report.provider_requests);
 check('fixture allowed no unexpected API request',report.unexpected_api.length===0,report.unexpected_api);
 report.status='PASS';await context.close();
}catch(error){report.status='FAIL';report.failures.push(error.stack||String(error));if(page)await page.screenshot({path:'/tmp/v22-proposal-recovery-failure.png',fullPage:true}).catch(()=>{});
}finally{if(browser)await browser.close();const output=resolve(process.env.REPORT_PATH||'/tmp/v22-proposal-recovery/report.json');await mkdir(resolve(output,'..'),{recursive:true});await writeFile(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,failures:report.failures}));if(report.status!=='PASS')process.exitCode=1;}
