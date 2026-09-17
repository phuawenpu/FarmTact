import { access, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const base = (process.env.BASE_URL || "http://127.0.0.1:4196").replace(/\/$/, "");
const statePath = process.env.STORAGE_STATE || "/tmp/farmtact-v15-cards-storage.json";
const reportPath = resolve(root, "reports/v15/reservation-eligibility-browser.json");
const reason = "Controlled server reason: no free reservation window remains.";
const report = { started_at: new Date().toISOString(), base, checks: [], failures: [], fixture: "Labelled GET response fixture only; no server records or provider calls." };
const check = (name, pass, detail = "") => { report.checks.push({ name, pass: Boolean(pass), detail }); if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`); };

let browser;
try {
  await access(statePath);
  browser = await chromium.launch({ headless: true });
  const discovery = await browser.newContext({ storageState: statePath });
  const listResponse = await discovery.request.get(`${base}/api/v1/planning-sessions`), listed = await listResponse.json();
  let fixtureSession;
  for (const item of listed.sessions) {
    if (!item.workflow) continue;
    const response = await discovery.request.get(`${base}/api/v1/planning-sessions/${encodeURIComponent(item.id)}`);
    const session = await response.json();
    if (session.result?.strategies?.length && session.tactical_context?.grow_space) { fixtureSession = session; break; }
  }
  await discovery.close();
  check("fixture uses an existing calculated workflow", Boolean(fixtureSession), fixtureSession?.id || "missing");

  for (const width of [360, 390, 430, 1280]) {
    const context = await browser.newContext({ storageState: statePath, viewport: { width, height: width > 500 ? 900 : 844 }, reducedMotion: "reduce" });
    await context.addInitScript(id => {
      localStorage.setItem("farmtact:v15:planning-session", id);
      localStorage.removeItem(`farmtact:v15:integrated-cards-navigation:${id}`);
    }, fixtureSession.id);
    const page = await context.newPage();
    let mode = "denied", posts = 0, providers = 0;
    page.on("request", request => { if (request.method() === "POST") posts++; if (/deepseek|provider|inference/i.test(request.url())) providers++; });
    await page.route("**/api/v1/**", async route => {
      if (route.request().method() === "POST") return route.abort("blockedbyclient");
      return route.fallback();
    });
    await page.route(`**/api/v1/planning-sessions/${fixtureSession.id}`, async route => {
      const response = await route.fetch(), session = await response.json();
      const eligible = mode === "eligible";
      session.tactical_context.grow_space = { ...session.tactical_context.grow_space, reservation_active: mode === "approval", reserve_eligible: eligible, reserve_disabled_reason: eligible ? null : reason };
      await route.fulfill({ response, json: session });
    });
    await page.route("**/api/v1/farm-workflow", async route => {
      const response = await route.fetch(), workflow = await response.json();
      workflow.proposals = workflow.proposals.filter(item => item.session_id !== fixtureSession.id);
      workflow.tasks = workflow.tasks.filter(item => workflow.proposals.some(proposal => proposal.id === item.proposal_id));
      if (mode === "approval") {
        const before = { tentative_orders: [], future_demand: [], seasonal: [], order_changes: [], reservations: [], ...(fixtureSession.assumptions || {}) };
        const after = { ...before, reservations: [...(before.reservations || []).filter(row => row.bed_id !== fixtureSession.tactical_context.grow_space.id), { bed_id: fixtureSession.tactical_context.grow_space.id, ...fixtureSession.tactical_context.grow_space.reservation_window }] };
        workflow.proposals.push({ id: "controlled-denied-approval", session_id: fixtureSession.id, base_revision: fixtureSession.revision - 1, proposal_revision: fixtureSession.revision, status: "applied", selected_strategy_id: fixtureSession.selected_strategy_id, changes: [{ kind: "planning_assumptions", assumptions: after }], inverse_changes: [{ kind: "planning_assumptions", assumptions: before }], recalculation_job: { id: fixtureSession.result_id, status: "COMPLETED" }, calculated_metrics: {}, approval: { available: false, reason: "Controlled server reason: approval is unavailable." } });
      }
      await route.fulfill({ response, json: workflow });
    });
    const openReservation = async () => {
      await page.locator(".ic-shell").waitFor();
      const previous = page.getByRole("button", { name: "← Previous", exact: true });
      for (let i = 0; i < 20 && await previous.isEnabled(); i++) await previous.click();
      for (let i = 0; i < 12 && !(await page.getByRole("heading", { name: /Keep .+ available|is reserved/, exact: true }).isVisible().catch(() => false)); i++)
        await page.getByRole("button", { name: "Next →", exact: true }).click();
      await page.getByRole("heading", { name: /Keep .+ available|is reserved/, exact: true }).waitFor();
    };

    await page.goto(`${base}/play`, { waitUntil: "domcontentloaded" }); await openReservation();
    const denied = page.getByRole("button", { name: "Review reservation", exact: true });
    const card = page.locator(".ic-card");
    const deniedActions = JSON.parse(await card.getAttribute("data-card-actions") || "[]");
    const deniedMeta = deniedActions.find(item => item.label === "Review reservation");
    check(`${width}: denied reservation metadata is server-derived`, deniedMeta?.eligible === false && deniedMeta?.eligibilitySource === "server" && deniedMeta?.disabledReason === reason, deniedMeta);
    check(`${width}: denied reservation DOM matches metadata`, await denied.isDisabled() && await denied.getAttribute("title") === reason, { disabled: await denied.isDisabled(), title: await denied.getAttribute("title") });
    check(`${width}: exact server reason is visible`, await page.getByText(reason, { exact: true }).isVisible());

    await card.focus(); await card.press("Enter"); await page.waitForTimeout(100);
    check(`${width}: keyboard Enter cannot submit denied reservation`, posts === 0 && await page.getByRole("button", { name: "Apply & recalculate", exact: true }).count() === 0, String(posts));
    await page.getByRole("button", { name: "Explain", exact: true }).click();
    await page.getByRole("heading", { name: "What this means", exact: true }).waitFor();
    await page.getByRole("button", { name: "Back", exact: true }).click();
    const beforeSwipe = await card.getAttribute("data-card-id");
    const box = await card.boundingBox();
    if (!box) throw new Error("Reservation card has no rendered box");
    await page.mouse.move(box.x + box.width * .8, box.y + Math.min(100, box.height / 2)); await page.mouse.down();
    await page.mouse.move(box.x + box.width * .15, box.y + Math.min(100, box.height / 2), { steps: 4 }); await page.mouse.up();
    check(`${width}: Explain and swipe remain read-only`, posts === 0 && providers === 0, { posts, providers, beforeSwipe, afterSwipe: await card.getAttribute("data-card-id") });

    mode = "eligible";
    await page.reload({ waitUntil: "domcontentloaded" }); await openReservation();
    const allowed = page.getByRole("button", { name: "Review reservation", exact: true });
    const allowedActions = JSON.parse(await page.locator(".ic-card").getAttribute("data-card-actions") || "[]");
    const allowedMeta = allowedActions.find(item => item.label === "Review reservation");
    check(`${width}: eligible control enables DOM and metadata together`, allowedMeta?.eligible === true && allowedMeta?.eligibilitySource === "server" && await allowed.isEnabled(), { metadata: allowedMeta, disabled: await allowed.isDisabled() });
    if (width === 390) {
      mode = "approval"; await page.reload({ waitUntil: "domcontentloaded" }); await openReservation();
      const approve = page.getByRole("button", { name: "Approve actions", exact: true }), approvalReason = "Controlled server reason: approval is unavailable.";
      const approvalActions = JSON.parse(await page.locator(".ic-card").getAttribute("data-card-actions") || "[]"), approvalMeta = approvalActions.find(item => item.label === "Approve actions");
      check("390: denied approval metadata and DOM expose exact server reason", approvalMeta?.eligible === false && approvalMeta?.eligibilitySource === "server" && approvalMeta?.disabledReason === approvalReason && await approve.isDisabled() && await page.getByText(approvalReason, { exact: true }).isVisible(), { metadata: approvalMeta, disabled: await approve.isDisabled() });
      await page.locator(".ic-card").focus(); await page.locator(".ic-card").press("Enter"); await page.waitForTimeout(100);
      check("390: keyboard Enter cannot bypass denied approval", posts === 0, String(posts));
    }
    check(`${width}: fixture journey creates no mutation or provider request`, posts === 0 && providers === 0, { posts, providers });
    await context.close();
  }

  const approvedStatePath = "/tmp/farmtact-v15-records-extended-storage.json";
  await access(approvedStatePath);
  const approvedContext = await browser.newContext({ storageState: approvedStatePath, viewport: { width: 390, height: 844 }, reducedMotion: "reduce" });
  const workflowResponse = await approvedContext.request.get(`${base}/api/v1/farm-workflow`), approvedWorkflow = await workflowResponse.json();
  const approvedProposal = [...approvedWorkflow.proposals].reverse().find(proposal => ["approved", "applied"].includes(proposal.status) && approvedWorkflow.tasks.some(task => task.proposal_id === proposal.id));
  check("positive control uses an existing persisted task proposal", Boolean(approvedProposal), approvedProposal?.id || "missing");
  await approvedContext.addInitScript(id => {
    localStorage.setItem("farmtact:v15:planning-session", id);
    localStorage.removeItem(`farmtact:v15:integrated-cards-navigation:${id}`);
  }, approvedProposal.session_id);
  const approvedPage = await approvedContext.newPage(); let approvedPosts = 0;
  approvedPage.on("request", request => { if (request.method() === "POST") approvedPosts++; });
  await approvedPage.route("**/api/v1/**", route => route.request().method() === "POST" ? route.abort("blockedbyclient") : route.continue());
  await approvedPage.goto(`${base}/play`, { waitUntil: "domcontentloaded" }); await approvedPage.locator(".ic-shell").waitFor();
  const approvedPrevious = approvedPage.getByRole("button", { name: "← Previous", exact: true });
  for (let i = 0; i < 20 && await approvedPrevious.isEnabled(); i++) await approvedPrevious.click();
  for (let i = 0; i < 20 && !(await approvedPage.getByRole("button", { name: "Review sandbox work", exact: true }).isVisible().catch(() => false)); i++)
    await approvedPage.getByRole("button", { name: "Next →", exact: true }).click();
  const reviewWork = approvedPage.getByRole("button", { name: "Review sandbox work", exact: true });
  await reviewWork.waitFor();
  const workActions = JSON.parse(await approvedPage.locator(".ic-card").getAttribute("data-card-actions") || "[]"), workMeta = workActions.find(item => item.label === "Review sandbox work");
  check("persisted task navigation remains locally eligible", await reviewWork.isEnabled() && workMeta?.eligible === true && workMeta?.authority === "local_navigation" && workMeta?.eligibilitySource === "local", { metadata: workMeta, disabled: await reviewWork.isDisabled() });
  await approvedPage.locator(".ic-card").focus(); await approvedPage.locator(".ic-card").press("Enter");
  await approvedPage.locator(".integrated-records").waitFor();
  check("keyboard opens existing sandbox work without mutation", approvedPosts === 0, String(approvedPosts));
  await approvedContext.close();
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL"; report.failures.push(error instanceof Error ? error.stack : String(error)); process.exitCode = 1;
} finally {
  report.finished_at = new Date().toISOString(); await browser?.close();
  await mkdir(dirname(reportPath), { recursive: true }); await writeFile(reportPath, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failures: report.failures }, null, 2));
}
