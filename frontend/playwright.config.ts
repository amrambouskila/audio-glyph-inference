import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  reporter: "list",
  // The first page.goto blocks on Vite's cold dependency pre-bundle (three, drei,
  // chart.js). On a cold node_modules/.vite the default 30s per-test timeout loses
  // that race roughly half the time; the worst cold run measured 35.1s locally, and
  // constraining to 4 logical CPUs (ubuntu-latest's vCPU count) tripled per-test time.
  timeout: 180_000,
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 5320 --strictPort",
    url: "http://127.0.0.1:5320",
    reuseExistingServer: false,
    timeout: 60_000
  },
  use: {
    baseURL: "http://127.0.0.1:5320",
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 720 } }
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Pixel 7"] }
    }
  ]
});
