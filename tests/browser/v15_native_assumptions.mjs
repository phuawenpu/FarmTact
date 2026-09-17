import { access, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const baseURL = process.env.BASE_URL || "http://127.0.0.1:4196";
const reportPath = resolve(root, "reports/v15/native-assumptions-browser.json");
const candidates = ["/tmp/farmtact-v15-cards-storage.json", "/tmp/farmtact-v15-records-extended-storage.json"];
const report = { started_at: new Date().toISOString(), base_url: baseURL, checks: [], failures: [], notes: ["Proposal POST was intercepted after the explicit Create proposal action; no server mutation was performed."] };
function check(name, pass, detail = "") { report.checks.push({ name, pass: Boolean(pass), detail }); if (!pass) throw new Error(`${name}: ${detail}`); }
async function storageState() { for (const path of candidates) try { await access(path); return path; } catch {} throw new Error("No existing private V15 browser storage state found"); }

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 430, height: 900 }, storageState: await storageState() });
  const page = await context.newPage();
  const errors = []; page.on("pageerror", error => errors.push(error.message));
  let postCount = 0, proposalBody;
  await page.route("**/api/v1/**", async route => {
    const request = route.request();
    if (request.method() !== "POST") return route.continue();
    postCount++;
    if (!request.url().endsWith("/farm-workflow/proposals")) return route.abort("blockedbyclient");
    proposalBody = request.postDataJSON();
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      id: "intercepted-native-fields-proposal", session_id: proposalBody.session_id,
      base_revision: proposalBody.base_revision, proposal_revision: 1, status: "draft",
      selected_strategy_id: proposalBody.selected_strategy_id, calculated_metrics: {},
    }) });
  });
  const response = await page.goto(baseURL, { waitUntil: "networkidle" });
  check("application responds", response?.status() === 200, String(response?.status()));
  await page.evaluate(() => {
    const empty = JSON.stringify({ tentative_orders: [], future_demand: [], seasonal: [], order_changes: [], reservations: [] }, null, 2);
    for (const key of Object.keys(localStorage)) if (key.includes("planning-assumptions-draft")) localStorage.setItem(key, empty);
  });
  await page.reload({ waitUntil: "networkidle" });

  const openTools = async () => {
    const button = page.getByRole("button", { name: /^(Farm tools|Tools)$/ }).filter({ visible: true }).first();
    if (await button.isVisible().catch(() => false)) await button.click();
    else await page.getByRole("button", { name: "More", exact: true }).filter({ visible: true }).first().click();
  };
  const openPlanAssumptions = async () => {
    if (await page.getByRole("heading", { name: "Resource & demand assumptions" }).isVisible().catch(() => false)) return;
    if (await page.locator(".integrated-tool").isVisible().catch(() => false)) {
      for (let i = 0; i < 7 && !(await page.getByText("Resources & assumptions", { exact: true }).isVisible().catch(() => false)); i++)
        await page.getByRole("button", { name: "Next", exact: true }).click();
      await page.getByRole("button", { name: "Open", exact: true }).click();
      await page.getByRole("heading", { name: "Resource & demand assumptions" }).waitFor();
      return;
    }
    await openTools();
    for (let i = 0; i < 7 && !(await page.getByText("Plan", { exact: true }).isVisible().catch(() => false)); i++) await page.getByRole("button", { name: /^(Previous|Next)$/ }).filter({ visible: true }).last().click();
    await page.getByText("Plan", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Open tool", exact: true }).click();
    for (let i = 0; i < 2; i++) await page.getByRole("button", { name: "Next", exact: true }).click();
    await page.getByRole("button", { name: "Open", exact: true }).click();
    await page.getByRole("heading", { name: "Resource & demand assumptions" }).waitFor();
  };
  await openPlanAssumptions();

  const snapshot = await page.evaluate(async () => {
    const remembered = Object.entries(localStorage).find(([key]) => key.includes("planning-session"))?.[1];
    const list = await (await fetch("/api/v1/planning-sessions")).json();
    const summary = list.sessions.find(item => item.id === remembered && item.workflow) || list.sessions.find(item => item.workflow);
    return await (await fetch(`/api/v1/planning-sessions/${encodeURIComponent(summary.id)}`)).json();
  });
  const crop = snapshot.farm.orders[0]?.crop_id || Object.keys(snapshot.farm.recipe_calendar || {})[0];
  const order = snapshot.farm.orders[0];
  const bed = snapshot.tactical_context?.grow_space?.id || snapshot.farm.beds[0].id;
  const start = snapshot.farm.planning_date || snapshot.farm.cutoff.slice(0, 10);
  const end = order?.due_date || snapshot.tactical_context?.grow_space?.reservation_window?.end_date || start;
  check("test uses actual farm crop, order, and bed", Boolean(crop && order?.id && bed), JSON.stringify({ crop, order: order?.id, bed }));

  await page.getByLabel("Nursery sites").fill("2345");
  await page.getByLabel("Labour hours per week").fill("41.5");
  await page.getByLabel("Cash available (SGD)").fill("4321.25");

  const addThenRemove = async (title, button) => {
    const fieldset = page.getByRole("group", { name: title, exact: true });
    await page.getByRole("button", { name: button, exact: true }).click();
    check(`${title} row can be added`, await fieldset.getByRole("button", { name: /^Remove/ }).count() > 0);
    await fieldset.getByRole("button", { name: /^Remove/ }).last().click();
    check(`${title} row can be removed`, await fieldset.getByRole("button", { name: /^Remove/ }).count() === 0);
    await page.getByRole("button", { name: button, exact: true }).click();
    return fieldset;
  };

  let group = await addThenRemove("Tentative orders", "Add tentative orders");
  await group.getByLabel("Order reference").fill("native-tentative-1");
  await group.getByLabel("Crop").selectOption(crop); await group.getByLabel("Due date").fill(end);
  await group.getByLabel("Quantity (kg)").fill("12.5"); await group.getByLabel("Price (SGD/kg)").fill("7.75");

  group = await addThenRemove("Future demand", "Add future demand");
  await group.getByLabel("Crop").selectOption(crop); await group.getByLabel("From").fill(start); await group.getByLabel("Through").fill(end); await group.getByLabel("Expected demand (%)").fill("123");

  group = await addThenRemove("Seasonal yield and delay", "Add seasonal yield and delay");
  await group.getByLabel("Crop").selectOption(crop); await group.getByLabel("From").fill(start); await group.getByLabel("Through").fill(end);
  await group.getByLabel("Yield retained (%)").fill("88"); await group.getByLabel("Harvest delay (days)").fill("4"); await group.getByLabel("Reason").fill("Native seasonal review");

  group = await addThenRemove("Confirmed order changes", "Add confirmed order changes");
  await group.getByLabel("Change").selectOption("amend"); await group.getByLabel("Order reference").selectOption(order.id); await group.getByLabel("Quantity (kg)").fill("19.25");

  group = await addThenRemove("Bed reservations", "Add reservation");
  await group.getByLabel("Bed").selectOption(bed); await group.getByLabel("Reserved from").fill(start); await group.getByLabel("Reserved through").fill(end);
  check("all local edits make no POST request", postCount === 0, String(postCount));

  await page.reload({ waitUntil: "networkidle" });
  await openPlanAssumptions();
  check("capacity draft persists across reload", await page.getByLabel("Cash available (SGD)").inputValue() === "4321.25");
  check("all five row groups persist across reload", await page.getByRole("button", { name: /^Remove/ }).count() === 5, String(await page.getByRole("button", { name: /^Remove/ }).count()));
  check("seasonal draft value persists", await page.getByLabel("Reason", { exact: true }).inputValue() === "Native seasonal review");
  check("reload still causes no write", postCount === 0, String(postCount));

  await page.getByRole("button", { name: "Review", exact: true }).click();
  await page.getByRole("heading", { name: "Review planning changes" }).waitFor();
  const review = await page.locator(".integrated-tool__card").innerText();
  for (const expected of ["2345", "41.5", "4321.25", "native-tentative-1", "12.5", "123", "88", "4", "Native seasonal review", order.id, "19.25", bed])
    check(`review shows ${expected}`, review.includes(String(expected)));
  check("review navigation causes no write", postCount === 0, String(postCount));

  await page.getByRole("button", { name: "Create proposal", exact: true }).click();
  await page.getByRole("heading", { name: "Proposal and recalculation" }).waitFor();
  check("only explicit Create proposal attempts a POST", postCount === 1, String(postCount));
  const sent = proposalBody?.changes?.[0]?.assumptions;
  check("submitted capacity matches native fields", sent?.capacity?.nursery_sites === 2345 && sent?.capacity?.labour_hours_per_week === 41.5 && sent?.capacity?.cash_sgd === 4321.25, JSON.stringify(sent?.capacity));
  check("submitted arrays retain one reviewed row each", ["tentative_orders", "future_demand", "seasonal", "order_changes", "reservations"].every(key => sent?.[key]?.length === 1), JSON.stringify(Object.fromEntries(["tentative_orders", "future_demand", "seasonal", "order_changes", "reservations"].map(key => [key, sent?.[key]?.length]))));
  const allowedCrops = new Set(["caixin", "pak_choi", "kailan", "lettuce"]);
  check("submitted enum values match the planning contract", sent.tentative_orders[0].status === "tentative" && sent.seasonal[0].system === "sheltered_hydroponic" && sent.seasonal[0].provenance === "synthetic_assumption" && [sent.tentative_orders[0], sent.future_demand[0], sent.seasonal[0]].every(row => allowedCrops.has(row.crop_id)) && ["add", "amend", "cancel"].includes(sent.order_changes[0].operation), JSON.stringify({ tentative_status: sent.tentative_orders[0].status, seasonal_system: sent.seasonal[0].system, seasonal_provenance: sent.seasonal[0].provenance, crops: [sent.tentative_orders[0].crop_id, sent.future_demand[0].crop_id, sent.seasonal[0].crop_id], order_operation: sent.order_changes[0].operation }));
  check("submitted domain semantics are exact", sent.tentative_orders[0].status === "tentative" && sent.seasonal[0].system === "sheltered_hydroponic" && sent.seasonal[0].provenance === "synthetic_assumption" && sent.order_changes[0].operation === "amend" && sent.order_changes[0].crop_id === undefined && sent.order_changes[0].due_date === undefined, JSON.stringify(sent));
  check("no page errors", errors.length === 0, errors.join("; "));
} catch (error) {
  report.failures.push(error instanceof Error ? `${error.message}\n${error.stack || ""}` : String(error));
} finally {
  if (browser) await browser.close();
  report.finished_at = new Date().toISOString(); report.passed = report.failures.length === 0;
  await mkdir(dirname(reportPath), { recursive: true }); await writeFile(reportPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ passed: report.passed, checks: report.checks.length, failures: report.failures }, null, 2));
}
if (!report.passed) process.exitCode = 1;
