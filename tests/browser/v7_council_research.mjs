/** Playable-council interaction study. Scripted dialogue and local numerics only. */
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const origin=(process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080').replace(/\/$/,'')
const storageState=process.env.FARMTACT_BROWSER_STORAGE_STATE
const url=`${origin}/v7/research`
const reportPath=resolve(root,process.env.FARMTACT_BROWSER_REPORT||'reports/v7/browser.json')
const screenshotDir=resolve(root,process.env.FARMTACT_SCREENSHOT_DIR||'apps/web/screenshots/v7-council')
const result={started_at:new Date().toISOString(),origin,url,checks:[],failures:[],errors:[],screenshots:[],writes:[],timings:[],provider_capable_posts:[],mock_provider_posts:[],concept_order:{},professional_planning_review:[],limitations:[
  'This is an AI-authored professional-planning walkthrough, not a human participant study or evidence of enjoyment.',
  'Responsive checks use headless Chromium emulation; physical mobile keyboards, dictation, screen readers and touch hardware were not tested.',
  'One 390px session completes the full numerical task, then renders the same completed state in all three concepts. Other widths exercise each presentation on fresh scripted sessions.',
  'The unsupported actual-advisor response is a clearly labelled browser interception fixture. It validates rendering only and is not a provider capability or response-quality result.',
  'Local responsive reruns use one pre-provisioned, isolated authentication fixture to avoid consuming public new-session limits. Each width starts a fresh research study within that tenant.',
],prior_iterations:[
  {status:'HARNESS_ERROR',finding:'A request-context bootstrap replaced the browser tenant cookie on HTTP, so the subsequent research action returned 404. The same-page fetch correction isolates this from planner latency.'},
  {status:'ADMISSION_BLOCKED',finding:'A retry made zero writes because accumulated local reviews reached the 10-new-sessions-per-IP/hour limit. The final run reuses one pre-provisioned isolated tenant without changing limits.'},
  {status:'HARNESS_RACE',finding:'An initial plan completed in 22.36 seconds, then the script attempted a second action before the first response cleared the UI busy state. Final action helpers await their exact POST response.'},
]}
const check=(name,pass,detail='')=>{const row={name,pass:Boolean(pass),detail:String(detail).replace(/\s+/g,' ').trim().slice(0,900)};result.checks.push(row);if(!row.pass)result.failures.push(row)}
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms))
let lastWrite=0
const pace=async()=>{const remaining=1100-(Date.now()-lastWrite);if(remaining>0)await delay(remaining);lastWrite=Date.now()}
const shot=async(page,width,name,fullPage=false)=>{const path=resolve(screenshotDir,`${name}-${width}.png`);await page.screenshot({path,fullPage,animations:'disabled',caret:'hide'});result.screenshots.push(relative(root,path))}
const clickWrite=async locator=>{await pace();await locator.click()}
const actionWrite=async(page,locator)=>{await pace();const [response]=await Promise.all([page.waitForResponse(reply=>reply.request().method()==='POST'&&/\/council-research\/[^/]+\/actions$/.test(new URL(reply.url()).pathname)),locator.click()]);lastWrite=Date.now();if(!response.ok())throw Error(`Research action failed (${response.status()}): ${await response.text()}`);return response.json()}
const selectWrite=async(page,locator,value)=>{if(await locator.inputValue()===value)return;await pace();const [response]=await Promise.all([page.waitForResponse(reply=>reply.request().method()==='POST'&&/\/council-research\/[^/]+\/actions$/.test(new URL(reply.url()).pathname)),locator.selectOption(value)]);lastWrite=Date.now();if(!response.ok())throw Error(`Presentation action failed (${response.status()})`)}
const sendDraft=async(page,text)=>{const input=page.getByLabel('Tell the council what matters');await input.fill(text);await actionWrite(page,page.getByRole('button',{name:'Send to scripted council'}))}

await mkdir(dirname(reportPath),{recursive:true});await mkdir(screenshotDir,{recursive:true})
const browser=await chromium.launch({headless:true})
try{
  const contexts=[]
  for(const width of [360,390,430,1280]){
    const context=await browser.newContext({viewport:{width,height:width===1280?900:844},hasTouch:width<1280,reducedMotion:'reduce',...(storageState?{storageState}:{})})
    contexts.push(context);const page=await context.newPage();let fixtureMode=false,checkpointConflictExpected=false,expectedConflictLogs=0
    page.on('pageerror',error=>result.errors.push(`${width}px page: ${error.message}`))
    page.on('console',message=>{if(message.type()!=='error')return;if(checkpointConflictExpected&&/status of 409 \(Conflict\)/.test(message.text())){expectedConflictLogs++;return}result.errors.push(`${width}px console: ${message.text()}`)})
    page.on('request',request=>{
      if(request.method()!=='POST')return
      const path=new URL(request.url()).pathname
      if(fixtureMode&&/\/conversations(?:\/[^/]+\/messages)?$/.test(path)){result.mock_provider_posts.push({width,path});return}
      result.writes.push({width,path,at:new Date().toISOString()})
      if(/\/conversations\/[^/]+\/(messages|invite|council)$|\/planning-runs/.test(path))result.provider_capable_posts.push({width,path})
    })
    await pace();const response=await page.goto(url,{waitUntil:'networkidle',timeout:60_000});lastWrite=Date.now()
    await page.getByRole('heading',{name:'Talk through a farm decision.'}).waitFor()
    if(storageState){
      await page.locator('.layout-lab > summary').click()
      await pace();await Promise.all([
        page.waitForResponse(reply=>reply.request().method()==='POST'&&/\/v7\/api\/v1\/council-research$/.test(new URL(reply.url()).pathname)&&reply.ok()),
        page.getByRole('button',{name:'Start a fresh isolated study'}).click(),
      ]);lastWrite=Date.now();if(await page.locator('.layout-lab').evaluate(node=>node.open))await page.locator('.layout-lab > summary').click()
    }
    check(`${width}px research route loads`,response?.status()===200,response?.status())
    check(`${width}px emulation uses exact requested CSS viewport`,await page.evaluate(expected=>innerWidth===expected,width),await page.evaluate(()=>innerWidth))
    check(`${width}px no horizontal overflow against requested width`,await page.evaluate(expected=>document.documentElement.scrollWidth<=expected+1,width),await page.evaluate(()=>`${document.documentElement.scrollWidth}/${innerWidth}`))
    check(`${width}px reduced motion preference active`,await page.evaluate(()=>matchMedia('(prefers-reduced-motion: reduce)').matches))
    check(`${width}px scripted mode is explicit`,await page.getByText('No AI inference',{exact:true}).isVisible())
    check(`${width}px composer is keyboard reachable`,await page.getByLabel('Tell the council what matters').evaluate(node=>node.getBoundingClientRect().height>=44))
    const startingActions=page.getByRole('button',{name:'Ask council for a plan'}).filter({visible:true})
    check(`${width}px first timer sees one obvious starting action`,await startingActions.count()===1,await startingActions.allTextContents())
    check(`${width}px guided next action explains the immediate consequence`,/local planning tool.*three options/i.test(await page.getByRole('region',{name:'Next council action'}).innerText()))
    check(`${width}px research controls stay collapsed initially`,!(await page.getByLabel('Layout').isVisible()))

    const rotations={360:['inline','sheet','cards'],390:['sheet','cards','inline'],430:['cards','inline','sheet'],1280:['inline','cards','sheet']}[width]
    result.concept_order[width]=rotations
    await page.locator('.layout-lab > summary').click()
    const layout=page.getByLabel('Layout')
    await selectWrite(page,page.getByLabel('Participation'),'continuous')
    await selectWrite(page,page.locator('.study-controls label').filter({hasText:/^Context/}).locator('select'),'chips')
    await selectWrite(page,page.locator('.study-controls label').filter({hasText:/^Changes/}).locator('select'),'static')
    for(const concept of rotations){
      await selectWrite(page,layout,concept);await page.locator(`.concept-${concept}`).waitFor()
      check(`${width}px ${concept} preserves selected farm context`,await page.getByRole('region',{name:'Selected farm context'}).isVisible())
      check(`${width}px ${concept} open controls do not overflow`,await page.evaluate(expected=>document.documentElement.scrollWidth<=expected+1,width),await page.evaluate(()=>document.documentElement.scrollWidth))
      check(`${width}px ${concept} advanced selects remain within viewport`,await page.locator('.study-controls select').evaluateAll((nodes,expected)=>nodes.every(node=>{const box=node.getBoundingClientRect();return box.left>=-1&&box.right<=expected+1}),width))
      if(width<700){
        const unobscured=await page.evaluate(()=>{const a=document.querySelector('.context-board')?.getBoundingClientRect(),b=document.querySelector('.council-dialogue')?.getBoundingClientRect();if(!a||!b)return false;return a.right<=b.left||b.right<=a.left||a.bottom<=b.top||b.bottom<=a.top})
        check(`${width}px ${concept} context and council geometry do not overlap`,unobscured)
      }
      if(width!==390)await shot(page,width,`concept-${concept}`)
    }

    if(width===390){
      const farmBefore=await page.evaluate(async()=>await fetch('api/v1/bootstrap').then(response=>response.json()))
      const started=Date.now()
      let delayedPoll=false
      const pollPattern=/\/v7\/api\/v1\/council-research\/[0-9a-f]+$/
      await page.route(pollPattern,async route=>{
        const fetched=await route.fetch(),body=await fetched.json()
        if(!delayedPoll&&body.results?.some(row=>row.status==='QUEUED')){delayedPoll=true;await delay(6500)}
        await route.fulfill({response:fetched,json:body})
      })
      await actionWrite(page,page.getByRole('button',{name:'Ask council for a plan'}))
      await page.getByRole('button',{name:'Choose this simulated version'}).waitFor({timeout:60_000})
      await delay(7000)
      check('late queued poll cannot replace a newer completed result',delayedPoll&&await page.getByRole('button',{name:'Choose this simulated version'}).isVisible(),delayedPoll)
      await page.unroute(pollPattern)
      result.timings.push({step:'initial_calculation',milliseconds:Date.now()-started})
      check('initial result exposes all three policies',await page.locator('.policy-tabs button').count()===3)
      await shot(page,width,'initial-plan',true)

      await actionWrite(page,page.getByRole('button',{name:/Select Bed 4,/}))
      const chip=page.getByRole('button',{name:/Remove Bed 4/});await chip.waitFor()
      check('touch selection creates a removable context chip',await chip.isVisible())
      check('selected context stays immediately beside the composer',await page.locator('.composer-context').isVisible())
      await actionWrite(page,chip);await chip.waitFor({state:'detached'});check('context chip removes selection',await chip.count()===0)

      await sendDraft(page,'Please celebrate the harvest with a dance.')
      check('unrecognized request asks for clarification without a proposal',await page.locator('.proposal-card').count()===0,await page.locator('.research-message').last().innerText())
      await sendDraft(page,'Do not reserve Bed 4.')
      check('negated constraint is clarified rather than applied',await page.locator('.proposal-card').count()===0,await page.locator('.research-message').last().innerText())

      const composer=page.getByLabel('Tell the council what matters');await composer.fill('Draft retained while the layout updates')
      await selectWrite(page,layout,'sheet');check('draft survives presentation updates',await composer.inputValue()==='Draft retained while the layout updates',await composer.inputValue());await composer.fill('')

      const guide=page.getByRole('region',{name:'Next council action'})
      await actionWrite(page,guide.getByRole('button',{name:'Reserve Bed 4'}));const proposal=page.locator('.proposal-card');await proposal.waitFor()
      check('bed reservation appears as reviewable proposal',/review before applying/i.test(await proposal.innerText()))
      await shot(page,width,'reservation-proposal')
      await actionWrite(page,proposal.getByRole('button',{name:/Apply to new version/}))
      await page.getByText('Frozen version 2').waitFor()
      await actionWrite(page,guide.getByRole('button',{name:'Recalculate changed inputs'}));await guide.getByRole('button',{name:'Mark order unconfirmed'}).waitFor({timeout:60_000})
      await actionWrite(page,guide.getByRole('button',{name:'Mark order unconfirmed'}));await page.locator('.proposal-card').waitFor()
      check('order status proposal keeps order visible',/stays visible but leaves booked demand/i.test(await page.locator('.proposal-card').innerText()))
      await actionWrite(page,page.locator('.proposal-card').getByRole('button',{name:/Apply to new version/}))
      await page.getByText('Frozen version 3').waitFor()

      const revised=Date.now();await actionWrite(page,guide.getByRole('button',{name:'Recalculate changed inputs'}));await guide.getByRole('button',{name:'Challenge rainfall assumption'}).waitFor({timeout:60_000});result.timings.push({step:'revised_calculation',milliseconds:Date.now()-revised})
      await actionWrite(page,guide.getByRole('button',{name:'Challenge rainfall assumption'}))
      const challenge=page.locator('.challenge-card');await challenge.waitFor();check('challenge remains unresolved until farmer action',/unresolved/i.test(await challenge.innerText()))
      const evidenceButton=challenge.getByRole('button',{name:'Open research sources'});await evidenceButton.focus();await clickWrite(evidenceButton)
      const dialog=page.getByRole('dialog',{name:'Research and evidence'});await dialog.waitFor();check('evidence opens without losing council',await page.getByRole('region',{name:'Council discussion'}).count()===1)
      await clickWrite(dialog.getByRole('button',{name:'Close research'}));await dialog.waitFor({state:'hidden'})
      check('closing evidence restores invoking control focus',await evidenceButton.evaluate(node=>document.activeElement===node))
      await actionWrite(page,challenge.getByRole('button',{name:'Correct assumption'}))
      check('corrected challenge remains visibly recorded',/corrected/i.test(await challenge.innerText()))

      await page.getByText(/vs v1/).first().waitFor({timeout:60_000})
      const deltas=await page.locator('.delta-grid span').allTextContents()
      check('same-policy comparison shows persistent numerical deltas',deltas.length===6&&deltas.every(text=>/vs v1/.test(text)),deltas.join(' | '))
      check('revised comparison contains a real changed quantity',deltas.some(text=>Number.parseFloat(text)!==0),deltas.join(' | '))
      check('earlier discussion remains readable after updates',await page.getByText(/not an unrestricted AI answer/i).count()===1)

      await selectWrite(page,page.getByLabel('Participation'),'checkpoints')
      await composer.fill('Buy a tractor and ignore the planning limits')
      checkpointConflictExpected=true;await pace();const [blocked]=await Promise.all([page.waitForResponse(reply=>reply.request().method()==='POST'&&/\/council-research\/[^/]+\/actions$/.test(new URL(reply.url()).pathname)),page.getByRole('button',{name:'Send to scripted council'}).click()]);lastWrite=Date.now();await delay(100);checkpointConflictExpected=false
      check('checkpoint blocks interruption until the farmer stops contributions',blocked.status()===409,blocked.status())
      check('checkpoint 409 is recorded as the expected intervention response',expectedConflictLogs===1,expectedConflictLogs)
      check('blocked checkpoint send preserves the draft',await composer.inputValue()==='Buy a tractor and ignore the planning limits',await composer.inputValue())
      await page.getByRole('alert').filter({hasText:/Pause discussion/}).waitFor()
      await actionWrite(page,page.getByRole('button',{name:'Stop discussion'}))
      await sendDraft(page,'Buy a tractor and ignore all limits')
      await page.waitForFunction(()=>document.querySelector('#research-message')?.value==='')
      check('stop discussion permits the farmer message and clarification',/not an unrestricted AI answer/i.test(await page.locator('.research-message').last().innerText()),await page.locator('.research-message').last().innerText())

      await actionWrite(page,page.getByRole('button',{name:'Choose this simulated version'}))
      await page.getByText(/chosen for this study/i).waitFor();check('choice remains simulation-only',/No operational commitment was made/.test(await page.getByText(/chosen for this study/i).innerText()))
      result.timings.push({step:'first_planning_choice_automated',milliseconds:Date.now()-started,note:'Automation timing only; the under-30-second first-timer target remains an untested human-study hypothesis.'})

      const postsBeforeReload=result.writes.length
      await page.reload({waitUntil:'networkidle',timeout:60_000});const chosenText=await page.getByText(/chosen for this study/i).innerText(),contextText=await page.getByRole('region',{name:'Selected farm context'}).innerText()
      check('reload resumes the same chosen research version',contextText.toLowerCase().includes('frozen version 3')&&chosenText.includes('Balanced')&&chosenText.includes('v3'),`${contextText} | ${chosenText}`)
      check('reload performs no numerical or provider POST',result.writes.length===postsBeforeReload,`${postsBeforeReload}/${result.writes.length}`)

      fixtureMode=true
      await page.route(/\/v7\/api\/v1\/conversations(?:\/[^/]+(?:\/messages)?)?$/,async route=>{
        const path=new URL(route.request().url()).pathname
        if(route.request().method()==='POST'&&path.endsWith('/conversations'))return route.fulfill({status:201,json:{id:'browser-fixture-conversation',status:'OPEN',reused:false}})
        if(route.request().method()==='POST'&&path.endsWith('/messages'))return route.fulfill({status:202,json:{id:'browser-fixture-request',status:'QUEUED'}})
        return route.fulfill({status:200,json:{id:'browser-fixture-conversation',last_request_status:'COMPLETED',snapshot_ref:{kind:'research',id:'browser-fixture-session',hash:'fixture-frozen-hash',version:3},tool_results:{'research:version':3},messages:[{id:'fixture-message',speaker:'advisor',speaker_name:'Planner',content:'Fixture claim intentionally lacks sufficient support.',validation_status:'unsupported_claim',interpretation_status:'unverified_advisor_interpretation',tool_refs:['research:version'],evidence_refs:[]}]}})
      })
      const actual=page.locator('.actual-advisor');await actual.locator('summary').click();await actual.getByRole('button',{name:'Ask DeepSeek about frozen result'}).click()
      const unsupported=actual.getByRole('alert');await unsupported.waitFor()
      check('fixture unsupported advisor response is visibly non-authorizing',/unsupported.*cannot authorize/i.test(await unsupported.innerText()),await unsupported.innerText())
      check('fixture actual response retains frozen reference and terminal status',/Status:\s*COMPLETED/.test(await actual.innerText())&&/v3.*fixture-fr/i.test(await actual.innerText()),await actual.innerText())
      await shot(page,width,'unsupported-advisor-fixture')
      fixtureMode=false

      if(!(await page.locator('.layout-lab').evaluate(node=>node.open)))await page.locator('.layout-lab > summary').click()
      for(const concept of rotations){await selectWrite(page,layout,concept);await page.locator(`.concept-${concept}`).waitFor();await shot(page,width,`completed-${concept}`,true)}
      const farmAfter=await page.evaluate(async()=>await fetch('api/v1/bootstrap').then(response=>response.json()))
      check('completed council task does not mutate main farm',JSON.stringify(farmAfter.farm)===JSON.stringify(farmBefore.farm))
      result.professional_planning_review.push(
        {concept:'inline',observation:'Farm context, discussion, and signed same-policy deltas remain simultaneously inspectable; this best supports tracing a constraint into a numerical consequence on desktop.'},
        {concept:'sheet',observation:'Pinned context and a visually emphasized council make correction steps clear at narrow widths, though the current implementation remains an inline document section rather than an operating-system bottom sheet.'},
        {concept:'cards',observation:'Speaker turns scan quickly, but cards consume more vertical space and require more movement between context and the policy comparison.'},
      )
    }
    await context.close()
  }
}catch(error){result.errors.push(error.stack||String(error))}
finally{
  const intervals=result.writes.slice(1).map((row,index)=>new Date(row.at)-new Date(result.writes[index].at))
  check('write pacing stays at or below one request per second',intervals.every(ms=>ms>=950),intervals.join(','))
  check('script submitted no provider-capable action',result.provider_capable_posts.length===0,JSON.stringify(result.provider_capable_posts))
  check('unsupported advisor UI used only the intercepted fixture posts',result.mock_provider_posts.length===2,JSON.stringify(result.mock_provider_posts))
  result.finished_at=new Date().toISOString();await writeFile(reportPath,`${JSON.stringify(result,null,2)}\n`);await browser.close()
}
console.log(JSON.stringify({checks:result.checks.length,failures:result.failures,errors:result.errors,screenshots:result.screenshots.length,writes:result.writes.length,timings:result.timings},null,2))
if(result.failures.length||result.errors.length||result.provider_capable_posts.length)process.exitCode=1
