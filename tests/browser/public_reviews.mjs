import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs'
import {mkdir,writeFile} from 'node:fs/promises'
const base=process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080',expected=Number(process.env.FARMTACT_REVIEW_COUNT||10)
const output=process.env.FARMTACT_REVIEW_REPORT||'reports/public_reviews_browser.json',dir=process.env.FARMTACT_REVIEW_SHOTS||'apps/web/screenshots/public-reviews'
const report={status:'RUNNING',base,expected,checks:[],errors:[],requests:[],screenshots:[]}
const browser=await chromium.launch();await mkdir(dir,{recursive:true});let page
const check=(name,pass)=>{report.checks.push({name,pass});if(!pass)throw Error(name)}
try{
 const c=await browser.newContext({viewport:{width:360,height:844},hasTouch:true,reducedMotion:'reduce'});page=await c.newPage();page.on('pageerror',e=>report.errors.push(e.message));page.on('request',r=>{if(r.url().includes('/api/'))report.requests.push(r.url())})
 await page.goto(`${base}/review`,{waitUntil:'networkidle'});await page.locator('.review-card').first().waitFor()
 const response=await c.request.get(`${base}/api/v1/reviews`);check('Public API responds without sign-in',response.status()===200);const panel=await response.json()
 check(`${expected} independently authored reports present`,panel.reviews.length===expected&&new Set(panel.reviews.map(r=>r.reviewer_agent)).size===expected)
 check('All reviewers read source rubric',panel.reviews.every(r=>r.rubric_status==='read'&&JSON.stringify(r.rubric_source).includes('13')))
 check('Seven source rubric criteria rendered',await page.locator('.review-scorecard tbody tr').count()===7)
 check('Page explicitly identifies AI personas and unofficial scoring',(await page.locator('.review-disclosure').innerText()).includes('not official'))
 check('No farm session is created',(await c.cookies()).every(x=>x.name!=='farmtact_session'))
 for(const [i,criterion]of panel.rubric.criteria.entries()){
  const scores=panel.reviews.flatMap(r=>r.rubric_scores.filter(s=>s.criterion===criterion&&typeof s.score==='number').map(s=>s.score))
  const expectedMean=scores.length?(scores.reduce((a,b)=>a+b,0)/scores.length).toFixed(1):'Untested'
  check(`Mean excludes untested: ${criterion}`,await page.locator('.review-scorecard tbody tr').nth(i).locator('td').first().innerText()===expectedMean)
 }
 await page.getByLabel('Perspective',{exact:true}).selectOption('judge');check('Judge filter is accurate',await page.locator('.review-card').count()===panel.reviews.filter(r=>r.reviewer_type==='judge').length)
 await page.getByLabel('Perspective',{exact:true}).selectOption('end_user');check('End-user filter is accurate',await page.locator('.review-card').count()===panel.reviews.filter(r=>r.reviewer_type==='end_user').length)
 await page.getByLabel('Perspective',{exact:true}).selectOption('all');await page.getByLabel('Findings',{exact:true}).selectOption('high');check('Priority filter hides other priorities',await page.locator('.review-priority').evaluateAll(ns=>ns.every(n=>n.textContent==='high')))
 await page.getByLabel('Findings',{exact:true}).selectOption('all');await page.getByLabel('Search reviews',{exact:true}).fill('no-such-review-zz99');check('Empty search has clear feedback',await page.getByText('No reviewers match these filters.',{exact:true}).isVisible());await page.getByLabel('Search reviews',{exact:true}).fill('')
 const card=page.locator('.review-card').first(),e=card.locator('.review-evidence-links a').first();await e.click();const id=(await e.getAttribute('href')).slice(1)
 check('Evidence link expands its actual gallery',await page.locator(`[id="${id}"]`).isVisible())
 for(const r of panel.reviews){for(const e of r.evidence.filter(x=>x.type==='screenshot')){const image=await c.request.get(`${base}${e.path}`);check(`${r.id}/${e.id}: public evidence image resolves`,image.status()===200&&(image.headers()['content-type']||'').includes('image/png'))}}
 for(const width of [360,390,430,1280]){
  await page.setViewportSize({width,height:width<700?844:900});await page.evaluate(()=>scrollTo(0,0));check(`${width}: no horizontal overflow`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));const path=`${dir}/${width}.png`;await page.screenshot({path,animations:'disabled'});report.screenshots.push(path)
 }
 await page.getByLabel('Perspective',{exact:true}).focus();await page.keyboard.press('j');await page.keyboard.press('Tab');check('Filters work with keyboard',await page.getByLabel('Findings',{exact:true}).evaluate(n=>n===document.activeElement))
 check('No bootstrap or provider calls during review browsing',report.requests.every(x=>x.endsWith('/api/v1/reviews')))
 check('No page errors',report.errors.length===0);report.status='PASS'
}catch(e){report.status='FAIL';report.errors.push(String(e));if(page)await page.screenshot({path:`${dir}/failure.png`}).catch(()=>{});process.exitCode=1}
finally{await browser.close();await writeFile(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,errors:report.errors}))}
