import {chromium} from '../../apps/web/node_modules/@playwright/test/index.mjs'
import {mkdir,readFile,writeFile} from 'node:fs/promises'
const base=process.env.FARMTACT_BASE_URL||'http://127.0.0.1:8080'
const out=process.env.FARMTACT_NAV_REPORT||'reports/mobile_navigation.json'
const dir=process.env.FARMTACT_NAV_SHOTS||'apps/web/screenshots/mobile-navigation'
const editionState=process.env.FARMTACT_EDITION_STATE
const report={status:'RUNNING',base,checks:[],errors:[],screenshots:[],limitations:['Chromium touch emulation, not physical iOS/Android hardware.']}
const browser=await chromium.launch();await mkdir(dir,{recursive:true})
function check(name,pass){report.checks.push({name,pass});if(!pass)throw Error(name)}
let page
try{
 for(const width of [360,390,430,1280]){
  const mobile=width<700,context=await browser.newContext({viewport:{width,height:900},hasTouch:mobile,isMobile:mobile,reducedMotion:'reduce',...(editionState?{storageState:editionState}:{})})
  if(!editionState){const state=JSON.parse(await readFile(process.env.FARMTACT_BROWSER_SESSION_STATE||'/tmp/farmtact-explorer-saved-release.json','utf8'));await context.addCookies([{name:'farmtact_session',value:state.cookie,url:base}])}
  page=await context.newPage();page.on('pageerror',e=>report.errors.push(e.message));await page.goto(base,{waitUntil:'networkidle'})
  const map=page.getByRole('group',{name:'Farm map',exact:true}),canvas=page.locator('.farm-world-canvas')
  await map.waitFor();await map.scrollIntoViewIfNeeded()
  const transform=()=>canvas.getAttribute('style')
  const cdp=await context.newCDPSession(page)
  const drag=async(x,y,dx,dy,cancel=false)=>{
   if(mobile){await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});for(let i=1;i<=12;i++){await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+dx*i/12,y:y+dy*i/12}]});await page.waitForTimeout(18)}await cdp.send('Input.dispatchTouchEvent',{type:cancel?'touchCancel':'touchEnd',touchPoints:[]})}
   else{await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x+dx,y+dy,{steps:12});await page.mouse.up()}
   await page.waitForTimeout(220)
  }
  if(mobile){
   const before=await transform(),scroll=await page.evaluate(()=>scrollY),r=await map.boundingBox()
   await drag(r.x+18,Math.min(r.y+r.height-35,800),0,-160)
   check(`${width}: ordinary swipe scrolls page`,await page.evaluate(()=>scrollY)>scroll+30)
   check(`${width}: ordinary swipe does not move map`,await transform()===before)
   await page.getByRole('button',{name:'Move farm',exact:true}).click();await map.scrollIntoViewIfNeeded()
  }
  const bedPoint=async()=>page.locator('.world-bed').evaluateAll(nodes=>{const v=document.querySelector('.farm-world-viewport').getBoundingClientRect();for(const n of nodes){const r=n.getBoundingClientRect(),x=r.x+r.width/2,y=r.y+r.height/2;if(x>v.x+35&&x<v.right-120&&y>Math.max(v.y+50,70)&&y<Math.min(v.bottom-70,800))return{x,y}}return null})
  let point=await bedPoint();if(!point)throw Error('No visible bed for actual gesture')
  const before=await transform();await drag(point.x,point.y,65,-25)
  check(`${width}: direct drag starting on a bed pans map`,await transform()!==before)
  check(`${width}: dragging does not open bed or advisor`,await page.getByRole('dialog').count()===0)
  check(`${width}: drag state clears on release`,!(await map.getAttribute('class')).includes('is-dragging'))
  check(`${width}: map dragging does not select page text`,await page.evaluate(()=>!getSelection()?.toString()))
  point=await bedPoint();if(mobile)await page.touchscreen.tap(point.x,point.y);else await page.mouse.click(point.x,point.y)
  await page.getByRole('dialog').waitFor();check(`${width}: next deliberate tap opens details`,await page.getByRole('dialog').isVisible())
  await page.getByRole('dialog').getByRole('button',{name:/Close/}).first().click()
  await page.getByRole('button',{name:'Recenter farm',exact:true}).click();await map.scrollIntoViewIfNeeded()
  const centered=await transform();await page.getByRole('button',{name:'View farm right',exact:true}).click();check(`${width}: visible arrow pans map`,await transform()!==centered)
  await map.focus();const old=await transform();await page.keyboard.press('ArrowLeft');check(`${width}: keyboard pans map`,await transform()!==old)
  await page.keyboard.press('Home');check(`${width}: keyboard Home recenters`,(await transform()).includes('translate(0px, 0px)'))
  if(mobile){point=await bedPoint();await drag(point.x,point.y,25,15,true);check(`${width}: cancelled touch clears dragging`,!(await map.getAttribute('class')).includes('is-dragging'));await page.getByRole('button',{name:'Exit map movement',exact:true}).click();check(`${width}: explicit exit restores scroll mode`,await map.evaluate(n=>getComputedStyle(n).touchAction==='pan-y pinch-zoom'))}
  else{const scroll=await page.evaluate(()=>scrollY);await map.hover();await page.mouse.wheel(0,200);await page.waitForTimeout(350);check('Desktop wheel scrolls page instead of trapping zoom',await page.evaluate(()=>scrollY)>scroll)}
  const preview=page.getByRole('slider',{name:'Preview simulation date',exact:true})
  await page.getByRole('button',{name:'Next preview day',exact:true}).click();check(`${width}: next-day tap advances preview`,await preview.inputValue()==='1')
  await page.getByRole('button',{name:'Previous preview day',exact:true}).click();check(`${width}: previous-day tap restores preview`,await preview.inputValue()==='0')
  check(`${width}: no horizontal page overflow`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))
  await page.getByRole('button',{name:mobile?'Move farm':'Move farm',exact:true}).scrollIntoViewIfNeeded();const path=`${dir}/${width}.png`;await page.screenshot({path,animations:'disabled'});report.screenshots.push(path)
  await context.close()
 }
 check('No browser runtime errors',report.errors.length===0);report.status='PASS'
}catch(e){report.status='FAIL';report.errors.push(String(e));if(page)await page.screenshot({path:`${dir}/failure.png`}).catch(()=>{});process.exitCode=1}
finally{await browser.close();await writeFile(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,errors:report.errors}))}
