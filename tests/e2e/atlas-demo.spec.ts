import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const apiBaseUrl = process.env.ATLAS_E2E_API_URL || "http://127.0.0.1:8100";

async function resetDemo(request: APIRequestContext) {
  await request.post(`${apiBaseUrl}/api/demo/reset`);
}

async function seedDemo(request: APIRequestContext) {
  const response = await request.post(`${apiBaseUrl}/api/demo/seed`);
  expect(response.ok()).toBeTruthy();
}

async function seedDemoFromUi(page: Page) {
  await page.goto("/demo");
  await page.getByRole("button", { name: "Seed Demo" }).click();
  await expect(page.getByText("Generated Artifact", { exact: true })).toBeVisible();
}

test.beforeEach(async ({ request }) => {
  await resetDemo(request);
});

test.afterEach(async ({ request }) => {
  await resetDemo(request);
});

test("seed demo completes the golden path and shows artifact copy", async ({ page }) => {
  await seedDemoFromUi(page);

  await expect(page.getByRole("heading", { name: "One complete Atlas story" })).toBeVisible();
  await expect(page.getByText("Atlas auto-demo pack").first()).toBeVisible();
  await expect(
    page.getByText("Built Atlas, a personal AI operating system that unifies memory").first()
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Copy Resume Bullet" })).toBeVisible();
});

test("run next step advances an unseeded demo", async ({ page }) => {
  await page.goto("/demo");
  await page.getByRole("button", { name: "Run Next" }).click();

  await expect(page.getByText("Ran demo step: Upload resume and extract evidence.")).toBeVisible();
  await expect(page.getByText("Latest resume parsed from atlas-demo-resume.pdf.")).toBeVisible();
});

test("provider health page loads deterministic and external provider state", async ({ page }) => {
  await page.goto("/providers");

  await expect(page.getByRole("heading", { name: "Model and embedding health" })).toBeVisible();
  await expect(page.getByText("Deterministic fallback")).toBeVisible();
  await expect(page.getByText("OpenAI", { exact: true })).toBeVisible();
  await expect(page.getByText("Active embedding provider")).toBeVisible();
});

test("trace page shows generated demo trace", async ({ page, request }) => {
  await seedDemo(request);
  await page.goto("/traces");

  await expect(page.getByRole("heading", { name: "AI action observability" })).toBeVisible();
  await expect(page.getByText("Trace runs")).toBeVisible();
  await expect(page.getByText("approval:generate_auto_demo_pack")).toBeVisible();
});

test("action page shows approved auto-demo artifact", async ({ page, request }) => {
  await seedDemo(request);
  await page.goto("/actions");

  await expect(
    page.getByRole("heading", { name: "Tool actions with previews and audit logs" })
  ).toBeVisible();
  await expect(page.getByText("Atlas auto-demo pack").first()).toBeVisible();
  await expect(page.getByText("Approved outputs")).toBeVisible();
});

test("labs page shows systems proof tracks", async ({ page }) => {
  await page.goto("/labs");

  await expect(
    page.getByRole("heading", { name: "Systems proof for a recruiter-grade AI OS" })
  ).toBeVisible();
  await expect(page.getByText("Tiny Database From Scratch")).toBeVisible();
  await expect(page.getByText("Local Code Intelligence Engine")).toBeVisible();
  await expect(page.getByText("End-To-End ML Platform Lite")).toBeVisible();
  await expect(page.getByRole("heading", { name: "TinyAtlasDatabase" })).toBeVisible();
});
