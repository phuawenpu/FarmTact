/** Independent novice/mobile/accessibility walkthrough; no provider-capable actions. */
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const origin=(process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080').replace(/\/$/,'')
const url=`${origin}/v7/research`
const reportPath=resolve(root,process.env.FARMTACT_NOVICE_REPORT||'reports/v7/novice_review.json')
const screenshotDir=resolve(root,process.env.FARMTACT_NOVICE_SCREENSHOTS||'apps/web/screenshots/v7-novice')
const storageState=process.env.FARMTACT_BROWSER_STORAGE_STATE
const result={started_at:new Date().toISOString(),origin,url,checks:[],failures:[],errors:[],screenshots:[],writes:[],timings:{},observations:[],limitations:[
  'This is an independent Codex walkthrough using a novice heuristic, not a human participant study or evidence of enjoyment.',
  'Widths use headless Chromium emulation. Physical touch, screen readers, software-keyboard occlusion, native dictation, and device performance were not tested.',
  'The 30-second time-to-first-choice value is a future human-study target. This automated timing is diagnostic and includes local numerical-worker latency.',
]}
const check=(name,pass,detail='')=>{const row={name,pass:Boolean(pass),detail:String(detail).replace(/\s+/g,' ').trim().slice(0,900)};result.checks.push(row);if(!row.pass)result.failures.push(row)}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
let lastWrite=0
const pace=async()=>{const left=1100-(Date.now()-lastWrite);if(left>0)await sleep(left);lastWrite=Date.now()}
const clickWrite=async locator=>{await pace();await locator.click()}
const shot=async(page,width,name,fullPage=false)=>{const path=resolve(screenshotDir,`${name}-${width}.png`);await page.screenshot({path,fullPage,animations:'disabled',caret:'hide'});result.screenshots.push(relative(root,path))}

await mkdir(dirname(reportPath),{recursive:true});await mkdir(screenshotDir,{recursive:true})
const browser=await chromium.launch({headless:true})
try{
  for(const width of [360,390,430,1280]){
    const context=await browser.newContext({...(storageState?{storageState}:{}),viewport:{width,height:width===1280?900:844},hasTouch:width<1280,isMobile:width<1280,reducedMotion:'reduce'})
    const page=await context.newPage()
    page.on('pageerror',error=>result.errors.push(`${width}px page: ${error.message}`))
    page.on('console',message=>{if(message.type()==='error')result.errors.push(`${width}px console: ${message.text()}`)})
    page.on('request',request=>{if(request.method()!=='POST')return;const path=new URL(request.url()).pathname;result.writes.push({width,path,at:new Date().toISOString()});if(/\/conversations\/[^/]+\/(messages|invite|council)$|\/planning-runs/.test(path))result.errors.push(`${width}px provider-capable POST: ${path}`)})
    await pace();const response=await page.goto(url,{waitUntil:'networkidle',timeout:60_000});lastWrite=Date.now()
    await page.getByRole('heading',{name:'Talk through a farm decision.'}).waitFor()
    const layoutLab=page.locator('.layout-lab')
    await layoutLab.locator('summary').click()
    const resetResponse=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname.endsWith('/api/v1/council-research'))
    await clickWrite(layoutLab.getByRole('button',{name:'Start a fresh isolated study'}));await resetResponse
    const start=page.getByRole('button',{name:'Ask council for a plan'});await start.waitFor()
    await layoutLab.locator('summary').click();await page.evaluate(()=>scrollTo(0,0))
    const rect=await start.boundingBox()
    check(`${width}px one clear starting action is visible`,await start.isVisible()&&await start.count()===1,rect?`${Math.round(rect.x)},${Math.round(rect.y)} ${Math.round(rect.width)}x${Math.round(rect.height)}`:'missing')
    check(`${width}px starting action is in initial viewport`,!!rect&&rect.y>=0&&rect.y+rect.height<=(width===1280?900:844),rect?.y)
    check(`${width}px advanced concept controls start closed`,!(await page.getByText('Layout',{exact:true}).isVisible()),'Compare research layouts is progressively disclosed')
    check(`${width}px task language names farm actions`,/Ask for a plan.*Reserve Bed 4.*Mark the additional order unconfirmed.*Challenge one assumption.*Choose a simulated version/s.test((await page.getByRole('list',{name:'Council study task'}).innerText()).replace(/\s+/g,' ')))
    const viewport=await page.evaluate(()=>({innerWidth,scrollWidth:document.documentElement.scrollWidth}))
    check(`${width}px CSS viewport preserves requested width`,viewport.innerWidth===width,`${viewport.innerWidth}/${width}`)
    check(`${width}px no horizontal overflow`,viewport.scrollWidth<=width+1,`${viewport.scrollWidth}/${width}`)
    check(`${width}px reduced-motion preference active`,await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches))
    await shot(page,width,'first-view')

    if(width===390){
      const journeyStart=Date.now()
      await clickWrite(start)
      await page.getByRole('button',{name:'Reserve Bed 4'}).first().waitFor({timeout:60_000})
      const firstPolicy=page.getByRole('button',{name:'Balanced'})
      await firstPolicy.waitFor()
      result.timings.first_meaningful_plan_choice_ms=Date.now()-journeyStart
      check('first result exposes three plain policy choices',await page.locator('.policy-tabs button').count()===3,await page.locator('.policy-tabs').innerText())
      result.observations.push('The single Start here action led directly to three calculated policy choices without opening instructions or research settings.')

      const bed4=page.getByRole('button',{name:/Select Bed 4,/})
      await shot(page,width,'initial-plan',true)
      let bedTouchWorked=true
      await pace()
      try{await bed4.click({timeout:4000})}catch(error){bedTouchWorked=false;result.observations.push(`Bed 4 touch target was visually present but intercepted: ${String(error).split('\n')[0]}`);await bed4.focus();await page.keyboard.press('Enter')}
      check('Bed 4 can be selected with an ordinary touch click',bedTouchWorked,'Keyboard Enter was used only to continue the accessibility review after the failed click.')
      const pinned=page.getByRole('region',{name:'Council discussion'}).getByText('Talking about',{exact:true})
      await pinned.waitFor({state:'visible'})
      check('selected context is repeated beside the composer',await pinned.isVisible(),await pinned.locator('..').innerText())
      check('selected context has a labelled removal control',await page.getByRole('button',{name:/Remove Bed 4/}).count()===1)
      const composer=page.getByLabel('Tell the council what matters')
      check('composer and selected context remain in the same council region',await composer.evaluate((node,pinnedText)=>node.closest('[aria-label="Council discussion"]')?.textContent?.includes(String(pinnedText))===true,'Talking about'))

      const guided=page.getByRole('region',{name:'Next council action'})
      await clickWrite(guided.getByRole('button',{name:'Reserve Bed 4'}))
      const proposal=page.locator('.proposal-card');await proposal.waitFor()
      const proposalText=await proposal.innerText()
      const proposalBox=await proposal.boundingBox(),headerBox=await page.locator('.topbar').boundingBox()
      check('proposal scrolls below the fixed mobile header',!!proposalBox&&!!headerBox&&proposalBox.y>=headerBox.y+headerBox.height-1,`${proposalBox?.y}/${headerBox?headerBox.y+headerBox.height:'missing'}`)
      check('reservation proposal exposes dates and recorded occupancy before apply',/Start.*End.*recorded harvest/s.test(proposalText),proposalText)
      check('apply and discard are both keyboard buttons',await proposal.getByRole('button',{name:/Apply to new version/}).isEnabled()&&await proposal.getByRole('button',{name:'Discard'}).isEnabled())
      await shot(page,width,'reservation-review')
      await clickWrite(proposal.getByRole('button',{name:/Apply to new version/}))
      await page.getByText('Frozen version 2').first().waitFor()
      await clickWrite(guided.getByRole('button',{name:'Recalculate changed inputs'}))
      await guided.getByRole('button',{name:'Mark order unconfirmed'}).waitFor({timeout:60_000})

      await clickWrite(guided.getByRole('button',{name:'Mark order unconfirmed'}))
      await page.locator('.proposal-card').waitFor()
      check('order remains visible while confirmation change is previewed',/stays visible but leaves booked demand/i.test(await page.locator('.proposal-card').innerText()))
      await clickWrite(page.locator('.proposal-card').getByRole('button',{name:/Apply to new version/}))
      await page.getByText('Frozen version 3').first().waitFor()
      await clickWrite(guided.getByRole('button',{name:'Recalculate changed inputs'}))
      await guided.getByRole('button',{name:'Challenge rainfall assumption'}).waitFor({timeout:60_000})

      await clickWrite(guided.getByRole('button',{name:'Challenge rainfall assumption'}))
      const challenge=page.locator('.challenge-card');await challenge.waitFor()
      const blockedChoice=page.getByRole('button',{name:'Choose this simulated version'})
      check('challenge is visibly unresolved and blocks silent choice',/unresolved/i.test(await challenge.innerText())&&((await blockedChoice.count())===0||await blockedChoice.isDisabled()))
      const evidence=challenge.getByRole('button',{name:'Open research sources'});await evidence.focus();await clickWrite(evidence)
      const dialog=page.getByRole('dialog',{name:'Research and evidence'});await dialog.waitFor()
      check('evidence dialog has an accessible name and close control',await dialog.getByRole('button',{name:'Close research'}).isVisible())
      await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'})
      check('Escape returns focus to the evidence action',await evidence.evaluate(node=>document.activeElement===node))
      await clickWrite(challenge.getByRole('button',{name:'Correct assumption'}))
      await page.locator('.challenge-card.status-corrected').waitFor()

      await page.getByText(/vs v1/).first().waitFor({timeout:60_000})
      const values=await page.locator('.delta-grid').innerText()
      check('comparison retains six plain labels, units, and deltas',await page.locator('.delta-grid > div').count()===6&&/delivery shortfall.*kg.*labour.*hours.*margin.*sgd/s.test(values.replace(/\s+/g,' ').toLowerCase()),values)
      const choose=page.getByRole('button',{name:'Choose this simulated version'})
      check('feasible current version exposes an explicit choice',await choose.isEnabled())
      await clickWrite(choose);await page.getByText(/chosen for this study/i).waitFor()
      check('choice states that no operation occurred',/No operational commitment was made/.test(await page.getByText(/chosen for this study/i).innerText()))
      result.timings.complete_task_ms=Date.now()-journeyStart
      await shot(page,width,'completed-task',true)

      const lab=page.getByText('Compare research layouts and pacing',{exact:true});await lab.focus();await lab.press('Enter')
      check('concept controls are keyboard-reachable after optional disclosure',await page.getByLabel('Layout').isVisible())
      for(const concept of ['inline','sheet','cards']){await pace();const configured=page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname.endsWith('/actions'));await page.getByLabel('Layout').selectOption(concept);await configured;await page.locator(`.concept-${concept}`).waitFor();check(`${concept} retains context, council, and consequence regions`,await page.getByRole('region',{name:'Selected farm context'}).isVisible()&&await page.getByRole('region',{name:'Council discussion'}).isVisible()&&await page.getByRole('region',{name:'Planning consequences'}).isVisible());await shot(page,width,`completed-${concept}`)}
      result.observations.push('The default sheet keeps selected context beside the composer; advanced layout/pacing controls stay behind an optional disclosure.')
      result.observations.push('The six-value comparison is legible but uses planning terms such as fill rate and shortfall; units appear in labels, while novice comprehension still requires human testing.')
    }
    await context.close()
  }
}catch(error){result.errors.push(error.stack||String(error))}
finally{
  const gaps=result.writes.slice(1).map((row,i)=>new Date(row.at)-new Date(result.writes[i].at))
  check('write pacing stays at or below one request per second',gaps.every(ms=>ms>=950),gaps.join(','))
  result.finished_at=new Date().toISOString();await writeFile(reportPath,`${JSON.stringify(result,null,2)}\n`);await browser.close()
}
console.log(JSON.stringify({checks:result.checks.length,failures:result.failures,errors:result.errors,timings:result.timings,screenshots:result.screenshots.length},null,2))
if(result.failures.length||result.errors.length)process.exitCode=1
