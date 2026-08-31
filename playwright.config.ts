import { defineConfig, devices } from "@playwright/test";

const python = process.env.PERSONAL_AI_OS_E2E_PYTHON || "python";

export default defineConfig({
  testDir: "e2e",
  outputDir: "output/playwright/test-results",
  timeout: 45_000,
  fullyParallel: false,
  reporter: process.env.CI ? [["github"], ["html", { outputFolder: "output/playwright/report", open: "never" }]] : "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
  webServer: [
    {
      command: `${python} scripts/e2e-api.py --data-dir output/playwright/e2e-data --port 8000`,
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 45_000,
    },
    {
      command: "pnpm --filter @personal-ai-os/web dev --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: false,
      timeout: 60_000,
      env: { NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000" },
    },
  ],
});
