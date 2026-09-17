import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const baseURL = process.env.BASE_URL || "http://127.0.0.1:4191";
const reportPath = resolve(root, "reports/v15/records-browser.json");
const report = { started_at: new Date().toISOString(), base_url: baseURL, checks: [], failures: [], notes: [] };
function check(name, pass, detail = "") { report.checks.push({ name, pass: Boolean(pass), detail }); if (!pass) report.failures.push({ name, detail }); }
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const response = await page.goto(baseURL, { waitUntil: "networkidle" });
  check("application responds", response?.status() === 200, String(response?.status()));

  const openTools = async () => {
    const tools = page.getByRole("button", { name: /^(Farm tools|Tools)$/ }).filter({ visible: true }).first();
    if (await tools.isVisible().catch(() => false)) await tools.click();
    else await page.getByRole("button", { name: "More", exact: true }).filter({ visible: true }).first().click();
  };
  await openTools();
  for (let attempt = 0; attempt < 7 && !(await page.getByText("Records & work", { exact: true }).isVisible().catch(() => false)); attempt++) {
    await page.getByRole("button", { name: /Next/ }).filter({ visible: true }).first().click();
  }
  await page.getByText("Records & work", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Open tool", exact: true }).click();
  await page.getByRole("heading", { name: "Records & work", exact: true }).waitFor();
  check("integrated records tool opens", true);

  await page.getByRole("button", { name: /Open farm records/i }).click();
  const add = page.getByRole("button", { name: "Add candidate", exact: true });
  if (await add.count()) { await add.click(); await page.getByRole("button", { name: "Manual instead", exact: true }).click(); }
  else await page.getByRole("button", { name: "Manual record", exact: true }).click();
  const description = page.getByLabel("Description (optional)");
  const draft = `v15 persistent draft ${Date.now()}`;
  await description.fill(draft);
  await page.reload({ waitUntil: "networkidle" });
  await openTools();
  for (let attempt = 0; attempt < 7 && !(await page.getByText("Records & work", { exact: true }).isVisible().catch(() => false)); attempt++) await page.getByRole("button", { name: /Next/ }).filter({ visible: true }).first().click();
  await page.getByRole("button", { name: "Open tool", exact: true }).click();
  await page.getByRole("button", { name: /Open farm records/i }).click();
  if (await add.count()) { await add.click(); await page.getByRole("button", { name: "Manual instead", exact: true }).click(); }
  else await page.getByRole("button", { name: "Manual record", exact: true }).click();
  check("manual draft survives reload", await page.getByLabel("Description (optional)").inputValue() === draft);
  const sourceName = `V15 browser candidate ${Date.now()}`;
  await page.getByLabel("Source name").fill(sourceName);
  await page.getByLabel("Amount (SGD)").fill("12.34");
  const reference = `v15-browser-${Date.now()}`;
  await page.getByLabel("Record reference").fill(reference);
  const interruptionKeys = [];
  let interrupted = false;
  await page.route("**/api/v1/farm-workflow/imports", async route => {
    if (route.request().method() !== "POST") return route.continue();
    interruptionKeys.push(route.request().headers()["idempotency-key"]);
    if (!interrupted) {
      interrupted = true;
      await route.fetch();
      return route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Simulated response interruption after commit" }) });
    }
    return route.continue();
  });
  await page.getByRole("button", { name: "Create review candidate", exact: true }).click();
  await page.getByRole("alert").getByText(/Simulated response interruption/).waitFor();
  check("uncertain 503 retains manual draft", await page.getByLabel("Description (optional)").inputValue() === draft);
  await page.reload({ waitUntil: "networkidle" });
  await openTools();
  for (let attempt = 0; attempt < 7 && !(await page.getByText("Records & work", { exact: true }).isVisible().catch(() => false)); attempt++) await page.getByRole("button", { name: /Next/ }).filter({ visible: true }).first().click();
  await page.getByRole("button", { name: "Open tool", exact: true }).click();
  await page.getByRole("button", { name: /Open farm records/i }).click();
  if (await add.count()) { await add.click(); await page.getByRole("button", { name: "Manual instead", exact: true }).click(); }
  else await page.getByRole("button", { name: "Manual record", exact: true }).click();
  check("uncertain mutation draft survives reload", await page.getByLabel("Record reference").inputValue() === reference);
  await page.getByRole("button", { name: "Create review candidate", exact: true }).click();
  check("uncertain retry reuses idempotency key", interruptionKeys.length === 2 && interruptionKeys[0] === interruptionKeys[1], interruptionKeys.map(value => value?.slice(0, 8)).join(" / "));
  const candidateCopies = await page.evaluate(async name => (await (await fetch("/api/v1/farm-workflow")).json()).inbox.filter(item => item.source_name === name).length, sourceName);
  check("uncertain retry creates one candidate", candidateCopies === 1, String(candidateCopies));
  report.notes.push("Transport fault check deliberately returned one synthetic 503 after forwarding the real mutation to the isolated API.");
  await page.unroute("**/api/v1/farm-workflow/imports");
  const review = page.getByRole("button", { name: "Review candidate", exact: true });
  if (!(await page.getByRole("heading", { name: sourceName, exact: true }).isVisible().catch(() => false))) {
    const next = page.getByRole("button", { name: /Next/ }).filter({ visible: true });
    for (let attempt = 0; attempt < 20 && !(await page.getByRole("heading", { name: sourceName, exact: true }).isVisible().catch(() => false)); attempt++) {
      if (await next.isDisabled()) break;
      await next.click();
    }
  }
  check("new candidate appears as its own stable card", await page.getByRole("heading", { name: sourceName, exact: true }).isVisible(), sourceName);
  await review.click();
  await page.getByRole("button", { name: "Confirm reviewed fields", exact: true }).click();
  await page.getByText("confirmed", { exact: true }).waitFor();
  check("manual candidate requires and completes explicit confirmation", true, reference);

  const throttledName = `V15 throttled candidate ${Date.now()}`;
  await page.getByRole("button", { name: "Add candidate", exact: true }).click();
  await page.getByRole("button", { name: "Manual instead", exact: true }).click();
  await page.getByLabel("Source name").fill(throttledName);
  await page.getByLabel("Record reference").fill(`v15-throttle-${Date.now()}`);
  await page.getByLabel("Amount (SGD)").fill("3.21");
  let throttleRequests = 0;
  await page.route("**/api/v1/farm-workflow/imports", async route => {
    if (route.request().method() !== "POST") return route.continue();
    throttleRequests += 1;
    if (throttleRequests === 1) return route.fulfill({ status: 429, headers: { "Retry-After": "0.2" }, contentType: "application/json", body: JSON.stringify({ detail: "Simulated admission throttle" }) });
    return route.continue();
  });
  await page.getByRole("button", { name: "Create review candidate", exact: true }).click();
  await page.getByRole("alert").getByText(/Simulated admission throttle/).waitFor();
  await page.getByRole("button", { name: "Create review candidate", exact: true }).click();
  check("Retry-After prevents immediate network retry", throttleRequests === 1, String(throttleRequests));
  await page.waitForTimeout(250);
  await page.getByRole("button", { name: "Create review candidate", exact: true }).click();
  check("429 retry waits then reaches real API", throttleRequests === 2, String(throttleRequests));
  report.notes.push("Admission test synthesized one 429 before allowing the unchanged draft to reach the real isolated API.");
  await page.unroute("**/api/v1/farm-workflow/imports");

  await page.getByRole("button", { name: "Back", exact: true }).last().click();
  const seeded = await page.evaluate(async () => {
    const call = async (path, init = {}) => { const response = await fetch(`/api/v1${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init.method === "POST" ? { "Idempotency-Key": crypto.randomUUID() } : {}), ...(init.headers || {}) } }); if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`); return response.json(); };
    const state = await call("/farm-workflow");
    if (state.tasks.some(task => task.event_revision > 0)) return { existing: true };
    const sessions = await call("/planning-sessions");
    let session = sessions.sessions.find(item => item.workflow === true) || sessions.sessions[0];
    if (!session) session = await call("/planning-sessions", { method: "POST", body: JSON.stringify({ name: "V15 records browser", workflow: true }) });
    const wait = async () => { for (let i = 0; i < 80; i++) { session = await call(`/planning-sessions/${encodeURIComponent(session.id)}`); if (!["QUEUED", "RUNNING"].includes(session.job?.status || "")) return; await new Promise(resolve => setTimeout(resolve, 250)); } throw new Error("planning job timeout"); };
    if (!session.result?.strategies?.length) { session = await call(`/planning-sessions/${encodeURIComponent(session.id)}/calculate`, { method: "POST", body: JSON.stringify({ revision: session.revision }) }); await wait(); }
    const strategy = session.result?.strategies?.find(item => String(item.status).toUpperCase() === "FEASIBLE") || session.result?.strategies?.[0]; if (!strategy) throw new Error("no calculated strategy");
    const start = session.farm.planning_date || session.farm.cutoff.slice(0, 10), crop = strategy.allocations?.[0]?.crop_id || session.farm.orders[0]?.crop_id;
    const assumptions = { tentative_orders: [], future_demand: [{ crop_id: crop, start_date: start, end_date: start, percent: 100 }], seasonal: [{ crop_id: crop, system: "sheltered_hydroponic", start_date: start, end_date: start, yield_percent: 100, delay_days: 0, reason: "V15 browser verification", provenance: "synthetic_assumption" }], order_changes: [], reservations: [], capacity: { nursery_sites: session.farm.resources.nursery_sites, labour_hours_per_week: session.farm.resources.labour_hours_per_week, cash_sgd: session.farm.resources.cash_sgd } };
    let proposal = await call("/farm-workflow/proposals", { method: "POST", body: JSON.stringify({ session_id: session.id, base_revision: session.revision, changes: [{ kind: "planning_assumptions", assumptions }], selected_strategy_id: strategy.id, source_candidate_ids: [], idempotency_key: crypto.randomUUID() }) });
    await call(`/farm-workflow/proposals/${encodeURIComponent(proposal.id)}/apply`, { method: "POST", body: JSON.stringify({ proposal_id: proposal.id, expected_base_revision: proposal.base_revision, idempotency_key: crypto.randomUUID() }) });
    await wait();
    const updated = await call("/farm-workflow"); proposal = updated.proposals.find(item => item.id === proposal.id) || proposal;
    const approved = await call(`/farm-workflow/proposals/${encodeURIComponent(proposal.id)}/approve-actions`, { method: "POST", body: JSON.stringify({ proposal_id: proposal.id, proposal_revision: proposal.proposal_revision, selected_strategy_id: proposal.recalculated_strategy_id || proposal.selected_strategy_id, idempotency_key: crypto.randomUUID() }) });
    const task = approved.tasks[0]; if (!task) throw new Error("approval created no task");
    await call(`/farm-workflow/tasks/${encodeURIComponent(task.id)}/result`, { method: "POST", body: JSON.stringify({ expected_status: task.status, result_status: "completed", actual_quantity: task.unit ? Number(task.planned_quantity || 0) : null, rejected_quantity: task.action === "delivery" ? 0 : null, unit: task.unit || undefined, photo_reference: null, checklist_completed: task.checklist, note: "V15 browser prerequisite result" }) });
    return { existing: false, task: task.id };
  });
  report.notes.push(seeded.existing ? "Used an existing task result for correction." : `Created real task prerequisite ${seeded.task}.`);
  await page.reload({ waitUntil: "networkidle" });
  await openTools();
  for (let attempt = 0; attempt < 7 && !(await page.getByText("Records & work", { exact: true }).isVisible().catch(() => false)); attempt++) await page.getByRole("button", { name: /Next/ }).filter({ visible: true }).first().click();
  await page.getByRole("button", { name: "Open tool", exact: true }).click();
  await page.getByRole("button", { name: /Open tasks & results/i }).click();
  const correction = page.getByRole("button", { name: "Correct record", exact: true });
  for (let attempt = 0; attempt < 50 && !(await correction.isVisible().catch(() => false)); attempt++) {
    const nextTask = page.getByRole("button", { name: /Next/ }).filter({ visible: true }).first();
    if (await nextTask.isDisabled()) break;
    await nextTask.click();
  }
  if (await correction.isVisible().catch(() => false)) {
    await correction.click();
    await page.getByLabel("Reason").fill(`Browser correction ${Date.now()}`);
    await page.getByRole("button", { name: "Review & save correction", exact: true }).click();
    check("task correction reaches real API", await page.getByText(/event revision/i).isVisible().catch(() => false));
  } else check("real task result exposes correction workflow", false, "No task with an event revision after real API prerequisite setup.");
  check("no uncaught page errors", errors.length === 0, errors.join(" | "));
} catch (error) {
  report.failures.push({ name: "browser run", detail: error instanceof Error ? error.stack : String(error) });
} finally {
  report.finished_at = new Date().toISOString();
  report.status = report.failures.length ? "FAILED" : "PASSED";
  await mkdir(dirname(reportPath), { recursive: true });
  await writeFile(reportPath, JSON.stringify(report, null, 2));
  await browser?.close();
}
if (report.failures.length) { console.error(JSON.stringify(report.failures, null, 2)); process.exitCode = 1; }
else console.log(`V15 records browser checks passed (${report.checks.length}).`);
