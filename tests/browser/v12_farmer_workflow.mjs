import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";
const root = resolve(new URL("../..", import.meta.url).pathname),
  base = process.env.FARMTACT_BASE_URL || "http://127.0.0.1:8080",
  report = { status: "RUNNING", checks: [], screenshots: [], failures: [] },
  check = (name, pass, detail) => {
    report.checks.push({ name, pass: Boolean(pass), detail });
    if (!pass) throw new Error(name);
  };
const beds = Array.from({ length: 8 }, (_, i) => ({
    id: `B${i + 1}`,
    name: `Bed ${i + 1}`,
    area_m2: 12.5,
    system: "sheltered_hydroponic",
    stage: i < 4 ? "growing" : "empty",
    progress: 0.5,
    crop_id: i < 4 ? ["caixin", "pak_choi", "lettuce", "kailan"][i] : undefined,
  })),
  farm = {
    id: "sg",
    name: "Singapore Leafy Greens Demo",
    location: "Singapore",
    timezone: "Asia/Singapore",
    data_mode: "synthetic_demo",
    cutoff: "2026-09-16T00:00:00Z",
    planning_date: "2026-09-16",
    horizon_days: 56,
    version: 12,
    resources: {
      area_m2: 100,
      nursery_sites: 500,
      labour_hours_per_week: 92,
      cash_sgd: 5400,
    },
    orders: [
      {
        id: "O1",
        crop_id: "caixin",
        due_date: "2026-10-02",
        quantity_kg: 120,
        price_sgd_per_kg: 8,
      },
    ],
    beds,
  },
  crops = ["caixin", "pak_choi", "lettuce", "kailan"].map((id) => ({
    id,
    label: id.replaceAll("_", " "),
    aliases: [],
    harvested_part: "leaves",
    evidence_ids: [],
    warnings: [],
    recipe: {
      cycle_days: 28,
      nursery_days: 9,
      yield_kg_per_m2: 2.4,
      validation_status: "synthetic",
    },
  }));
const strategy = (id, name, fill, waste, margin) => ({
    id,
    name,
    status: "FEASIBLE",
    description: `${name} uses the same inputs.`,
    metrics: {
      booked_requested_kg: 740,
      booked_delivered_kg: 740 * fill,
      waste_kg: waste,
      margin_sgd: margin,
      harvest_kg: 320,
      shortfall_kg: 740 - 740 * fill,
      cost_sgd: 400,
      labour_hours: 60,
      area_m2: 80,
      closing_stock_kg: 14,
    },
    allocations: [0, 1, 2].map((i) => ({
      id: `${id}-${i}`,
      bed_id: `B${i + 1}`,
      crop_id: crops[i].id,
      sow_date: "2026-09-18",
      transplant_date: "2026-09-27",
      harvest_date: "2026-10-16",
      area_m2: 10,
      expected_kg: 40 + i * 5,
    })),
    weekly: [],
    violations: [],
    assumptions: [],
  }),
  findings = [
    "Demand Planner",
    "Crop Planner",
    "Weather & Risk Monitor",
    "Market & Price Analyst",
    "Capacity & Cost Analyst",
    "Farm Planner",
    "Plan Reviewer",
  ].map((role, i) => ({
    role,
    functional_role: role,
    status: i === 1 ? "unavailable" : i === 5 ? "rejected" : "validated",
    truth_status: i === 3 ? "partial" : i === 1 || i === 5 ? "withheld" : "validated",
    summary: `${role} reviewed the candidate.`,
    question: `${role} challenge`,
    evidence: i === 1 ? [] : [{ id: `F00${i + 1}` }],
    tool_status:
      i === 1 ? "unavailable" : i === 5 ? "validation_failed" : "available",
    rejection_reasons: i === 5 ? ["Claim exceeded admitted evidence."] : [],
  }));
const session = {
    id: "session-v12",
    revision: 3,
    workflow: true,
    created_at: "2026-09-16",
    updated_at: "2026-09-16",
    status: "ready",
    stage: "review",
    farm,
    input_hash: "abc123def456",
    data_mode: "synthetic_demo",
    selected_strategy_id: "balanced",
    result: {
      strategies: [
        strategy("lean", "Lean", 0.72, 12, -48),
        strategy("balanced", "Balanced", 0.88, 7, 202),
        strategy("resilient", "Resilient", 0.94, 16, 150),
      ],
    },
    review: { status: "partial", truth_status: "partial", findings },
    simulation: null,
    job: null,
  },
  workflow = {
    version: "farmer-workflow-v1",
    phase: "decision",
    revision: 0,
    inbox: [{candidate_id:"photo-1",source_name:"harvest.jpg",source_kind:"photo_observation",status:"confirmed",authority:"observation_only",planning_eligible:false,provenance:{origin:"farmer_upload"},warnings:["Photo cannot establish yield."],rows:[{observation:"Leaf colour visible",crop_id:"caixin"}]}],
    proposals: [{id:"proposal-1",session_id:session.id,base_revision:3,proposal_revision:2,status:"applied",selected_strategy_id:"balanced",calculated_metrics:{coverage_kg:600,surplus_kg:14,expiry_kg:7,rejection_kg:null,margin_sgd:202,waste_rescue_kg:0}}],
    tasks: [{id:"task-1",proposal_id:"proposal-1",proposal_revision:2,action:"delivery",due_date:"2026-10-16",crop_id:"caixin",batch_id:"batch-1",location:"customer-1",checklist:["Confirm lot","Record accepted crop","Record rejected crop"],planned_quantity:40,actual_quantity:38,rejected_quantity:2,unit:"kg",status:"recovery_required",event_revision:1}],
    events: [],
    real_operations_enabled: false,
  };
let browser, page;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    reducedMotion: "reduce",
  });
  page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body = {};
    if (path.endsWith('/conversations') && route.request().method()==='POST') body={id:'conversation-1',status:'READY'};
    else if (path.endsWith('/conversations/conversation-1/messages')) body={id:'request-1',conversation_id:'conversation-1',status:'COMPLETED',message_id:'question-1'};
    else if (path.endsWith('/conversations/conversation-1')) body={id:'conversation-1',last_request_status:'COMPLETED',messages:[{id:'advisor-message-1',speaker:'advisor',speaker_name:'Idris',content:'Review a bounded demand adjustment.',validation_status:'references_verified',evidence_status:'partial',interpretation_status:'qualitative_unverified',evidence_refs:['F004'],rendered_facts:[{reference:'strategy.metrics.booked_delivered_kg',value:442,unit:'kg',context:'strategy',entity:{type:'strategy',id:'balanced_strategy'},snapshot_hash:'snapshot-abc',verification:'source_bound'}],proposed_actions:[{control:'demand_percent',target_id:'caixin',value:8,unit:'percent',status:'hypothesis_only'}]}]};
    else if (path.endsWith("/farm-workflow/imports") && route.request().method()==="POST") {
      const input=route.request().postDataJSON();
      body={candidate_id:"manual-1",source_name:input.source_name,source_kind:"manual",status:"candidate",authority:"review_candidate",planning_eligible:true,provenance:{origin:"farmer_manual_unverified"},warnings:["Requires farmer confirmation."],rows:input.rows};
      workflow.inbox.push(body);
    } else if (/\/farm-workflow\/imports\/[^/]+\/review$/.test(path) && route.request().method()==="POST") {
      const id=path.split('/').at(-2), item=workflow.inbox.find(row=>row.candidate_id===id);
      if(item)item.status=route.request().postDataJSON().decision==="confirm"?"confirmed":"rejected";
      body=item;
    } else if (path.endsWith("/farm-workflow")) body = workflow;
    else if (path.endsWith("/bootstrap"))
      body = {
        farm,
        crops,
        sources: [],
        capabilities: {
          deepseek: { status: "available", models: [] },
          vision: { status: "unavailable" },
          data_mode: "synthetic_demo",
          execution_mode: "simulation",
        },
        latest_run: null,
      };
    else if (path.endsWith("/planning-sessions"))
      body =
        route.request().method() === "POST" ? session : { sessions: [session] };
    else if (path.includes("/planning-sessions/")) body = session;
    else return route.continue();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
  await page.goto(`${base}/v12`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: /See the farm/ }).waitFor();
  check(
    "seven-stage workflow",
    (await page.locator(".flow-rail button").count()) === 7,
  );
  check(
    "five metrics",
    (
      await Promise.all(
        ["Coverage", "Surplus", "Expiry", "Rejection", "Margin"].map((x) =>
          page.getByText(x, { exact: true }).count(),
        ),
      )
    ).every(Boolean),
  );
  check("seven roles", (await page.locator(".role-card").count()) === 7);
  check(
    "rejected withheld",
    await page.getByText(/Withheld: Claim exceeded/).isVisible(),
  );
  check('partial Council role remains explicit',(await page.locator('.role-card--partial').count())===1);
  const reducedMotion=await page.locator('.farmer-flow button').first().evaluate(element=>({animation:getComputedStyle(element).animationDuration,transition:getComputedStyle(element).transitionDuration}));
  check('reduced-motion media query suppresses UI motion',
    ['0s','0.000001s','0.00001s','1e-06s'].includes(reducedMotion.animation)&&['0s','0.000001s','0.00001s','1e-06s'].includes(reducedMotion.transition),reducedMotion);
  await page.locator('.role-card').filter({hasText:'Market & Price Analyst'}).getByRole('button',{name:'Ask this specialist'}).click();
  await page.getByRole('button',{name:'Ask specialist'}).click();
  await page.getByRole('button',{name:'Review a proposal from this discussion'}).waitFor();
  check('reference checks do not overstate qualitative interpretation',
    await page.getByText('Evidence references checked; interpretation unverified').isVisible()&&
    await page.getByText(/Evidence status partial/).isVisible()&&
    await page.getByText('Typed facts from the frozen snapshot').isVisible()&&
    await page.getByText('442 kg').isVisible()&&
    await page.getByText('Booked delivered · balanced strategy').isVisible());
  await page.getByText('Fact provenance').click();
  check('raw fact identifiers remain available in expandable provenance',
    await page.getByText('snapshot-abc').isVisible()&&await page.getByText(/strategy · balanced_strategy/).isVisible()&&await page.getByText('source_bound').isVisible());
  check('validated discussion renders bounded proposed action',await page.getByText(/demand percent · target caixin · 8 percent/).isVisible());
  await page.getByRole('button',{name:'Review a proposal from this discussion'}).click();
  check('discussion handoff opens explicit editable proposal review',
    await page.getByText('Reviewed advisory context').isVisible()&&await page.getByText(/nothing is copied, widened or applied automatically/).isVisible()&&await page.getByRole('dialog',{name:/Challenge constraints/}).getByRole('button',{name:/Apply & Recalculate/}).isVisible());
  await page.getByRole('button',{name:/Close Challenge constraints/}).click();
  check(
    "approval gate",
    await page
      .getByRole("button", { name: /Approve & Create Actions/ })
      .isVisible(),
  );
  const taskText=await page.locator(".action-stage").innerText();
  check("durable task result controls are visible",["Rejected quantity (kg)","Checklist completed","Reviewed task photo"].every(value=>taskText.includes(value)),taskText);
  check("auditable correction control is visible",taskText.includes("Correct a reported quantity"),taskText);
  await page.getByRole("button", { name: /Inbox/ }).click();
  check(
    "upload families",
    await page.getByText(/CSV, XLSX, document or photo/).isVisible(),
  );
  await page.getByText('Review extracted evidence').first().click();
  const evidenceText=await page.locator('.candidate-review').first().innerText();
  check('candidate review exposes provenance warnings and extracted observations',
    ['farmer_upload','Photo cannot establish yield','Leaf colour visible'].every(value=>evidenceText.includes(value)),evidenceText);
  await page.getByRole('button',{name:'Open manual entry'}).click();
  await page.getByLabel('Record kind').selectOption('correction');
  check('manual correction requires target and signed delta',
    await page.getByLabel('Target transaction reference').isVisible()&&await page.getByLabel('Signed correction amount (SGD)').isVisible()&&await page.getByText(/Positive raises the target/).isVisible());
  await page.getByLabel('Record kind').selectOption('expense');
  await page.getByLabel('Source name').fill('Mock manual expense');
  await page.getByLabel('Amount (SGD)').fill('17.25');
  await page.getByRole('button',{name:'Create review candidate'}).click();
  await page.getByText('Mock manual expense · candidate').waitFor();
  check('manual record remains candidate with reviewable fields',
    (await page.locator('.upload-review').filter({hasText:'Mock manual expense'}).innerText()).includes('17.25'));
  await page.locator('.upload-review').filter({hasText:'Mock manual expense'}).getByRole('button',{name:'Confirm reviewed fields'}).click();
  await page.getByText('Mock manual expense · confirmed').waitFor();
  check('manual candidate requires explicit confirmation',await page.getByText('Mock manual expense · confirmed').isVisible());
  await page.getByRole("button", { name: /Close Farm Inbox/ }).click();
  await page.getByRole("button", { name: /How it works/ }).click();
  check(
    "caption tracks",
    (await page.locator('video track[kind="captions"]').count()) === 3,
  );
  check("downloads", (await page.getByText("Download MP4").count()) === 3);
  await page.getByRole("button", { name: /Close Three short guides/ }).click();
  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 });
    const dims = await page.evaluate(() => ({
      body: document.body.scrollWidth,
      viewport: innerWidth,
    }));
    check(`${width}px no overflow`, dims.body <= dims.viewport + 1, dims);
    const file = resolve(root, `apps/web/screenshots/v12-farmer-${width}.png`);
    await page.screenshot({
      path: file,
      fullPage: true,
      animations: "disabled",
    });
    report.screenshots.push(file.slice(root.length + 1));
  }
  check("no page exceptions", errors.length === 0, errors);
  report.status = "PASS";
  await context.close();
} catch (e) {
  report.status = "FAIL";
  report.failures.push(e.stack || String(e));
  if (page) report.failures.push((await page.locator("body").innerText()).slice(0, 3000));
} finally {
  if (browser) await browser.close();
  await mkdir(resolve(root, "reports/v12"), { recursive: true });
  await writeFile(
    resolve(root, "reports/v12/frontend-browser.json"),
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
