import { defineConfig, devices } from "@playwright/test";

const apiPort = 8100;
const webPort = 3100;
const apiBaseUrl = `http://127.0.0.1:${apiPort}`;
const webBaseUrl = `http://localhost:${webPort}`;

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 45_000,
  expect: {
    timeout: 8_000
  },
  fullyParallel: false,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: webBaseUrl,
    trace: "on-first-retry"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ],
  webServer: [
    {
      command:
        "mkdir -p .tmp && rm -f .tmp/e2e-atlas.sqlite3 && " +
        "ATLAS_STORAGE_PATH=.tmp/e2e-atlas.sqlite3 " +
        `ATLAS_CORS_ORIGINS='[\"${webBaseUrl}\"]' ` +
        `.venv/bin/uvicorn atlas_api.main:app --port ${apiPort}`,
      cwd: "apps/api",
      url: `${apiBaseUrl}/healthz`,
      timeout: 120_000,
      reuseExistingServer: false
    },
    {
      command:
        `PORT=${webPort} NEXT_PUBLIC_API_BASE_URL=${apiBaseUrl} ` +
        "npm --workspace apps/web run dev",
      url: webBaseUrl,
      timeout: 120_000,
      reuseExistingServer: false
    }
  ]
});
