import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/mobile",
  webServer: {
    command: "python -m http.server 8790 --directory public",
    port: 8790,
  },
  use: { baseURL: "http://127.0.0.1:8790" },
  projects: [
    {
      name: "iphone",
      use: {
        browserName: "webkit",
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
    {
      name: "tablet",
      use: { browserName: "chromium", viewport: { width: 768, height: 1024 } },
    },
    {
      name: "desktop",
      use: { browserName: "chromium", viewport: { width: 1440, height: 1000 } },
    },
  ],
});
