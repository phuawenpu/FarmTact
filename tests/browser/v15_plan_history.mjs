import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const baseURL = process.env.BASE_URL || "http://127.0.0.1:4194";
const reportPath = resolve(root, "reports/v15/plan-history-browser.json");
const report = { started_at: new Date().toISOString(), base_url: baseURL, checks: [], failures: [], prerequisites: [], notes: [] };
function check(name, pass, detail = "") { report.checks.push({ name, pass: Boolean(pass), detail }); if (!pass) throw new Error(`${name}: ${detail}`); }
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "no-preference" });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  const response = await page.goto(baseURL, { waitUntil: "networkidle" });
  check("application responds", response?.status() === 200, String(response?.status()));

  const openTools = async () => {
    const explicit = page.getByRole("button", { name: /^(Farm tools|Tools)$/ }).filter({ visible: true }).first();
    if (await explicit.isVisible().catch(() => false)) await explicit.click();
    else await page.getByRole("button", { name: "More", exact: true }).filter({ visible: true }).first().click();
  };
  const openTool = async title => {
    if (!(await page.locator(".ic-path").isVisible().catch(() => false))) await openTools();
    const order = ["Plan", "Records & work", "Knowledge & evidence", "Experiments", "History & preferences"];
    for (let i = 0; i < 7 && !(await page.getByText(title, { exact: true }).isVisible().catch(() => false)); i++) {
      const path = await page.locator(".ic-path").textContent();
      const current = order.findIndex(item => path?.endsWith(item)), target = order.indexOf(title);
      const direction = current > target ? "Previous" : "Next";
      const move = page.getByRole("button", { name: new RegExp(direction) }).filter({ visible: true }).first();
      if (await move.isDisabled()) throw new Error(`Farm tool not found: ${title}`);
      await move.click();
    }
    await page.getByText(title, { exact: true }).waitFor();
    await page.getByRole("button", { name: "Open tool", exact: true }).click();
  };
  const api = (path, init) => page.evaluate(async ({ path, init }) => {
    const response = await fetch(`/api/v1${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.method === "POST" ? { "Idempotency-Key": crypto.randomUUID() } : {}), ...(init?.headers || {}) } });
    const text = await response.text(); if (!response.ok) throw new Error(`${path}: ${response.status} ${text}`); return text ? JSON.parse(text) : null;
  }, { path, init });

  await openTool("Plan");
  await page.getByRole("button", { name: "Open", exact: true }).click();
  check("objective card shows all confirmed demand", await page.getByText("All confirmed orders and modeled demand stay in the calculation.").isVisible());
  const calculate = page.getByRole("button", { name: "Calculate locally", exact: true });
  if (await calculate.isVisible().catch(() => false)) await calculate.click();
  await page.getByRole("button", { name: "Refresh", exact: true }).waitFor({ timeout: 120_000 });
  const sessions = await api("/planning-sessions");
  const sessionSummary = sessions.sessions.find(item => item.workflow === true);
  let session;
  for (let i = 0; i < 120; i++) {
    session = await api(`/planning-sessions/${encodeURIComponent(sessionSummary.id)}`);
    if (session.result?.strategies?.length) break;
    await page.waitForTimeout(500);
  }
  check("objective calculation stores three strategies", session?.result?.strategies?.length === 3, String(session?.result?.strategies?.length));

  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  check("strategy schedule card exposes allocations", await page.getByText("Preview—not saved.").isVisible());
  const feasible = session.result.strategies.find(item => String(item.status).toUpperCase() === "FEASIBLE") || session.result.strategies[0];
  await page.getByLabel("Compare strategy").selectOption(feasible.id);
  check("strategy selection exposes projected schedule", (await page.locator(".record-facts").count()) >= 2);
  await page.getByRole("button", { name: "Prepare proposal", exact: true }).click();

  const firstOrder = session.farm.orders[0], start = session.farm.planning_date || session.farm.cutoff.slice(0, 10);
  const assumptions = {
    tentative_orders: [],
    future_demand: [{ crop_id: firstOrder.crop_id, start_date: start, end_date: firstOrder.due_date, percent: 100 }],
    seasonal: [],
    order_changes: [{ operation: "amend", order_id: firstOrder.id, crop_id: firstOrder.crop_id, due_date: firstOrder.due_date, quantity_kg: firstOrder.quantity_kg, price_sgd_per_kg: firstOrder.price_sgd_per_kg }],
    reservations: [],
    capacity: { nursery_sites: session.farm.resources.nursery_sites, labour_hours_per_week: session.farm.resources.labour_hours_per_week, cash_sgd: session.farm.resources.cash_sgd },
  };
  await page.getByText("Import saved settings", {exact:true}).click();await page.getByLabel("Planning assumptions JSON").fill(JSON.stringify(assumptions, null, 2));
  await page.getByRole("button", { name: "Review", exact: true }).click();
  check("assumptions require a distinct review card", await page.getByRole("heading", { name: "Review planning changes" }).isVisible());
  await page.getByRole("button", { name: "Create proposal", exact: true }).click();
  await page.getByRole("button", { name: "Apply & recalculate", exact: true }).waitFor();
  check("draft proposal is separate from apply", await page.getByText("draft", { exact: true }).isVisible().catch(() => false));
  await page.getByRole("button", { name: "Apply & recalculate", exact: true }).click();
  const deadline = Date.now() + 120_000;
  let applied;
  while (Date.now() < deadline) {
    const state = await api("/farm-workflow");
    applied = [...state.proposals].reverse().find(item => item.session_id === session.id && item.selected_strategy_id === feasible.id);
    if (applied?.status === "applied" && applied.recalculated_strategy_id) break;
    await page.waitForTimeout(500);
  }
  check("proposal recalculation completes with result strategy", applied?.status === "applied" && Boolean(applied.recalculated_strategy_id), JSON.stringify({ status: applied?.status, strategy: applied?.recalculated_strategy_id }));
  await page.getByRole("button", { name: "Refresh result", exact: true }).click();
  check("applied result remains reviewable", await page.getByText("applied", { exact: true }).isVisible().catch(() => false));

  const approval = await api(`/farm-workflow/proposals/${encodeURIComponent(applied.id)}/approve-actions`, { method: "POST", body: JSON.stringify({ proposal_id: applied.id, proposal_revision: applied.proposal_revision, selected_strategy_id: applied.recalculated_strategy_id, idempotency_key: crypto.randomUUID() }) });
  report.prerequisites.push(`Approved proposal ${applied.id} through the real API so History could test an eligible reviewed time advance.`);
  check("approved prerequisite creates simulation tasks", approval.tasks?.length > 0, String(approval.tasks?.length));

  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await openTool("History & preferences");
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await page.getByRole("button", { name: "Read-only replay", exact: true }).waitFor();
  for (let i = 0; i < 30 && !(await page.getByText(session.id, { exact: true }).isVisible().catch(() => false)); i++) {
    const next = page.getByRole("button", { name: "Next", exact: true }); if (await next.isDisabled()) break; await next.click();
  }
  check("saved plan identity appears in history", await page.getByText(session.id, { exact: true }).isVisible(), session.id);
  await page.getByRole("button", { name: "Read-only replay", exact: true }).click();
  await page.getByText(/Reading this card makes no provider calls/).waitFor();
  check("saved plan replay is explicitly read-only", await page.getByText(/Reading this card makes no provider calls/).isVisible());
  await page.getByRole("button", { name: "Saved versions", exact: true }).click();
  const versionOptions = page.getByLabel("Saved result").locator("option");
  check("frozen versions are selectable", await versionOptions.count() > 0, String(await versionOptions.count()));
  await page.getByRole("button", { name: "Replay saved result", exact: true }).click();
  await page.getByText("Read-only saved replay", { exact: true }).waitFor();
  check("saved version replay returns recorded result", await page.getByText("Read-only saved replay", { exact: true }).isVisible());
  await page.getByRole("button", { name: "Saved versions", exact: true }).click();
  await page.getByRole("button", { name: "Review time advance", exact: true }).click();
  await page.getByLabel("Days to advance").selectOption("7");
  check("seven-day advance has explicit review", await page.getByText(/^Explicitly advance 7 simulated days/).isVisible());
  await page.getByRole("button", { name: "Advance seven days", exact: true }).click();
  await page.getByText("Read-only saved replay", { exact: true }).waitFor({ timeout: 120_000 });
  check("reviewed seven-day advance returns recorded state", true);

  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  const motion = page.getByLabel("Reduced motion"); await motion.check();
  check("reduced motion preference persists", await page.evaluate(() => document.documentElement.dataset.reducedMotion) === "true");
  check("audio controls are reachable", await page.getByText(/audio/i).count() > 0);
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  check("help explains swipe and arrow controls", await page.getByText(/swipe horizontally or use Previous\/Next/).isVisible());

  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await openTool("Plan");
  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  const beforeAttempts = (await api("/planning-sessions")).sessions.map(item => item.id);
  await page.getByRole("button", { name: "Create new attempt", exact: true }).click();
  await page.getByRole("heading", { name: "Objectives and all demand", exact: true }).waitFor();
  const afterAttempts = (await api("/planning-sessions")).sessions;
  const newAttempt = afterAttempts.find(item => !beforeAttempts.includes(item.id));
  check("new planning attempt creates a distinct session", Boolean(newAttempt), newAttempt?.id || "missing");
  check("new planning attempt preserves prior session", afterAttempts.some(item => item.id === session.id), session.id);

  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await openTool("Records & work");
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await page.getByRole("button", { name: "Review farm JSON", exact: true }).click();
  const importedFarm = JSON.parse(await readFile(resolve(root, "data/fixtures/synthetic_farm.json"), "utf8"));
  importedFarm.name = `V15 reviewed import ${Date.now()}`;
  importedFarm.version = Number(importedFarm.version || 0) + 1;
  await page.getByLabel("Farm JSON").fill(JSON.stringify({ farm: importedFarm }, null, 2));
  await page.getByRole("button", { name: "Review parsed farm", exact: true }).click();
  await page.getByText("Review farm import", { exact: true }).waitFor();
  check("full JSON import has explicit parsed review", await page.getByText("Review farm import", { exact: true }).isVisible());
  const sessionsBeforeImport = (await api("/planning-sessions")).sessions.map(item => item.id);
  await page.getByRole("button", { name: "Confirm atomic import", exact: true }).click();
  let sessionsAfterImport = [];
  for (let i = 0; i < 40; i++) { sessionsAfterImport = (await api("/planning-sessions")).sessions; if (sessionsAfterImport.some(item => !sessionsBeforeImport.includes(item.id))) break; await page.waitForTimeout(250); }
  const importedSession = sessionsAfterImport.find(item => !sessionsBeforeImport.includes(item.id));
  check("confirmed import creates a fresh remembered workflow session", importedSession?.farm?.name === importedFarm.name, importedSession?.farm?.name || "missing");
  check("confirmed import retains prior sessions", sessionsAfterImport.some(item => item.id === session.id) && sessionsAfterImport.some(item => item.id === newAttempt.id));
  check("confirmed import returns to farm setup card", await page.getByRole("heading", { name: "Farm setup", exact: true }).isVisible().catch(() => false), await page.getByRole("alert").allTextContents().then(rows => rows.join(" | ")));
  check("no uncaught page errors", pageErrors.length === 0, pageErrors.join(" | "));
} catch (error) {
  report.failures.push({ name: "browser run", detail: error instanceof Error ? error.stack : String(error) });
} finally {
  report.finished_at = new Date().toISOString(); report.status = report.failures.length ? "FAILED" : "PASSED";
  await mkdir(dirname(reportPath), { recursive: true }); await writeFile(reportPath, JSON.stringify(report, null, 2)); await browser?.close();
}
if (report.failures.length) { console.error(JSON.stringify(report.failures, null, 2)); process.exitCode = 1; }
else console.log(`V15 plan/history browser checks passed (${report.checks.length}).`);
