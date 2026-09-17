import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const root = resolve(new URL("../..", import.meta.url).pathname);
const base = (process.env.FARMTACT_BASE_URL || "http://127.0.0.1:8080").replace(/\/$/, "");
const expectDevelopmentDock = process.env.FARMTACT_EXPECT_DEV_DOCK === "1";
const result = { status: "RUNNING", checks: [], failures: [], screenshots: [] };
const check = (name, pass, detail) => {
  result.checks.push({ name, pass: Boolean(pass), detail });
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`);
};

const beds = [
  ["bed-01", "A1", "caixin", "growing"],
  ["bed-02", "A2", "pak_choi", "growing"],
  ["bed-03", "A3", "lettuce", "ready"],
  ["bed-04", "B1", "kailan", "growing"],
  ["bed-05", "B2", null, "empty"],
  ["bed-07", "B3", "kailan", "growing"],
].map(([id, name, crop_id, stage]) => ({
  id,
  name,
  crop_id: crop_id || undefined,
  stage,
  area_m2: 12.5,
  system: "sheltered_hydroponic",
  progress: stage === "empty" ? 0 : 0.56,
}));
const farm = {
  id: "singapore-demo",
  name: "Singapore Demo Farm",
  location: "Singapore",
  timezone: "Asia/Singapore",
  data_mode: "synthetic_demo",
  cutoff: "2026-09-17T00:00:00Z",
  planning_date: "2026-09-17",
  horizon_days: 56,
  version: 13,
  resources: {
    area_m2: 75,
    nursery_sites: 420,
    labour_hours_per_week: 88,
    cash_sgd: 5175,
  },
  orders: [
    {
      id: "order-confirmed-1",
      crop_id: "caixin",
      due_date: "2026-10-05",
      quantity_kg: 173,
      price_sgd_per_kg: 8.4,
      status: "confirmed",
    },
  ],
  beds,
  batches: [{
    id: "batch-07",
    bed_id: "bed-07",
    crop_id: "kailan",
    recipe_id: "recipe-kailan",
    sow_date: "2026-08-29",
    transplant_date: "2026-09-07",
    harvest_date: "2026-09-28",
    expected_marketable_kg: 48,
    executed: true,
  }],
};
const crops = ["caixin", "pak_choi", "lettuce", "kailan"].map((id) => ({
  id,
  label: id.replaceAll("_", " "),
  aliases: [],
  harvested_part: "leaves",
  evidence_ids: [],
  warnings: [],
  recipe: {
    cycle_days: 31,
    nursery_days: 9,
    yield_kg_per_m2: 2.4,
    validation_status: "synthetic",
  },
}));

const strategy = (id, name, metrics) => ({
  id,
  name,
  status: "FEASIBLE",
  description: `${name} is calculated from the frozen planning snapshot.`,
  metrics: {
    fill_rate: metrics.fill_rate,
    booked_requested_kg: 617,
    booked_delivered_kg: metrics.booked_delivered_kg,
    booked_shortfall_kg: Math.max(0, 617 - metrics.booked_delivered_kg),
    margin_sgd: metrics.margin_sgd,
    waste_kg: metrics.waste_kg,
    harvest_kg: metrics.harvest_kg,
    shortfall_kg: metrics.shortfall_kg,
    cost_sgd: metrics.cost_sgd,
    labour_hours: metrics.labour_hours,
    area_m2: metrics.area_m2,
    closing_stock_kg: metrics.closing_stock_kg,
  },
  allocations: ["bed-01", "bed-02", "bed-04"].map((bed_id, index) => ({
    id: `${id}-allocation-${index}`,
    bed_id,
    crop_id: crops[index].id,
    sow_date: "2026-09-19",
    transplant_date: "2026-09-28",
    harvest_date: "2026-10-20",
    area_m2: 12.5,
    expected_kg: 43 + index,
  })),
  weekly: [],
  violations: [],
  assumptions: [],
  input_hash: `input-${id}`,
});
const beforeStrategies = [
  strategy("lean", "Lean", {
    fill_rate: 0.713,
    booked_delivered_kg: 439.9,
    margin_sgd: 271.35,
    waste_kg: 11.8,
    harvest_kg: 451.7,
    shortfall_kg: 177.1,
    cost_sgd: 406.7,
    labour_hours: 58.3,
    area_m2: 50,
    closing_stock_kg: 11.8,
  }),
  strategy("balanced", "Balanced", {
    fill_rate: 0.817,
    booked_delivered_kg: 504.1,
    margin_sgd: 318.42,
    waste_kg: 7.3,
    harvest_kg: 511.4,
    shortfall_kg: 112.9,
    cost_sgd: 431.2,
    labour_hours: 66.4,
    area_m2: 62.5,
    closing_stock_kg: 7.3,
  }),
  strategy("resilient", "Resilient", {
    fill_rate: 0.864,
    booked_delivered_kg: 533.1,
    margin_sgd: 294.17,
    waste_kg: 13.2,
    harvest_kg: 546.3,
    shortfall_kg: 83.9,
    cost_sgd: 469.8,
    labour_hours: 72.1,
    area_m2: 75,
    closing_stock_kg: 13.2,
  }),
];
const afterStrategies = [
  strategy("lean-revised", "Lean", {
    fill_rate: 0.681,
    booked_delivered_kg: 420.2,
    margin_sgd: 252.91,
    waste_kg: 10.4,
    harvest_kg: 430.6,
    shortfall_kg: 196.8,
    cost_sgd: 401.1,
    labour_hours: 55.7,
    area_m2: 50,
    closing_stock_kg: 10.4,
  }),
  strategy("balanced-revised", "Balanced", {
    fill_rate: 0.764,
    booked_delivered_kg: 471.4,
    margin_sgd: 286.73,
    waste_kg: 5.9,
    harvest_kg: 477.3,
    shortfall_kg: 145.6,
    cost_sgd: 423.6,
    labour_hours: 61.2,
    area_m2: 50,
    closing_stock_kg: 5.9,
  }),
  strategy("resilient-revised", "Resilient", {
    fill_rate: 0.803,
    booked_delivered_kg: 495.5,
    margin_sgd: 269.08,
    waste_kg: 9.7,
    harvest_kg: 505.2,
    shortfall_kg: 121.5,
    cost_sgd: 451.9,
    labour_hours: 68.3,
    area_m2: 62.5,
    closing_stock_kg: 9.7,
  }),
];

const session = {
  id: "session-v13-tactical",
  revision: 7,
  workflow: true,
  created_at: "2026-09-17T00:00:00Z",
  updated_at: "2026-09-17T00:00:00Z",
  status: "COMPLETED",
  stage: "review",
  farm,
  input_hash: "frozen-v13-input-7841",
  result_id: "result-before-7841",
  data_mode: "synthetic_demo",
  selected_strategy_id: "balanced",
  result: { strategies: beforeStrategies },
  review: { status: "partial", truth_status: "partial", findings: [] },
  job: { id: "job-before", kind: "planning", status: "COMPLETED", stage: "completed" },
  tactical_context: {
    version: "v13-tactical-prototype-v1",
    planning_snapshot: {
      session_id: "session-v13-tactical",
      result_id: "result-before-7841",
      input_hash: "frozen-v13-input-7841",
      revision: 7,
      status: "COMPLETED",
    },
    scenario: {
      id: "synthetic-heavy-rainfall-v1",
      entity_kind: "scenario",
      title: "Heavy rainfall",
      label: "SIMULATION · SCENARIO ONLY",
      source: "Frozen synthetic seasonal record",
      execution_mode: "simulation",
      inference_triggered: false,
      ask_eligible: true,
      ask_disabled_reason: null,
    },
    grow_space: {
      id: "bed-07",
      entity_kind: "grow_space",
      title: "Keep grow space B3 free",
      name: "B3",
      area_m2: 12.5,
      system: "sheltered_hydroponic",
      source: "Frozen planning snapshot",
      reservation_window: { start_date: "2026-10-01", end_date: "2026-11-11" },
      reservation_active: false,
      reserve_eligible: true,
      reserve_disabled_reason: null,
      ask_eligible: true,
      ask_disabled_reason: null,
    },
  },
  scenario_set: [
    {
      id: "heavy-rainfall-scenario",
      title: "Heavy rainfall",
      reason: "Synthetic seasonal stress test",
      provenance: "synthetic_assumption",
      observed_at: null,
      retrieved_at: "2026-09-17T00:00:00Z",
      yield_percent: 82,
      delay_days: 3,
    },
  ],
  assumptions: {
    future_demand: [],
    order_changes: [],
    seasonal: [
      {
        id: "heavy-rainfall-scenario",
        crop_id: "caixin",
        system: "sheltered_hydroponic",
        start_date: "2026-09-17",
        end_date: "2026-10-14",
        yield_percent: 82,
        delay_days: 3,
        reason: "Heavy rainfall",
        provenance: "synthetic_assumption",
      },
    ],
  },
};
const proposal = {
  id: "proposal-reserve-bed-07",
  session_id: session.id,
  base_revision: 7,
  proposal_revision: 1,
  status: "draft",
  selected_strategy_id: "balanced",
  calculated_metrics: {
    coverage_kg: 504.1,
    surplus_kg: 7.3,
    expiry_kg: 7.3,
    rejection_kg: 0,
    margin_sgd: 318.42,
  },
  changes: [
    {
      kind: "planning_assumptions",
      assumptions: {
        tentative_orders: [],
        future_demand: [],
        seasonal: [],
        order_changes: [],
        reservations: [
          { bed_id: "bed-07", start_date: "2026-10-01", end_date: "2026-11-11" },
        ],
      },
    },
  ],
};
const workflow = {
  version: "farmer-workflow-v1",
  phase: "decision",
  revision: 0,
  inbox: [],
  proposals: [],
  tasks: [],
  events: [],
  real_operations_enabled: false,
};
const inverseProposal = {
  id: "proposal-inverse-bed-07",
  session_id: session.id,
  base_revision: 8,
  proposal_revision: 9,
  status: "applied",
  selected_strategy_id: "balanced-revised",
  calculated_metrics: {},
  changes: [{ kind: "planning_assumptions", assumptions: { ...session.assumptions, reservations: [] } }],
  inverse_of_proposal_id: proposal.id,
  recalculation_job: { id: "result-inverse-bed-07", status: "QUEUED" },
};

let browser;
let activePage;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  activePage = page;
  const pageErrors = [];
  const providerMutations = [];
  const proposalBodies = [];
  const inverseBodies = [];
  const conversationBodies = [];
  let calculationPolls = 0;
  let applied = false;
  let inverseApplied = false;
  let inversePolls = 0;
  let interveningChange = false;

  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();
    let body;
    let status = 200;

    if (path.endsWith("/bootstrap")) {
      body = {
        farm,
        crops,
        sources: [
          {
            id: "heavy-rainfall-scenario",
            name: "Heavy rainfall",
            status: "scenario",
            observed_at: null,
            retrieved_at: "2026-09-17T00:00:00Z",
            freshness: "frozen planning scenario",
            origin: "synthetic",
            execution_mode: "simulation",
            summary: "Synthetic seasonal stress test; not a weather observation.",
            snapshot_id: "frozen-v13-input-7841",
          },
        ],
        capabilities: {
          deepseek: { status: "available", models: [] },
          vision: { status: "unavailable" },
          data_mode: "synthetic_demo",
          execution_mode: "simulation",
        },
        latest_run: null,
      };
    } else if (path.endsWith("/planning-sessions") && method === "GET") {
      body = { sessions: [session] };
    } else if (path.endsWith(`/planning-sessions/${session.id}`) && method === "GET") {
      if (inverseApplied) {
        inversePolls += 1;
        if (inversePolls === 1) {
          session.job = { id: "result-inverse-bed-07", kind: "recalculation", status: "RUNNING", stage: "solving" };
          session.status = "RUNNING";
        } else {
          session.revision = 9;
          session.status = "COMPLETED";
          session.result_id = "result-inverse-bed-07";
          session.selected_strategy_id = "balanced";
          session.result = { strategies: beforeStrategies };
          session.job = { id: "result-inverse-bed-07", kind: "recalculation", status: "COMPLETED", stage: "completed" };
          session.tactical_context.planning_snapshot = {
            ...session.tactical_context.planning_snapshot,
            result_id: "result-inverse-bed-07",
            revision: 9,
            status: "COMPLETED",
          };
          session.tactical_context.grow_space.reservation_active = false;
          session.tactical_context.grow_space.reserve_eligible = true;
          session.tactical_context.grow_space.reserve_disabled_reason = null;
          inverseProposal.recalculation_job.status = "COMPLETED";
        }
      } else if (applied && !interveningChange) {
        calculationPolls += 1;
        if (calculationPolls === 1) {
          session.job = { id: "job-reserve-bed-07", kind: "recalculation", status: "RUNNING", stage: "solving" };
          session.status = "RUNNING";
        } else {
          session.revision = 8;
          session.status = "COMPLETED";
          session.stage = "review";
          session.result_id = "result-after-3109";
          session.selected_strategy_id = "balanced-revised";
          session.result = { strategies: afterStrategies };
          session.job = { id: "job-reserve-bed-07", kind: "recalculation", status: "COMPLETED", stage: "completed" };
          session.tactical_context.planning_snapshot = {
            ...session.tactical_context.planning_snapshot,
            result_id: "result-after-3109",
            revision: 8,
            status: "COMPLETED",
          };
          session.tactical_context.grow_space.reservation_active = true;
          session.tactical_context.grow_space.reserve_eligible = false;
          session.tactical_context.grow_space.reserve_disabled_reason = "This grow space is already reserved.";
          proposal.status = "applied";
          proposal.proposal_revision = 8;
          proposal.applied_session_revision = 7;
          proposal.recalculation_job = { id: "result-after-3109", status: "COMPLETED" };
          proposal.recalculated_metrics = {
            coverage_kg: 471.4,
            surplus_kg: 5.9,
            expiry_kg: 5.9,
            rejection_kg: 0,
            margin_sgd: 286.73,
          };
          proposal.metric_deltas = {
            coverage_kg: -32.7,
            surplus_kg: -1.4,
            expiry_kg: -1.4,
            rejection_kg: 0,
            margin_sgd: -31.69,
          };
          proposal.undo = { available: true, reason: null, expected_session_revision: 8 };
        }
      }
      body = session;
    } else if (path.endsWith("/farm-workflow") && method === "GET") {
      if (workflow.proposals[0]) {
        workflow.proposals[0].undo = interveningChange
          ? { available: false, reason: "Undo is stale after an intervening revision." }
          : workflow.proposals[0].undo;
      }
      body = workflow;
    } else if (path.endsWith("/farm-workflow/proposals") && method === "POST") {
      const submitted = request.postDataJSON();
      proposalBodies.push(submitted);
      body = { ...proposal, base_revision: submitted.base_revision };
      status = 201;
    } else if (path.endsWith(`/farm-workflow/proposals/${proposal.id}/apply`) && method === "POST") {
      applied = true;
      proposal.status = "applied";
      proposal.recalculation_job = { id: "job-reserve-bed-07", status: "QUEUED" };
      proposal.undo = { available: false, reason: "Wait for recalculation to finish." };
      workflow.proposals = [proposal];
      session.job = { id: "job-reserve-bed-07", kind: "recalculation", status: "QUEUED", stage: "queued" };
      session.status = "QUEUED";
      body = proposal;
    } else if (path.endsWith(`/farm-workflow/proposals/${proposal.id}/inverse`) && method === "POST") {
      inverseBodies.push(request.postDataJSON());
      if (session.revision !== proposal.proposal_revision) {
        status = 409;
        body = { detail: "The inverse is stale after an intervening revision." };
      } else {
        inverseApplied = true;
        inversePolls = 0;
        proposal.inverse_proposal_id = inverseProposal.id;
        proposal.undo = { available: false, reason: "Undo has already been submitted." };
        workflow.proposals = [proposal, inverseProposal];
        session.status = "QUEUED";
        session.job = { id: "result-inverse-bed-07", kind: "recalculation", status: "QUEUED", stage: "queued" };
        body = inverseProposal;
        status = 202;
      }
    } else if (path.endsWith("/conversations") && method === "POST") {
      providerMutations.push(path);
      conversationBodies.push(request.postDataJSON());
      body = { id: "conversation-focused-bed-07", status: "READY" };
      status = 201;
    } else if (path.endsWith("/conversations/conversation-focused-bed-07/messages") && method === "POST") {
      providerMutations.push(path);
      body = {
        id: "conversation-request-bed-07",
        conversation_id: "conversation-focused-bed-07",
        status: "COMPLETED",
        message_id: "question-bed-07",
      };
      status = 201;
    } else if (path.endsWith("/conversations/conversation-focused-bed-07") && method === "GET") {
      body = {
        id: "conversation-focused-bed-07",
        status: "READY",
        last_request_status: "COMPLETED",
        focus: {
          card_id: "constraint-bed-07",
          entity_kind: "grow_space",
          entity_id: "bed-07",
          title: "Grow space B3",
          source: "planning_snapshot",
        },
        messages: [],
      };
    } else {
      await route.continue();
      return;
    }
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await page.goto(`${base}/v13`, { waitUntil: "domcontentloaded" });
  await page.locator(".tc-shell").waitFor();
  check(
    "opens on the heavy rainfall scenario",
    (await page.locator(".tc-shell").getAttribute("data-selected-card")) === "scenario-heavy-rainfall" &&
      (await page.getByRole("heading", { name: /Heavy rainfall/i }).isVisible()),
  );
  check(
    "scenario provenance is explicit",
    await page.locator(".tc-provenance").getByText("SIMULATION · SCENARIO ONLY", { exact: true }).isVisible() &&
      (await page.getByText(/synthetic · simulation/i).count()) > 0,
  );
  check(
    "one readable active card and two assistive-hidden depth layers",
    (await page.locator(".tc-card").count()) === 1 &&
      (await page.locator('.tc-card-stack > [aria-hidden="true"]').count()) === 2 &&
      (await page.locator('.tc-card-stack > [aria-hidden="true"] button, .tc-card-stack > [aria-hidden="true"] a').count()) === 0,
  );
  check(
    "no card exposes more than three visible actions",
    (await page.locator(".tc-card-panel .tc-action").count()) <= 3,
  );
  const primaryPosition = await page.locator(".tc-action--primary").evaluate((element) => ({
    column: getComputedStyle(element.parentElement).gridColumnStart,
    height: element.getBoundingClientRect().height,
  }));
  check("center primary action has a 44px target", primaryPosition.column === "2" && primaryPosition.height >= 44, primaryPosition);
  check(
    "default action dock remains in normal flow",
    (await page.locator(".tc-action-dock").evaluate((element) => getComputedStyle(element).position)) === "static",
  );

  await page.getByRole("button", { name: "Next tactical card" }).click();
  check(
    "Next reaches the B3 constraint",
    (await page.locator(".tc-shell").getAttribute("data-selected-card")) === "constraint-bed-07" &&
      (await page.getByRole("heading", { name: /Keep grow space B3 free/i }).isVisible()),
  );
  await page.getByRole("button", { name: "Previous tactical card" }).click();
  check("Previous returns to rainfall", (await page.locator(".tc-shell").getAttribute("data-selected-card")) === "scenario-heavy-rainfall");
  await page.locator(".tc-card-stack").focus();
  await page.keyboard.press("ArrowRight");
  check("keyboard navigation selects B3", (await page.locator(".tc-shell").getAttribute("data-selected-card")) === "constraint-bed-07");

  const box = await page.locator(".tc-card-stack").boundingBox();
  if (!box) throw new Error("card stack has no box");
  await page.mouse.move(box.x + box.width / 2, box.y + 120);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 5, box.y + 215, { steps: 5 });
  await page.mouse.up();
  check("vertical scroll gesture does not change the card", (await page.locator(".tc-shell").getAttribute("data-selected-card")) === "constraint-bed-07");
  await page.mouse.move(box.x + box.width / 2, box.y + 120);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 105, box.y + 124, { steps: 5 });
  await page.mouse.up();
  check("horizontal swipe navigates cards", (await page.locator(".tc-shell").getAttribute("data-selected-card")) === "scenario-heavy-rainfall");
  await page.getByRole("button", { name: "Next tactical card" }).click();

  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator(".tc-shell").waitFor();
  check("edition-scoped selection survives reload", (await page.locator(".tc-shell").getAttribute("data-selected-card")) === "constraint-bed-07");
  const storage = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage).filter(([key]) => key.includes("v13") && key.includes("tactical-card-stack"))));
  check("stored selection is edition scoped", Object.keys(storage).length === 1 && Object.keys(storage)[0].startsWith("farmtact:v13:"), storage);

  await page.locator(".tc-board-column").evaluate((element) => element.scrollIntoView({ block: "start" }));
  await page.locator(".tc-selected-summary").waitFor({ timeout: 5000 });
  check(
    "selected-card summary appears after the stack scrolls away",
    (await page.locator(".tc-selected-summary").innerText()).includes("Keep grow space B3 free"),
  );
  await page.locator(".tc-selected-summary").click();

  await page.getByRole("button", { name: "More" }).click();
  const moreText = await page.locator(".tc-more-sheet").innerText();
  check(
    "secondary tools live under More",
    ["Data Explorer", "Council research", "Reviews", "Edition", "Audio", "Settings"].every((label) => moreText.toLowerCase().includes(label.toLowerCase())),
    moreText,
  );
  await page.getByRole("button", { name: "Close More" }).click();

  await page.getByRole("button", { name: "Reserve space" }).click();
  await page.locator(".tc-action-dock--progress").waitFor({ timeout: 5000 });
  check(
    "reserve submits a revision-bound bed-07 proposal",
    proposalBodies.length === 1 &&
      proposalBodies[0].base_revision === 7 &&
      JSON.stringify(proposalBodies[0]).includes("bed-07"),
    proposalBodies,
  );
  check("progress replaces card actions while calculation runs", (await page.locator(".tc-action-dock--progress").count()) === 1);
  await page.getByText("Active Constraints", { exact: true }).waitFor({ timeout: 15000 });
  await page.getByRole("button", { name: "Undo" }).waitFor({ timeout: 15000 });
  check(
    "completed recalculation converts the constraint card in place",
    (await page.locator(".tc-shell").getAttribute("data-selected-card")) === "constraint-bed-07" &&
      (await page.getByRole("button", { name: "View new plan" }).isVisible()) &&
      (await page.getByRole("button", { name: "Ask why" }).isVisible()),
  );
  const target = page.locator('[data-board-target-id="bed-07"]');
  check(
    "B3 is highlighted from the selected card target",
    (await target.count()) === 1 && (await target.getAttribute("data-highlighted")) === "true",
  );
  const changes = await page.locator(".tc-metric-changes").innerText();
  check(
    "recalculated values and signed deltas come from the mocked server response",
    changes.includes("471.4") && changes.includes("286.7") && changes.includes("−32.7") && !changes.includes("97%") && !changes.includes("92%"),
    changes,
  );

  const callsBeforeAsk = providerMutations.length;
  const askTrigger = page.getByRole("button", { name: "Ask why" });
  await askTrigger.click();
  check("opening Ask Why does not call a provider", providerMutations.length === callsBeforeAsk, [...providerMutations]);
  check(
    "Ask Why is a focused card-grounded dialog",
    await page.getByRole("dialog", { name: "Ask why" }).isVisible() &&
      (await page.locator(".tc-ask-card").innerText()).includes("bed-07") &&
      (await page.locator(".tc-ask-panel textarea").evaluate((element) => element === document.activeElement)),
  );
  await page.locator(".tc-ask-panel textarea").fill("Why did reserving B3 change the balanced plan?");
  await Promise.all([
    page.waitForResponse((response) => response.url().endsWith("/conversations") && response.request().method() === "POST"),
    page.waitForResponse((response) => response.url().endsWith("/conversations/conversation-focused-bed-07/messages") && response.request().method() === "POST"),
    page.getByRole("button", { name: "Ask with this card" }).click(),
  ]);
  check(
    "explicit Ask submit carries validated focus",
    conversationBodies.length === 1 &&
      conversationBodies[0].focus?.card_id === "constraint-bed-07" &&
      conversationBodies[0].focus?.entity_kind === "grow_space" &&
      conversationBodies[0].focus?.entity_id === "bed-07" &&
      providerMutations.length === callsBeforeAsk + 2,
    { conversationBodies, providerMutations },
  );
  await page.keyboard.press("Escape");
  check("closing the Ask dialog restores focus", await askTrigger.evaluate((element) => element === document.activeElement));

  await page.getByRole("button", { name: "Undo" }).click();
  await page.locator(".tc-action-dock--progress").waitFor({ timeout: 5000 });
  check(
    "Undo appends an inverse at the current revision",
    inverseBodies.length === 1 &&
      inverseBodies[0].proposal_id === proposal.id &&
      inverseBodies[0].proposal_revision === 8 &&
      inverseBodies[0].expected_session_revision === 8,
    inverseBodies,
  );
  await page.getByRole("button", { name: "Reserve space" }).waitFor({ timeout: 15000 });
  check(
    "inverse recalculation returns B3 to the stack without deleting history",
    (await page.getByRole("heading", { name: "Keep grow space B3 free" }).isVisible()) &&
      workflow.proposals.length === 2 &&
      workflow.proposals[0].id === proposal.id &&
      workflow.proposals[1].inverse_of_proposal_id === proposal.id,
    workflow.proposals,
  );

  const inverseCountBeforeStaleCheck = inverseBodies.length;
  inverseApplied = false;
  interveningChange = true;
  session.revision = 9;
  session.status = "COMPLETED";
  session.result_id = "result-after-3109";
  session.selected_strategy_id = "balanced-revised";
  session.result = { strategies: afterStrategies };
  session.job = { id: "job-reserve-bed-07", kind: "recalculation", status: "COMPLETED", stage: "completed" };
  session.tactical_context.planning_snapshot = {
    ...session.tactical_context.planning_snapshot,
    result_id: "result-after-3109",
    revision: 9,
    status: "COMPLETED",
  };
  session.tactical_context.grow_space.reservation_active = true;
  session.tactical_context.grow_space.reserve_eligible = false;
  session.tactical_context.grow_space.reserve_disabled_reason = "This grow space is already reserved.";
  delete proposal.inverse_proposal_id;
  workflow.proposals = [proposal];
  proposal.undo = { available: false, reason: "Undo is stale after an intervening revision." };
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator(".tc-shell").waitFor();
  const undo = page.getByRole("button", { name: "Undo" });
  check(
    "intervening revision disables stale Undo with a visible reason",
    await undo.isDisabled() && (await page.getByText(/stale|intervening revision/i).count()) > 0,
  );
  check("stale Undo sends no inverse mutation", inverseBodies.length === inverseCountBeforeStaleCheck, inverseBodies);

  const reducedMotion = await page.locator(".tc-card").evaluate((element) => ({
    transition: getComputedStyle(element).transitionDuration,
    animation: getComputedStyle(element).animationDuration,
  }));
  check(
    "reduced motion removes transforms over time",
    ["0s", "0.000001s", "1e-09s"].includes(reducedMotion.transition) &&
      ["0s", "0.000001s", "1e-09s"].includes(reducedMotion.animation),
    reducedMotion,
  );

  await mkdir(resolve(root, "apps/web/screenshots"), { recursive: true });
  for (const width of [360, 390, 430, 1280]) {
    await page.setViewportSize({ width, height: width === 1280 ? 900 : 844 });
    const measurements = await page.evaluate(() => {
      const shell = document.querySelector(".tc-shell");
      const stack = document.querySelector(".tc-card-stack");
      const panel = document.querySelector(".tc-card-panel");
      const workspace = document.querySelector(".tc-workspace");
      return {
        bodyWidth: document.body.scrollWidth,
        viewportWidth: innerWidth,
        stackWidth: stack?.getBoundingClientRect().width || 0,
        panelRatio: panel && workspace ? panel.getBoundingClientRect().width / workspace.getBoundingClientRect().width : 0,
        navVisible: document.querySelector(".tc-mobile-nav") ? getComputedStyle(document.querySelector(".tc-mobile-nav")).display !== "none" : false,
        shellWidth: shell?.getBoundingClientRect().width || 0,
      };
    });
    check(`${width}px has no horizontal overflow`, measurements.bodyWidth <= measurements.viewportWidth + 1, measurements);
    check(`${width}px keeps the card at mobile proportions`, measurements.stackWidth <= 366, measurements);
    if (width === 1280) {
      check("desktop card panel uses 25–35% of workspace", measurements.panelRatio >= 0.25 && measurements.panelRatio <= 0.35, measurements);
      check("desktop hides mobile bottom navigation", !measurements.navVisible, measurements);
    } else {
      check(`${width}px exposes four-item bottom navigation`, measurements.navVisible && (await page.locator(".tc-mobile-nav button").count()) === 4, measurements);
    }
    const screenshot = resolve(root, `apps/web/screenshots/v13-tactical-${width}.png`);
    await page.screenshot({ path: screenshot, fullPage: true, animations: "disabled" });
    result.screenshots.push(screenshot.slice(root.length + 1));
  }

  if (expectDevelopmentDock) {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${base}/v13?v13Dock=inline`, { waitUntil: "domcontentloaded" });
    await page.locator(".tc-shell--dock-inline").waitFor();
    check(
      "development inline dock flag remains in normal flow",
      (await page.locator(".tc-action-dock").evaluate((element) => getComputedStyle(element).position)) === "static",
    );
    await page.goto(`${base}/v13?v13Dock=sticky`, { waitUntil: "domcontentloaded" });
    await page.locator(".tc-shell--dock-sticky").waitFor();
    const stickyDock = await page.locator(".tc-action-dock").evaluate((element) => {
      const dock = element.getBoundingClientRect();
      const panel = element.closest(".tc-card-panel");
      return {
        position: getComputedStyle(element).position,
        bottom: dock.bottom,
        viewportHeight: innerHeight,
        panelBottomReserve: panel ? Number.parseFloat(getComputedStyle(panel).paddingBottom) : 0,
        dockHeight: dock.height,
      };
    });
    check("development sticky dock flag uses sticky positioning", stickyDock.position === "sticky", stickyDock);
    check(
      "sticky dock reserves space and stays inside the safe viewport",
      stickyDock.panelBottomReserve >= stickyDock.dockHeight && stickyDock.bottom <= stickyDock.viewportHeight,
      stickyDock,
    );
  }
  check("no browser exceptions", pageErrors.length === 0, pageErrors);
  result.status = "PASS";
  await context.close();
} catch (error) {
  result.status = "FAIL";
  result.failures.push(error.stack || String(error));
  if (activePage) result.failures.push((await activePage.locator("body").innerText()).slice(0, 5000));
} finally {
  if (browser) await browser.close();
  console.log(JSON.stringify(result, null, 2));
  if (result.status !== "PASS") process.exitCode = 1;
}
