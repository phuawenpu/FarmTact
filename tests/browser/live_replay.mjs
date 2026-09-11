/** Inspect the bounded live release transcript without requesting inference. */
import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
const state=JSON.parse(await readFile('/tmp/farmtact-gameplay-release.json','utf8'))
const report={status:'RUNNING',base_url:state.url,checks:[],screenshots:[],inference_posts:0}
const check=(name,pass)=>{report.checks.push({name,pass});if(!pass)throw Error(name)}
const browser=await chromium.launch()
try {
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'})
 await context.addCookies([{name:'farmtact_session',value:state.cookie,url:state.url,httpOnly:true,secure:true}])
 const page=await context.newPage(),errors=[]
 page.on('pageerror',e=>errors.push(e.message))
 page.on('request',r=>{if(r.method()==='POST'&&/\/conversations\/[^/]+\/(messages|invite|council)$/.test(new URL(r.url()).pathname))report.inference_posts++})
 await page.goto(state.url,{waitUntil:'networkidle'})
 await page.getByRole('button',{name:'Talk to advisors',exact:true}).click()
 await page.getByRole('button',{name:'Talk to Mei',exact:true}).click()
 const dialog=page.getByRole('dialog',{name:'Mei · Crop scientist'})
 await dialog.getByRole('combobox',{name:'Saved discussions'}).selectOption(state.conversation_id)
 await dialog.locator('.message-card--advisor').nth(10).waitFor()
 report.advisor_card_count=await dialog.locator('.message-card--advisor').count(); check('Live transcript contains eleven persisted advisor replies',report.advisor_card_count===11)
 check('Council shows all six speakers',await dialog.getByLabel('Council speakers').locator('span').count()===6)
 check('Final critic conclusion is visible',await dialog.getByText('Critic’s conclusion',{exact:true}).isVisible())
 check('Legacy tool references render as qualitative context',await dialog.getByText('Qualitative context references',{exact:true}).count()>0)
 check('Invited advisor disagreement is visible',await dialog.getByText('disagreement',{exact:true}).count()>0)
 const blocked=dialog.locator('.message-card--advisor').filter({has:page.locator('.validation-chip--bad')})
 check('Unsupported live suggestions remain disabled',await blocked.locator('.proposed-actions button:disabled').count()>0)
 await dialog.getByRole('button',{name:'Replay',exact:true}).click()
 await dialog.getByText('Recorded replay · opening and replaying use no new inference.').waitFor()
 await mkdir('apps/web/screenshots/live',{recursive:true})
 for(const width of [390,1280]){
  await page.setViewportSize({width,height:width===1280?900:844})
  const shortcuts=await dialog.getByLabel('Advisor shortcuts').boundingBox(); check(`${width}px recorded-council shortcuts retain their height`,!!shortcuts&&shortcuts.height>=58); await dialog.getByText('Critic’s conclusion',{exact:true}).scrollIntoViewIfNeeded(); const shot=`apps/web/screenshots/live/advisor-replay-${width}.png`;await page.screenshot({path:shot,animations:'disabled'});report.screenshots.push(shot)
  check(`${width}px replay has no horizontal page overflow`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
 }
 check('Viewing and replaying live messages requests no inference',report.inference_posts===0)
 check('Live transcript has no page exceptions',errors.length===0)
 report.status='PASS'
 await context.close()
}catch(e){report.status='FAIL';report.error=e.stack||String(e);process.exitCode=1}
finally{await browser.close();await writeFile('reports/live_replay_browser.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,error:report.error,inference_posts:report.inference_posts}))}
