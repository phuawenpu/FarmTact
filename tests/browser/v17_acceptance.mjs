import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'

// Prepared acceptance for the V17 persona workflow. It intentionally refuses to
// run until the integrating owner marks the V17 build ready.
if (process.env.V17_READY !== '1') {
  console.error('V17 acceptance is prepared but not run: set V17_READY=1 after the integrating owner confirms the build.')
  process.exit(2)
}

const base=(process.env.BASE_URL||'http://127.0.0.1:4196').replace(/\/$/,'')
const storage=process.env.STORAGE_STATE||'/tmp/farmtact-v15-cards-storage.json'
const reportPath=resolve(process.env.REPORT_PATH||'reports/v17/personas/v17-acceptance.json')
const report={status:'RUNNING',build:null,realApiSmoke:[],checks:[],fixtures:[],requests:{providerCapable:[],unexpectedWrites:[]},failures:[]}
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)throw new Error(`${name}: ${JSON.stringify(detail)}`)}
const record=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)report.failures.push(`${name}: ${JSON.stringify(detail)}`)}
const click=(page,name)=>page.getByRole('button',{name,exact:true}).filter({visible:true}).first().click()
const json=(route,body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)})
const showSpecialists=async page=>{const selector=page.getByRole('button',{name:/^Specialists\b/}).filter({visible:true});if(await selector.isVisible().catch(()=>false))await selector.click()}

async function enterKnowledge(page){
  const skip=page.getByRole('button',{name:'Skip demonstration',exact:true}).filter({visible:true})
  if(await skip.isVisible().catch(()=>false))await skip.click()
  const more=page.getByRole('button',{name:'More',exact:true}).filter({visible:true}).first()
  for(let i=0;i<8&&!await more.isVisible().catch(()=>false);i++){
    const back=page.getByRole('button',{name:'Back',exact:true}).filter({visible:true}).first()
    if(!await back.isVisible().catch(()=>false))break
    await back.click()
  }
  await more.waitFor()
  await more.click()
  for(let i=0;i<5;i++){
    if(await page.getByRole('button',{name:/Knowledge & evidence/i}).filter({visible:true}).count())break
    await page.getByRole('button',{name:/Next/}).filter({visible:true}).first().click()
  }
  const category=page.getByRole('button',{name:/Knowledge & evidence/i}).filter({visible:true}).first()
  if(await category.isVisible().catch(()=>false))await category.click();else await click(page,'Open tool')
  await page.getByRole('heading',{name:'Inspect the facts. Ask deliberately.',exact:true}).waitFor()
}

let browser
try{
  browser=await chromium.launch({headless:true})

  // Real service smoke is deliberately GET-only and separate from the labelled
  // provider-result transport below.
  const smoke=await browser.newContext({storageState:storage,viewport:{width:390,height:844}})
  const smokePage=await smoke.newPage();const smokeWrites=[]
  smokePage.on('request',r=>{if(!['GET','HEAD','OPTIONS'].includes(r.method()))smokeWrites.push(`${r.method()} ${new URL(r.url()).pathname}`)})
  await smokePage.route('**/api/v1/**',r=>['GET','HEAD','OPTIONS'].includes(r.request().method())?r.continue():r.abort('blockedbyclient'))
  await smokePage.goto(base,{waitUntil:'domcontentloaded'});await smokePage.locator('.ic-shell').waitFor()
  report.build=await smokePage.locator('script[type=module]').first().getAttribute('src')
  const liveSeed=await smokePage.evaluate(async()=>{const bootstrap=await(await fetch('/api/v1/bootstrap')).json();const listed=await(await fetch('/api/v1/planning-sessions')).json();const id=listed.sessions?.[0]?.id;return{bootstrap,listed,live:id?await(await fetch(`/api/v1/planning-sessions/${id}`)).json():null}})
  await enterKnowledge(smokePage)
  const indexText=await smokePage.locator('.ik-card').innerText()
  check('real API exposes the V17 Knowledge category index without inference',/Crops/.test(indexText)&&/Sources/.test(indexText)&&/Specialists/.test(indexText)&&/Saved discussions/.test(indexText),indexText)
  check('real API category smoke performs no writes',smokeWrites.length===0,smokeWrites)
  report.realApiSmoke.push({kind:'GET-only existing tenant',writes:smokeWrites,note:'No live inference and no new tenant/session.'})
  await smoke.close()

  const context=await browser.newContext({storageState:storage,viewport:{width:390,height:844},reducedMotion:'reduce'})
  const page=await context.newPage();const {bootstrap,live}=liveSeed
  const colonOrder={id:'order:with:colon',crop_id:'lettuce',due_date:'2026-10-01',quantity_kg:12}
  const planning={...(live||{}),id:live?.id||'v17-planning-fixture',revision:live?.revision||1,selected_strategy_id:live?.selected_strategy_id||live?.result?.strategies?.[0]?.id||'balanced',farm:{...(live?.farm||{}),orders:[colonOrder,...(live?.farm?.orders||[])] ,beds:live?.farm?.beds||[{id:'bed:with:colon',name:'Fixture bed',area_m2:10}]},result:live?.result?.strategies?.length?live.result:{strategies:[{id:'balanced',name:'Balanced',status:'FEASIBLE',metrics:{},allocations:[],violations:[]}]},assumptions:live?.assumptions||{tentative_orders:[],future_demand:[],seasonal:[],order_changes:[],reservations:[]}}
  const cited={id:'v17-cited-finding',speaker:'advisor',speaker_name:'Ravi',content:'The saved reply cites the frozen order and remains a bounded hypothesis.',validation_status:'references_verified',evidence_status:'partial',interpretation_status:'qualitative_unverified',fact_refs:['order:confirmed:fixture'],evidence_refs:['evidence:frozen-order'],rendered_facts:[{reference:'order:confirmed:fixture',label:'Confirmed order',value:12,unit:'kg',source:'frozen planning snapshot'}],proposed_actions:[{control:'labour_percent',value:75,unit:'percent',status:'hypothesis_only'}]}
  const withheld={id:'v17-withheld-finding',speaker:'advisor',speaker_name:'Idris',content:'The invited specialist withheld a recommendation because evidence is incomplete.',validation_status:'withheld',evidence_status:'withheld',interpretation_status:'withheld',fact_refs:[],citations:[],rendered_facts:[],proposed_actions:[]}
  const council={id:'v17-council-finding',speaker:'advisor',speaker_name:'Planning Council',content:'Council preserved the cited reply and recorded a bounded conclusion.',validation_status:'references_verified',evidence_status:'validated',interpretation_status:'qualitative_unverified',fact_refs:['order:confirmed:fixture'],citations:[{title:'Frozen order record',url:'https://example.invalid/frozen-order'}],rendered_facts:cited.rendered_facts,proposed_actions:[]}
  const conversation={id:'v17-persona-thread',title:'V17 labelled gateway fixture',advisor_id:'ravi',status:'COMPLETED',last_request_status:'COMPLETED',created_at:'2026-09-17T00:00:00Z',updated_at:'2026-09-17T00:00:00Z',snapshot_ref:{kind:'planning',id:`${planning.id}:result-fixture`,hash:'v17-frozen-hash',version:1},focus:null,evidence_context:[{evidence_id:'evidence:frozen-order',title:'Frozen order record',finding:'The recorded order quantity is 12 kg.',scope:'This frozen planning result only.',limit:'It does not validate the qualitative recommendation.',source_url:'https://example.invalid/frozen-order',access_review_status:'fixture'}],messages:[]}
  let creates=0,direct=0,invites=0,councils=0,proposalBody=null,applyBody=null,createBody=null
  await page.route('**/api/v1/bootstrap',r=>json(r,bootstrap))
  await page.route('**/api/v1/planning-sessions',r=>r.request().method()==='GET'?json(r,{sessions:[planning]}):r.continue())
  await page.route(`**/api/v1/planning-sessions/${planning.id}`,r=>json(r,planning))
  await page.route('**/api/v1/conversations',r=>{if(r.request().method()==='GET')return json(r,{conversations:[conversation]});creates++;createBody=r.request().postDataJSON();conversation.focus=createBody.focus;return json(r,{id:conversation.id,status:'READY'},201)})
  await page.route(`**/api/v1/conversations/${conversation.id}`,r=>json(r,conversation))
  await page.route(`**/api/v1/conversations/${conversation.id}/replay`,r=>json(r,{...conversation,replay:true}))
  await page.route(`**/api/v1/conversations/${conversation.id}/messages`,r=>{direct++;const body=r.request().postDataJSON();conversation.messages.push({id:'v17-direct-question',speaker:'user',content:body.content,validation_status:'recorded'},cited);return json(r,{id:'direct-request',conversation_id:conversation.id,status:'COMPLETED'},202)})
  await page.route(`**/api/v1/conversations/${conversation.id}/invite`,r=>{invites++;conversation.messages.push({id:'v17-invite-question',speaker:'user',content:r.request().postDataJSON().question,validation_status:'recorded'},withheld);return json(r,{id:'invite-request',conversation_id:conversation.id,status:'COMPLETED'},202)})
  await page.route(`**/api/v1/conversations/${conversation.id}/council`,r=>{councils++;conversation.messages.push({id:'v17-council-question',speaker:'user',content:r.request().postDataJSON().question,validation_status:'recorded'},council);return json(r,{id:'council-request',conversation_id:conversation.id,status:'COMPLETED'},202)})
  await page.route('**/api/v1/farm-workflow/proposals',r=>{proposalBody=r.request().postDataJSON();return json(r,{id:'v17-linked-proposal',session_id:planning.id,base_revision:planning.revision,proposal_revision:1,status:'draft',selected_strategy_id:planning.selected_strategy_id,calculated_metrics:{},source_conversation_id:proposalBody.source_conversation_id,source_message_id:proposalBody.source_message_id})})
  await page.route('**/api/v1/farm-workflow/proposals/v17-linked-proposal/apply',r=>{applyBody=r.request().postDataJSON();return json(r,{id:'v17-linked-proposal',session_id:planning.id,base_revision:planning.revision,proposal_revision:2,status:'applied',selected_strategy_id:planning.selected_strategy_id,calculated_metrics:{}})})
  page.on('request',r=>{const path=new URL(r.url()).pathname;if(/\/conversations\/[^/]+\/(messages|invite|council)$/.test(path))report.requests.providerCapable.push(`${r.method()} ${path}`);else if(!['GET','HEAD','OPTIONS'].includes(r.method())&&!/\/conversations$|\/farm-workflow\/proposals/.test(path))report.requests.unexpectedWrites.push(`${r.method()} ${path}`)})
  report.fixtures.push('Labelled in-browser validated-gateway transport: direct partial+cited reply, withheld invite, validated Council, and discussion-linked draft/apply. No external provider is contacted.')
  await page.goto(base,{waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor()
  await page.evaluate(()=>{for(const key of Object.keys(localStorage))if(/knowledge-(drafts|bindings|focus)/.test(key))localStorage.removeItem(key)})
  await page.reload({waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();await enterKnowledge(page)
  await showSpecialists(page);await page.getByRole('button',{name:/Ravi/}).click();await page.getByRole('heading',{name:/Ravi · Demand/}).waitFor();await click(page,'Back')
  await page.waitForFunction(()=>/Ravi/.test(document.activeElement?.textContent||''))
  const returnedFocus=await page.evaluate(()=>({text:document.activeElement?.textContent?.replace(/\s+/g,' ').trim(),scroll:window.scrollY}))
  check('category detail Back restores the Knowledge index and originating specialist control',await page.getByRole('heading',{name:'Choose what you need',exact:true}).isVisible()&&/Ravi/.test(returnedFocus.text||''),returnedFocus)
  await showSpecialists(page);await page.getByRole('button',{name:/Ravi/}).click();await page.getByLabel('Frozen focus').selectOption(`order:${planning.farm.orders[0].id}`)
  await page.getByLabel('Question about the frozen planning session').fill('Explain the frozen order trade-off.');await click(page,'Submit question');await page.getByText(cited.content,{exact:true}).waitFor()
  check('direct submission preserves canonical colon context and renders citation/fact evidence',direct===1&&createBody?.focus?.entity_id===colonOrder.id&&createBody?.focus?.card_id===`order-${colonOrder.id}`&&await page.getByText(/Frozen order record/).first().isVisible()&&await page.locator('[data-fact-reference="order:confirmed:fixture"]').isVisible(),{direct,focus:createBody?.focus})
  await page.getByLabel('Discussion action').selectOption('invite');await page.getByLabel('Reply to saved specialist finding').selectOption(cited.id);await page.getByLabel('Question about the frozen planning session').fill('Ask the invited specialist to review the cited finding.');await click(page,'Invite specialist');await page.getByText(withheld.content,{exact:true}).waitFor()
  await page.getByLabel('Discussion action').selectOption('council');await page.getByLabel('Reply to saved specialist finding').selectOption(withheld.id);await page.getByLabel('Question about the frozen planning session').fill('Convene Council on this saved exchange.');await click(page,'Convene Council');await page.getByText(council.content,{exact:true}).waitFor()
  const withheldCard=await page.locator('.ik-message',{hasText:withheld.content}).innerText(),councilCard=await page.locator('.ik-message',{hasText:council.content}).innerText(),citationCount=await page.getByText(/Frozen order record/).count()
  check('invite and Council preserve partial/withheld/validated statuses',invites===1&&councils===1&&/withheld/i.test(withheldCard)&&/references verified|validated/i.test(councilCard)&&citationCount>0,{invites,councils,withheldCard,councilCard,citationCount})
  const beforeReload={id:conversation.id,count:conversation.messages.length,focus:conversation.focus,snapshot:conversation.snapshot_ref}
  await page.reload({waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();await enterKnowledge(page);await showSpecialists(page);await page.getByRole('button',{name:/Ravi/}).click()
  const autoRestored=await page.getByText(council.content,{exact:true}).waitFor({timeout:5000}).then(()=>true).catch(()=>false)
  if(!autoRestored)await page.getByLabel('Frozen focus').selectOption(`order:${colonOrder.id}`)
  const restored=await page.getByText(council.content,{exact:true}).isVisible().catch(()=>false)
  record('reload restores the same frozen focus and thread without manual context repair or provider resubmission',autoRestored&&await page.getByLabel('Frozen focus').inputValue()===`order:${colonOrder.id}`&&conversation.id===beforeReload.id&&conversation.messages.length===beforeReload.count&&direct===1&&invites===1&&councils===1,{...beforeReload,selectedFocus:await page.getByLabel('Frozen focus').inputValue(),manualRepairNeeded:!autoRestored})
  await page.getByText(council.content,{exact:true}).waitFor()
  await click(page,'Back');await enterKnowledge(page);await page.getByRole('button',{name:'Saved discussions',exact:false}).click();await page.getByLabel('Saved thread').selectOption(conversation.id);await click(page,'Open read-only replay');await page.getByLabel('Validated message').selectOption(cited.id);await page.getByLabel('Exact planning assumptions').fill(JSON.stringify(planning.assumptions,null,2));await click(page,'Create reviewed proposal')
  check('discussion handoff preserves exact source conversation and message IDs',proposalBody?.source_conversation_id===conversation.id&&proposalBody?.source_message_id===cited.id,proposalBody)
  await click(page,'Apply reviewed proposal');check('linked proposal applies only after explicit review action',applyBody?.proposal_id==='v17-linked-proposal',applyBody)
  check('transport emitted only the four explicit provider-capable requests',creates===1&&direct===1&&invites===1&&councils===1,{creates,direct,invites,councils})
  check('no unexpected write escaped the labelled fixture',report.requests.unexpectedWrites.length===0,report.requests.unexpectedWrites)
  await context.close();report.status=report.failures.length?'FAIL':'PASS';if(report.failures.length)process.exitCode=1
}catch(error){report.status='FAIL';report.failures.push(error instanceof Error?error.stack:String(error));process.exitCode=1}
finally{await browser?.close();await mkdir(dirname(reportPath),{recursive:true});await writeFile(reportPath,JSON.stringify(report,null,2)+'\n')}
console.log(`V17 acceptance ${report.status}: ${report.checks.filter(item=>item.pass).length}/${report.checks.length} checks`)
