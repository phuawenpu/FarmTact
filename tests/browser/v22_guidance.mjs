import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';
import {mkdir,writeFile} from 'node:fs/promises';
const report={status:'RUNNING',checks:[],errors:[],provider_requests:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass,detail});console.log(pass?'PASS':'FAIL',name);if(!pass)throw Error(name)};
await mkdir('/tmp/v22-guidance',{recursive:true});
const browser=await chromium.launch();
try{
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
 const page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));
 const writes=[];page.on('request',r=>{if(r.method()==='POST'){writes.push(new URL(r.url()).pathname);if(/\/conversations|\/review$/.test(r.url()))report.provider_requests.push(r.url())}});
 await page.goto(process.env.BASE_URL||'http://127.0.0.1:4199');
 const demo=page.getByRole('dialog',{name:'Meet your farm Council'});await demo.waitFor();
 const baseline=writes.length;
 check('demo clearly identifies illustration',await demo.getByText(/Illustration of the workflow/).isVisible());
 check('demo heading receives focus',await demo.locator('h2').evaluate(el=>el===document.activeElement));
 for(let index=0;index<3;index++)await demo.getByRole('button',{name:'Next scene',exact:true}).click();
 check('fourth scene explains reported versus projected and recovery',await demo.getByText('Report, compare and recover',{exact:true}).isVisible());
 await demo.getByRole('button',{name:'Start planning',exact:true}).click();
 check('demo playback makes no writes',writes.length===baseline);
 for(const width of [360,390,430,1280]){
  await page.setViewportSize({width,height:844});await page.evaluate(()=>scrollTo(0,0));
  const box=await page.locator('.decision-guide').getByRole('button',{name:'Compare planting plans',exact:true}).boundingBox();
  check(`${width} first action visible without scrolling`,box&&box.y>=0&&box.y+box.height<844,box);
  const dim=await page.evaluate(()=>({body:document.body.scrollWidth,width:innerWidth}));check(`${width} no page horizontal overflow`,dim.body<=dim.width+1,dim);
 }
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>document.documentElement.style.fontSize='24px');
 const zoom=await page.evaluate(()=>({body:document.body.scrollWidth,width:innerWidth}));check('150 percent text no horizontal overflow',zoom.body<=zoom.width+1,zoom);
 await page.evaluate(()=>document.documentElement.style.fontSize='');
 await page.locator('.flow-rail button').filter({hasText:'Discuss'}).click();
 const council=await page.locator('.council-room').evaluate(el=>({focus:document.activeElement===el,top:el.getBoundingClientRect().top}));
 check('Council jump focuses heading below fixed header',council.focus&&council.top>=80&&council.top<844,council);
 await page.locator('.decision-guide').getByRole('button',{name:'Hide guidance',exact:true}).click();
 await page.reload();await page.locator('.decision-guide').waitFor();check('dismissed demo stays dismissed on reload',await page.getByRole('dialog').count()===0);check('hidden guidance remembered',await page.getByRole('button',{name:'Show guidance',exact:true}).isVisible());
 await page.getByRole('button',{name:'Replay demo',exact:true}).click();await page.keyboard.press('Escape');check('Escape dismisses demo',await page.getByRole('dialog').count()===0);
 await page.screenshot({path:'/tmp/v22-guidance/mobile.png',fullPage:true});
 check('guidance and navigation trigger no inference',report.provider_requests.length===0);check('no browser exceptions',report.errors.length===0,report.errors);report.status='PASS';
}catch(e){report.status='FAIL';report.error=String(e);process.exitCode=1}finally{await browser.close();await writeFile('/tmp/v22-guidance/report.json',JSON.stringify(report,null,2)+'\n')}
