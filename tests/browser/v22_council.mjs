import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";
import { readFileSync } from "node:fs";

const base = process.env.FARMTACT_BASE_URL || "http://127.0.0.1:4199";
const report = { checks: [], writes: [], failures: [] };
const check = (name, pass, detail = "") => {
  report.checks.push({ name, pass, detail });
  if (!pass) report.failures.push({ name, detail });
};
const json = (route, body, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  const page = await context.newPage();
  page.setDefaultTimeout(5_000);
  page.on("pageerror", (error) => report.failures.push({ name: "browser exception", detail: error.message }));
  const isolated = JSON.parse(readFileSync("/tmp/v22-ui-fixture.json", "utf8"));
  const resultId = "v22-council-result-current";
  const strategies = ["Lean", "Balanced", "Resilient"].map((name, index) => ({ id: `v22-${name.toLowerCase()}`, name, status: "FEASIBLE", metrics: { margin_sgd: 100 - index * 5, shortfall_kg: index, waste_kg: index + 1, closing_stock_kg: 2 + index }, allocations: [], deliveries: [], violations: [] }));
  const fixture = structuredClone(isolated.session);
  Object.assign(fixture, { status: "COMPLETED", stage: "review", result_id: resultId, selected_strategy_id: strategies[1].id, result: { strategies }, job: null, review: { status: "completed", result_id: resultId, findings: [{ role: "demand_analyst", status: "validated", rendered_interpretation: "Protect the recorded booked delivery before optional demand.", rendered_facts: ["Booked demand is frozen for this result."], proposed_strategy_id: strategies[1].id }] } });
  const restored = { id: "v22-restored-thread", title: "Restored current discussion", advisor_id: "ravi", status: "COMPLETED", last_request_status: "COMPLETED", created_at: "2026-09-18T00:00:00Z", snapshot_ref: { kind: "planning", id: `${fixture.id}:${resultId}`, result_id: resultId }, focus: { result_id: resultId }, messages: [{ id: "restored-message", conversation_id: "v22-restored-thread", speaker: "advisor", speaker_name: "ravi", content: "Restored transcript sentinel.", validation_status: "references_verified", evidence_status: "validated", rendered_facts: [] }] };
  const fresh = { ...structuredClone(restored), id: "v22-fresh-thread", title: "Fresh discussion", messages: [], status: "READY", last_request_status: "READY" };
  let creates = 0, direct = 0, councils = 0, reads = 0;
  let holdRestored = false, releaseRestored = () => {};
  let restoredGate = Promise.resolve();
  const handler = async (route) => {
    const request = route.request(), url = new URL(request.url()), path = url.pathname, method = request.method();
    if (method !== "GET") report.writes.push(`${method} ${path}`);
    if (method === "GET" && path.endsWith("/bootstrap")) return json(route, isolated.bootstrap);
    if (method === "GET" && path.endsWith("/farm-workflow")) return json(route, isolated.workflow);
    if (method === "GET" && path.endsWith("/planning-sessions")) return json(route, { sessions: [fixture] });
    if (method === "GET" && /\/planning-sessions\/[^/]+$/.test(path)) return json(route, fixture);
    if (method === "GET" && path.endsWith("/conversations")) return json(route, { conversations: [restored], next_before: null });
    if (method === "POST" && path.endsWith("/conversations")) { creates += 1; const body = request.postDataJSON(); fresh.advisor_id = body.advisor; check("conversation creation binds the displayed Council review result", body.council_review_result_id === resultId, body); return json(route, { id: fresh.id, status: "READY" }, 201); }
    if (method === "GET" && path.endsWith(`/conversations/${restored.id}`)) { reads += 1; if (holdRestored) await restoredGate; return json(route, restored); }
    if (method === "GET" && path.endsWith(`/conversations/${fresh.id}`)) { reads += 1; return json(route, fresh); }
    if (method === "POST" && path.endsWith(`/conversations/${fresh.id}/messages`)) { direct += 1; fresh.messages.push({ id: "fresh-user", conversation_id: fresh.id, speaker: "user", content: request.postDataJSON().content, validation_status: "recorded" }, { id: "fresh-answer", conversation_id: fresh.id, speaker: "advisor", speaker_name: "ravi", content: "Direct response sentinel.", validation_status: "references_verified", evidence_status: "validated", rendered_facts: [] }); fresh.status = fresh.last_request_status = "COMPLETED"; return json(route, { id: "direct-request", conversation_id: fresh.id, status: "COMPLETED" }, 202); }
    if (method === "POST" && path.endsWith(`/conversations/${fresh.id}/council`)) { councils += 1; fresh.messages.push({ id: "council-answer", conversation_id: fresh.id, speaker: "advisor", speaker_name: "asha", content: "Council response sentinel.", relationship: "conclusion", validation_status: "references_verified", evidence_status: "validated", rendered_facts: [] }); fresh.status = fresh.last_request_status = "COMPLETED"; return json(route, { id: "council-request", conversation_id: fresh.id, status: "COMPLETED" }, 202); }
    if (method !== "GET") return route.abort("blockedbyclient");
    return route.fallback();
  };
  await page.route("**/api/v1/**", handler);
  await page.goto(`${base}/play`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Skip demo" }).click().catch(() => {});
  const room = page.locator(".council-room");
  if (!await room.count()) throw new Error(`Council room missing: ${(await page.locator("body").innerText()).slice(0, 1200)}`);
  await room.getByRole("heading", { name: "Planning Council" }).waitFor();
  check("stored transcript list is restored with filtered read", await room.getByText("Restored current discussion").isVisible());
  await room.getByRole("button", { name: /Restored current discussion/ }).click();
  await room.getByText("Restored transcript sentinel.").waitFor();
  check("interpretation is retained as finding summary fallback", await room.getByText("Protect the recorded booked delivery before optional demand.").first().isVisible());
  const writesBeforePrompt = report.writes.length;
  await room.getByRole("button", { name: "Add question: Which plan protects confirmed demand best?" }).click();
  check("suggested prompt selection performs no mutation", report.writes.length === writesBeforePrompt, report.writes.slice(writesBeforePrompt));
  const textarea = room.getByLabel("Your question");
  await textarea.fill("Edition-scoped draft reload sentinel");
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.locator(".council-room").getByLabel("Your question").waitFor();
  check("unsent result-and-role draft survives reload", await page.locator(".council-room").getByLabel("Your question").inputValue() === "Edition-scoped draft reload sentinel");
  await page.locator(".council-room").getByLabel("Recipient").selectOption("hana");
  await page.locator(".council-room").getByLabel("Your question").fill("Ask the selected weather role only.");
  await page.locator(".council-room").getByRole("button", { name: "Send to Weather & Risk" }).click();
  await page.locator(".council-room").getByText("Direct response sentinel.").waitFor();
  await page.locator(".council-room").getByLabel("Your question").fill("Compare the recorded specialist differences.");
  await page.locator(".council-room").getByRole("button", { name: "Ask Council", exact: true }).click();
  await page.locator(".council-room").getByText("Council response sentinel.").waitFor();
  check("direct send is one explicit request", creates === 1 && direct === 1, { creates, direct });
  check("Ask Council is one separate explicit request", councils === 1, { councils });
  check("polling reads a stored transcript and does not repeat a mutation", reads >= 2 && direct === 1 && councils === 1, { reads, direct, councils });
  await page.locator(".council-room").screenshot({ path: "/tmp/v22-council-390.png", animations: "disabled" });

  holdRestored = true;
  restoredGate = new Promise((resolve) => { releaseRestored = resolve; });
  await page.locator(".council-room").getByRole("button", { name: /Restored current discussion/ }).click();
  const reload = page.reload({ waitUntil: "domcontentloaded" });
  await new Promise((resolve) => setTimeout(resolve, 100));
  releaseRestored();
  await reload;
  await page.locator(".council-room").waitFor();
  check("delayed transcript response cannot mutate the reloaded context", await page.getByText("Restored transcript sentinel.").count() === 0);
  holdRestored = false;

  // A rejected admission must leave the exact unsent draft and must not retry.
  const ratePage = await context.newPage();
  ratePage.setDefaultTimeout(5_000);
  let rateCreates = 0;
  await ratePage.route("**/api/v1/**", async (route) => {
    const request = route.request(), path = new URL(request.url()).pathname;
    if (request.method() === "GET" && path.endsWith("/bootstrap")) return json(route, isolated.bootstrap);
    if (request.method() === "GET" && path.endsWith("/farm-workflow")) return json(route, isolated.workflow);
    if (request.method() === "GET" && path.endsWith("/planning-sessions")) return json(route, { sessions: [fixture] });
    if (request.method() === "GET" && /\/planning-sessions\/[^/]+$/.test(path)) return json(route, fixture);
    if (request.method() === "GET" && path.endsWith("/conversations")) return json(route, { conversations: [] });
    if (request.method() === "POST" && path.endsWith("/conversations")) { rateCreates += 1; return route.fulfill({ status: 429, headers: { "Retry-After": "2", "Content-Type": "application/json" }, body: JSON.stringify({ detail: "Controlled admission limit" }) }); }
    if (request.method() !== "GET") return route.abort("blockedbyclient");
    return route.fallback();
  });
  await ratePage.goto(`${base}/play`, { waitUntil: "domcontentloaded" });
  const rateRoom = ratePage.locator(".council-room"); await rateRoom.getByLabel("Your question").fill("Retain this exact 429 draft"); await rateRoom.getByRole("button", { name: "Send to Demand Planner" }).click();
  await ratePage.getByText("Controlled admission limit").waitFor();
  check("429 retains the draft and makes no automatic retry", await rateRoom.getByLabel("Your question").inputValue() === "Retain this exact 429 draft" && rateCreates === 1, { rateCreates });
  await ratePage.close();

  check("fixture never reached an unhandled provider endpoint", report.writes.every((entry) => /\/conversations(?:$|\/)/.test(entry)), report.writes);
  console.log(JSON.stringify(report, null, 2));
  if (report.failures.length) process.exitCode = 1;
} catch (error) {
  console.error(error);
  console.error(JSON.stringify(report, null, 2));
  process.exitCode = 1;
} finally {
  await browser?.close();
}
