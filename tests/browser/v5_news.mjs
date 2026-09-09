import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { mkdir, writeFile } from 'node:fs/promises'

const base=process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080'
const edition=process.env.FARMTACT_EDITION||'v5'
const state=process.env.FARMTACT_BROWSER_STATE||'/tmp/farmtact-v5-browser-state.json'
const output=process.env.FARMTACT_NEWS_REPORT||'reports/v5/news_browser.json'
const report={status:'RUNNING',base,edition,checks:[],page_errors:[],provider_submissions:0,fixtures:[]}
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),...(detail?{detail}:{})});if(!pass)throw Error(name)}
const browser=await chromium.launch()
try{
  const context=await browser.newContext({storageState:state,viewport:{width:390,height:844},reducedMotion:'reduce'})
  const page=await context.newPage()
  page.on('pageerror',e=>report.page_errors.push(e.message))
  page.on('request',r=>{if(r.method()==='POST'&&/\/planning-runs$|\/conversations.*\/(messages|invite|council)$/.test(new URL(r.url()).pathname))report.provider_submissions++})
  await page.goto(`${base}/${edition}/`,{waitUntil:'networkidle'})
  const panel=page.getByRole('region',{name:'News scout',exact:true})
  await panel.waitFor()
  await panel.locator('.news-browser>summary').click()
  await panel.locator('.news-records article').first().waitFor()
  check('real cached records appear',await panel.locator('.news-records article').count()>0)
  check('separate News and farm clocks',await panel.getByText(/Farm planning date:/).isVisible())
  check('no automatic numerical effect is claimed',await panel.getByText(/does not change your orders/).isVisible())
  const select=async(label,value)=>{
    await Promise.all([page.waitForResponse(r=>r.url().includes('/api/v1/news?')&&r.status()===200),panel.getByLabel(label,{exact:true}).selectOption(value)]); await page.waitForFunction(()=>document.querySelector('.news-panel')?.getAttribute('aria-busy')==='false')
  }
  await select('Region','regional')
  check('region filter updates records',await panel.locator('.news-records article>.kicker').evaluateAll(nodes=>nodes.every(n=>n.textContent.includes('regional'))))
  await select('Time','recent')
  check('recent means publication freshness',await panel.locator('.news-context-tag').evaluateAll(nodes=>nodes.every(n=>n.textContent.includes('Recent publication'))))
  await select('Time','future')
  check('missing future observations are explicit',await panel.getByText(/No matching source records provide explicit future event dates/).isVisible())
  await select('Time','ongoing')
  check('ongoing date filter is available',await panel.getByLabel('Time',{exact:true}).inputValue()==='ongoing')
  await select('Time','all')
  await select('Crop in headline','caixin')
  check('missing crop coverage is explicit',await panel.getByText(/No matching dated records/).isVisible())
  await select('Crop in headline','')
  await select('Region','all')
  await panel.locator('.news-source-list>summary').click()
  check('Reddit access is gated',await panel.getByText(/Approved API access and retention/).isVisible())
  check('restricted event calendar is not copied',await panel.getByText(/Calendar found, but published reuse terms/).isVisible())

  // Delay the obsolete region response. The actual source API still supplies
  // its body; only transport timing is a deliberate browser fixture.
  report.fixtures.push('delayed obsolete region response; no fabricated source records')
  await page.route('**/api/v1/news?**',async route=>{
    const response=await route.fetch()
    if(new URL(route.request().url()).searchParams.get('geography')==='singapore')await new Promise(r=>setTimeout(r,700))
    await route.fulfill({response})
  })
  await panel.getByLabel('Region',{exact:true}).selectOption('singapore')
  await panel.getByLabel('Region',{exact:true}).selectOption('regional')
  await page.waitForTimeout(1000)
  check('stale response cannot replace newer region results',await panel.locator('.news-records article>.kicker').evaluateAll(nodes=>nodes.length>0&&nodes.every(n=>n.textContent.includes('regional'))))
  await page.unroute('**/api/v1/news?**')

  for(const width of [360,390,430,1280]){
    await page.setViewportSize({width,height:900})
    check(`no document overflow at ${width}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))
    const boxes=await panel.locator('select').evaluateAll(nodes=>nodes.map(n=>({height:n.getBoundingClientRect().height,width:n.getBoundingClientRect().width})))
    check(`comfortable filter controls at ${width}`,boxes.every(b=>b.height>=44&&b.width>=100),boxes)
  }
  await page.setViewportSize({width:390,height:844})
  await panel.getByLabel('Time',{exact:true}).focus()
  check('keyboard focus is retained',await panel.getByLabel('Time',{exact:true}).evaluate(n=>n===document.activeElement))
  await mkdir('apps/web/screenshots/v5-news',{recursive:true})
  await panel.screenshot({path:'apps/web/screenshots/v5-news/news-390.png'})
  check('no provider submissions',report.provider_submissions===0)
  check('no page errors',report.page_errors.length===0,report.page_errors)
  report.status='PASS'
}catch(error){report.status='FAIL';report.error=String(error);process.exitCode=1}
finally{await browser.close();await mkdir(output.slice(0,output.lastIndexOf('/')),{recursive:true});await writeFile(output,JSON.stringify(report,null,2)+'\n');console.log(report.status,report.checks.length,'News browser checks')}
