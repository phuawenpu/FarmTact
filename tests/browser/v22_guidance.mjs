import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const base=(process.env.BASE_URL||'http://127.0.0.1:4199').replace(/\/$/,'');
const artifacts=process.env.ARTIFACT_DIR||'/tmp/v22-guidance';
const report={status:'RUNNING',checks:[],errors:[],provider_requests:[],screenshots:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:!!pass,detail});console.log(pass?'PASS':'FAIL',name);if(!pass)throw Error(`${name}: ${JSON.stringify(detail)}`)};
await mkdir(artifacts,{recursive:true});let browser,context,page,transport;
try{
 if(process.env.STAGED_SOURCE){if(base!=='http://127.0.0.1:4199')throw Error('Staged transport requires fixed loopback browser origin');const module=await import('./restored_staged_transport.mjs');transport=await module.stagedTransport(process.env.STAGED_SOURCE)}
 if(process.env.UI_FIXTURE_PATH&&process.env.STAGED_SOURCE)throw Error('UI fixture and staged transport modes are mutually exclusive');
 browser=await chromium.launch({headless:true});context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:process.env.NORMAL_MOTION?'no-preference':'reduce',...(process.env.VIDEO_DIR?{recordVideo:{dir:process.env.VIDEO_DIR,size:{width:390,height:844}}}:{})});
 if(transport)await transport.attach(context);context.setDefaultTimeout(transport?180000:45000);page=await context.newPage();page.on('pageerror',error=>report.errors.push(error.message));
 if(process.env.UI_FIXTURE_PATH){
  const fixture=JSON.parse(await readFile(process.env.UI_FIXTURE_PATH,'utf8'));report.fixture_scope='Isolated UI fixture responses; not a real backend or lifecycle result.';
  await page.route('**/*',async route=>{const request=route.request(),url=new URL(request.url());if(url.origin!==base)return route.abort('blockedbyclient');if(!url.pathname.startsWith('/api/v1/'))return route.fallback();if(request.method()!=='GET'&&request.method()!=='HEAD')return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Fixture guidance test blocks all mutations'})});let body;
   if(url.pathname==='/api/v1/bootstrap')body=fixture.bootstrap;
   else if(url.pathname==='/api/v1/planning-sessions')body={sessions:[fixture.session]};
   else if(/^\/api\/v1\/planning-sessions\/[^/]+$/.test(url.pathname))body=fixture.session;
   else if(url.pathname==='/api/v1/farm-workflow')body=fixture.workflow;
   else if(url.pathname==='/api/v1/conversations/advisors')body={advisors:[]};
   else if(url.pathname==='/api/v1/conversations')body={conversations:[],next_before:null};
   else return route.fulfill({status:404,contentType:'application/json',body:JSON.stringify({detail:'Fixture route unavailable'})});
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  });
 }
 const writes=[];page.on('request',request=>{if(request.method()==='POST'){writes.push(new URL(request.url()).pathname);if(/\/conversations|\/review$/.test(request.url()))report.provider_requests.push(request.url())}});
 await page.goto(base+(process.env.APP_PATH||'/'),{waitUntil:'domcontentloaded'});check('expected V22 edition is rendered',await page.locator(`[data-edition="${process.env.EXPECTED_EDITION||'v22'}"]`).count()===1);
 const demo=page.getByRole('dialog',{name:'Meet your farm Council'});await demo.waitFor();const baseline=writes.length;
 check('demo clearly identifies illustration',await demo.getByText(/Illustration of the workflow/).isVisible());check('demo heading receives focus',await demo.locator('h2').evaluate(element=>element===document.activeElement));
 if(process.env.NORMAL_MOTION){const opening=await demo.locator('.decision-demo-scene').innerText();await page.waitForFunction(text=>document.querySelector('.decision-demo-scene')?.textContent!==text,opening,{timeout:10000});await demo.getByRole('button',{name:'Pause',exact:true}).click();const paused=await demo.locator('.decision-demo-scene').innerText();await page.waitForTimeout(3500);check('normal-motion demo advances and pauses',await demo.locator('.decision-demo-scene').innerText()===paused,paused)}
 else check('reduced-motion demo uses manual scenes',await demo.getByRole('button',{name:'Pause',exact:true}).count()===0);
 while(await demo.getByRole('button',{name:'Next scene',exact:true}).count())await demo.getByRole('button',{name:'Next scene',exact:true}).click();
 check('fourth scene explains reported versus projected and recovery',await demo.getByText('Report, compare and recover',{exact:true}).isVisible());await demo.getByRole('button',{name:'Start planning',exact:true}).click();check('demo playback makes no writes',writes.length===baseline);
 const firstViewport=resolve(artifacts,'guidance-first-viewport.png');await page.screenshot({path:firstViewport,animations:'disabled'});report.screenshots.push(firstViewport);
 check('all short public Council role labels appear',await page.locator('.v22-council-workspace .cw-roster article').evaluateAll((cards,labels)=>labels.every(label=>cards.some(card=>card.textContent?.includes(label))),['Demand Planner','Crop Planner','Weather & Risk','Market Analyst','Resource Planner','Supply Planner','Chair']));
 for(const width of [360,390,430,1280]){await page.setViewportSize({width,height:width===1280?900:844});await page.evaluate(()=>scrollTo(0,0));const box=await page.locator('.decision-guide').getByRole('button',{name:'Compare planting plans',exact:true}).boundingBox();check(`${width} first action visible without scrolling`,box&&box.y>=0&&box.y+box.height<(width===1280?900:844),box);const dimensions=await page.evaluate(()=>({body:document.body.scrollWidth,width:innerWidth}));check(`${width} no page horizontal overflow`,dimensions.body<=dimensions.width+1,dimensions)}
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>document.documentElement.style.fontSize='24px');const zoom=await page.evaluate(()=>({body:document.body.scrollWidth,width:innerWidth}));check('150 percent text no horizontal overflow',zoom.body<=zoom.width+1,zoom);await page.evaluate(()=>document.documentElement.style.fontSize='');
 await page.locator('.flow-rail button').filter({hasText:'Discuss'}).click();await page.waitForTimeout(500);const council=await page.locator('.council-room').evaluate(element=>({focus:document.activeElement===element,top:element.getBoundingClientRect().top,headingTop:element.querySelector('h2')?.getBoundingClientRect().top}));check('settled Council stage heading clears sticky header',council.focus&&council.top>=80&&council.headingTop>=80&&council.headingTop<844,council);
 await page.locator('.decision-guide').getByRole('button',{name:'Hide guidance',exact:true}).click();await page.reload({waitUntil:'domcontentloaded'});await page.locator('.decision-guide').waitFor();check('dismissed demo stays dismissed on reload',await page.getByRole('dialog').count()===0);check('hidden guidance remembered',await page.getByRole('button',{name:'Show guidance',exact:true}).isVisible());await page.getByRole('button',{name:'Replay demo',exact:true}).click();await page.keyboard.press('Escape');check('Escape dismisses demo',await page.getByRole('dialog').count()===0);
 const fullPage=resolve(artifacts,'guidance-full-page.png');await page.screenshot({path:fullPage,fullPage:true,animations:'disabled'});report.screenshots.push(fullPage);check('guidance and navigation trigger no inference',report.provider_requests.length===0,report.provider_requests);check('no browser exceptions',report.errors.length===0,report.errors);report.status='PASS';
}catch(error){report.status='FAIL';report.error=error.stack||String(error);process.exitCode=1}
finally{if(process.env.STORAGE_STATE_OUT&&context)await context.storageState({path:process.env.STORAGE_STATE_OUT}).catch(()=>{});if(transport)report.staged_transport=transport.evidence;if(context)await context.close();if(browser)await browser.close();await writeFile(resolve(process.env.REPORT_PATH||resolve(artifacts,'report.json')),JSON.stringify(report,null,2)+'\n')}
