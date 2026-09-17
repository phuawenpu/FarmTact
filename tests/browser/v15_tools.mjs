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
const backToShell = async (page) => {
  for (let depth = 0; depth < 4; depth += 1) {
    if (await page.getByRole("button", { name: "More", exact: true }).count()) return;
    const close = page.getByRole("button", { name: "Close", exact: true });
    if (await close.count()) await close.click();
    else await page.getByRole("button", { name: "Back", exact: true }).last().click();
  }
  await page.getByRole("button", { name: "More", exact: true }).waitFor();
};
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
  check("scenario branch persisted separately", !!scenario?.id, { id: scenario?.id, status: scenario?.status });
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
  check("research calculation records three strategies", await page.evaluate(async (id) => { const s = await (await fetch(`/api/v1/council-research/${id}`)).json(); return s.results.at(-1)?.calculation?.strategies?.length === 3; }, researchId));
  // Review/apply a labour edit.
  await click(page, "Back");
  for (let i = 0; i < 3; i += 1) await click(page, "Next");
  await click(page, "Open Reviewed proposal");
  await page.getByLabel("Edit type").selectOption("labour");
  await page.getByLabel("Labour allowance (%)").fill("75");
  const proposalResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname.endsWith(`/api/v1/council-research/${researchId}/actions`));
  await click(page, "Review proposal"); await proposalResponse;
  check("research edit is previewed before apply", await page.evaluate(async (id) => !!(await (await fetch(`/api/v1/council-research/${id}?t=${Date.now()}`, { cache: "no-store" })).json()).proposal, researchId));
  const applyResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname.endsWith(`/api/v1/council-research/${researchId}/actions`));
  await click(page, "Apply reviewed edit"); await applyResponse;
  check("research apply creates a new frozen input version", await page.evaluate(async (id) => (await (await fetch(`/api/v1/council-research/${id}`)).json()).input_version === 2, researchId));
  await page.getByRole("heading", { name: "Review proposed edit", exact: true }).waitFor({ state: "detached" });
  // Challenge and resolve the supported sheltered-rainfall boundary.
  await click(page, "Back"); for (let i = 0; i < 5; i += 1) await click(page, "Next");
  await click(page, "Open Challenge");
  const challengeResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname.endsWith(`/api/v1/council-research/${researchId}/actions`));
  await click(page, "Open challenge"); await challengeResponse;
  await page.getByRole("combobox").filter({ has: page.locator('option[value="corrected"]') }).selectOption("corrected");
  const resolutionResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname.endsWith(`/api/v1/council-research/${researchId}/actions`));
  await click(page, "Record resolution"); await resolutionResponse;
  check("research challenge records corrected evidence status", await page.evaluate(async (id) => (await (await fetch(`/api/v1/council-research/${id}`)).json()).challenge?.status === "corrected", researchId));
  await click(page, "Back"); for (let i = 0; i < 7; i += 1) await click(page, "Next");
  await click(page, "Open Revision history");
  await page.getByRole("heading", { name: /Recorded revision/ }).waitFor();
  check("research append-only revision history is reachable in cards", await page.getByText(/read-only replay · zero inference/i).isVisible());
  check("research history endpoint declares zero inference", await page.evaluate(async (id) => (await (await fetch(`/api/v1/council-research/${id}/history?after=-1&limit=20`)).json()).inference_triggered === false, researchId));
  check("full local research cycle makes no provider request", report.requests.provider.length === 0, report.requests.provider);

  // Explicit transport fixture: the provider is not called. It supplies one already-recorded,
  // references-verified adviser message so the V15 DOM handoff can be exercised deterministically.
  const fixtureConversation = { id: "v15-recorded-thread", title: "Recorded adviser fixture", advisor_id: "idris", status: "COMPLETED", created_at: "2026-09-17T00:00:00Z", updated_at: "2026-09-17T00:00:00Z", replay: true, last_request_status: "COMPLETED", messages: [{ id: "v15-validated-message", speaker: "advisor", speaker_name: "Idris", content: "Review this bounded labour assumption.", validation_status: "references_verified", evidence_status: "partial", proposed_actions: [{ control: "labour_percent", value: 75, unit: "percent", status: "hypothesis_only" }], fact_refs: [], rendered_facts: [] }] };
  let linkedProposalBody, linkedApplyBody;
  await page.route("**/api/v1/conversations", async (route) => route.request().method() === "GET" ? route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ conversations: [fixtureConversation] }) }) : route.continue());
  await page.route("**/api/v1/conversations/v15-recorded-thread/replay", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fixtureConversation) }));
  await page.route("**/api/v1/farm-workflow/proposals", async (route) => { linkedProposalBody = route.request().postDataJSON(); await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "v15-linked-proposal", session_id: linkedProposalBody.session_id, base_revision: linkedProposalBody.base_revision, proposal_revision: 1, status: "draft", selected_strategy_id: linkedProposalBody.selected_strategy_id, calculated_metrics: {}, source_conversation_id: linkedProposalBody.source_conversation_id, source_message_id: linkedProposalBody.source_message_id }) }); });
  await page.route("**/api/v1/farm-workflow/proposals/v15-linked-proposal/apply", async (route) => { linkedApplyBody = route.request().postDataJSON(); await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "v15-linked-proposal", session_id: linkedProposalBody.session_id, base_revision: linkedProposalBody.base_revision, proposal_revision: 2, status: "applied", selected_strategy_id: linkedProposalBody.selected_strategy_id, calculated_metrics: {} }) }); });
  await page.goto(base, { waitUntil: "domcontentloaded" }); await page.locator(".ic-shell").waitFor();
  await openMore(page); await toolAt(page, 2, "Inspect the facts. Ask deliberately.");
  for (let i = 0; i < 20; i += 1) await click(page, "Next");
  await page.getByLabel("Saved thread").selectOption("v15-recorded-thread"); await click(page, "Open read-only replay");
  await page.getByText("Review this bounded labour assumption.", { exact: true }).waitFor();
  await page.getByLabel("Validated message").selectOption("v15-validated-message");
  await click(page, "Create reviewed proposal"); await page.getByText("v15-linked-proposal", { exact: true }).waitFor();
  check("recorded adviser handoff preserves exact source IDs", linkedProposalBody?.source_conversation_id === "v15-recorded-thread" && linkedProposalBody?.source_message_id === "v15-validated-message", linkedProposalBody);
  const linkedApplyResponse = page.waitForResponse((response) => response.request().method() === "POST" && new URL(response.url()).pathname.endsWith("/farm-workflow/proposals/v15-linked-proposal/apply"));
  await click(page, "Apply reviewed proposal"); await linkedApplyResponse;
  check("linked draft is applied only by the explicit footer action", linkedApplyBody?.proposal_id === "v15-linked-proposal", linkedApplyBody);

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
