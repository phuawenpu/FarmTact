import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '../../apps/web/node_modules/@playwright/test/index.mjs';

const root=resolve(new URL('../..',import.meta.url).pathname),base=(process.env.BASE_URL||'http://127.0.0.1:4196').replace(/\/$/,'');
const report={status:'RUNNING',base,checks:[],failures:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)throw Error(`${name}: ${JSON.stringify(detail)}`)};
let browser;
try{
  browser=await chromium.launch({headless:true});
  const context=await browser.newContext({viewport:{width:360,height:520},storageState:'/tmp/farmtact-v15-cards-storage.json',reducedMotion:'reduce'}),page=await context.newPage(),writes=[],providers=[];
  page.on('request',request=>{const path=new URL(request.url()).pathname;if(!['GET','HEAD','OPTIONS'].includes(request.method()))writes.push(`${request.method()} ${path}`);if(/provider|deepseek|conversations\/.+\/messages|council|research\/.+\/(submit|review)/i.test(path))providers.push(`${request.method()} ${path}`)});
  await page.goto(`${base}/play`,{waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();
  for(let i=0;i<18&&!await page.getByRole('button',{name:'More',exact:true}).isVisible().catch(()=>false);i++){const back=page.getByRole('button',{name:'Back',exact:true}).filter({visible:true}).first();if(!await back.count())break;await back.click()}
  await page.getByRole('button',{name:'More',exact:true}).waitFor();
  await page.getByRole('button',{name:'Next →',exact:true}).click();
  const card=page.locator('.ic-card'),before={cardId:await card.getAttribute('data-card-id'),pager:await page.locator('.ic-deck-nav span').innerText()};
  const more=page.getByRole('button',{name:'More',exact:true});await more.scrollIntoViewIfNeeded();await page.evaluate(()=>window.scrollBy(0,80));before.scroll=await page.evaluate(()=>window.scrollY);await more.focus();before.focus=await page.evaluate(()=>document.activeElement?.textContent?.trim());
  const baselineWrites=writes.length,baselineProviders=providers.length;await more.click();await page.getByRole('button',{name:'Open tool',exact:true}).click();await page.locator('.integrated-tool,.integrated-records,.ik-shell').first().waitFor();const toolHeading=await page.locator('.ic-tool-parent').innerText();
  await page.reload({waitUntil:'domcontentloaded'});await page.locator('.ic-shell').waitFor();await page.locator('.integrated-tool,.integrated-records,.ik-shell').first().waitFor();
  check('reload restores the exact open tool',await page.locator('.ic-tool-parent').innerText()===toolHeading,{toolHeading,after:await page.locator('.ic-tool-parent').innerText()});
  for(let i=0;i<12&&!await page.locator('.ic-path').isVisible().catch(()=>false);i++){const back=page.getByRole('button',{name:'Back',exact:true}).filter({visible:true}).first();if(!await back.count())break;await back.click()}
  check('tool Back returns to the preserved More index',await page.locator('.ic-path').isVisible()&&/Farm tools/.test(await page.locator('.ic-path').innerText()),await page.locator('body').innerText());
  await page.getByRole('button',{name:'Back',exact:true}).click();await page.locator(`.ic-card[data-card-id="${before.cardId}"]`).waitFor();await page.waitForTimeout(100);
  const after={cardId:await card.getAttribute('data-card-id'),pager:await page.locator('.ic-deck-nav span').innerText(),scroll:await page.evaluate(()=>window.scrollY),focus:await page.evaluate(()=>document.activeElement?.textContent?.trim())};
  check('Back restores exact mission card ID and index',after.cardId===before.cardId&&after.pager===before.pager,{before,after});
  check('Back restores original More focus',after.focus==='More',{before,after});
  check('Back restores original document scroll',Math.abs(after.scroll-before.scroll)<=2,{before,after});
  check('reload-return browsing makes zero farm writes',writes.length===baselineWrites,{baselineWrites,writes});
  check('reload-return browsing makes zero provider submissions',providers.length===baselineProviders,{baselineProviders,providers});
  report.status='PASS';await context.close();
}catch(error){report.status='FAIL';report.failures.push(error instanceof Error?error.stack:String(error));process.exitCode=1}finally{await browser?.close();await mkdir(resolve(root,'reports/v15'),{recursive:true});await writeFile(resolve(root,'reports/v15/shell-reload-return.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2))}
