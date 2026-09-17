import { access, mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const baseURL = process.env.BASE_URL || "http://127.0.0.1:4196";
const reportPath = resolve(root, "reports/v15/plan-strategy-selection-browser.json");
const states = ["/tmp/farmtact-v15-cards-storage.json", "/tmp/farmtact-v15-records-extended-storage.json"];
const report = { started_at: new Date().toISOString(), base_url: baseURL, checks: [], failures: [], prerequisites: [] };
function check(name, pass, detail = "") { report.checks.push({ name, pass: Boolean(pass), detail }); if (!pass) throw new Error(`${name}: ${detail}`); }
async function state() { for (const path of states) try { await access(path); return path; } catch {} throw new Error("Existing private browser storage is unavailable"); }

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 430, height: 900 }, storageState: await state() });
  const page = await context.newPage();
  const pageErrors = []; page.on("pageerror", error => pageErrors.push(error.message));
  const response = await page.goto(baseURL, { waitUntil: "networkidle" });
  check("application responds", response?.status() === 200, String(response?.status()));
  const setup = await page.evaluate(async () => {
    const response = await fetch("/api/v1/planning-sessions", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ name: "Strategy selection acceptance", workflow: true }) });
    if (!response.ok) throw new Error(`session setup ${response.status}: ${await response.text()}`);
    const session = await response.json();
    const key = Object.keys(localStorage).find(item => item.includes("planning-session"));
    if (!key) throw new Error("remembered planning session key unavailable");
    localStorage.setItem(key, session.id);
    return { id: session.id, revision: session.revision };
  });
  report.prerequisites.push(`Created ordinary workflow ${setup.id} through the existing planning-session API; calculation itself used the Plan UI.`);
  await page.reload({ waitUntil: "networkidle" });

  const farmTools = page.getByRole("button", { name: /^(Farm tools|Tools)$/ }).filter({ visible: true }).first();
  if (await farmTools.isVisible().catch(() => false)) await farmTools.click();
  else await page.getByRole("button", { name: "More", exact: true }).filter({ visible: true }).first().click();
  for (let i = 0; i < 7 && !(await page.getByText("Plan", { exact: true }).isVisible().catch(() => false)); i++) await page.getByRole("button", { name: "Previous", exact: true }).filter({ visible: true }).first().click();
  await page.getByText("Plan", { exact: true }).waitFor(); await page.getByRole("button", { name: "Open tool", exact: true }).click();

  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  const initial = page.getByLabel("Selected strategy");
  const initialLabel = await initial.locator("option:checked").textContent();
  check("uncalculated session shows strategy placeholder", /not calculated|calculate strategies/i.test(initialLabel || ""), initialLabel || "");
  check("uncalculated strategy selector is disabled", await initial.isDisabled());

  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await page.getByRole("button", { name: "Calculate locally", exact: true }).click();
  await page.getByRole("button", { name: "Refresh", exact: true }).waitFor();

  let calculated;
  for (let i = 0; i < 180; i++) {
    calculated = await page.evaluate(async id => (await (await fetch(`/api/v1/planning-sessions/${encodeURIComponent(id)}`)).json()), setup.id);
    if (calculated.result?.strategies?.length && !["QUEUED", "RUNNING"].includes(calculated.job?.status || "")) break;
    await page.waitForTimeout(500);
  }
  check("real UI calculation produced strategies", calculated?.result?.strategies?.length > 1, String(calculated?.result?.strategies?.length));
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  const compare = page.getByLabel("Compare strategy");
  const validIds = calculated.result.strategies.map(item => item.id);
  const defaultSelection = await compare.inputValue();
  check("calculated result defaults to a valid strategy", validIds.includes(defaultSelection), defaultSelection);

  const explicit = validIds.find(id => id !== defaultSelection) || validIds[0];
  await compare.selectOption(explicit);
  check("farmer can explicitly select another valid strategy", await compare.inputValue() === explicit, await compare.inputValue());
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  await page.getByRole("button", { name: "Refresh", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Open", exact: true }).click();
  check("valid explicit selection survives result refresh", await page.getByLabel("Compare strategy").inputValue() === explicit, await page.getByLabel("Compare strategy").inputValue());
  check("no page errors", pageErrors.length === 0, pageErrors.join("; "));
} catch (error) {
  report.failures.push(error instanceof Error ? `${error.message}\n${error.stack || ""}` : String(error));
} finally {
  if (browser) await browser.close();
  report.finished_at = new Date().toISOString(); report.passed = report.failures.length === 0;
  await mkdir(dirname(reportPath), { recursive: true }); await writeFile(reportPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ passed: report.passed, checks: report.checks.length, failures: report.failures }, null, 2));
}
if (!report.passed) process.exitCode = 1;
