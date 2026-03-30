import { defineConfig, devices } from "@playwright/test";

const isDocker = ["1", "true"].includes(
  (process.env.E2E_DOCKER ?? "").toLowerCase(),
);
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ||
  (isDocker ? "http://localhost:13000" : "http://localhost:3000");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Docker E2E 환경에서는 서버가 이미 컨테이너로 기동됨 → webServer 비활성화
  ...(isDocker
    ? {}
    : {
        webServer: [
          {
            command:
              "cd ../backend && uv run uvicorn main:app --host 127.0.0.1 --port 8000",
            port: 8000,
            reuseExistingServer: !process.env.CI,
            timeout: 30000,
          },
          {
            command: "npm run dev",
            port: 3000,
            reuseExistingServer: !process.env.CI,
            timeout: 120000,
          },
        ],
      }),
});
