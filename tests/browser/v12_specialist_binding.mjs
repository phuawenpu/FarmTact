import { readFile } from "node:fs/promises";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";
const base=(process.env.FARMTACT_BASE_URL||"http://127.0.0.1:8080").replace(/\/$/,"");
let browser;
const checks=[];
const check=(name,pass)=>{checks.push({name,pass:Boolean(pass)});if(!pass)throw new Error(name)};
try {
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:390,height:844}});
  try {
    const cookie=(await readFile('/tmp/v12-cookie.txt','utf8')).trim().split(/\s+/).at(-1);
    if(cookie)await context.addCookies([{name:'farmtact_session',value:cookie,url:base}]);
  } catch {}
  const page=await context.newPage();
  const provider=[];
  page.on('request',request=>{if(request.method()!=='GET'&&/conversations|\/review$/.test(request.url()))provider.push(request.url())});
  await page.goto(`${base}/v12`,{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:/See the farm/}).waitFor();
  for(const [role,id,name] of [['Crop Planner','mei','Mei'],['Weather & Risk Monitor','hana','Hana']]){
    await page.locator('.role-card').filter({hasText:role}).getByRole('button',{name:'Ask this specialist'}).click();
    const select=page.getByRole('dialog',{name:'Ask a planning specialist'}).locator('select');
    check(`${role} binds ${name}`,await select.inputValue()===id&&(await select.locator('option:checked').textContent())?.includes(`${name} · ${role}`));
    await page.getByRole('button',{name:/Close Ask a planning specialist/}).click();
  }
  check('no provider submission',provider.length===0);
  await context.close();
  console.log(JSON.stringify({status:'PASS',checks:checks.length,failures:0}));
} catch(error) {
  console.log(JSON.stringify({status:'FAIL',checks:checks.length,failures:[String(error)]}));
  process.exitCode=1;
} finally {if(browser)await browser.close()}
