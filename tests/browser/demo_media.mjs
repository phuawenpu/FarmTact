import { chromium } from "../../apps/web/node_modules/@playwright/test/index.mjs";

const base = (process.env.BASE_URL || "http://127.0.0.1:8080").replace(/\/$/, "");
const report = { base_url: base, checks: [], failures: [] };
const check = (name, pass, detail) => {
  report.checks.push({ name, pass: Boolean(pass), detail });
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`);
};

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    reducedMotion: "no-preference",
  });
  await context.addInitScript(() => localStorage.clear());
  const page = await context.newPage();
  const providerMutations = [];
  page.on("request", (request) => {
    if (
      request.method() !== "GET" &&
      /conversations|planning-sessions\/.+\/review/.test(request.url())
    ) providerMutations.push([request.method(), request.url()]);
  });

  await page.goto(base, { waitUntil: "domcontentloaded" });
  await page.locator(".decision-demo").waitFor();
  const demo = page.locator(".decision-demo");
  await demo.getByRole("button", { name: "Pause", exact: true }).click();
  const first = await demo.locator(".decision-demo-scene h3").textContent();
  await demo.getByRole("button", { name: "Next scene", exact: true }).click();
  const second = await demo.locator(".decision-demo-scene h3").textContent();
  await demo.getByRole("button", { name: "Previous", exact: true }).click();
  check(
    "first-use Demo supports pause, next and back",
    first && second && first !== second &&
      (await demo.locator(".decision-demo-scene h3").textContent()) === first,
    { first, second },
  );
  await demo.getByRole("button", { name: "Skip demo", exact: true }).click();
  check("first-use Demo can be skipped", (await page.locator(".decision-demo").count()) === 0);
  await page.getByRole("button", { name: "Replay demo", exact: true }).click();
  check("first-use Demo replay reopens at scene one", await demo.getByText("30-second introduction · 1 of 4").isVisible());
  await demo.getByRole("button", { name: "Skip demo", exact: true }).click();

  await page.getByRole("button", { name: /How it works/ }).click();
  const guide = page.getByRole("dialog", { name: "Three short guides" });
  const videos = guide.locator("video");
  check("three prerecorded guides are linked", (await videos.count()) === 3);
  for (let index = 0; index < 3; index += 1) {
    const result = await videos.nth(index).evaluate(async (video) => {
      if (video.readyState < 1)
        await new Promise((resolve, reject) => {
          video.addEventListener("loadedmetadata", resolve, { once: true });
          video.addEventListener("error", () => reject(new Error("media error")), { once: true });
          video.load();
        });
      await video.play();
      video.currentTime = Math.min(6, Math.max(0, video.duration - 1));
      await new Promise((resolve) => video.addEventListener("seeked", resolve, { once: true }));
      const value = {
        duration: video.duration,
        currentTime: video.currentTime,
        poster: video.getAttribute("poster"),
        caption: video.querySelector('track[kind="captions"]')?.getAttribute("src"),
        source: video.querySelector("source")?.getAttribute("src"),
      };
      video.pause();
      return value;
    });
    check(`guide ${index + 1} loads, plays and seeks`, result.duration >= 47 && result.currentTime >= 5, result);
    check(`guide ${index + 1} has poster and captions`, Boolean(result.poster && result.caption), result);
  }
  await guide.getByText("Transcript", { exact: true }).first().click();
  const transcriptPayload = await page.evaluate(() => fetch("/explainers/transcripts.json").then((response) => response.json()));
  const expectedScenes = Object.values(transcriptPayload).flat();
  await page.waitForFunction(
    (count) => document.querySelectorAll(".explainer-transcript-scene").length === count,
    expectedScenes.length,
  );
  const renderedTranscript = await guide.locator(".explainer-transcript").allTextContents();
  check(
    "all declared transcript scenes render with exact text",
    expectedScenes.length > 0 && expectedScenes.every((scene) =>
      renderedTranscript.some((text) => text.includes(scene.title) && text.includes(scene.text))),
    { expected: expectedScenes.length, rendered: await guide.locator(".explainer-transcript-scene").count() },
  );
  const downloads = await guide.getByText("Download MP4", { exact: true }).evaluateAll((links) => links.map((link) => link.href));
  const responses = await Promise.all(downloads.map((url) => page.request.get(url)));
  check(
    "all download URLs return MP4 data",
    responses.every((response) => response.ok() && /video\/mp4/.test(response.headers()["content-type"] || "")),
    responses.map((response) => ({ status: response.status(), type: response.headers()["content-type"] })),
  );
  await page.getByRole("button", { name: /Close Three short guides/ }).click();

  await page.route("**/explainers/*.mp4", (route) => route.abort("failed"));
  await page.route("**/explainers/transcripts.json", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ "observe-decide": [] }) }),
  );
  await page.getByRole("button", { name: /How it works/ }).click();
  const failedGuide = page.getByRole("dialog", { name: "Three short guides" });
  await failedGuide.locator("video").first().evaluate((video) => video.load());
  await failedGuide.getByText("Transcript", { exact: true }).nth(1).click();
  await failedGuide.getByText(/full transcript is unavailable/i).waitFor();
  check(
    "failed video sources expose written fallbacks",
    (await failedGuide.getByText(/guide video is unavailable/i).count()) === 3 &&
      (await failedGuide.getByText("MP4 download unavailable", { exact: true }).count()) === 3,
  );
  check("valid transcript JSON with a missing guide reports unavailable", await failedGuide.getByText(/full transcript is unavailable/i).isVisible());
  await page.getByRole("button", { name: /Close Three short guides/ }).click();
  await page.unroute("**/explainers/transcripts.json");
  await page.route("**/explainers/transcripts.json", (route) => route.abort("failed"));
  await page.getByRole("button", { name: /How it works/ }).click();
  const transcriptFailure = page.getByRole("dialog", { name: "Three short guides" });
  await transcriptFailure.getByText("Transcript", { exact: true }).first().click();
  await transcriptFailure.getByText(/full transcript is unavailable/i).waitFor();
  check("failed transcript request exposes a written fallback", await transcriptFailure.getByText(/full transcript is unavailable/i).isVisible());
  check("media and Demo checks submit no provider requests", providerMutations.length === 0, providerMutations);
  report.status = "PASS";
} catch (error) {
  report.status = "FAIL";
  report.failures.push(error instanceof Error ? error.stack : String(error));
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  console.log(JSON.stringify(report, null, 2));
}
