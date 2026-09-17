import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const base=(process.env.BASE_URL||"http://127.0.0.1:4192").replace(/\/$/,"");
const report={status:"RUNNING",checks:[],failures:[]};
const check=(name,pass,detail)=>{report.checks.push({name,pass:Boolean(pass),detail});if(!pass)throw new Error(`${name}: ${JSON.stringify(detail)}`)};
const click=(page,name)=>page.getByRole("button",{name,exact:true}).click();
const actionResponse=(page,id)=>page.waitForResponse(r=>r.request().method()==="POST"&&new URL(r.url()).pathname.endsWith(`/api/v1/council-research/${id}/actions`));
const openResearch=async page=>{await click(page,"More");for(let i=0;i<3;i++)await click(page,"Next →");await click(page,"Open tool");for(let i=0;i<4;i++)await click(page,"Next");await click(page,"Open");await click(page,"Open research cards");};
const returnShell=async page=>{for(let i=0;i<8;i++){if(await page.getByRole("button",{name:"More",exact:true}).count())return;const back=page.getByRole("button",{name:"Back",exact:true});if(await back.count())await back.last().click();else break}await page.getByRole("button",{name:"More",exact:true}).waitFor()};
const backMenu=async page=>{await click(page,"Back");};
const menu=["Presentation","Frozen context","Discussion","Reviewed proposal","Calculation","Challenge","Results","Revision history","Actual adviser","Research report"];
const openMenu=async(page,index,label)=>{const current=(await page.locator(".integrated-tool__card h3").first().textContent())?.trim();const at=Math.max(0,menu.indexOf(current));for(let i=at;i<index;i++)await click(page,"Next");for(let i=at;i>index;i--)await click(page,"Previous");await click(page,`Open ${label}`)};
let browser;
try{
 browser=await chromium.launch({headless:true});const context=await browser.newContext({viewport:{width:390,height:844},reducedMotion:"reduce"});const page=await context.newPage();const errors=[];page.on("pageerror",e=>errors.push(e.message));
 await page.goto(base,{waitUntil:"domcontentloaded"});await page.locator(".ic-shell").waitFor();await openResearch(page);await click(page,"New study");await page.getByRole("heading",{name:/Research v1/}).waitFor();
 const id=await page.evaluate(async()=>((await(await fetch('/api/v1/council-research')).json()).sessions[0].id));

 // Continuous dialogue creates queued turns; stopping is separate from calculation.
 await openMenu(page,4,"Calculation");let response=actionResponse(page,id);await click(page,"Calculate version");await response;for(let i=0;i<120;i++){const done=await page.evaluate(async id=>(await(await fetch(`/api/v1/council-research/${id}`)).json()).numerical_calculation_status==="completed",id);if(done)break;await page.waitForTimeout(500)}await backMenu(page);
 await openMenu(page,2,"Discussion");await page.getByLabel("Saved draft").fill("Plan this frozen study and compare the trade-off.");response=actionResponse(page,id);await click(page,"Send scripted message");await response;await page.getByRole("button",{name:"Stop queued turns",exact:true}).waitFor();response=actionResponse(page,id);await click(page,"Stop queued turns");await response;
 check("V15 research stop clears queued scripted turns",await page.evaluate(async id=>(await(await fetch(`/api/v1/council-research/${id}`)).json()).pending_turns.length===0,id));

 // Reserve-bed preview is reviewed and discarded without changing the frozen input version.
 await backMenu(page);await openMenu(page,3,"Reviewed proposal");await page.getByLabel("Edit type").selectOption("reserve_bed");response=actionResponse(page,id);await click(page,"Review proposal");await response;await page.getByText(/Preview — not applied/).waitFor();response=actionResponse(page,id);await click(page,"Discard proposal");await response;
 check("V15 reservation preview can be discarded without mutation",await page.evaluate(async id=>{const s=await(await fetch(`/api/v1/council-research/${id}`)).json();return s.input_version===1&&s.proposal===null},id));

 // Order-confirmation edit goes through review and explicit apply.
 await page.getByLabel("Edit type").selectOption("order_status");await page.getByLabel("State").selectOption("unconfirmed");response=actionResponse(page,id);await click(page,"Review proposal");await response;response=actionResponse(page,id);await click(page,"Apply reviewed edit");await response;
 check("V15 order edit creates a new frozen version",await page.evaluate(async id=>(await(await fetch(`/api/v1/council-research/${id}`)).json()).input_version===2,id));

 // Calculate v2 and choose one eligible simulation-only result.
 await page.getByRole("heading",{name:"Prepare research edit",exact:true}).waitFor();await backMenu(page);await openMenu(page,4,"Calculation");response=actionResponse(page,id);await click(page,"Calculate version");await response;
 for(let i=0;i<120;i++){const done=await page.evaluate(async id=>["completed","failed","cancelled"].includes((await(await fetch(`/api/v1/council-research/${id}`)).json()).numerical_calculation_status),id);if(done)break;await page.waitForTimeout(500)}
 await page.getByText(/Version 2 · completed/i).waitFor({timeout:30000});
 await backMenu(page);await openMenu(page,6,"Results");check("historical Research result cannot be chosen as current",await page.getByRole("button",{name:"Choose simulation-only result",exact:true}).isDisabled());if(!await page.getByRole("heading",{name:"Saved result v2",exact:true}).count())await click(page,"Next");await page.getByRole("heading",{name:"Saved result v2",exact:true}).waitFor();const eligiblePolicy=await page.evaluate(async id=>{const s=await(await fetch(`/api/v1/council-research/${id}`)).json(),r=s.results.find(row=>row.version===s.input_version);return r?.calculation?.strategies.find(row=>row.status==="FEASIBLE"&&!row.violations.length)?.name||null},id);check("research fixture has an eligible strategy to choose",!!eligiblePolicy,eligiblePolicy);const researchBinding=await page.locator(".integrated-tool__card:visible").evaluate(card=>({entityId:card.getAttribute("data-entity-id"),entityKind:card.getAttribute("data-entity-kind"),sessionId:card.getAttribute("data-session-id"),inputHash:card.getAttribute("data-input-hash"),basis:card.getAttribute("data-outcome-basis"),actions:JSON.parse(card.getAttribute("data-card-actions")||"[]")}));check("V15 Research result card publishes frozen server binding and eligibility",researchBinding.entityId===`${id}:result:2`&&researchBinding.entityKind==="research_result"&&researchBinding.sessionId===id&&!!researchBinding.inputHash&&researchBinding.basis==="recorded_simulation"&&researchBinding.actions.some(action=>action.label==="Choose simulation-only result"&&action.eligibilitySource==="server"),researchBinding);await page.getByLabel("Policy").selectOption(eligiblePolicy);const choose=page.getByRole("button",{name:"Choose simulation-only result",exact:true});check("eligible result enables explicit choose action",await choose.isEnabled(),eligiblePolicy);response=actionResponse(page,id);await choose.click();await response;
 check("V15 eligible research result is explicitly chosen simulation-only",await page.evaluate(async id=>(await(await fetch(`/api/v1/council-research/${id}`)).json()).chosen?.simulation_only===true,id));

 // Create enough immutable revisions to exercise the second history page.
 await backMenu(page);await openMenu(page,0,"Presentation");for(let i=0;i<22;i++){await page.getByLabel("Change display").selectOption(i%2?"static":"transition");response=actionResponse(page,id);await click(page,"Save presentation settings");await response}
 await backMenu(page);await openMenu(page,7,"Revision history");await page.getByRole("button",{name:"Load next history page",exact:true}).waitFor();await click(page,"Load next history page");
 check("V15 research history loads beyond the first 20 revisions",await page.getByText(/Recorded server revision/).isVisible());

 // Report documents and links live in the same card deck.
 await backMenu(page);await openMenu(page,9,"Research report");await click(page,"Load research report");await page.getByText("Research sources",{exact:true}).waitFor();
 check("V15 research report exposes documents sources and screenshots",await page.getByText("Review screenshots",{exact:true}).isVisible()&&await page.locator("a").count()>0);

 // Returning to the saved-session index and reopening is read-only.
 await backMenu(page);await backMenu(page);await page.getByRole("heading",{name:"Saved Council research",exact:true}).waitFor();await click(page,"Open saved study");
 await page.getByRole("heading",{name:"Research v2",exact:true}).waitFor();check("V15 saved research study reopens with its current frozen version",true);

 // Explicit validated-gateway transport fixture for reload identity and accepted-POST refresh.
 let actualCreates=0,actualSends=0,failActualGet=false;const actualConversation={id:"v15-research-actual",snapshot_ref:{kind:"research",id,version:2},last_request_status:"COMPLETED",messages:[]};
 await page.route("**/api/v1/conversations",async route=>{if(route.request().method()!=="POST")return route.continue();actualCreates++;return route.fulfill({status:201,contentType:"application/json",body:JSON.stringify({id:actualConversation.id,status:"READY"})})});
 await page.route(`**/api/v1/conversations/${actualConversation.id}`,route=>{if(failActualGet){failActualGet=false;return route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({detail:"Fixture transcript refresh unavailable"})})}return route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(actualConversation)})});
 await page.route(`**/api/v1/conversations/${actualConversation.id}/messages`,route=>{actualSends++;const content=route.request().postDataJSON().content;actualConversation.messages.push({id:`actual-user-${actualSends}`,speaker:"user",content,validation_status:"recorded",fact_refs:[],rendered_facts:[]});return route.fulfill({status:202,contentType:"application/json",body:JSON.stringify({id:`actual-request-${actualSends}`,conversation_id:actualConversation.id,status:"COMPLETED"})})});
 await openMenu(page,8,"Actual adviser");await click(page,"Create frozen discussion");await page.getByText(/snapshot ref/i).waitFor();await page.goto(`${base}/play`,{waitUntil:"domcontentloaded"});await page.locator(".ic-shell").waitFor();const restoredExperiments=page.getByRole("heading",{name:"Scenarios & quests",exact:true});await restoredExperiments.waitFor({timeout:10000}).catch(()=>{});if(await restoredExperiments.count()){for(let i=0;i<4;i++)await click(page,"Next");await click(page,"Open");await click(page,"Open research cards")}else{await returnShell(page);await openResearch(page)}await click(page,"Open saved study");await openMenu(page,8,"Actual adviser");await page.getByText(/snapshot ref/i).waitFor();check("V15 research actual discussion identity survives reload without provider create",actualCreates===1,actualCreates);
 await page.getByLabel("Saved question draft").fill("Accepted research question before transcript refresh.");failActualGet=true;await click(page,"Submit explicit question");await page.getByRole("button",{name:"Refresh accepted submission",exact:true}).waitFor();check("accepted Research provider POST is not presented as a resend",actualSends===1,actualSends);await click(page,"Refresh accepted submission");check("Research transcript refresh makes no duplicate provider submission",actualSends===1,actualSends);

 // Explicit calculation-control transport fixture: hold each server state long enough to
 // exercise cancel and retry without racing the intentionally fast local worker.
 let calculationFixture=await page.evaluate(async id=>(await(await fetch(`/api/v1/council-research/${id}`)).json()),id),calculationActions=[];
 await page.route(`**/api/v1/council-research/${id}`,route=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(calculationFixture)}));
 await page.route(`**/api/v1/council-research/${id}/actions`,route=>{const body=route.request().postDataJSON();calculationActions.push(body.action);const next=structuredClone(calculationFixture);next.revision+=1;const current=next.results.find(row=>row.version===next.input_version);if(body.action==="run"){next.numerical_calculation_status="running";if(current)current.status="RUNNING"}else if(body.action==="cancel_calculation"){next.numerical_calculation_status="cancelled";if(current)current.status="CANCELLED"}else if(body.action==="retry_calculation"){next.numerical_calculation_status="queued";if(current)current.status="QUEUED"}calculationFixture=next;return route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(next)})});
 await backMenu(page);await openMenu(page,4,"Calculation");await click(page,"Recalculate version");await page.getByRole("button",{name:"Cancel calculation",exact:true}).waitFor();await click(page,"Cancel calculation");await page.getByRole("button",{name:"Retry calculation",exact:true}).waitFor();await click(page,"Retry calculation");check("V15 Research calculation exposes explicit run cancel retry sequence",calculationActions.join(",")==="run,cancel_calculation,retry_calculation",calculationActions);
 check("V15 research parity suite has no browser errors",errors.length===0,errors);report.status="PASS";
}catch(error){report.status="FAIL";report.failures.push(error instanceof Error?error.stack:String(error));process.exitCode=1}finally{if(browser)await browser.close();const path=resolve("reports/v15/research-browser.json");await mkdir(resolve("reports/v15"),{recursive:true});await writeFile(path,JSON.stringify(report,null,2)+"\n");process.stdout.write(JSON.stringify(report,null,2)+"\n")}
