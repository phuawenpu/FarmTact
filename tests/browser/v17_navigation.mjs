import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs';
import {mkdir,writeFile} from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4196';
const report={checks:[],errors:[],writes:[]};const check=(name,pass,detail)=>{report.checks.push({name,pass,detail});if(!pass)throw Error(name)};
const browser=await chromium.launch();
const context=await browser.newContext({storageState:process.env.STORAGE_STATE||'/tmp/farmtact-v17-navigation-state.json',viewport:{width:390,height:844},reducedMotion:'reduce'});
const page=await context.newPage();page.on('pageerror',e=>report.errors.push(String(e)));page.on('request',r=>{if(r.method()==='POST')report.writes.push(new URL(r.url()).pathname)});
await mkdir('reports/v17/navigation',{recursive:true});
const shot=async(name)=>page.screenshot({path:`reports/v17/navigation/${name}.png`,fullPage:true});
const back=()=>page.getByRole('button',{name:'Back',exact:true}).filter({visible:true}).click();
const choose=async(name)=>{await page.locator('.ic-tool-index').getByRole('button',{name:new RegExp('^'+name)}).click();await page.locator('.integrated-tool:visible, .integrated-records:visible').waitFor();};
try{
 await page.goto(base+'/play');await page.locator('.ic-shell').waitFor();if(await page.getByRole('button',{name:'Skip demonstration'}).count())await page.getByRole('button',{name:'Skip demonstration'}).click();
 const baseline=report.writes.length;await page.getByRole('button',{name:'More',exact:true}).click();
 await choose('Plan');await page.getByRole('button',{name:/^Strategies & schedules/}).click();await page.getByRole('heading',{name:'Strategies & allocation schedules',exact:true}).waitFor();await shot('planning-schedule');await back();
 await page.waitForFunction(()=>/Strategies & schedules/.test(document.activeElement?.textContent||''));check('plan index restores selected category focus',/Strategies & schedules/.test(await page.evaluate(()=>document.activeElement?.textContent||'')));await back();
 await choose('Records & work');await page.getByRole('button',{name:/^Confirmed orders ·/}).click();await shot('order-record');check('order record includes actual demand',/22/.test(await page.locator('.ir-card').innerText()));await back();
 await page.waitForFunction(()=>/Confirmed orders/.test(document.activeElement?.textContent||''));check('records category restore focus',/Confirmed orders/.test(await page.evaluate(()=>document.activeElement?.textContent||'')));await back();
 await choose('History & preferences');await page.getByRole('button',{name:/^Help/}).click();await page.getByRole('heading',{name:'Using FarmTact',exact:true}).waitFor();check('help distinguishes planning Council and research',/Planning Council reviews your ordinary frozen plan/.test(await page.locator('.integrated-tool').innerText()));await shot('help');await back();await page.waitForFunction(()=>/^Help/.test(document.activeElement?.textContent||''));check('history index restores Help focus',/^Help/.test(await page.evaluate(()=>document.activeElement?.textContent||'')));await back();
 check('all root category browsing is provider and mutation free',report.writes.length===baseline,report.writes.slice(baseline));check('no browser errors',!report.errors.length,report.errors);
 await context.storageState({path:'/tmp/farmtact-v17-navigation-state.json'});report.status='PASS';
}catch(e){report.status='FAIL';report.errors.push(String(e));await shot('failure');process.exitCode=1}
finally{await browser.close();await writeFile('reports/v17/navigation/checks.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));}
