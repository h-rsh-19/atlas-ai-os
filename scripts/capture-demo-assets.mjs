import { chromium } from "@playwright/test";
import { mkdir, rename, rm } from "node:fs/promises";
import path from "node:path";

const baseUrl = process.env.ATLAS_SCREENSHOT_BASE_URL || "http://localhost:3000";
const apiBaseUrl = process.env.ATLAS_SCREENSHOT_API_BASE_URL || "http://127.0.0.1:8000";
const outputDir = path.resolve("docs/screenshots");
const screenshots = [
  ["/demo", "01-demo-flow.png"],
  ["/providers", "02-providers.png"],
  ["/traces", "03-traces.png"],
  ["/code", "04-code-intelligence.png"],
  ["/actions", "05-actions.png"]
];

async function waitForPage(page) {
  await page.waitForLoadState("load");
  await page.waitForTimeout(1200);
}

async function goto(page, route) {
  await page.goto(`${baseUrl}${route}`);
  await waitForPage(page);
}

async function seedDemo(page) {
  const reset = await fetch(`${apiBaseUrl}/api/demo/reset`, { method: "POST" });
  if (!reset.ok) {
    throw new Error(`Demo reset failed with ${reset.status}`);
  }
  const seed = await fetch(`${apiBaseUrl}/api/demo/seed`, { method: "POST" });
  if (!seed.ok) {
    throw new Error(`Demo seed failed with ${seed.status}`);
  }
  await goto(page, "/demo");
  await page.getByText("Generated Artifact", { exact: true }).waitFor({ timeout: 20_000 });
}

async function captureScreenshots(browser) {
  const context = await browser.newContext({
    deviceScaleFactor: 1,
    viewport: { width: 1440, height: 1000 }
  });
  const page = await context.newPage();
  await seedDemo(page);

  for (const [route, filename] of screenshots) {
    await goto(page, route);
    await page.screenshot({
      path: path.join(outputDir, filename),
      fullPage: true
    });
  }

  await context.close();
}

async function captureVideo(browser) {
  const videoDir = path.join(outputDir, "video-temp");
  const target = path.join(outputDir, "atlas-demo-walkthrough.webm");
  await rm(videoDir, { force: true, recursive: true });
  await rm(target, { force: true });

  const context = await browser.newContext({
    recordVideo: {
      dir: videoDir,
      size: { width: 1440, height: 900 }
    },
    viewport: { width: 1440, height: 900 }
  });
  const page = await context.newPage();

  await goto(page, "/demo");
  await page.waitForTimeout(8_000);
  await page.getByRole("button", { name: "Open Artifact" }).click();
  await page.waitForTimeout(8_000);
  await goto(page, "/providers");
  await page.waitForTimeout(10_000);
  await goto(page, "/traces");
  await page.waitForTimeout(10_000);
  await goto(page, "/code");
  await page.waitForTimeout(10_000);
  await goto(page, "/actions");
  await page.waitForTimeout(10_000);
  await goto(page, "/demo");
  await page.waitForTimeout(8_000);

  const video = page.video();
  await context.close();
  if (!video) {
    throw new Error("Playwright did not produce a video handle.");
  }
  await rename(await video.path(), target);
  await rm(videoDir, { force: true, recursive: true });
}

await mkdir(outputDir, { recursive: true });
const browser = await chromium.launch();
try {
  await captureScreenshots(browser);
  await captureVideo(browser);
} finally {
  await browser.close();
}

console.log(`Captured screenshots and video in ${outputDir}`);
