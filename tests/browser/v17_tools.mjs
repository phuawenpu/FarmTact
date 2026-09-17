import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { access, mkdir, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root=resolve(new URL('../..',import.meta.url).pathname)
const base=(process.env.BASE_URL||'http://127.0.0.1:4196').replace(/\/$/,'')
const storage=process.env.STORAGE_STATE||'/tmp/farmtact-v15-cards-storage.json'
const out=resolve(root,'reports/v17/tools')
await Promise.all([access(storage),mkdir(out,{recursive:true})])
const browser=await chromium.launch({headless:true})
const context=await browser.newContext({storageState:storage,viewport:{width:390,height:844},reducedMotion:'reduce'})
const page=await context.newPage(), writes=[], provider=[], errors=[], checks=[], screenshots=[]
page.on('request',request=>{const path=new URL(request.url()).pathname;if(!['GET','HEAD','OPTIONS'].includes(request.method()))writes.push(`${request.method()} ${path}`);if(/provider|deepseek|inference/i.test(request.url()))provider.push(`${request.method()} ${path}`)})
page.on('pageerror',error=>errors.push(error.message))
await page.route(`${base}/api/**`,route=>['GET','HEAD','OPTIONS'].includes(route.request().method())?route.continue():route.abort('blockedbyclient'))
const check=(name,pass,detail='')=>{checks.push({name,pass,detail});if(!pass)throw new Error(`${name}: ${detail}`)}
const snap=async name=>{await page.screenshot({path:resolve(out,`${name}.png`),fullPage:true});screenshots.push(`${name}.png`)}
async function openTools(){if(await page.getByRole('button',{name:'More',exact:true}).isVisible())await page.getByRole('button',{name:'More',exact:true}).click();await page.locator('.ic-card h1').waitFor()}
async function openTool(title){
 await openTools()
 const direct=page.locator('.ic-card').getByRole('button',{name:new RegExp(title,'i')}).first()
 if(await direct.isVisible()){await direct.click();await page.locator('.integrated-tool,.ik-shell').first().waitFor();return}else{
  const previous=page.locator('.ic-deck-nav button:first-child');while(await previous.isEnabled())await previous.click()
  for(let i=0;i<6;i++){if((await page.locator('.ic-card h1').innerText()).includes(title))break;const next=page.locator('.ic-deck-nav button:last-child');if(!await next.isEnabled())break;await next.click()}
 }
 check(`tool index reaches ${title}`,(await page.locator('.ic-card h1').innerText()).includes(title))
 await page.getByRole('button',{name:'Open tool',exact:true}).click()
}
async function closeIntegrated(){await page.getByRole('button',{name:'Back',exact:true}).last().click();await page.locator('.ic-card h1').waitFor()}
try{
 await page.goto(`${base}/play`,{waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor({timeout:45000});const skip=page.getByRole('button',{name:'Skip demonstration',exact:true});if(await skip.isVisible())await skip.click()
 await openTool('Knowledge')
 await page.getByRole('heading',{name:'Choose what you need'}).waitFor();check('knowledge index exposes three scanable categories',await page.getByRole('heading',{name:'Crops',exact:true}).isVisible()&&await page.getByRole('heading',{name:'Sources',exact:true}).isVisible()&&await page.getByRole('heading',{name:'Specialists',exact:true}).isVisible());check('seven specialists visible',await page.locator('.ik-picker.is-people button').count()===7,String(await page.locator('.ik-picker.is-people button').count()));await snap('01-knowledge-index-390')
 const search=page.getByRole('searchbox',{name:'Find a crop'});await search.fill('caixin');const crop=page.locator('.ik-category').first().getByRole('button',{name:/Caixin/i}).first();check('crop search narrows atlas',await page.locator('.ik-category').first().locator('.ik-picker button').count()===1);await crop.focus();await crop.click();await page.getByRole('heading',{name:/Caixin/i}).waitFor();await snap('02-crop-profile-390');await page.getByRole('button',{name:'Back',exact:true}).last().click();await search.waitFor();await page.waitForFunction(()=>document.activeElement?.textContent?.includes('Caixin'));check('crop Back restores exact picker focus',await crop.evaluate(node=>node===document.activeElement));check('crop search draft retained',await search.inputValue()==='caixin');await snap('03-crop-return-390')
 await closeIntegrated();await openTool('Experiments');await page.getByRole('heading',{name:'Experiments & data'}).waitFor();check('experiments landing names five choices',await page.locator('.ie-choice-grid button').count()===5);await snap('04-experiments-index-390')
 await page.getByRole('button',{name:/Data Explorer/}).click();await page.getByRole('heading',{name:'Saved datasets'}).waitFor();const overview=await page.locator('.integrated-tool__card').innerText();check('dataset overview exposes frozen identity',/Snapshot/.test(overview)&&/Content hash/.test(overview),overview.slice(0,180));await snap('05-data-overview-390')
 const inspect=page.getByRole('button',{name:'Inspect records',exact:true});check('real saved snapshot is inspectable',await inspect.isEnabled());await inspect.click();await page.getByRole('heading',{name:/Dataset/}).waitFor();const chart=page.locator('.explorer-chart');check('actual snapshot renders accessible chart or truthful empty state',await chart.count()===1||await page.locator('.explorer-empty').count()===1);if(await chart.count()){const box=await chart.boundingBox();check('chart fits mobile card',!!box&&box.width<=390,JSON.stringify(box));check('chart has accessible time-series title',/Time series/.test(await chart.locator('title').innerText()))}await snap('06-data-records-chart-390')
 await page.getByRole('button',{name:'Back',exact:true}).last().click();await page.getByRole('button',{name:'Back',exact:true}).last().click();await page.getByRole('heading',{name:'Experiments & data'}).waitFor();await page.getByRole('button',{name:/Council research study/}).click();await page.getByRole('heading',{name:'Council research study'}).waitFor();await page.getByRole('button',{name:'Open research study'}).click();await page.getByRole('heading',{name:'Saved Council research'}).waitFor();const openSaved=page.getByRole('button',{name:'Open saved study'});check('saved Council study available without creating data',await openSaved.isVisible());await openSaved.click();await page.getByRole('heading',{name:/Council research v/}).waitFor();check('research overview exposes complete study path',await page.locator('.ix-jump-grid button').count()===9,String(await page.locator('.ix-jump-grid button').count()));await snap('07-research-overview-390')
 await page.getByRole('button',{name:/Scripted discussion/}).click();await page.getByRole('heading',{name:'Scripted Council transcript'}).waitFor();check('complete saved transcript remains reachable',await page.locator('.ix-transcript article').count()>0,String(await page.locator('.ix-transcript article').count()));await snap('08-research-transcript-390');await page.getByRole('button',{name:'Back',exact:true}).last().click();await page.getByRole('heading',{name:/Council research v/}).waitFor();check('research detail returns to narrative overview',true)
 check('no write or provider request during discovery',writes.length===0&&provider.length===0,JSON.stringify({writes,provider}));check('no browser errors',errors.length===0,errors.join(' | '))
}catch(error){errors.push(error instanceof Error?error.stack:String(error));try{await snap('failure')}catch{}}
const status=errors.length||writes.length||provider.length||checks.some(row=>!row.pass)?'FAIL':'PASS'
const report={status,base,viewport:{width:390,height:844},scope:'Read-only V17 Knowledge, Experiments, Data Explorer and Council research discoverability; existing saved tenant; provider and all writes blocked.',checks,writes,provider,errors,screenshots}
await writeFile(resolve(out,'browser.json'),JSON.stringify(report,null,2)+'\n');await context.close();await browser.close();console.log(JSON.stringify(report,null,2));if(status!=='PASS')process.exitCode=1
