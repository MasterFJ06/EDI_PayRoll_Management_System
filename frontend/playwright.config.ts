import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./smoke-tests",
  fullyParallel: false,
  workers: 1,
  forbidOnly: true,
  retries: 0,
  reporter: "list",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.EPMS_SMOKE_WEB_BASE_URL || "http://127.0.0.1:5173",
    browserName: "chromium",
    headless: true,
    screenshot: "off",
    trace: "off",
    video: "off",
  },
});
