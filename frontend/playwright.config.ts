import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  reporter: "list",
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
