import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const root=process.cwd();
const {chromium}=await import(pathToFileURL(resolve(root,'apps/web/node_modules/@playwright/test/index.mjs')));
const base=process.env.BASE_URL||'http://127.0.0.1:4199';
const report={status:'RUNNING',checks:[],failures:[],screenshots:[],provider_requests:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:!!pass,detail});console.log(`${pass?'PASS':'FAIL'} ${name}`);if(!pass)throw Error(name);};
const artifacts=process.env.ARTIFACT_DIR||'/tmp/v21-ux';
let browser,transport,page;
try{
 await mkdir(artifacts,{recursive:true});
 if(process.env.STAGED_SOURCE){
  if(base!=='http://127.0.0.1:4199')throw Error('Staged transport requires fixed loopback origin');
  const {stagedTransport}=await import(pathToFileURL(resolve(root,'tests/browser/restored_staged_transport.mjs')));
  transport=await stagedTransport(process.env.STAGED_SOURCE);
 }
 browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
 if(transport)await transport.attach(context);
 context.setDefaultTimeout(transport?180000:30000);
 page=await context.newPage();
 const errors=[],writes=[]; let session;
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.method()!=='GET'&&r.url().includes('/api/'))writes.push({method:r.method(),path:new URL(r.url()).pathname});if(r.method()==='POST'&&/\/conversations|\/planning-sessions\/[^/]+\/review$/.test(r.url()))report.provider_requests.push(new URL(r.url()).pathname);});
 page.on('response',async response=>{if(/\/planning-sessions(?:\/[^/?]+)?$/.test(new URL(response.url()).pathname)&&response.ok()){try{const body=await response.json();if(body.farm&&body.id)session=body;}catch{}}});
 await page.goto(base+(process.env.APP_PATH||'/'),{waitUntil:'domcontentloaded'});
 await page.getByRole('heading',{name:/See the farm/}).waitFor();
 check('V12 remains explicit experience in new edition',await page.locator(`[data-experience="v12"][data-edition="${process.env.EXPECTED_EDITION||'v21'}"]`).count()===1);
 const calculate=page.getByRole('button',{name:/Calculate options/});
 await calculate.waitFor();
 const position=await page.evaluate(()=>{const action=[...document.querySelectorAll('button')].find(el=>el.textContent.includes('Calculate options'));const board=document.querySelector('.living-board');return {action:action.getBoundingClientRect().top,board:board.getBoundingClientRect().top};});
 check('Calculate options precedes board',position.action<position.board,position);
 check('initial board is recorded farm snapshot',await page.locator('.living-board').getByText('Recorded farm snapshot').isVisible());
 check('initial board has no plan preview binding',(await page.locator('.living-board').getAttribute('data-preview-strategy'))==='');
 const initialBedText=await page.locator('.living-board__beds').innerText();
 check('initial farm shows recorded crop stages instead of all available',!/\bavailable\b/i.test(initialBedText)&&/recorded batch|growing|nursery|ready|transplant|harvested|sanitation/i.test(initialBedText),initialBedText);
 const initialWrites=writes.length;
 await page.locator('.flow-rail button').filter({hasText:'Replan'}).click();
 check('unavailable stage explains prerequisite',await page.getByText('Calculate options first. No farm change has been made.').isVisible());
 check('unavailable stage focuses calculate guidance',await page.locator('.flow-callout').evaluate(el=>document.activeElement===el));
 check('navigation does not manufacture completed stages',await page.locator('.flow-rail .is-done').count()===0);
 check('stage navigation makes no API writes',writes.length===initialWrites);
 await calculate.click();
 await page.locator('.proposal-card').filter({hasText:'Balanced'}).waitFor({timeout:240000});
 await page.waitForFunction(()=>document.querySelectorAll('.proposal-card').length===3);
 session=await page.evaluate(async id=>{const response=await fetch(`/api/v1/planning-sessions/${id}`);if(!response.ok)throw Error('Planning session read failed');return response.json();},session.id);
 const browseWrites=writes.length;
 for(const name of ['Lean','Resilient']){
  await page.locator('.proposal-card').filter({hasText:name}).click();
  const chosen=session.result.strategies.find(item=>item.name===name);
  check(`${name} candidate matches board and detailed brief`,(await page.locator('.proposal-card.is-selected h3').textContent())===name&&(await page.locator('.living-board').getAttribute('data-preview-strategy'))===chosen.id&&(await page.locator('.v12-plan-brief').getAttribute('data-preview-strategy'))===chosen.id);
  const details=page.locator('.v12-plan-brief details');
  if(!(await details.evaluate(el=>el.open)))await details.locator('summary').click();
  check(`${name} reveals complete dated schedule`,await details.locator('li').count()===chosen.allocations.length);
  const scheduleText=await details.innerText();
  check(`${name} schedule contains authoritative dates`,chosen.allocations.every(item=>[item.sow_date,item.transplant_date,item.harvest_date].every(date=>scheduleText.includes(date))));
  check(`${name} preview explicitly does not approve or save`,await page.getByText(/Selecting a candidate changes this preview only/).isVisible());
 }
 for(const width of [360,390,430,1280]){
  await page.setViewportSize({width,height:width===1280?900:844});
  for(const [label,selector]of [['Observe','.flow-observe'],['Discuss','.council-room'],['Decide','.decision-stage'],['Approve','.decision-actions']]){
   await page.locator('.flow-rail button').filter({hasText:label}).click();
   const state=await page.locator(selector).evaluate(el=>({focused:document.activeElement===el,top:el.getBoundingClientRect().top}));
   check(`${width}px ${label} rail focuses and scrolls to stage`,state.focused&&state.top>=-1&&state.top<innerHeightFor(width),state);
  }
  check(`${width}px rail has no false completion`,await page.locator('.flow-rail .is-done').count()===0);
  const opener=page.getByRole('button',{name:'Apply & Recalculate',exact:true});
  await opener.scrollIntoViewIfNeeded();await opener.focus();
  const scroll=await page.evaluate(()=>({x:scrollX,y:scrollY}));
  await opener.click();
  const dialog=page.getByRole('dialog',{name:/Challenge constraints/});await dialog.waitFor();
  check(`${width}px proposal dialog opens with heading focus`,await dialog.locator('h2').evaluate(el=>document.activeElement===el));
  const contained=[];for(let i=0;i<18;i++){await page.keyboard.press(i<9?'Tab':'Shift+Tab');contained.push(await dialog.evaluate(el=>el.contains(document.activeElement)));}
  check(`${width}px dialog Tab and Shift+Tab stay inside`,contained.every(Boolean));
  await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
  const returned=await page.evaluate(()=>({x:scrollX,y:scrollY}));
  check(`${width}px Escape restores opener and scroll`,await opener.evaluate(el=>document.activeElement===el)&&Math.abs(returned.y-scroll.y)<2&&Math.abs(returned.x-scroll.x)<2,{before:scroll,after:returned});
  const dimensions=await page.evaluate(()=>({body:document.body.scrollWidth,viewport:innerWidth}));
  check(`${width}px no horizontal overflow`,dimensions.body<=dimensions.viewport+1,dimensions);
  const file=resolve(artifacts,`plan-${width}.png`);await page.screenshot({path:file,fullPage:true,animations:'disabled'});report.screenshots.push(file);
 }
 await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>document.documentElement.style.fontSize='24px');
 const zoom=await page.evaluate(()=>({body:document.body.scrollWidth,viewport:innerWidth}));
 check('150 percent text size has no page horizontal overflow',zoom.body<=zoom.viewport+1,zoom);
 await page.getByRole('button',{name:'Apply & Recalculate',exact:true}).click();
 check('larger text preserves visible proposal action',await page.getByRole('dialog').getByRole('button',{name:'Apply & Recalculate',exact:true}).isVisible());
 await page.keyboard.press('Escape');
 await page.evaluate(()=>document.documentElement.style.fontSize='');
 check('preview, schedules, stage navigation and dialogs make no writes',writes.length===browseWrites);
 await page.setViewportSize({width:1280,height:900});
 await page.locator('.side-rail nav').getByRole('button',{name:'Crops',exact:true}).click();
 await page.getByRole('heading',{name:'Recipes with receipts.'}).waitFor();
 let release,seen;const gate=new Promise(r=>release=r),requestSeen=new Promise(r=>seen=r);
 const heldProfile=await page.evaluate(async()=>{const bootstrap=await fetch('/api/v1/bootstrap').then(r=>r.json());const id=bootstrap.crops[0].id;const response=await fetch(`/api/v1/crops/${encodeURIComponent(id)}/evidence`);if(!response.ok)throw Error('Profile preload failed');return {id,body:await response.text()};});
 report.delayed_profile_scope='Actual server profile snapshot, held and fulfilled by one browser route to avoid overlapping operator transports.';
 await page.route(`**/api/v1/crops/${encodeURIComponent(heldProfile.id)}/evidence`,async route=>{seen();await gate;await route.fulfill({status:200,contentType:'application/json',body:heldProfile.body});},{times:1});
 const crop=page.locator('.crop-profile-card').first();await crop.click();await requestSeen;
 const cropDialog=page.getByRole('dialog');await cropDialog.waitFor();
 await page.keyboard.press('Escape');await cropDialog.waitFor({state:'hidden'});
 check('crop Escape while evidence loads restores source focus',await crop.evaluate(el=>document.activeElement===el));
 const responseDone=page.waitForResponse(response=>/\/crops\/[^/]+\/evidence$/.test(response.url()));release();await responseDone;
 await page.waitForTimeout(200);
 check('late crop evidence response cannot reopen closed profile',await page.getByRole('dialog').count()===0);
 await crop.click();await page.getByText('Loading evidence profile…').waitFor({state:'hidden'});
 const profile=page.getByRole('dialog');
 const cropContained=[];for(let i=0;i<10;i++){await page.keyboard.press(i<5?'Tab':'Shift+Tab');cropContained.push(await profile.evaluate(el=>el.contains(document.activeElement)));}
 check('crop profile Tab and Shift+Tab stay inside',cropContained.every(Boolean));
 await profile.getByRole('button',{name:'Close',exact:true}).click();
 check('crop Close button restores source focus',await crop.evaluate(el=>document.activeElement===el));
 check('no inference requests submitted',report.provider_requests.length===0,report.provider_requests);
 check('no page exceptions',errors.length===0,errors);
 report.status='PASS';await context.close();
}catch(error){report.status='FAIL';report.failures.push(error.stack||String(error));if(page)await page.screenshot({path:resolve(artifacts,'failure.png'),fullPage:true}).catch(()=>{});
}finally{if(browser)await browser.close();if(transport)report.staged_transport=transport.evidence;const output=resolve(process.env.REPORT_PATH||'/tmp/v21-ux/report.json');await mkdir(resolve(output,'..'),{recursive:true});await writeFile(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,failures:report.failures}));if(report.status!=='PASS')process.exitCode=1;}
function innerHeightFor(width){return width===1280?900:844;}
