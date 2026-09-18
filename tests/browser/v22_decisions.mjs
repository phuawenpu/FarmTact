import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';

const root=process.cwd();
const {chromium}=await import(pathToFileURL(resolve(root,'apps/web/node_modules/@playwright/test/index.mjs')));
const base=process.env.BASE_URL||'http://127.0.0.1:4199';
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('V22 decision verification is local-only');
const artifacts=process.env.ARTIFACT_DIR||'/tmp/v22-decisions';
const report={status:'RUNNING',scope:'V22 decision clarity against the local UI and numerical API',checks:[],failures:[],page_errors:[],writes:[],blocked_writes:[],provider_requests:[],screenshots:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:!!pass,detail});console.log(`${pass?'PASS':'FAIL'} ${name}`);if(!pass)throw Error(name);};
let browser,page;
try{
 await mkdir(artifacts,{recursive:true});
 browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});
 context.setDefaultTimeout(45000);
 page=await context.newPage();
 page.on('pageerror',error=>report.page_errors.push(error.message));
 page.on('request',request=>{
  const path=new URL(request.url()).pathname;
  if(request.method()!=='GET'&&path.includes('/api/'))report.writes.push({method:request.method(),path});
  if(request.method()==='POST'&&/\/conversations(?:\/|$)|\/planning-sessions\/[^/]+\/review$/.test(path))report.provider_requests.push(path);
 });
 let creates=0,calculations=0;
 await page.route('**/api/**',async route=>{
  const request=route.request(),method=request.method(),path=new URL(request.url()).pathname;
  if(method==='GET'||method==='HEAD')return route.fallback();
  if(method==='POST'&&/\/planning-sessions$/.test(path)&&creates++===0)return route.fallback();
  if(method==='POST'&&/\/planning-sessions\/[^/]+\/calculate$/.test(path)&&calculations++===0)return route.fallback();
  report.blocked_writes.push({method,path});
  return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'V22 decision test blocked an unexpected mutation'})});
 });

 await page.goto(base+(process.env.APP_PATH||'/'),{waitUntil:'domcontentloaded'});
 await page.locator('.decision-guide h1').waitFor({timeout:60000});
 const skip=page.getByRole('button',{name:'Skip demo',exact:true});
 await skip.waitFor();await skip.click();
 const calculate=page.locator('.decision-guide').getByRole('button',{name:'Compare planting plans',exact:true}).or(page.getByRole('button',{name:'Calculate options',exact:true}));
 if(await calculate.isVisible().catch(()=>false))await calculate.click();
 await page.locator('.proposal-card').first().waitFor({timeout:240000});
 check('one local planning calculation at most',calculations<=1,{calculations,creates});

 const metricText=await page.locator('.metric-strip').innerText();
 check('metrics distinguish percent, fulfilled/requested kg, period and shortfall',/Booked coverage[\s\S]*%/i.test(metricText)&&/Confirmed orders[\s\S]*\d{2}\/\d{2}\/\d{4}[\s\S]*kg[\s\S]*shortfall/i.test(metricText),metricText);
 const cards=page.locator('.proposal-card');
 check('all available strategies explain modeled feasibility',await cards.count()>=2&&await cards.evaluateAll(items=>items.every(item=>/Feasible within modeled limits|constraints? flagged/i.test(item.textContent||''))));

 const brief=page.locator('.v12-plan-brief');
 const briefText=await brief.innerText();
 check('brief distinguishes feasibility from fulfillment and margin from net profit',/does not mean every order is fulfilled/i.test(briefText)&&/not net profit/i.test(briefText),briefText);
 check('brief shows signed alternative differences',/Difference if you choose another plan/i.test(briefText)&&/[+−±]\d/.test(briefText),briefText);
 const details=brief.locator('details');
 if(!(await details.evaluate(node=>node.open)))await details.locator('summary').click();
 const fullRows=await details.locator('ol > li').count();
 check('full dated schedule initially retains every row',fullRows>0&&await details.getByText(new RegExp(`${fullRows} of ${fullRows} complete schedule rows shown`)).isVisible(),{fullRows});
 const scheduleFilters=details.locator('.schedule-filters');
 const cropFilter=scheduleFilters.locator('label').filter({hasText:/^Crop/}).locator('select');
 const bedFilter=scheduleFilters.locator('label').filter({hasText:/^Bed/}).locator('select');
 const filterCounts=[await cropFilter.count(),await bedFilter.count(),await details.getByLabel('Active on/after',{exact:true}).count(),await details.getByLabel('Active on/before',{exact:true}).count()];
 check('complete schedule exposes crop, bed and date filters',filterCounts.every(count=>count===1),{filterCounts});
 const crop=await cropFilter.locator('option').nth(1).getAttribute('value');
 await cropFilter.selectOption(crop);
 const cropRows=await details.locator('ol > li').count();
 check('crop filter narrows without inventing schedule rows',cropRows>0&&cropRows<=fullRows,{cropRows,fullRows,crop});
 const firstDates=await details.locator('ol > li').first().innerText();
 const dates=firstDates.match(/\d{4}-\d{2}-\d{2}/g)||[];
 if(dates.length===3){
  await details.getByLabel('Active on/after',{exact:true}).fill(dates[2]);
  await details.getByLabel('Active on/before',{exact:true}).fill(dates[0]);
  check('date filters use complete allocation overlap',await details.locator('ol > li').count()>=1,{dates});
 }
 await cropFilter.selectOption('');
 await details.getByLabel('Active on/after',{exact:true}).fill('');
 await details.getByLabel('Active on/before',{exact:true}).fill('');

 const openEditor=async()=>{
  await page.getByRole('button',{name:/Adjust assumptions|Apply & Recalculate/,exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'Challenge constraints and recalculate'});await dialog.waitFor();return dialog;
 };
 let dialog=await openEditor();
 const labeled=(scope,label,control='input,select')=>scope.locator('label').filter({hasText:new RegExp(`^${escapeRegex(label)}`)}).locator(control).first();
 const scenarioCropField=labeled(dialog,'Crop affected by demand, yield and delay','select');
 check('editor exposes Crop affected by demand, yield and delay',await scenarioCropField.isVisible());
 await dialog.getByLabel('Add an order to this scenario').check();
 const orderFields=dialog.locator('.proposal-order-fields');
 for(const [label,control] of [['Customer / order reference','input'],['Crop','select'],['Due date','input'],['Quantity (kg)','input'],['Price (SGD/kg)','input'],['Status','select']])check(`editor exposes ${label}`,await labeled(orderFields,label,control).isVisible());
 const scenarioCrop=await scenarioCropField.inputValue();
 const scenarioHelp=await dialog.getByText(/Only this crop changes for/).innerText();
 check('percent assumptions name current-estimate baseline and exact dates',/current estimate is 100%/.test(await dialog.innerText())&&/\d{2}\/\d{2}\/\d{4}.+\d{2}\/\d{2}\/\d{4}/.test(scenarioHelp),scenarioHelp);
 await dialog.getByLabel('Expected demand',{exact:false}).fill('124');
 await dialog.getByLabel('Seasonal yield',{exact:false}).fill('83');
 await dialog.getByLabel('Harvest delay',{exact:false}).fill('3');
 await labeled(orderFields,'Customer / order reference').fill('V22-BUYER-17');
 const orderCrop=await labeled(orderFields,'Crop','select').inputValue();
 const due=await labeled(orderFields,'Due date').inputValue();
 await labeled(orderFields,'Quantity (kg)').fill('16');
 await labeled(orderFields,'Price (SGD/kg)').fill('9.5');
 await labeled(orderFields,'Status','select').selectOption('tentative');
 const summary=await dialog.locator('.proposal-review').innerText();
 check('review summary states exact scoped assumptions',summary.includes(scenarioCrop)&&summary.includes('124%')&&summary.includes('83%')&&/3 days later/.test(summary),summary);
 check('review summary states exact order reference, crop, date, kg, SGD and status',summary.includes('V22-BUYER-17')&&summary.includes(orderCrop)&&summary.includes('16 kg')&&summary.includes('SGD 9.5/kg')&&summary.includes('Tentative')&&summary.includes(formatCivil(due)),summary);
 check('review protects recorded past and keeps approval separate',/Past recorded work stays unchanged/.test(summary)&&/does not approve tasks/.test(summary),summary);
 check('submission verb is Calculate revised plans',await dialog.getByRole('button',{name:'Calculate revised plans',exact:true}).isVisible());
 await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});

 await page.reload({waitUntil:'domcontentloaded'});
 const reloadSkip=page.getByRole('button',{name:'Skip demo',exact:true});
 if(await reloadSkip.isVisible().catch(()=>false))await reloadSkip.click();
 await page.locator('.proposal-card').first().waitFor({timeout:60000});
 dialog=await openEditor();
 check('edition/session/revision draft survives reload',await labeled(dialog.locator('.proposal-order-fields'),'Customer / order reference').inputValue()==='V22-BUYER-17'&&await dialog.getByLabel('Expected demand',{exact:false}).inputValue()==='124');
 const storage=await page.evaluate(()=>Object.entries(localStorage).filter(([key])=>/proposal|draft/i.test(key)).map(([key,value])=>({key,value})).filter(item=>item.value.includes('V22-BUYER-17')));
 check('persistent draft is browser-local and edition namespaced',storage.length===1&&/v22/i.test(storage[0].key),storage.map(item=>({key:item.key,containsMarker:item.value.includes('V22-BUYER-17')})));
 await dialog.getByRole('button',{name:'Discard saved draft',exact:true}).click();
 dialog=await openEditor();
 check('discard clears the scoped draft',await dialog.getByLabel('Expected demand',{exact:false}).inputValue()==='100'&&!await dialog.getByLabel('Add an order to this scenario').isChecked());
 await page.keyboard.press('Escape');
 const remaining=await page.evaluate(()=>Object.values(localStorage).some(value=>value.includes('V22-BUYER-17')));
 check('discard removes persisted marker',!remaining);
 check('test made no provider requests',report.provider_requests.length===0,report.provider_requests);
 const blockedDuplicateCreates=report.blocked_writes.filter(item=>item.method==='POST'&&/\/planning-sessions$/.test(item.path));
 const otherBlocked=report.blocked_writes.filter(item=>!blockedDuplicateCreates.includes(item));
 check('session guard prevented a fresh-session storm',creates<=2&&blockedDuplicateCreates.length<=1,{creates,blockedDuplicateCreates});
 check('guard blocked no other unexpected writes',otherBlocked.length===0,otherBlocked);
 check('page raised no exceptions',report.page_errors.length===0,report.page_errors);
 const screenshot=resolve(artifacts,'decision-clarity-390.png');await page.screenshot({path:screenshot,fullPage:true,animations:'disabled'});report.screenshots.push(screenshot);
 report.status='PASS';await context.close();
}catch(error){report.status='FAIL';report.failures.push(error.stack||String(error));if(page)await page.screenshot({path:resolve(artifacts,'failure.png'),fullPage:true}).catch(()=>{});
}finally{
 if(browser)await browser.close();
 const output=resolve(process.env.REPORT_PATH||'/tmp/v22-decisions/report.json');await mkdir(resolve(output,'..'),{recursive:true});await writeFile(output,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,checks:report.checks.length,failures:report.failures}));if(report.status!=='PASS')process.exitCode=1;
}

function formatCivil(value){const [year,month,day]=value.split('-');return `${day}/${month}/${year}`;}
function escapeRegex(value){return value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}
