import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const root = resolve(new URL("../..", import.meta.url).pathname);
const base = (process.env.FARMTACT_BASE_URL || "http://127.0.0.1:4190").replace(/\/$/, "");
const result = { status: "RUNNING", checks: [], failures: [], screenshots: [] };
const check = (name, pass, detail = null) => {
  result.checks.push({ name, pass: Boolean(pass), detail });
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`);
};

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  const providerMutations = [];
  page.on("request", (request) => {
    if (request.method() === "POST" && /\/conversations(?:\/[^/]+\/messages)?$/.test(new URL(request.url()).pathname)) {
      providerMutations.push({ method: request.method(), url: request.url() });
    }
  });

  await page.goto(`${base}/v13/`, { waitUntil: "domcontentloaded", timeout: 30_000 });
  await page.locator(".tc-shell").waitFor({ timeout: 20_000 });
  check("opens on labelled rainfall simulation", await page.getByRole("heading", { name: "Heavy rainfall" }).isVisible()
    && await page.getByText("SIMULATION · SCENARIO ONLY", { exact: true }).first().isVisible());
  check("opening the mission makes no provider request", providerMutations.length === 0, providerMutations);

  await page.getByRole("button", { name: "Calculate baseline" }).click();
  await page.locator(".tc-demand-bar").getByText(/kg$/).first().waitFor({ timeout: 120_000 });
  const summary = await page.locator(".tc-demand-bar").innerText();
  check("baseline shows server-derived demand, supply, and booked gap", /BOOKED DEMAND\s+[\d,.]+ kg/.test(summary)
    && /PLANNED SUPPLY\s+[\d,.]+ kg/.test(summary)
    && /BOOKED GAP\s+[\d,.]+ kg/.test(summary), summary);
  check("baseline still makes no provider request", providerMutations.length === 0, providerMutations);

  await page.getByRole("button", { name: "Next tactical card" }).click();
  await page.getByRole("heading", { name: "Keep grow space B3 free" }).waitFor();
  const constraintText = await page.locator(".tc-card").innerText();
  check("B3 reservation starts after crop sanitation clears", constraintText.includes("2026-10-01"), constraintText);
  await page.getByRole("button", { name: "Details" }).click();
  check("Details updates the contextual panel", (await page.locator(".tm-focus").innerText()).includes("Keep grow space B3 free"));
  await page.getByRole("button", { name: "Reserve space" }).click();
  await page.locator(".tc-action-dock--progress").waitFor({ timeout: 10_000 });
  await page.getByRole("button", { name: "Undo" }).waitFor({ timeout: 120_000 });
  const tray = await page.locator(".tm-strategy-wrap").innerText();
  check("recalculated plan retains at least one feasible strategy", tray.includes("FEASIBLE") && !tray.includes("NO FEASIBLE OPTION"), tray);
  check("B3 is highlighted after reserve", await page.locator('[data-board-target-id="bed-07"]').getAttribute("data-highlighted") === "true");
  const deltas = page.locator(".tc-metric-changes");
  await deltas.scrollIntoViewIfNeeded();
  check("calculated deltas are visible", await deltas.isVisible(), await deltas.innerText());
  check("reserve and recalculation make no provider request", providerMutations.length === 0, providerMutations);

  await page.getByRole("button", { name: "Ask why" }).click();
  check("opening Ask Why makes no provider request", providerMutations.length === 0, providerMutations);
  check("Ask dialog keeps card context visible", await page.getByRole("dialog", { name: "Ask why" }).isVisible()
    && (await page.locator(".tc-ask-card").innerText()).includes("bed-07"));
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "Undo" }).click();
  await page.locator(".tc-action-dock--progress").waitFor({ timeout: 10_000 });
  await page.getByRole("button", { name: "Reserve space" }).waitFor({ timeout: 120_000 });
  check("inverse recalculation returns the constraint to the stack", await page.getByRole("button", { name: "Reserve space" }).isEnabled());
  check("full reserve/undo journey makes no automatic provider request", providerMutations.length === 0, providerMutations);

  await mkdir(resolve(root, "apps/web/screenshots"), { recursive: true });
  const screenshot = resolve(root, "apps/web/screenshots/v13-real-mobile-390.png");
  await page.screenshot({ path: screenshot, fullPage: true, animations: "disabled" });
  result.screenshots.push(screenshot.slice(root.length + 1));
  result.status = "PASS";
} catch (error) {
  result.status = "FAIL";
  result.failures.push(error instanceof Error ? error.stack : String(error));
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}
