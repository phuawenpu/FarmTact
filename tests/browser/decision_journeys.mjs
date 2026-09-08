/** Real numerical browser journeys; no mocked planner or inference requests. */
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
const base = process.env.FARMTACT_BASE_URL || 'http://127.0.0.1:8080'
const dir = process.env.FARMTACT_DECISION_SCREENSHOTS || 'apps/web/screenshots/decisions'
const reportFile = process.env.FARMTACT_DECISION_REPORT || 'reports/decision_journeys.json'
const report = { status: 'RUNNING', base_url: base, inference_policy: 'No inference requested. All experiments run the actual backend planner.', checks: [], failures: [], screenshots: [], branches: [] }
function check(name, condition, detail) { report.checks.push({ name, pass: Boolean(condition), ...(detail === undefined ? {} : { detail }) }); if (!condition) throw new Error(name + (detail ? ': ' + JSON.stringify(detail) : '')) }
const pause = ms => new Promise(resolve => setTimeout(resolve, ms))
async function json(response) { if (!response.ok()) throw new Error(`API status ${response.status()}: ${await response.text()}`); return response.json() }
async function range(page, dialog, name, value) {
  const slider = dialog.getByRole('slider', { name: new RegExp(`^${name}`) })
  const min = Number(await slider.getAttribute('min')), max = Number(await slider.getAttribute('max'))
  await slider.focus(); const fromMin = value - min <= max - value
  await page.keyboard.press(fromMin ? 'Home' : 'End')
  for (let n = 0; n < (fromMin ? value - min : max - value); n++) await page.keyboard.press(fromMin ? 'ArrowRight' : 'ArrowLeft')
  check(`${name} edits through keyboard`, Number(await slider.inputValue()) === value)
}
async function click(page, name) { const button = page.getByRole('button', { name, exact: true }).filter({ visible: true }).first(); await button.scrollIntoViewIfNeeded(); await button.click() }
async function awaitScenario(request, id) {
  const until = Date.now() + 180000
  while (Date.now() < until) { const s = await json(await request.get(`${base}/api/v1/scenarios/${id}`)); if (['COMPLETED','FAILED'].includes(s.status)) return s; await pause(750) }
  throw new Error('Numerical branch did not complete within180 seconds')
}
await mkdir(dir, { recursive: true })
let browser
try {
  browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 360, height: 844 }, reducedMotion: 'reduce' })
  const page = await context.newPage(), errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(base, { waitUntil: 'networkidle' })
  const original = await json(await context.request.get(`${base}/api/v1/bootstrap`))
  const created = await json(await context.request.post(`${base}/api/v1/planning-runs`, { data: { council: false }, headers: { 'Idempotency-Key': 'decision-journey-main' } }))
  let main
  for (let i = 0; i < 180; i++) { main = await json(await context.request.get(`${base}/api/v1/planning-runs/${created.id}`)); if (!['CREATED','RUNNING'].includes(main.status)) break; await pause(750) }
  check('Main numerical plan establishes an accepted worklist', main.status === 'ACCEPTED_FOR_SIMULATION')
  const worklist = await (await context.request.get(`${base}/api/v1/planning-runs/${main.id}/worklist.csv`)).text()
  const journeys = [
    { width: 360, title: 'Late harvest', id: 'late_harvest', controls: [['Harvest delay',7],['Expected yield',70]] },
    { width: 390, title: 'Busy market', id: 'busy_market', controls: [['Market demand',130]] },
    { width: 430, title: 'Short-handed week', id: 'short_handed_week', controls: [['Available labour',60]] },
    { width: 1280, title: 'Tight budget', id: 'tight_budget', controls: [['Available cash',60]] },
  ]
  for (const j of journeys) {
    await page.setViewportSize({ width: j.width, height: j.width === 1280 ? 900 : 844 }); await page.goto(base, { waitUntil: 'networkidle' })
    await click(page,'Quest journal')
    const journal = page.getByRole('dialog',{name:'Quest journal'})
    await journal.locator('.quest-list article').filter({has: page.getByRole('heading',{name:j.title,exact:true})}).getByRole('button',{name:/Start quest|Try again/}).click()
    const lab = page.getByRole('dialog',{name:'Scenario lab'}); await lab.waitFor()
    check(`${j.width}px ${j.title}: advisor briefing is visible`, await lab.locator('.brief-card').isVisible())
    for (const [label,value] of j.controls) await range(page,lab,label,value)
    const createdResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/scenarios') && response.request().method() === 'POST')
    await lab.getByRole('button',{name:'Run experiment',exact:true}).click()
    const response = await createdResponse; check(`${j.title} creates a branch`,response.status()===201,await response.text()); const branchId = (await response.json()).id
    const branch = await awaitScenario(context.request,branchId)
    check(`${j.title} completes using local calculation`,branch.status==='COMPLETED'&&branch.inference_calls===0)
    report.branches.push({id:branch.id,quest_id:branch.quest_id,status:branch.status,simulation_status:branch.simulation_status})
    await lab.getByRole('heading',{name:'Inspect the trade-offs'}).waitFor({timeout:15000})
    for (const policy of ['Lean','Balanced','Resilient']) {
      await lab.getByRole('button',{name:policy,exact:true}).click()
      check(`${j.title}: ${policy} comparison is explicit`,(await lab.locator('table caption').textContent()).includes(policy))
      check(`${j.title}: ${policy} displays all outcome changes`,await lab.locator('.metric-delta').count()>=6)
      const row = branch.policy_comparisons.find(row=>row.policy===policy)
      check(`${j.title}: ${policy} baseline shares frozen inputs`,Boolean(row?.baseline_strategy_id)&&Boolean(row?.scenario_strategy_id))
    }
    await lab.getByRole('button',{name:'Mark trade-offs inspected',exact:true}).click()
    await lab.getByRole('button',{name:'Trade-off badge earned',exact:true}).waitFor()
    check(`${j.title}: debrief inspection persisted`,(await json(await context.request.get(`${base}/api/v1/quests`))).quests.find(q=>q.id===j.id).inspected_ids.includes(branch.id))
    const image = `${dir}/quest-${j.id}-${j.width}.png`; await page.screenshot({path:image,animations:'disabled'}); report.screenshots.push(image)
    await lab.getByRole('button',{name:'Ask an advisor about this branch',exact:true}).click()
    const chat = page.getByRole('dialog',{name:/Asha/}); await chat.waitFor()
    await chat.getByText(new RegExp(`frozen branch ${branch.id.slice(0,8)}`)).waitFor()
    await chat.getByText('Start with a farm question',{exact:true}).waitFor()
    const conversations = (await json(await context.request.get(`${base}/api/v1/conversations`))).conversations
    const attached = conversations.find(c=>c.snapshot_ref?.id===branch.id)
    check(`${j.title}: explanation opens the exact computed snapshot`,attached?.snapshot_ref?.hash===branch.input_hash,{snapshot:attached?.snapshot_ref,expected_hash:branch.input_hash})
    const events=(await json(await context.request.get(`${base}/api/v1/conversations/${attached.id}/events`))).events
    check(`${j.title}: opening explanation makes no inference call`,!events.some(e=>e.event_type==='inference_request_reserved'))
    await page.keyboard.press('Escape'); await page.reload({waitUntil:'networkidle'})
    const after = await json(await context.request.get(`${base}/api/v1/bootstrap`))
    check(`${j.title}: main farm and latest plan stay unchanged`,JSON.stringify(after.farm)===JSON.stringify(original.farm)&&after.latest_run.id===main.id)
    check(`${j.title}: accepted main worklist stays valid`,await (await context.request.get(`${base}/api/v1/planning-runs/${main.id}/worklist.csv`)).text()===worklist)
    await click(page,'Quest journal')
    const reopened=page.getByRole('dialog',{name:'Quest journal'}).locator('.quest-list article').filter({has:page.getByRole('heading',{name:j.title,exact:true})})
    await reopened.getByText('Trade-off finder',{exact:true}).waitFor()
    check(`${j.title}: badge survives page reload`,await reopened.getByText('Trade-off finder').isVisible())
    await page.keyboard.press('Escape')
  }
  await click(page,'Scenario lab')
  const lab=page.getByRole('dialog',{name:'Scenario lab'})
  await lab.getByRole('button',{name:/3.*Compare/}).click()
  const boxes=lab.locator('.branch-picker input[type=checkbox]')
  for (let i=0;i<await boxes.count();i++) if(await boxes.nth(i).isChecked()) await boxes.nth(i).uncheck()
  for(let i=0;i<3;i++) await boxes.nth(i).check()
  check('Fourth branch is disabled at comparison limit',await boxes.nth(3).isDisabled())
  await lab.getByRole('button',{name:'Compare selected',exact:true}).click()
  await lab.locator('thead th').nth(4).waitFor()
  check('Comparison shows baseline plus three branches',await lab.locator('thead th').count()===5)
  const compareShot=`${dir}/three-branch-comparison-1280.png`;await page.screenshot({path:compareShot,animations:'disabled'});report.screenshots.push(compareShot)
  await lab.getByRole('button',{name:/2.*Assumptions/}).click()
  await lab.getByRole('combobox',{name:'Challenge',exact:true}).selectOption('sandbox')
  const parentId=report.branches[3].id
  await lab.getByRole('combobox',{name:'Continue branch',exact:true}).selectOption(parentId)
  await range(page,lab,'Available cash',75)
  const continuedResponse=page.waitForResponse(r=>r.url().endsWith('/api/v1/scenarios')&&r.request().method()==='POST')
  await lab.getByRole('button',{name:'Run experiment',exact:true}).click()
  const continuedCreated=await continuedResponse;check('Sandbox continuation creates a saved branch',continuedCreated.status()===201,await continuedCreated.text())
  const continued=await awaitScenario(context.request,(await continuedCreated.json()).id)
  const parent=await json(await context.request.get(`${base}/api/v1/scenarios/${parentId}`))
  check('Continued experiment retains root baseline and parent relationship',continued.status==='COMPLETED'&&continued.parent_scenario_id===parentId&&continued.baseline_hash===parent.baseline_hash)
  check('Continuation applies cash relative to parent',Number(continued.input_snapshot.resources.cash_sgd)===Number(parent.input_snapshot.resources.cash_sgd)*.75)
  check('Open sandbox does not claim a quest badge',continued.quest_id===null)
  const final=await json(await context.request.get(`${base}/api/v1/bootstrap`))
  check('Continuation preserves main farm and accepted worklist',JSON.stringify(final.farm)===JSON.stringify(original.farm)&&final.latest_run.id===main.id&&await (await context.request.get(`${base}/api/v1/planning-runs/${main.id}/worklist.csv`)).text()===worklist)
  check('Decision journeys have no page exceptions',errors.length===0,errors)
  report.status='PASS'; await context.close()
} catch(error) { report.status='FAIL';report.failures.push(error.stack||String(error)) }
finally { if(browser) await browser.close();report.completed_at=new Date().toISOString();await writeFile(reportFile,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,failures:report.failures,report:reportFile}));if(report.status!=='PASS')process.exitCode=1 }
