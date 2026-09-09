/** Focused semantic assertions over the V5 fixture and rendered decision evidence. */
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const base=(process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080').replace(/\/$/,'')
const state=process.env.FARMTACT_BROWSER_STATE
const browser=await chromium.launch({headless:true})
const context=await browser.newContext({viewport:{width:390,height:844},...(state?{storageState:state}:{})})
const page=await context.newPage()
const assert=(condition,message)=>{if(!condition)throw Error(message)}
try{
  await page.goto(`${base}/`,{waitUntil:'networkidle'})
  const mission=page.getByRole('region',{name:'Current planning mission'}).first()
  const text=await mission.innerText()
  assert(/28 kg\s+booked for this date/.test(text),'mission must use dated booked orders')
  assert(/week’s statistical forecast is 33 kg/.test(text),'weekly forecast must remain separately labelled context')
  assert(/35-day recipe/.test(text)&&!/37-day recipe/.test(text),'maturity must add nursery and grow days without sanitation turnaround')
  assert(/0 kg\s+harvest eligible by shelf life/.test(text),'expired prior harvest must not cover the dated order')

  await mission.getByRole('button',{name:'Test this mission',exact:true}).click()
  const lab=page.getByRole('dialog',{name:'Scenario lab'})
  const resume=lab.getByRole('button',{name:/Resume last result/})
  if(await resume.count()){
    await resume.click()
    const perspectives=lab.getByRole('region',{name:/Computed numerical perspectives for Balanced/})
    const evidence=await perspectives.innerText()
    assert(/(increases|decreases) by|is unchanged/.test(evidence),'deltas must retain direction')
    assert(!/changes by -/.test(evidence),'deltas must not hide direction behind an absolute value')
  }

  await page.keyboard.press('Escape')
  await page.evaluate(()=>sessionStorage.setItem('farmtact:v5:decision-mission',JSON.stringify({version:'dated-order-mission-v1',mission:{bookedKg:null,date:'broken'}})))
  await page.reload({waitUntil:'networkidle'})
  const repaired=await page.getByRole('region',{name:'Current planning mission'}).first().innerText()
  assert(/booked for this date/.test(repaired)&&!/broken/.test(repaired),'malformed cached mission must be discarded and rederived')
  console.log(JSON.stringify({status:'PASS',checks:6}))
}finally{await context.close();await browser.close()}
