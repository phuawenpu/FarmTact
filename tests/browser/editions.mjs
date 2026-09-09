import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs'
import {mkdir,writeFile} from 'node:fs/promises'
const base=process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080'
const state=process.env.FARMTACT_EDITION_STATE||'/tmp/farmtact-edition-browser-state.json'
const out=process.env.FARMTACT_EDITION_REPORT||'reports/editions/browser.json'
const shots=process.env.FARMTACT_EDITION_SHOTS||'apps/web/screenshots/editions'
const report={status:'RUNNING',base,checks:[],errors:[],requests:[],screenshots:[]}
const check=(name,pass)=>{report.checks.push({name,pass});if(!pass)throw Error(name)}
const browser=await chromium.launch();await mkdir(shots,{recursive:true});let page
try{
 const anonymous=await browser.newContext();const chooser=await anonymous.newPage()
 await chooser.goto(base,{waitUntil:'domcontentloaded'});await chooser.getByRole('link',{name:'Play V2'}).waitFor()
 check('Chooser creates no game session',(await anonymous.cookies()).length===0);await anonymous.close()
 const context=await browser.newContext({storageState:state,viewport:{width:390,height:900},hasTouch:true,reducedMotion:'reduce'})
 await context.addInitScript(()=>{const NativeAudio=window.Audio;window.__editionAudio=[];window.Audio=function(...args){const audio=new NativeAudio(...args);window.__editionAudio.push(audio);return audio}})
 page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>{const path=new URL(r.url()).pathname;if(path.includes('/api/')||path.includes('/art/')||path.includes('/audio/'))report.requests.push({path,method:r.method()})})
 const visible=locator=>locator.filter({visible:true}).first()
 for(const width of [360,390,430,1280]){
  await page.setViewportSize({width,height:900})
  await page.goto(`${base}/`,{waitUntil:'domcontentloaded'});await page.getByRole('link',{name:'Play V1'}).waitFor()
  check(`${width}: chooser fits viewport`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await page.getByRole('link',{name:'Play V1'}).click();await page.getByRole('group',{name:'Farm map',exact:true}).waitFor()
  check(`${width}: v1 is silent`,await page.getByRole('button',{name:'Turn sound on'}).count()===0)
  if(width<700)await page.getByRole('button',{name:'Workspace status'}).click()
  const select=visible(page.getByLabel('Choose FarmTact edition'));await select.selectOption('v2')
  await page.waitForURL('**/v2/');await page.getByRole('group',{name:'Farm map',exact:true}).waitFor()
  check(`${width}: selector reaches independent v2`,await visible(page.getByRole('button',{name:'Turn sound on'})).isVisible())
  check(`${width}: v2 game fits viewport`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await page.screenshot({path:`${shots}/v2-${width}.png`});report.screenshots.push(`${shots}/v2-${width}.png`)
  await page.goto(`${base}/v2/changes`,{waitUntil:'domcontentloaded'});await page.getByRole('heading',{name:'What changed',exact:true}).waitFor()
  check(`${width}: changes load from public registry`,await page.getByRole('link',{name:'Git source'}).isVisible())
  check(`${width}: changes fit viewport`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await page.goto(`${base}/v1/review`,{waitUntil:'domcontentloaded'});await page.locator('.review-card').first().waitFor()
  check(`${width}: original reviews remain inspectable`,await page.locator('.review-card').count()===10)
  check(`${width}: review fits viewport`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
 }
 await page.setViewportSize({width:390,height:900});await page.goto(`${base}/v2/`,{waitUntil:'domcontentloaded'});await page.getByRole('group',{name:'Farm map',exact:true}).waitFor()
 check('No audio loads before enabling',!report.requests.some(r=>r.path.includes('/audio/')))
 await visible(page.getByRole('button',{name:'Turn sound on'})).click()
 await page.waitForFunction(()=>window.__editionAudio.some(a=>a.loop&&a.readyState>=2&&!a.paused),{timeout:15000})
 check('Original WAV decodes and plays with native browser audio',await page.evaluate(()=>window.__editionAudio.some(a=>a.duration>1&&a.loop&&!a.paused)))
 await visible(page.getByRole('button',{name:'Turn sound off'})).click()
 check('Master mute pauses every audio player',await page.evaluate(()=>window.__editionAudio.every(a=>a.paused)))
 await page.getByRole('button',{name:'Talk to advisors',exact:true}).click();await page.getByText('Voice typing: use the microphone on your device keyboard, if available.').waitFor()
 check('Native keyboard voice-typing hint is present',true)
 check('All art/audio requests stay edition-pinned',report.requests.filter(r=>/\/(art|audio)\//.test(r.path)).every(r=>/^\/v[12]\//.test(r.path)))
 check('No unversioned game API requests',report.requests.filter(r=>r.path.includes('/api/')).every(r=>r.path==='/api/releases'||/^\/v[12]\/api\//.test(r.path)))
 check('Browsing makes no provider submissions',report.requests.every(r=>r.method==='GET'))
 check('No page errors',report.errors.length===0)
 report.status='PASS'
}catch(error){report.status='FAIL';report.errors.push(String(error));if(page)await page.screenshot({path:`${shots}/failure.png`}).catch(()=>{});process.exitCode=1}
finally{await browser.close();await writeFile(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,errors:report.errors}))}
