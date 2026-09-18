import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';

const base=(process.env.BASE_URL||'http://127.0.0.1:4199').replace(/\/$/,'');
const fixturePath=process.env.UI_FIXTURE_PATH||'/tmp/v22-ui-fixture.json';
const artifacts=process.env.ARTIFACT_DIR||'/tmp/v22-initialization';
const report={status:'RUNNING',scope:'Isolated first-load fixture; not a real backend or lifecycle result.',checks:[],failures:[],requests:[],preference_writes:'Browser-local only; no preference API exists.'};
const check=(name,pass,detail)=>{report.checks.push({name,pass:!!pass,detail});console.log(`${pass?'PASS':'FAIL'} ${name}`);if(!pass)throw Error(`${name}: ${JSON.stringify(detail)}`)};
await mkdir(artifacts,{recursive:true});let browser,page;
try{
 const fixture=JSON.parse(await readFile(fixturePath,'utf8'));
 browser=await chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});page=await context.newPage();
 const counts={bootstrap:0,planningList:0,planningCreate:0,workflow:0},unexpected=[];
 await page.route('**/*',async route=>{const request=route.request(),url=new URL(request.url());if(url.origin!==base)return route.abort('blockedbyclient');if(!url.pathname.startsWith('/api/v1/'))return route.fallback();report.requests.push({method:request.method(),path:url.pathname});let body,status=200;
  if(request.method()==='GET'&&url.pathname==='/api/v1/bootstrap'){counts.bootstrap++;body=fixture.bootstrap}
  else if(request.method()==='GET'&&url.pathname==='/api/v1/planning-sessions'){counts.planningList++;body={sessions:[]}}
  else if(request.method()==='POST'&&url.pathname==='/api/v1/planning-sessions'){counts.planningCreate++;status=201;body=fixture.session}
  else if(request.method()==='GET'&&url.pathname==='/api/v1/farm-workflow'){counts.workflow++;body=fixture.workflow}
  else if(request.method()==='GET'&&url.pathname==='/api/v1/data-explorer/snapshots')body={snapshots:[]}
  else if(request.method()==='GET'&&url.pathname==='/api/v1/conversations')body={conversations:[],next_before:null}
  else {unexpected.push({method:request.method(),path:url.pathname});status=503;body={detail:'Initialization fixture blocked an unexpected API request'}}
  return route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
 });
 await page.goto(base+(process.env.APP_PATH||'/'),{waitUntil:'domcontentloaded'});const demo=page.getByRole('dialog',{name:'Meet your farm Council'});await demo.waitFor();await demo.getByRole('button',{name:'Skip demo',exact:true}).click();await page.locator('.decision-guide').waitFor();
 await page.waitForTimeout(500);
 check('Strict Mode shares one bootstrap request',counts.bootstrap===1,counts);
 check('empty planning history is listed once',counts.planningList===1,counts);
 check('empty planning history creates exactly one workflow',counts.planningCreate===1,counts);
 check('only workflow creation is an API mutation',report.requests.filter(item=>item.method!=='GET'&&item.method!=='HEAD').length===1&&report.requests.find(item=>item.method==='POST')?.path==='/api/v1/planning-sessions',report.requests);
 check('initialization made no unexpected request',unexpected.length===0,unexpected);
 const title=await page.locator('.decision-guide h1').innerText();check('first objective is a concrete dated order question',/\d+(?:\.\d+)?\s*kg/i.test(title)&&/\d{2}\/\d{2}\/\d{4}/.test(title)&&/\?$/.test(title),title);
 for(const width of [360,390]){
  await page.setViewportSize({width,height:844});await page.evaluate(()=>{document.documentElement.style.fontSize='24px';scrollTo(0,0)});await page.waitForTimeout(100);
  const box=await page.locator('.decision-guide').getByRole('button',{name:'Compare planting plans',exact:true}).boundingBox();check(`${width}px enlarged-text first CTA is fully visible`,box&&box.y>=0&&box.y+box.height<844,box);
  const dimensions=await page.evaluate(()=>({body:document.body.scrollWidth,viewport:innerWidth}));check(`${width}px enlarged text has no page overflow`,dimensions.body<=dimensions.viewport+1,dimensions);
 }
 await page.evaluate(()=>document.documentElement.style.fontSize='');const image=resolve(artifacts,'first-load-390.png');await page.screenshot({path:image,animations:'disabled'});report.screenshot=image;report.counts=counts;report.status='PASS';await context.close();
}catch(error){report.status='FAIL';report.failures.push(error.stack||String(error));process.exitCode=1}
finally{if(browser)await browser.close();await writeFile(resolve(artifacts,'report.json'),JSON.stringify(report,null,2)+'\n')}
