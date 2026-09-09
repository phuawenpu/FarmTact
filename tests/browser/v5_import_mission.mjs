/** Real-import mission rematch in one isolated local browser tenant. */
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const base=(process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080/v5').replace(/\/$/,'')
const reportPath=resolve(root,process.env.FARMTACT_IMPORT_MISSION_REPORT||'reports/v5/import_mission.json')
const report={status:'RUNNING',base_url:base,tenant_policy:'One fresh isolated browser tenant; shared review storage is not loaded or mutated.',checks:[],failures:[],requests:[],provider_requests:[],numerical_requests:[]}
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),...(detail===undefined?{}:{detail})});if(!pass)report.failures.push({name,detail})}
const pause=()=>new Promise(resolve=>setTimeout(resolve,50))

let browser
try{
  browser=await chromium.launch({headless:true})
  const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'})
  const page=await context.newPage()
  let imported=false,releaseExplorer
  const explorerGate=new Promise(resolve=>{releaseExplorer=resolve})
  const pageErrors=[]
  page.on('pageerror',error=>pageErrors.push(error.message))
  page.on('response',response=>{if(response.request().method()==='POST'&&new URL(response.url()).pathname.endsWith('/api/v1/imports')&&response.status()===201)imported=true})
  page.on('request',request=>{
    const path=new URL(request.url()).pathname,entry={method:request.method(),path}
    report.requests.push(entry)
    if(/deepseek|anthropic|openai/i.test(request.url()))report.provider_requests.push(entry)
    if(request.method()==='POST'&&/(planning-runs|scenarios|conversations)/.test(path))report.numerical_requests.push(entry)
  })
  await page.route('**/api/v1/data-explorer/snapshots**',async route=>{if(imported)await explorerGate;await route.continue()})

  await page.goto(base,{waitUntil:'networkidle'})
  const originalCard=page.getByRole('region',{name:'Current planning mission'}).first()
  await originalCard.waitFor()
  const originalText=await originalCard.innerText()
  check('fresh tenant starts with a real owned-farm mission',/booked for this date/.test(originalText)&&/Snapshot [a-f0-9]{10}/.test(originalText),originalText)

  const farm=await page.evaluate(async()=>{const response=await fetch('/v5/api/v1/farms/demo-farm/snapshot');if(!response.ok)throw Error(`snapshot ${response.status}`);return response.json()})
  const target=farm.orders.find(order=>order.crop_id==='pak_choi'&&order.due_date==='2026-09-21')
  check('raw owned farm contains the dated Pak Choi order',Boolean(target),farm.orders.map(order=>({id:order.id,crop_id:order.crop_id,due_date:order.due_date,quantity_kg:order.quantity_kg})))
  const originalGroup=farm.orders.filter(order=>order.crop_id==='pak_choi'&&order.due_date==='2026-09-21').reduce((sum,order)=>sum+Number(order.quantity_kg)-Number(order.cancelled_kg||0),0)
  target.quantity_kg=Number(target.quantity_kg)+9
  const expected=originalGroup+9

  await page.getByRole('button',{name:'Setup',exact:true}).filter({visible:true}).first().click()
  const chooser=page.locator('input[type=file]')
  const importResponse=page.waitForResponse(response=>response.request().method()==='POST'&&new URL(response.url()).pathname.endsWith('/api/v1/imports'))
  await chooser.setInputFiles({name:'isolated-import.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(farm))})
  const importedResponse=await importResponse
  check('Setup file UI performs a real validated import',importedResponse.status()===201,await importedResponse.text())

  await page.getByRole('button',{name:'Farm',exact:true}).filter({visible:true}).first().click()
  for(let i=0;i<20&&await page.getByRole('region',{name:'Current planning mission'}).count();i++)await pause()
  check('old mission disappears while owned explorer rematch is delayed',await page.getByRole('region',{name:'Current planning mission'}).count()===0)
  check('no stale mission action can run during rematch',await page.getByRole('button',{name:'Test this mission',exact:true}).count()===0)

  releaseExplorer()
  const newCard=page.getByRole('region',{name:'Current planning mission'}).first()
  await newCard.waitFor({timeout:30000})
  const newText=await newCard.innerText()
  const snapshots=await page.evaluate(async()=>{const response=await fetch('/v5/api/v1/data-explorer/snapshots');if(!response.ok)throw Error(`snapshots ${response.status}`);return response.json()})
  const newest=snapshots.snapshots.find(item=>item.kind==='farm'&&item.name.includes('version 2'))
  check('new mission uses changed dated booked quantity',newText.includes(`${expected} kg\nbooked for this date`),{expected,newText})
  check('new mission hash matches imported owned farm snapshot',Boolean(newest)&&newText.includes(`Snapshot ${newest.content_hash.slice(0,10)}`),{newest,newText})
  check('new mission cannot be the prior cached card',newText!==originalText,{before:originalText,after:newText})

  await page.reload({waitUntil:'networkidle'})
  const reloaded=page.getByRole('region',{name:'Current planning mission'}).first()
  await reloaded.waitFor()
  check('reload preserves the imported-farm mission',await reloaded.innerText()===newText,await reloaded.innerText())
  check('journey makes no numerical request',report.numerical_requests.length===0,report.numerical_requests)
  check('journey makes no provider request',report.provider_requests.length===0,report.provider_requests)
  check('browser has no page errors',pageErrors.length===0,pageErrors)
  await context.close()
}catch(error){report.failures.push({name:'suite execution',detail:error instanceof Error?error.stack||error.message:String(error)})}
finally{if(browser)await browser.close();report.status=report.failures.length?'FAIL':'PASS';report.completed_at=new Date().toISOString();await mkdir(dirname(reportPath),{recursive:true});await writeFile(reportPath,JSON.stringify(report,null,2)+'\n')}
console.log(JSON.stringify({status:report.status,checks:report.checks.length,failures:report.failures.length,report:reportPath.replace(root+'/','')}))
if(report.failures.length)process.exitCode=1
