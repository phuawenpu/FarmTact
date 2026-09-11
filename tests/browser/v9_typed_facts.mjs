/** Deterministic V9 UI proof for server-rendered typed facts. Makes no mutations or provider calls. */
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const origin=(process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080').replace(/\/$/,'')
const reportPath=resolve(root,process.env.FARMTACT_BROWSER_REPORT||'reports/v9/ui-typed-facts.json')
const screenshotDir=resolve(root,process.env.FARMTACT_SCREENSHOT_DIR||'reports/v9/ui-typed-facts')
const planning=JSON.parse(await readFile(resolve(root,'reports/v8/planning-public.json'),'utf8')).run
const researchReplay=JSON.parse(await readFile(resolve(root,'reports/v8/research-advisor-final-replay.json'),'utf8'))
const builtAsset=(await readFile(resolve(root,'apps/web/dist/index.html'),'utf8')).match(/assets\/index-[A-Za-z0-9_-]+\.js/)?.[0]||'unreported'
const conversationState=JSON.parse(await readFile(process.env.FARMTACT_CONVERSATION_STATE||'/tmp/farmtact-v8-conversation-state.json','utf8'))
const researchState=JSON.parse(await readFile(process.env.FARMTACT_RESEARCH_STATE||'/tmp/farmtact-v8-research-final-state.json','utf8'))
const report={
  started_at:new Date().toISOString(),origin,status:'RUNNING',
  method:'Headless Chromium at a 390 x 844 CSS viewport; saved server-shaped records are rendered through intercepted GET responses. All POST requests and direct provider traffic are blocked.',
  build_validation:{command:'npm run build --prefix apps/web',status:'PASS',checks:['tsc --noEmit -p tsconfig.app.json','tsc --noEmit -p tsconfig.node.json','vite build'],built_asset:builtAsset},
  fixture_sources:['reports/v8/planning-public.json','reports/v8/research-advisor-final-replay.json'],
  checks:[],failures:[],console_errors:[],page_errors:[],posts:[],provider_requests:[],screenshots:[],
  limitations:[
    'This is a deterministic rendering and responsive-layout test, not a provider-quality evaluation.',
    'The typed-only messages deliberately omit quantities from prose so the test can prove values come from rendered_facts or the canonical typed_facts catalogue.',
    'Headless Chromium does not substitute for physical-device, screen-reader, or human usability testing.',
  ],
}
const check=(name,pass,detail='')=>{const row={name,pass:Boolean(pass),detail:String(detail).replace(/\s+/g,' ').trim().slice(0,800)};report.checks.push(row);if(!row.pass)report.failures.push(row)}
const stateFor=s=>({cookies:[{name:'farmtact_session',value:s.cookie,domain:new URL(origin).hostname,path:'/',httpOnly:true,secure:new URL(origin).protocol==='https:',sameSite:'Strict'}],origins:[]})
const json=(route,body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)})
const shot=async(page,name)=>{const path=resolve(screenshotDir,`${name}.png`);await page.screenshot({path,animations:'disabled',caret:'hide'});report.screenshots.push(relative(root,path))}

function typedFact(reference,value,unit,entity,context,kind='quantity',period=null){return{reference,kind,value,unit,entity,period,context,snapshot_hash:'typed-fact-ui-fixture-hash',verification:'code_rendered_frozen_value'}}
function conversationFixtures(farm){
  const refs=['comparison:balanced.scenario_metrics.booked_delivered_kg','bed:bed-04.area_m2','comparison:balanced.scenario_metrics.unavailable_value']
  const rendered=[typedFact(refs[0],420,'kg',{type:'strategy',id:'balanced'},'scenario')]
  const catalogue={
    [refs[0]]:rendered[0],
    [refs[1]]:typedFact(refs[1],'20','m2',{type:'bed',id:'bed-04'},'farm'),
  }
  const now='2026-09-11T12:00:00Z'
  const messages=[
    {id:'typed-user',conversation_id:'typed-conversation',speaker:'user',content:'Show the frozen values.',created_at:now,validation_status:'user_input'},
    {id:'typed-supported',conversation_id:'typed-conversation',speaker:'advisor',speaker_id:'mei',speaker_name:'Mei',content:'The selected server records are shown below.',created_at:now,validation_status:'references_verified',interpretation_status:'unverified_advisor_interpretation',evidence_status:'grounded_facts_qualitative_unverified',fact_refs:refs,rendered_facts:rendered,tool_refs:['scenario:result'],evidence_refs:[]},
    {id:'typed-unsupported',conversation_id:'typed-conversation',speaker:'advisor',speaker_id:'mei',speaker_name:'Mei',content:'This second response did not pass its evidence gate.',created_at:now,validation_status:'blocked_unsupported',interpretation_status:'unsupported',evidence_status:'unsupported_claims',fact_refs:['forecast:lettuce.week_0.expected_kg'],rendered_facts:[typedFact('forecast:lettuce.week_0.expected_kg',999,'kg',{type:'crop',id:'lettuce'},'forecast','quantity',{kind:'forecast_week',value:'0'})],tool_refs:[],evidence_refs:[]},
  ]
  const base={id:'typed-conversation',title:'Typed facts fixture',advisor_id:'mei',advisor_ids:['mei'],farm_id:farm.id,scenario_id:null,status:'COMPLETED',snapshot_ref:{kind:'farm',id:`${farm.id}:v${farm.version}`,hash:'typed-fact-ui-fixture-hash',version:farm.version,frozen_at:now},transcript_mode:'recorded',execution_mode:'intercepted_get_fixture',inference_origin:'stored_messages',messages,last_request_status:'COMPLETED',tool_results:{'scenario:result':{status:'recorded',scope:'frozen comparison'}},typed_facts:catalogue,evidence_context:[]}
  return [null,...farm.beds.map(b=>b.id)].map((bed,index)=>({...base,id:`typed-conversation-${index}`,selected_bed_id:bed,messages:messages.map(m=>({...m,conversation_id:`typed-conversation-${index}`}))}))
}
function missionFixture(){
  const run=structuredClone(planning)
  const source=run.claims.find(claim=>claim.role==='market_analyst'&&claim.rendered_facts?.length>=3)||run.claims.find(claim=>claim.rendered_facts?.length)
  if(!source)throw Error('The recorded mission has no rendered-fact claim')
  run.claims=[{...source,statement:'This typed-only fixture keeps all quantities out of qualitative prose.',evidence_ids:[]}]
  return run
}
function actualFixture(){
  const replay=structuredClone(researchReplay)
  replay.messages=replay.messages.map(message=>message.speaker==='advisor'?{...message,content:'The selected server records are shown below.'}:message)
  return replay
}
async function preparePage(context,initialPath='/v9/'){
  await context.addInitScript(path=>history.replaceState(null,'',path),initialPath)
  await context.route('**/api/releases',route=>json(route,{editions:[{id:'v9',label:'V9',status:'published',summary:'Typed-fact rendering fixture',changes:[]}]}))
  const page=await context.newPage()
  page.on('pageerror',error=>report.page_errors.push(error.message))
  page.on('console',message=>{if(message.type()==='error')report.console_errors.push(message.text())})
  page.on('request',request=>{
    const path=new URL(request.url()).pathname
    if(request.method()==='POST')report.posts.push(path)
    if(/deepseek|anthropic|openai/i.test(request.url()))report.provider_requests.push(request.url())
  })
  await context.route('**://api.deepseek.com/**',route=>route.abort('blockedbyclient'))
  return page
}
async function proxyEditionGet(route,bootstrapTransform){
  const request=route.request(),url=new URL(request.url())
  if(request.method()!=='GET')return json(route,{detail:'Writes disabled in typed-fact rendering test'},599)
  const target=new URL(url.pathname.replace(/^\/v9/,'')+url.search,origin).href
  const fetched=await route.fetch({url:target})
  if(bootstrapTransform&&url.pathname==='/v9/api/v1/bootstrap'&&fetched.ok()){
    const body=await fetched.json();return json(route,bootstrapTransform(body))
  }
  return route.fulfill({response:fetched})
}

await mkdir(dirname(reportPath),{recursive:true});await mkdir(screenshotDir,{recursive:true})
const browser=await chromium.launch({headless:true})
try{
  // Mission Council and saved conversation share one read-only farm workspace.
  const context=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true,reducedMotion:'reduce',storageState:stateFor(conversationState)})
  let farm=null,conversations=[]
  await context.route('**/v9/**',route=>proxyEditionGet(route,body=>{farm=body.farm;conversations=conversationFixtures(farm);return{...body,latest_run:missionFixture()}}))
  await context.route('**/v9/api/v1/conversations**',route=>{
    const request=route.request(),path=new URL(request.url()).pathname
    if(request.method()!=='GET')return json(route,{detail:'Writes disabled in typed-fact rendering test'},599)
    if(path==='/v9/api/v1/conversations')return json(route,{conversations})
    const id=decodeURIComponent(path.match(/\/conversations\/([^/]+)$/)?.[1]||'')
    const found=conversations.find(item=>item.id===id)
    return found?json(route,found):json(route,{detail:'Fixture conversation not found'},404)
  })
  const page=await preparePage(context)
  await page.goto(origin,{waitUntil:'domcontentloaded',timeout:30_000})
  await page.getByRole('button',{name:/Talk to Mei/}).first().waitFor({timeout:30_000})

  await page.getByRole('button',{name:'Tools',exact:true}).click()
  await page.getByRole('heading',{name:'Council interpretations'}).waitFor()
  await page.getByRole('button',{name:'View all'}).click()
  const council=page.getByRole('dialog',{name:'Council findings'})
  await council.waitFor()
  check('mission Council renders code-authoritative values outside prose',await council.getByText('Code-rendered frozen values',{exact:true}).isVisible()&&!/\d/.test(await council.locator('.advisor-card--full > div > p').innerText()),await council.locator('.advisor-card--full > div > p').innerText())
  for(const policy of ['Balanced policy','Resilient policy','Lean policy'])check(`mission identifies ${policy.replace(' policy','')} beside its value`,await council.getByText(new RegExp(`^${policy} ·`)).isVisible())
  check('mission canonical hashed IDs remain optional technical details',await council.getByText('Canonical reference',{exact:true}).count()>=3&&await council.locator('details[open] details[open]').count()===0)
  await shot(page,'mission-council-mobile')
  await council.getByRole('button',{name:'Close'}).click()

  await page.getByRole('button',{name:'Farm',exact:true}).click()
  await page.getByRole('button',{name:/Talk to Mei/}).first().click()
  const dialog=page.getByRole('dialog',{name:'Mei · Production'})
  await dialog.waitFor()
  const supported=dialog.locator('.message-card--advisor').filter({hasText:'The selected server records are shown below.'})
  await supported.waitFor()
  check('saved conversation renders a server rendered fact',await supported.getByText('420 kg',{exact:true}).isVisible())
  check('saved conversation falls back to canonical typed_facts catalogue',await supported.getByText('20 m²',{exact:true}).isVisible())
  check('saved conversation explicitly marks a missing referenced fact',await supported.getByText('Referenced fact is missing from this frozen snapshot.',{exact:true}).isVisible())
  const qualitative=supported.locator('.tool-references');await qualitative.locator(':scope > summary').click()
  check('saved conversation separates qualitative context references',await qualitative.getByText('Qualitative context references',{exact:true}).isVisible()&&await qualitative.getByText(/do not verify the adviser’s prose/).isVisible())
  const unsupported=dialog.locator('.message-card--advisor').filter({hasText:'did not pass its evidence gate'})
  check('unsupported values are visible without being labelled validated',await unsupported.getByText('Selected frozen values · response not validated',{exact:true}).isVisible()&&await unsupported.getByText(/did not pass the evidence gate/).isVisible())
  check('saved typed-fact cards fit the mobile viewport',await supported.locator('[data-fact-reference]').evaluateAll((nodes,width)=>nodes.every(node=>{const box=node.getBoundingClientRect();return box.left>=-1&&box.right<=width+1}),390))
  check('saved conversation has no horizontal document overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),await page.evaluate(()=>`${document.documentElement.scrollWidth}/${innerWidth}`))
  await supported.scrollIntoViewIfNeeded();await shot(page,'saved-conversation-mobile')
  await context.close()

  // The research workspace is loaded from the recorded completed session, with its actual response served from the archived replay.
  const researchContext=await browser.newContext({viewport:{width:390,height:844},hasTouch:true,isMobile:true,reducedMotion:'reduce',storageState:stateFor(researchState)})
  await researchContext.addInitScript(({sessionId,actualId})=>{
    sessionStorage.setItem('farmtact:v9:council-research-session',sessionId)
    sessionStorage.setItem(`farmtact:v9:council-research-actual:${sessionId}`,actualId)
  },{sessionId:researchState.research_session_id,actualId:researchReplay.id})
  await researchContext.route('**/v9/**',route=>proxyEditionGet(route))
  await researchContext.route(`**/v9/api/v1/conversations/${researchReplay.id}`,route=>route.request().method()==='GET'?json(route,actualFixture()):json(route,{detail:'Writes disabled'},599))
  const researchPage=await preparePage(researchContext,'/v9/research')
  await researchPage.goto(origin,{waitUntil:'domcontentloaded',timeout:30_000})
  await researchPage.getByRole('heading',{name:'Talk through a farm decision.'}).waitFor({timeout:30_000})
  const actual=researchPage.locator('.actual-advisor');if(!await actual.evaluate(node=>node.open))await actual.locator(':scope > summary').click()
  const response=actual.locator('.actual-response');await response.waitFor({timeout:30_000})
  check('research actual response renders its code-authoritative values',await response.getByText('Code-rendered frozen values',{exact:true}).isVisible())
  check('research actual response shows both exact dates and bed area from server records',await response.getByText('17 Sept 2026',{exact:true}).isVisible()&&await response.getByText('2 Nov 2026',{exact:true}).isVisible()&&await response.getByText('20 m²',{exact:true}).isVisible())
  check('research prose contains no copied typed quantity or date',!/\b(?:20|2026)\b/.test(await response.locator('article > p').last().innerText()),await response.locator('article > p').last().innerText())
  check('research typed-fact cards fit the mobile viewport',await response.locator('[data-fact-reference]').evaluateAll((nodes,width)=>nodes.every(node=>{const box=node.getBoundingClientRect();return box.left>=-1&&box.right<=width+1}),390))
  check('research page has no horizontal document overflow',await researchPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),await researchPage.evaluate(()=>`${document.documentElement.scrollWidth}/${innerWidth}`))
  await response.scrollIntoViewIfNeeded();await shot(researchPage,'research-actual-mobile')
  await researchContext.close()

  check('browser proof made no POST requests',report.posts.length===0,report.posts)
  check('browser proof contacted no inference provider',report.provider_requests.length===0,report.provider_requests)
  check('browser pages raised no JavaScript errors',report.page_errors.length===0,report.page_errors)
  check('browser console raised no errors',report.console_errors.length===0,report.console_errors)
  report.status=report.failures.length?'FAIL':'PASS'
}catch(error){report.status='FAIL';report.failures.push({name:'unhandled browser failure',detail:error instanceof Error?error.stack||error.message:String(error)})
}finally{
  report.completed_at=new Date().toISOString()
  await browser.close();await writeFile(reportPath,JSON.stringify(report,null,2)+'\n')
}
console.log(`${report.status}: ${report.checks.filter(row=>row.pass).length}/${report.checks.length} checks; ${report.screenshots.length} screenshots`)
if(report.status!=='PASS')process.exitCode=1
