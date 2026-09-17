import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'

const base=(process.env.BASE_URL||'http://127.0.0.1:4196').replace(/\/$/,'')
const storage=process.env.STORAGE_STATE||'/tmp/farmtact-v15-records-extended-storage.json'
const reportPath=resolve(process.env.REPORT_PATH||'reports/v17/adapters.json')
const report={status:'RUNNING',build:null,checks:[],writes:[],failures:[],scope:'Existing acceptance tenant; navigation and local draft state only. Every API write is blocked.'}
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)throw new Error(`${name}: ${JSON.stringify(detail)}`)}
const visible=(page,name)=>page.getByRole('button',{name,exact:true}).filter({visible:true}).first()
const click=(page,name)=>visible(page,name).click()
const skip=async page=>{const button=visible(page,'Skip demonstration');if(await button.isVisible().catch(()=>false))await button.click()}
const resetMission=async page=>{await page.goto(base,{waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();const session=await page.evaluate(async()=>{const list=await(await fetch('/api/v1/planning-sessions')).json();return list.sessions?.[0]?.id});await page.evaluate(id=>{for(const key of Object.keys(localStorage))if(key.includes('integrated-cards-navigation:')||key.includes('first-use-demo:'))localStorage.removeItem(key)},session);await page.reload({waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();await skip(page);return session}
async function seek(page,buttonName){
 for(let i=0;i<14;i++){const previous=page.locator('.ic-deck-nav button').first();if(!await previous.isVisible().catch(()=>false)||await previous.isDisabled())break;await previous.click()}
 for(let i=0;i<14;i++){
  if(await visible(page,buttonName).isVisible().catch(()=>false))return true
  const next=page.getByRole('button',{name:/Next/}).filter({visible:true}).first();if(!await next.isVisible().catch(()=>false)||await next.isDisabled())break;await next.click()
 }
 return false
}
async function seekAny(page,names){for(let i=0;i<14;i++){const previous=page.locator('.ic-deck-nav button').first();if(!await previous.isVisible().catch(()=>false)||await previous.isDisabled())break;await previous.click()}for(let i=0;i<14;i++){for(const name of names)if(await visible(page,name).isVisible().catch(()=>false))return name;const next=page.getByRole('button',{name:/Next/}).filter({visible:true}).first();if(!await next.isVisible().catch(()=>false)||await next.isDisabled())break;await next.click()}return ''}
async function openToolIndex(page,label){await click(page,'More');const button=page.locator('.ic-tool-index').getByRole('button',{name:new RegExp(`^${label}\\b`,'i')}).filter({visible:true}).first();await button.waitFor();await button.click()}

let browser
try{
 browser=await chromium.launch({headless:true});const context=await browser.newContext({storageState:storage,viewport:{width:390,height:844},reducedMotion:'reduce'}),page=await context.newPage()
 page.on('request',request=>{if(!['GET','HEAD','OPTIONS'].includes(request.method()))report.writes.push(`${request.method()} ${new URL(request.url()).pathname}`)})
 await page.route('**/api/v1/**',route=>['GET','HEAD','OPTIONS'].includes(route.request().method())?route.continue():route.abort('blockedbyclient'))
 const sessionId=await resetMission(page);report.build=await page.locator('script[type=module]').first().getAttribute('src')

 const workLabel=await seekAny(page,['Review sandbox work','Open work records']);check('approved-task primary action is present',!!workLabel,await page.locator('.ic-card').innerText());await click(page,workLabel)
 await page.getByRole('heading',{name:'Tasks & results',exact:true}).waitFor();check('approved-task primary opens targeted Tasks & results',true,workLabel)
 await click(page,'Back');await visible(page,workLabel).waitFor();await page.waitForFunction(label=>document.activeElement?.textContent?.trim()===label,workLabel);check('targeted Records Back restores mission primary focus',true,await page.evaluate(()=>document.activeElement?.textContent?.trim()))

 await resetMission(page);check('recorded simulation primary action is present',await seek(page,'Open simulation history'),await page.locator('.ic-card').innerText());await click(page,'Open simulation history')
 await page.getByRole('heading',{name:'Simulations',exact:true}).waitFor();check('simulation primary opens targeted Simulations history',true)
 await click(page,'Back');await visible(page,'Open simulation history').waitFor();await page.waitForFunction(()=>document.activeElement?.textContent?.trim()==='Open simulation history');check('targeted History Back restores mission primary focus',true,await page.evaluate(()=>document.activeElement?.textContent?.trim()))

 await resetMission(page);check('strategy contextual schedule action is present',await seek(page,'Dated schedule'),await page.locator('.ic-card').innerText());await click(page,'Dated schedule')
 await page.getByRole('heading',{name:'Strategies & allocation schedules',exact:true}).waitFor();const planCard=await page.locator('[data-card-id^="plan:strategies:"]').evaluate(node=>({id:node.getAttribute('data-card-id'),kind:node.getAttribute('data-entity-kind')}))
 check('direct Strategies target renders the strategy card identity without Objectives fallback',planCard.id?.startsWith('plan:strategies:')&&planCard.kind==='strategy'&&!await page.getByRole('heading',{name:'Objectives and all demand',exact:true}).isVisible().catch(()=>false),planCard);await click(page,'Back')

 await resetMission(page);const legacyPlan='LEGACY-UNSCOPED-PLAN-DRAFT',legacyFarm='LEGACY-UNSCOPED-FARM-DRAFT'
 const live=await page.evaluate(async id=>await(await fetch(`/api/v1/planning-sessions/${id}`)).json(),sessionId),fixtureA={...live,id:'adapter-session-a',name:'Adapter farm A'},fixtureB={...live,id:'adapter-session-b',name:'Adapter farm B'}
 const planningFixture=route=>{if(route.request().method()!=='GET')return route.abort('blockedbyclient');const path=new URL(route.request().url()).pathname,id=path.split('/').at(-1);return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(path.endsWith('/planning-sessions')?{sessions:[fixtureA,fixtureB]}:id===fixtureB.id?fixtureB:fixtureA)})}
 await page.route('**/api/v1/planning-sessions',planningFixture);await page.route('**/api/v1/planning-sessions/**',planningFixture)
 await page.evaluate(([plan,farm])=>{localStorage.setItem('farmtact:v17:planning-assumptions-draft',plan);localStorage.setItem('farmtact:v17:records:v15-farm-json-draft',JSON.stringify(farm))},[legacyPlan,legacyFarm])
 const openAssumptions=async id=>{await page.evaluate(value=>{localStorage.setItem('farmtact:v17:planning-session',value);for(const key of Object.keys(localStorage))if(key.includes('integrated-cards-navigation:')||key.includes('first-use-demo:'))localStorage.removeItem(key)},id);await page.reload({waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();await skip(page);await openToolIndex(page,'Plan');await page.locator('.tool-category-index').getByRole('button',{name:/Resources & assumptions/}).click();await page.getByRole('heading',{name:'Resource & demand assumptions',exact:true}).waitFor();const bound=await page.locator('[data-card-id^="plan:assumptions:"]').getAttribute('data-session-id');check(`Plan assumptions binds requested ${id}`,bound===id,{requested:id,bound});await page.getByText('Import saved settings',{exact:true}).click()}
 await openAssumptions(fixtureA.id);const initialA=await page.getByLabel('Planning assumptions JSON').inputValue();check('session A ignores the historical unscoped Plan draft',!initialA.includes(legacyPlan),initialA.slice(0,80));const draftA=JSON.stringify({...fixtureA.assumptions,capacity:{cash_sgd:111}},null,2);await page.getByLabel('Planning assumptions JSON').fill(draftA);await page.waitForFunction(id=>localStorage.getItem(`farmtact:v17:planning-assumptions-draft:${id}`)?.includes('111'),fixtureA.id)
 await openAssumptions(fixtureB.id);const initialB=await page.getByLabel('Planning assumptions JSON').inputValue(),initialBValue=JSON.parse(initialB);check('session B does not inherit session A Plan draft',initialBValue.capacity?.cash_sgd!==111&&!initialB.includes(legacyPlan),{capacity:initialBValue.capacity});const draftB=JSON.stringify({...fixtureB.assumptions,capacity:{cash_sgd:222}},null,2);await page.getByLabel('Planning assumptions JSON').fill(draftB);await page.waitForFunction(id=>JSON.parse(localStorage.getItem(`farmtact:v17:planning-assumptions-draft:${id}`)||'{}').capacity?.cash_sgd===222,fixtureB.id)
 await openAssumptions(fixtureA.id);const restoredA=await page.getByLabel('Planning assumptions JSON').inputValue(),restoredAValue=JSON.parse(restoredA),planKeys=await page.evaluate(()=>Object.keys(localStorage).filter(key=>key.includes('planning-assumptions-draft')));check('Plan restores only the selected session draft',restoredAValue.capacity?.cash_sgd===111&&planKeys.includes('farmtact:v17:planning-assumptions-draft:adapter-session-a')&&planKeys.includes('farmtact:v17:planning-assumptions-draft:adapter-session-b'),{planKeys,capacity:restoredAValue.capacity})
 await click(page,'Back');await click(page,'Back');await page.locator('.ic-tool-index').getByRole('button',{name:/^Records & work\b/i}).click();await page.getByRole('button',{name:/Farm setup/}).click();await click(page,'Review farm JSON')
 const farmDraft=await page.getByLabel('Farm JSON').inputValue(),recordKeys=await page.evaluate(()=>Object.keys(localStorage).filter(key=>key.includes('farm-json-draft')))
 check('Records ignores the historical unscoped farm draft and creates a session-scoped key',farmDraft!==legacyFarm&&recordKeys.includes('farmtact:v17:records:adapter-session-a:v15-farm-json-draft'),{recordKeys,farmDraft})
 check('adapter audit performs no API writes',report.writes.length===0,report.writes)
 report.status='PASS';await context.close()
}catch(error){report.status='FAIL';report.failures.push(error instanceof Error?error.stack:String(error));process.exitCode=1}
finally{await browser?.close();await mkdir(dirname(reportPath),{recursive:true});await writeFile(reportPath,JSON.stringify(report,null,2)+'\n')}
console.log(`V17 adapters ${report.status}: ${report.checks.filter(item=>item.pass).length}/${report.checks.length}`)
