import { defineConfig, devices } from "@playwright/test";

// E2E runs against the live compose stack on http://localhost:8088.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: [["list"], ["html", { open: "never", outputFolder: "report" }]],
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:8088",
    screenshot: "on",
    trace: "retain-on-failure",
    actionTimeout: 20_000,
    navigationTimeout: 40_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
