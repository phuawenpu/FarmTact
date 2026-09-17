import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const root = resolve(new URL("../..", import.meta.url).pathname);
const base = (process.env.BASE_URL || process.env.FARMTACT_BASE_URL || "http://127.0.0.1:4191").replace(/\/$/, "");
const report = { status: "RUNNING", base_url: base, checks: [], requests: { provider: [], mutations: [] }, screenshots: [], failures: [] };
const check = (name, pass, detail = undefined) => { report.checks.push({ name, pass: Boolean(pass), detail }); if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`); };
const click = async (page, name) => page.getByRole("button", { name, exact: true }).click();
const openMore = async (page) => { const button = page.getByRole("button", { name: "More", exact: true }); await button.waitFor(); await button.click(); await page.getByRole("heading", { name: "Plan", exact: true }).waitFor(); };
const toolAt = async (page, offset, heading) => { for (let i = 0; i < offset; i += 1) await click(page, "Next →"); await click(page, "Open tool"); await page.getByRole("heading", { name: heading, exact: true }).waitFor(); };
const backToShell = async (page) => { const buttons = page.getByRole("button", { name: /Farm tools|Back/, exact: false }); await buttons.first().click(); };
const waitForResearchResult = async (page, sessionId) => {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const value = await page.evaluate(async (id) => (await (await fetch(`/api/v1/council-research/${encodeURIComponent(id)}?t=${Date.now()}`, { cache: "no-store" })).json()), sessionId);
    if (["completed", "failed", "cancelled"].includes(String(value.numerical_calculation_status))) return value;
    await page.waitForTimeout(1000);
  }
  throw new Error("Research calculation did not reach a terminal state");
};
const waitForScenario = async (page, id) => {
  for (let attempt = 0; attempt < 180; attempt += 1) {
    const value = await page.evaluate(async (scenarioId) => (await (await fetch(`/api/v1/scenarios/${encodeURIComponent(scenarioId)}?t=${Date.now()}`, { cache: "no-store" })).json()), id);
    if (["completed", "failed", "cancelled"].includes(String(value.status).toLowerCase())) return value;
    await page.waitForTimeout(1000);
  }
  throw new Error("Scenario did not reach a terminal state");
};

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 360, height: 800 }, reducedMotion: "reduce", acceptDownloads: true });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (request.method() !== "GET") report.requests.mutations.push(`${request.method()} ${url.pathname}`);
    if (request.method() !== "GET" && (/\/conversations(?:\/|$)/.test(url.pathname) || /\/planning-sessions\/[^/]+\/review$/.test(url.pathname))) report.requests.provider.push(`${request.method()} ${url.pathname}`);
  });
  await page.goto(base, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.locator(".ic-shell").waitFor({ timeout: 30_000 });
  check("360px shell has no horizontal document overflow", await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth })));

  // All five top-level tool cards must open real integrated cards.
  const tools = [
    { offset: 0, heading: "Objectives & all demand" },
    { offset: 1, heading: "Records & work" },
    { offset: 2, heading: "Inspect the facts. Ask deliberately." },
    { offset: 3, heading: "Scenarios & quests" },
    { offset: 4, heading: "Saved plans" },
  ];
  for (const item of tools) {
    await openMore(page); await toolAt(page, item.offset, item.heading);
    check(`tool reachable: ${item.heading}`, await page.getByRole("heading", { name: item.heading, exact: true }).isVisible());
    await backToShell(page);
  }
  check("browsing all tools makes no provider request", report.requests.provider.length === 0, report.requests.provider);

  // Knowledge: crop facts, source card and saved threads remain browse-only.
  await openMore(page); await toolAt(page, 2, "Inspect the facts. Ask deliberately.");
  check("crop card exposes recipe and evidence boundary", await page.getByText(/planning assumptions, not a real-farm growth guarantee/i).isVisible());
  const knowledgeCount = Number((await page.locator(".ik-actions span").textContent())?.split("/")[1]?.trim());
  check("knowledge deck contains crops, source status, advisers and history", knowledgeCount >= 22, knowledgeCount);
  for (let i = 0; i < 12; i += 1) await page.getByRole("button", { name: "Next", exact: true }).click();
  check("source card exposes freshness and status", await page.getByText("Freshness", { exact: true }).isVisible() && await page.getByText("Status", { exact: true }).isVisible());
  check("knowledge browse remains provider-free", report.requests.provider.length === 0, report.requests.provider);
  await backToShell(page);

  // Dataset generation, immutable save, export and scenario local run.
  await openMore(page); await toolAt(page, 3, "Scenarios & quests");
  await click(page, "Next"); await click(page, "Next"); await click(page, "Open");
  await page.getByRole("heading", { name: "Dataset & forecast settings", exact: true }).waitFor();
  const datasetName = `V15 browser dataset ${Date.now()}`;
  await page.getByLabel("Snapshot name").fill(datasetName);
  await click(page, "Preview locally");
  await page.getByText("Preview—not saved. Synthetic assumptions only.", { exact: true }).waitFor({ timeout: 30_000 });
  await click(page, "Save frozen dataset");
  await page.getByText("Frozen saved snapshot", { exact: false }).waitFor({ timeout: 30_000 });
  const savedSnapshot = await page.evaluate(async (name) => (await (await fetch("/api/v1/data-explorer/snapshots")).json()).snapshots.find((row) => row.name === name), datasetName);
  check("generated preview saves an immutable snapshot", !!savedSnapshot?.id && !!savedSnapshot?.content_hash, savedSnapshot);
  await click(page, "Snapshot actions");
  const downloadPromise = page.waitForEvent("download");
  await click(page, "Export CSV");
  const download = await downloadPromise;
  check("saved dataset export downloads CSV", (await download.suggestedFilename()).endsWith(".csv"), await download.suggestedFilename());
  await page.goto(base, { waitUntil: "domcontentloaded" });
  await page.locator(".ic-shell").waitFor();

  await openMore(page); await toolAt(page, 3, "Scenarios & quests");
  await click(page, "Open");
  if (await page.getByRole("button", { name: "New branch", exact: true }).count()) await click(page, "New branch");
  else await click(page, "Create scenario");
  await page.getByRole("heading", { name: "Prepare experiment", exact: true }).waitFor();
  const scenarioName = `V15 real scenario ${Date.now()}`;
  await page.getByLabel("Name").fill(scenarioName);
  await page.getByLabel("demand percent").fill("105");
  await page.getByLabel("Demand crop ID").fill("lettuce");
  await click(page, "Review");
  const scenarioResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/api/v1/scenarios"));
  await click(page, "Create frozen branch");
  const scenario = await (await scenarioResponse).json();
  check("scenario branch persisted separately", !!scenario?.id, scenario);
  await click(page, "Run locally");
  const completedScenario = await waitForScenario(page, scenario.id);
  check("scenario local run reaches a terminal result", completedScenario.status.toLowerCase() === "completed" && !!completedScenario.result, { status: completedScenario.status, result: !!completedScenario.result });
  check("dataset/scenario workflow makes no provider request", report.requests.provider.length === 0, report.requests.provider);

  // The integrated research deck must be reachable from Experiments.
  await backToShell(page); await openMore(page); await toolAt(page, 3, "Scenarios & quests");
  for (let i = 0; i < 4; i += 1) await click(page, "Next");
  await click(page, "Open"); await click(page, "Open research cards");
  await page.getByRole("heading", { name: "Saved Council research", exact: true }).waitFor({ timeout: 10_000 });
  await click(page, "New study");
  await page.getByRole("heading", { name: /Research v1/ }).waitFor();
  const researchId = await page.evaluate(async () => (await (await fetch("/api/v1/council-research")).json()).sessions[0].id);
  // Open Calculation card (index 4) and run the local planner.
  for (let i = 0; i < 4; i += 1) await click(page, "Next");
  await click(page, "Open Calculation"); await click(page, "Calculate version");
  await waitForResearchResult(page, researchId);
  await click(page, "Refresh status");
  check("research calculation records three strategies", await page.evaluate(async (id) => { const s = await (await fetch(`/api/v1/council-research/${id}`)).json(); return s.results.at(-1)?.calculation?.strategies?.length === 3; }, researchId));
  // Review/apply a labour edit.
  await click(page, "Back");
  await click(page, "Previous");
  await click(page, "Open Reviewed proposal");
  await page.getByLabel("Edit type").selectOption("labour");
  await page.getByLabel("Labour allowance (%)").fill("75");
  await click(page, "Review proposal");
  check("research edit is previewed before apply", await page.getByText(/Preview — not applied/).isVisible());
  await click(page, "Apply reviewed edit");
  check("research apply creates a new frozen input version", await page.evaluate(async (id) => (await (await fetch(`/api/v1/council-research/${id}`)).json()).input_version === 2, researchId));
  // Challenge and resolve the supported sheltered-rainfall boundary.
  await click(page, "Back"); await click(page, "Next"); await click(page, "Next");
  await click(page, "Open Challenge"); await click(page, "Open challenge");
  await page.getByLabel("Resolution").selectOption("corrected"); await click(page, "Record resolution");
  check("research challenge records corrected evidence status", await page.evaluate(async (id) => (await (await fetch(`/api/v1/council-research/${id}`)).json()).challenge?.status === "corrected", researchId));
  check("full local research cycle makes no provider request", report.requests.provider.length === 0, report.requests.provider);

  check("no browser page errors", pageErrors.length === 0, pageErrors);
  check("mobile tool cards retain vertical scrolling", await page.evaluate(() => document.documentElement.scrollHeight > document.documentElement.clientHeight && document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
  await mkdir(resolve(root, "apps/web/screenshots"), { recursive: true });
  const screenshot = resolve(root, "apps/web/screenshots/v15-tools-360.png");
  await page.screenshot({ path: screenshot, fullPage: true, animations: "disabled" });
  report.screenshots.push(screenshot.slice(root.length + 1)); report.status = "PASS";
} catch (error) {
  report.status = "FAIL"; report.failures.push(error instanceof Error ? error.stack : String(error)); process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
}
