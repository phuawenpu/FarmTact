/** Focused V5 decision-loop acceptance. Uses a real numerical branch and no inference. */
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'

const base=(process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080').replace(/\/$/,'')
const state=process.env.FARMTACT_BROWSER_STATE
const reportPath=process.env.FARMTACT_V5_GAME_REPORT||'reports/v5/game_browser.json'
const shots=process.env.FARMTACT_V5_GAME_SHOTS||'apps/web/screenshots/v5-game'
const report={status:'RUNNING',base_url:base,checks:[],failures:[],page_errors:[],inference_requests:[],screenshots:[],scenario_id:null}
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)throw Error(`${name}: ${JSON.stringify(detail)}`)}
await mkdir(shots,{recursive:true})
const browser=await chromium.launch({headless:true})
try{
  const context=await browser.newContext({viewport:{width:360,height:844},hasTouch:true,reducedMotion:'reduce',...(state?{storageState:state}:{})})
  const page=await context.newPage()
  page.on('pageerror',error=>report.page_errors.push(error.message))
  page.on('request',request=>{if(request.method()==='POST'&&/\/conversations\/[^/]+\/(messages|invite|council)$/.test(new URL(request.url()).pathname))report.inference_requests.push(request.url())})
  await page.goto(`${base}/`,{waitUntil:'networkidle'})
  const mission=page.getByRole('region',{name:'Current planning mission'}).first()
  await mission.waitFor()
  check('entry presents a dated quantified booked-order mission',/due \d{1,2} \w+ \d{4}/.test(await mission.innerText())&&/kg\s+booked for this date/.test(await mission.innerText()),await mission.innerText())
  check('mission labels gap as provisional and discloses allocation limit',/provisional supply gap/i.test(await mission.innerText())&&/does not allocate an eligible harvest or inventory lot/i.test(await mission.innerText()))
  check('reference mission uses dated order, weekly forecast context and biological stages correctly',/Pak Choi due 21 Sept 2026/.test(await mission.innerText())&&/28 kg\s+booked for this date/.test(await mission.innerText())&&/week’s statistical forecast is 33 kg/.test(await mission.innerText())&&/declared 35-day recipe/.test(await mission.innerText())&&/13 Oct 2026/.test(await mission.innerText()),await mission.innerText())
  check('mission exposes snapshot and linked record count',/Snapshot [a-f0-9]{10}/.test(await mission.innerText())&&/linked (?:input )?records/.test(await mission.innerText()))
  await mission.getByRole('button',{name:/Inspect \d+ linked input records/}).click();await mission.locator('.decision-mission__records details').first().waitFor()
  check('mission reveals actual contributing records before assumptions change',await mission.locator('.decision-mission__records details').count()>0&&/order|forecast|demand/i.test(await mission.locator('.decision-mission__records').innerText()))
  await page.screenshot({path:`${shots}/mission-360.png`,animations:'disabled',fullPage:true});report.screenshots.push(`${shots}/mission-360.png`)
  await mission.getByRole('button',{name:'Test this mission',exact:true}).click()
  const lab=page.getByRole('dialog',{name:'Scenario lab'});await lab.waitFor()
  check('mission survives into Scenario Lab',await lab.getByRole('region',{name:'Current planning mission'}).isVisible())
  check('scenario distinguishes calculation time from farm time',/main farm and its latest run remain unchanged/i.test(await lab.locator('.preview-note').innerText()))
  const demand=lab.getByRole('spinbutton',{name:'Market demand numeric value',exact:true})
  await demand.fill('137')
  check('exact numeric input synchronizes with range',await lab.getByRole('slider',{name:'Market demand',exact:true}).inputValue()==='137')
  const createdResponse=page.waitForResponse(response=>response.request().method()==='POST'&&/\/api\/v1\/scenarios$/.test(new URL(response.url()).pathname))
  await lab.getByRole('button',{name:'Run experiment',exact:true}).click()
  report.scenario_id=(await (await createdResponse).json()).id||null
  await lab.getByText(/Calculation time · waiting for the numerical worker and solver/).waitFor()
  check('waiting state says farm time is not advancing',await lab.getByText(/Farm time is not advancing/).isVisible())
  await lab.getByRole('heading',{name:'Inspect the trade-offs',exact:true}).waitFor({timeout:180000})
  const perspective=lab.getByRole('region',{name:/Computed numerical perspectives for Balanced/})
  await perspective.waitFor()
  check('all seven computed role perspectives are visible',await perspective.locator('.perspective-card').count()===7,await perspective.locator('.perspective-card h4').allTextContents())
  check('computed cards explicitly deny inference and agent-message status',/numerical, no inference/i.test(await perspective.innerText())&&/not agent messages/i.test(await perspective.innerText()))
  check('weather honestly reports an unchanged input',/No weather control changed/i.test(await perspective.innerText()))
  check('market assumption is not presented as observed sentiment',/player assumption, not observed market sentiment/i.test(await perspective.innerText()))
  check('numerical deltas retain their direction',/(increases|decreases|is unchanged) by|is unchanged/i.test(await perspective.innerText())&&!/changes by -/.test(await perspective.innerText()),await perspective.innerText())
  check('paid council remains a deliberate later action',/paid council interpretation/i.test(await perspective.innerText())&&await lab.getByRole('button',{name:/Open Asha · paid council only after you send/}).isVisible())
  await page.screenshot({path:`${shots}/perspectives-360.png`,animations:'disabled',fullPage:true});report.screenshots.push(`${shots}/perspectives-360.png`)
  await page.reload({waitUntil:'networkidle'});await page.getByRole('group',{name:'Farm map',exact:true}).waitFor()
  check('mission context survives reload',await page.getByRole('region',{name:'Current planning mission'}).first().isVisible())
  await page.getByRole('button',{name:'Scenario lab',exact:true}).click()
  const reopened=page.getByRole('dialog',{name:'Scenario lab'});const resume=reopened.getByRole('button',{name:/Resume saved result/});await resume.waitFor({timeout:15000});await resume.click()
  check('saved result has an obvious recovery action after reload',await reopened.getByRole('heading',{name:'Inspect the trade-offs',exact:true}).isVisible())
  for(const width of [360,390,430,1280]){
    await page.setViewportSize({width,height:width===1280?900:844})
    check(`${width}px has no document overflow`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,innerWidth})))
    const boxes=await reopened.locator('button,input:not([type=checkbox]),select').filter({visible:true}).evaluateAll(nodes=>nodes.slice(0,30).map(node=>{const b=node.getBoundingClientRect();return{w:b.width,h:b.height,label:node.getAttribute('aria-label')||node.textContent?.trim().slice(0,24)}}))
    check(`${width}px visible scenario controls remain usable`,boxes.every(box=>box.h>=40),boxes.filter(box=>box.h<40))
    const image=`${shots}/result-${width}.png`;await page.screenshot({path:image,animations:'disabled',fullPage:true});report.screenshots.push(image)
  }
  await page.keyboard.press('Escape')
  await page.evaluate(()=>sessionStorage.setItem('farmtact:v5:decision-mission',JSON.stringify({expectedKg:999,date:'bad-old-schema'})))
  await page.reload({waitUntil:'networkidle'});await page.getByRole('group',{name:'Farm map',exact:true}).waitFor()
  const repaired=page.getByRole('region',{name:'Current planning mission'}).first();await repaired.waitFor()
  check('malformed or old mission cache is discarded and rederived',!/999/.test(await repaired.innerText())&&/booked for this date/.test(await repaired.innerText()),await repaired.innerText())
  await page.getByRole('button',{name:'Data',exact:true}).filter({visible:true}).first().click();await page.locator('.explorer-page').waitFor()
  const snapshots=page.getByRole('combobox',{name:'Dataset snapshot',exact:true});await snapshots.locator('option').first().waitFor({state:'attached',timeout:15000});const options=await snapshots.locator('option').evaluateAll(nodes=>nodes.map(node=>({value:node.value,text:node.textContent||''})))
  let owned=options.find(option=>option.value.startsWith('saved:')||option.value.startsWith('scenario:'))
  if(!owned){
    const reference=options.find(option=>option.value==='reference'||option.value.startsWith('reference:'))
    check('reference playground fixture is available for persistence check',Boolean(reference),options)
    await snapshots.selectOption(reference.value)
    await page.getByRole('button',{name:'Generator',exact:true}).click()
    await page.getByLabel('Saved dataset name').fill(`V5 review ${Date.now()}`)
    const savedResponse=page.waitForResponse(response=>response.request().method()==='POST'&&/\/api\/v1\/data-explorer\/snapshots$/.test(new URL(response.url()).pathname))
    await page.getByRole('button',{name:'Save dataset',exact:true}).click()
    const saved=await (await savedResponse).json()
    owned={value:saved.id,text:saved.name||saved.id}
    await snapshots.waitFor();await snapshots.selectOption(owned.value)
  }
  if(owned){
    await snapshots.selectOption(owned.value);await page.getByRole('button',{name:'Run from this frozen dataset',exact:true}).waitFor();await page.getByRole('button',{name:'Run from this frozen dataset',exact:true}).click()
    check('saved-snapshot mission stays on its owned Experiments path',await page.getByRole('button',{name:'Experiments',exact:true}).getAttribute('class')==='is-active'&&await snapshots.inputValue()===owned.value,owned)
    await page.reload({waitUntil:'networkidle'});await page.locator('.explorer-page').waitFor()
    check('saved snapshot and Data destination survive reload',await page.getByRole('combobox',{name:'Dataset snapshot',exact:true}).inputValue()===owned.value)
  } else check('saved-snapshot preservation fixture is available',false,options)
  await page.getByRole('button',{name:'Farm',exact:true}).filter({visible:true}).first().click();await page.getByRole('group',{name:'Farm map',exact:true}).waitFor()
  const farmMissionText=await page.getByRole('region',{name:'Current planning mission'}).first().innerText(),farmHash=/Snapshot ([a-f0-9]{10})/.exec(farmMissionText)?.[1]||''
  const foreign=await page.evaluate(async prefix=>{const response=await fetch('api/v1/scenarios');const rows=await response.json();return (Array.isArray(rows)?rows:rows.items||[]).find(item=>String(item.comparison_root||'').startsWith('playground:'))||(Array.isArray(rows)?rows:rows.items||[]).find(item=>item.baseline_hash&&!String(item.baseline_hash).startsWith(prefix))||null},farmHash)
  if(foreign){
    await page.evaluate(id=>sessionStorage.setItem('farmtact:v5:selected-scenario',id),foreign.id)
    await page.reload({waitUntil:'networkidle'});if(await page.locator('.explorer-page').count())await page.getByRole('button',{name:'Farm',exact:true}).filter({visible:true}).first().click()
    await page.getByRole('button',{name:'Scenario lab',exact:true}).click();const guarded=page.getByRole('dialog',{name:'Scenario lab'});await guarded.waitFor()
    const resumeText=await guarded.getByRole('button',{name:/Resume saved result/}).allTextContents()
    check('main-farm reload never resumes an explorer-root result',resumeText.every(text=>!text.includes(foreign.name)),{foreign:foreign.name,resumeText})
    await guarded.locator('.scenario-steps button').filter({hasText:'Compare'}).click()
    const foreignChoice=guarded.locator('.branch-picker label').filter({hasText:foreign.name}).locator('input')
    if(await foreignChoice.count())check('mixed-root branch cannot join the selected main-farm comparison',await foreignChoice.isDisabled(),foreign.name)
  }
  check('numerical journey makes no inference submission',report.inference_requests.length===0,report.inference_requests)
  check('journey raises no page errors',report.page_errors.length===0,report.page_errors)
  report.status='PASS';await context.close()
}catch(error){report.status='FAIL';report.failures.push(error instanceof Error?error.stack||error.message:String(error));process.exitCode=1}
finally{await browser.close();report.completed_at=new Date().toISOString();await writeFile(reportPath,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,failures:report.failures.length,report:reportPath}))}
