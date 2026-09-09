import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs'
const base=(process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080').replace(/\/$/,'')
const browser=await chromium.launch({headless:true}),context=await browser.newContext({storageState:process.env.FARMTACT_BROWSER_STATE}),page=await context.newPage()
try{
  await page.goto(base,{waitUntil:'networkidle'});if(!await page.locator('.explorer-page').count())await page.getByRole('button',{name:'Data',exact:true}).filter({visible:true}).first().click()
  const select=page.getByRole('combobox',{name:'Dataset snapshot',exact:true});await select.locator('option').first().waitFor({state:'attached'})
  const current=await select.inputValue(),target=await select.locator('option').evaluateAll((options,current)=>options.map(option=>option.value).find(value=>value!==current)||'',current)
  if(!target)throw Error('A second snapshot is required for the race check')
  await page.route(url=>url.pathname.includes(`/data-explorer/snapshots/${encodeURIComponent(target)}`),async route=>{await new Promise(resolve=>setTimeout(resolve,800));await route.continue()},{times:1})
  await select.selectOption(target)
  await page.getByRole('status').filter({hasText:'Loading the selected snapshot'}).waitFor()
  if(await page.locator('.decision-mission,.generator-layout,.scenario-experiments').count())throw Error('Previous snapshot actions remained interactive while the new snapshot loaded')
  await page.getByText(/Loading the selected snapshot/).waitFor({state:'hidden'})
  if(await select.inputValue()!==target)throw Error('Selected snapshot changed during response')
  console.log(JSON.stringify({status:'PASS',checks:3}))
}finally{await context.close();await browser.close()}
