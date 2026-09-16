import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";
const root = resolve(new URL("../..", import.meta.url).pathname),
  base = (process.env.FARMTACT_BASE_URL || "http://127.0.0.1:8080").replace(
    /\/$/,
    "",
  ),
  report = {
    status: "RUNNING",
    base_url: `${base}/v12`,
    inference_policy: "No Council or specialist request submitted.",
    checks: [],
    screenshots: [],
    failures: [],
  };
const check = (name, pass, detail) => {
  report.checks.push({ name, pass: Boolean(pass), detail });
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`);
};
let browser;
try {
  browser = await chromium.launch({ headless: true });
  let cookieValue = "";
  try {
    cookieValue =
      (await readFile("/tmp/v12-cookie.txt", "utf8")).trim().split(/\s+/).at(-1) || "";
  } catch { /* optional existing isolated tenant */ }
  const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      reducedMotion: "reduce",
    });
  if (cookieValue)
    await context.addCookies([{ name: "farmtact_session", value: cookieValue, url: base }]);
  const
    page = await context.newPage(),
    errors = [],
    provider = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (r.method() !== "GET" && /conversations|planning-sessions\/.+\/review$/.test(r.url()))
      provider.push([r.method(), r.url()]);
  });
  await page.goto(report.base_url, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /See the farm/ }).waitFor();
  check(
    "real backend opens seven-stage farmer workflow",
    (await page.locator(".flow-rail button").count()) === 7,
  );
  check(
    "real operations boundary visible",
    await page
      .getByText("Real operations disabled", { exact: true })
      .isVisible(),
  );
  check(
    "projected and reported classifications visible",
    (await page.getByText("Projected", { exact: true }).count()) >= 6 &&
      (await page.getByText(/Farmer-reported · unverified/).isVisible()),
  );
  await page.getByRole("button", { name: "Dismiss tutorial" }).click();
  await page.reload({ waitUntil: "domcontentloaded" });
  check(
    "tutorial dismissal persists",
    (await page.getByRole("button", { name: "Dismiss tutorial" }).count()) ===
      0,
  );
  const calculate=page.getByRole("button", { name: /Calculate options/ });
  if(await calculate.count())await calculate.click();
  await page.getByText("Lean", { exact: true }).waitFor({ timeout: 180000 });
  check(
    "real numerical calculation returns three options",
    (
      await Promise.all(
        ["Lean", "Balanced", "Resilient"].map((x) =>
          page.getByText(x, { exact: true }).count(),
        ),
      )
    ).every(Boolean),
  );
  check(
    "Council review remains explicit and unsubmitted",
    await page.getByRole("button", { name: /Review with Council/ }).isVisible(),
  );
  const cropPlanner=page.locator('.role-card').filter({hasText:'Crop Planner'});
  await cropPlanner.getByRole('button',{name:'Ask this specialist'}).click();
  let specialistSelect=page.getByRole('dialog',{name:'Ask a planning specialist'}).locator('select');
  check('Crop Planner opens Mei production specialist',
    await specialistSelect.inputValue()==='mei' &&
    (await specialistSelect.locator('option:checked').textContent())?.includes('Crop Planner'));
  await page.getByRole('button',{name:/Close Ask a planning specialist/}).click();
  const weatherMonitor=page.locator('.role-card').filter({hasText:'Weather & Risk Monitor'});
  await weatherMonitor.getByRole('button',{name:'Ask this specialist'}).click();
  specialistSelect=page.getByRole('dialog',{name:'Ask a planning specialist'}).locator('select');
  check('Weather role opens Hana weather specialist',
    await specialistSelect.inputValue()==='hana' &&
    (await specialistSelect.locator('option:checked').textContent())?.includes('Weather & Risk Monitor'));
  await page.getByRole('button',{name:/Close Ask a planning specialist/}).click();
  await page.getByRole("button", { name: /Apply & Recalculate/ }).click();
  const constraintText = await page
    .getByRole("dialog", { name: /Challenge constraints/ })
    .innerText();
  check(
    "constraint editor covers farm bottlenecks",
    [
      "Expected demand",
      "Seasonal yield",
      "Harvest delay",
      "Reserve a bed",
      "Nursery sites",
      "Labour hours/week",
      "Cash capacity (SGD)",
      "Add confirmed order (kg)",
      "Add tentative order (kg)",
    ].every((x) => constraintText.includes(x)),
    constraintText,
  );
  await page
    .getByRole("button", { name: /Close Challenge constraints/ })
    .click();
  await page.getByRole("button", { name: /Inbox/ }).click();
  check(
    "real Inbox exposes explicit candidate boundary",
    await page.getByText(/remain candidates until explicit review/).isVisible(),
  );
  const uploadName=`acceptance-${Date.now()}.csv`;
  const uploadAmount=`${Date.now()%100}.50`;
  await page.locator('.sandbox-upload input[type="file"]').setInputFiles({name:uploadName,mimeType:'text/csv',buffer:Buffer.from(`date,kind,amount,currency,reference\n2026-09-01,expense,${uploadAmount},SGD,acceptance-${Date.now()}\n`)});
  await page.getByRole('button',{name:'Upload candidate'}).click();
  await page.getByText(new RegExp(`${uploadName} · candidate`)).waitFor();
  const uploadCard=page.locator('.upload-review').filter({hasText:uploadName});
  const reviewText=await uploadCard.locator('.candidate-review').innerText();
  check('real candidate exposes provenance and extracted fields before confirmation',
    ['Provenance','Authority','Current Planning Authority','2026-09-01',uploadAmount,'Amount Sgd'].every(value=>reviewText.includes(value)),reviewText);
  await page.getByRole('button',{name:'Confirm reviewed fields'}).last().click();
  await page.getByText(new RegExp(`${uploadName} · confirmed`)).waitFor();
  check('real upload requires and records explicit review',await page.getByText(new RegExp(`${uploadName} · confirmed`)).isVisible());
  const manualName=`Manual acceptance ${Date.now()}`;
  const manualAmount=`${20+(Date.now()%70)}.73`;
  await page.getByRole('button',{name:'Open manual entry'}).click();
  await page.getByLabel('Source name').fill(manualName);
  await page.getByLabel('Amount (SGD)').fill(manualAmount);
  const [manualResponse]=await Promise.all([
    page.waitForResponse(response=>response.url().endsWith('/farm-workflow/imports')&&response.request().method()==='POST'),
    page.getByRole('button',{name:'Create review candidate'}).click(),
  ]);
  check('manual candidate endpoint accepts tenant-scoped record',manualResponse.status()===201,{status:manualResponse.status(),body:await manualResponse.text()});
  const manualCard=page.locator('.upload-review').filter({hasText:manualName});
  await manualCard.getByText(`${manualName} · candidate`).waitFor();
  const manualReviewText=await manualCard.innerText();
  check('real manual entry creates reviewable unconfirmed candidate',
    manualReviewText.includes(manualAmount)&&manualReviewText.includes('Not active; confirmation required')&&manualReviewText.includes(manualName),manualReviewText);
  await manualCard.getByRole('button',{name:'Confirm reviewed fields'}).click();
  await page.getByText(`${manualName} · confirmed`).waitFor();
  check('real manual candidate requires explicit confirmation',await page.getByText(`${manualName} · confirmed`).isVisible());
  await page.getByRole("button", { name: /Close Farm Inbox/ }).click();
  await page.getByRole("button", { name: /Apply & Recalculate/ }).click();
  await page.getByLabel("Expected demand",{exact:true}).fill("105");
  await page.getByRole("button", { name: /^Apply & Recalculate$/ }).last().click();
  await page.getByRole("dialog", { name: /Challenge constraints/ }).waitFor({state:'hidden',timeout:30000});
  const workflowState=await page.evaluate(async()=>fetch(`${location.pathname.replace(/\/$/,'')}/api/v1/farm-workflow`).then(response=>response.json()));
  check('real proposal is persisted and applied',workflowState.proposals.some(item=>item.status==='applied'));
  const approveButton=page.getByRole('button',{name:/Approve & Create Actions/});
  await approveButton.waitFor({state:'visible',timeout:180000});
  await page.waitForFunction(() => {
    const button=[...document.querySelectorAll('button')].find(item=>item.textContent?.includes('Approve & Create Actions'));
    return button && !button.disabled;
  },null,{timeout:180000});
  await approveButton.click();
  check('approval discloses advisory Council state and numerical checks',
    await page.getByText(/Council evidence:/).isVisible() &&
    await page.getByText(/completed numerical checks/).isVisible());
  const alreadyApproved=[...workflowState.proposals].reverse().find(item=>item.status==='approved');
  let approvedState;
  if(alreadyApproved){
    await page.getByRole('button',{name:/Close Approve & Create Actions/}).click();
    approvedState=workflowState;
  }else{
    await page.getByRole('button',{name:/Approve revision & create actions/}).click();
    await page.getByRole('dialog',{name:/Approve & Create Actions/}).waitFor({state:'hidden',timeout:30000});
    approvedState=await page.evaluate(async()=>fetch(`${location.pathname.replace(/\/$/,'')}/api/v1/farm-workflow`).then(response=>response.json()));
  }
  const approvedProposal=[...approvedState.proposals].reverse().find(item=>item.status==='approved');
  const durableTasks=approvedState.tasks.filter(item=>item.proposal_id===approvedProposal?.id);
  check('explicit approval persists revision-bound actions',Boolean(approvedProposal)&&durableTasks.length>0,{proposal:approvedProposal?.id,tasks:durableTasks.length});
  const target=durableTasks.find(item=>['pending','in_progress'].includes(item.status)&&item.planned_quantity>0&&item.unit)||durableTasks.find(item=>item.planned_quantity>0&&item.unit)||durableTasks[0];
  await page.locator(`[data-task-id="${target.id}"]`).click();
  const actual=page.getByLabel(new RegExp('Actual quantity'));
  if(await actual.count())await actual.fill(String(Math.max(0,Number(target.planned_quantity||1)-1)));
  for(const checkbox of await page.locator('.result-form input[type="checkbox"]').all())await checkbox.check();
  await page.getByLabel('Farmer note').fill('Acceptance-reported short quantity');
  await page.getByRole('button',{name:/Save reported result/}).click();
  await page.locator(`[data-task-id="${target.id}"]`).getByText('recovery_required').waitFor({timeout:30000});
  check('short reported result opens durable recovery',await page.getByText(/Keep completed work, change only the future/).isVisible());
  const corrected=Math.max(0,Number(target.planned_quantity||1)-0.5);
  await page.getByLabel('Corrected quantity').fill(String(corrected));
  await page.getByLabel('Reason').fill('Scale reading reconciled');
  await page.getByRole('button',{name:/Save auditable correction/}).click();
  await page.reload({waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:/See the farm/}).waitFor();
  const reloadedState=await page.evaluate(async()=>fetch(`${location.pathname.replace(/\/$/,'')}/api/v1/farm-workflow`).then(response=>response.json()));
  const durableTask=reloadedState.tasks.find(item=>item.id===target.id);
  check('reported result and correction survive reload',durableTask?.event_revision>=2&&Number(durableTask.actual_quantity)===corrected,durableTask);
  await page.getByRole("button", { name: /Open Waste Rescue/ }).click();
  check(
    "Waste Rescue binds server-derived frozen stock",
    await page.getByText(/server derives quantity and expiry/).isVisible(),
  );
  await page.getByRole("button", { name: /Close Waste Rescue/ }).click();
  await page.getByRole("button", { name: /How it works/ }).click();
  check(
    "three videos have captions",
    (await page.locator('video track[kind="captions"]').count()) === 3,
  );
  check(
    "three transcripts and downloads",
    (await page.getByText("Transcript", { exact: true }).count()) === 3 &&
      (await page.getByText("Download MP4", { exact: true }).count()) === 3,
  );
  await page.getByText("Transcript", { exact: true }).first().click();
  await page.waitForFunction(
    () => document.querySelectorAll(".explainer-transcript-scene").length === 12,
  );
  check(
    "caption-matched guides expose all twelve transcript scenes",
    (await page.locator(".explainer-transcript-scene").count()) === 12,
  );
  await page.getByRole("button", { name: /Close Three short guides/ }).click();
  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 });
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(100);
    const dims = await page.evaluate(() => ({
      body: document.body.scrollWidth,
      viewport: innerWidth,
    }));
    check(
      `${width}px has no body overflow`,
      dims.body <= dims.viewport + 1,
      dims,
    );
    const file = resolve(root, `apps/web/screenshots/v12-real-${width}.png`);
    await page.screenshot({
      path: file,
      fullPage: true,
      animations: "disabled",
    });
    report.screenshots.push(file.slice(root.length + 1));
  }
  check("no inference mutation submitted", provider.length === 0, provider);
  check("no page exceptions", errors.length === 0, errors);
  report.status = "PASS";
  await context.close();
} catch (e) {
  report.status = "FAIL";
  report.failures.push(e.stack || String(e));
} finally {
  if (browser) await browser.close();
  await mkdir(resolve(root, "reports/v12"), { recursive: true });
  await writeFile(
    resolve(root, "reports/v12/frontend-real.json"),
    JSON.stringify(report, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      status: report.status,
      checks: report.checks.length,
      failures: report.failures.length,
    }),
  );
  if (report.status !== "PASS") process.exitCode = 1;
}
