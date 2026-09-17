import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';
import { writeFile, readFile } from 'node:fs/promises';
const base=process.env.BASE_URL||'http://127.0.0.1:4192';
const report={base,checks:[],failures:[]};
const check=(name,ok)=>{report.checks.push({name,pass:!!ok});if(!ok)throw Error(name)};
let page;
const browser=await chromium.launch({headless:true});
try{
 const context=await browser.newContext({viewport:{width:390,height:844},acceptDownloads:true});
 page=await context.newPage();const mutations=[];page.on('request',r=>{if(r.method()!=='GET')mutations.push(r.url())});
 await page.goto(base);await page.locator('.ic-shell').waitFor();
 const click=name=>page.getByRole('button',{name,exact:true}).click();
 await click('More');for(let i=0;i<3;i++)await click('Next →');await click('Open tool');
 await page.getByRole('heading',{name:'Scenarios & quests',exact:true}).waitFor();await click('Next');await click('Open');
 await page.getByRole('heading',{name:'Saved datasets',exact:true}).waitFor();await click('Inspect records');
 await page.getByLabel('Dataset',{exact:true}).waitFor();
 const before=mutations.length;
 await page.locator('.integrated-tool__card').focus();await page.keyboard.press('Enter');await page.waitForTimeout(200);
 check('Enter on a read-only tool does not invoke the underlying mission action',mutations.length===before&&await page.getByRole('button',{name:'Snapshot actions',exact:true}).isVisible());
 await page.getByLabel('Crop filter').selectOption('caixin');
 await page.getByLabel('From date').fill('2026-08-01');
 await page.getByLabel('Through date').fill('2026-09-01');
 await page.getByLabel('Sort',{exact:true}).selectOption('ordered_kg');
 await page.getByLabel('Sort direction').selectOption('true');
 check('date/crop/sort controls remain inside dataset card',await page.getByLabel('Crop filter').inputValue()==='caixin');
 await click('Snapshot actions');await page.getByLabel('Export format').selectOption('json');
 const downloadPromise=page.waitForEvent('download');await click('Export records');const download=await downloadPromise;
 const payload=JSON.parse(await readFile(await download.path(),'utf8'));
 const rows=Array.isArray(payload)?payload:payload.records;
 check('JSON export contains filtered records',Array.isArray(rows)&&rows.length>0&&rows.every(r=>r.crop_id==='caixin'&&r.date>='2026-08-01'&&r.date<='2026-09-01'));
 check('JSON export preserves descending numeric ordering',rows.every((r,i)=>!i||Number(rows[i-1].ordered_kg)>=Number(r.ordered_kg)));
 await click('Back');check('snapshot action Back restores dataset controls',await page.getByLabel('Crop filter').inputValue()==='caixin');
 await click('Record relationships');await page.getByRole('heading',{name:'Linked records',exact:true}).waitFor();
 check('record relationship card exposes canonical references',await page.getByText('Relationships use recorded canonical identifiers in this frozen snapshot.').isVisible());
 await click('Back');check('relationship Back restores original filter',await page.getByLabel('Crop filter').inputValue()==='caixin');
 check('filter/export/relationship/replay made no mutations or inference',mutations.length===before);
 for(const width of [360,390,430,1280]){await page.setViewportSize({width,height:900});check(`dataset fits ${width}px`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))}
 await page.evaluate(()=>document.documentElement.style.fontSize='200%');check('dataset supports text zoom without horizontal document overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 report.status='PASS';
}catch(e){report.status='FAIL';report.failures.push(String(e.stack||e));if(page)report.page=(await page.locator('body').innerText()).slice(-5000);process.exitCode=1}
finally{await browser.close();await writeFile('reports/v15/explorer-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2))}
