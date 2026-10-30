import { test, expect } from "@playwright/test";
test("responsive UI, navigation and offline fail closed", async ({ page }) => {
  await page.route("**/api/**", (route) =>
    route.fulfill({ status: 503, body: "offline" }),
  );
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText("BLOCKIERT");
  await page.getByRole("link", { name: "Portfolio", exact: true }).click();
  await expect(page).toHaveURL(/#portfolio/);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator("#accounts")).toContainText("Anzeige gesperrt");
});
test("empty authenticated snapshots are explicit, no invented data", async ({
  page,
}) => {
  await page.route("**/api/**", (route) => {
    const p = new URL(route.request().url()).pathname;
    return route.fulfill({
      json: p.endsWith("status")
        ? { stale: true, version: "2.0.0-phase-a" }
        : p.endsWith("markets")
          ? { assets: [], snapshot_utc: "fixture" }
          : [],
    });
  });
  await page.goto("/");
  await expect(page.locator("#accounts")).toContainText("Nicht eingerichtet");
  await expect(page.locator("#system-data")).toContainText("OFFEN");
});

test("populated dashboard fits viewport and renders untrusted reasons as text", async ({
  page,
}) => {
  const frame = {
    classification: "NEUTRAL",
    quality: { reason: "Validierte Testfixture" },
    agents: {
      trend: {
        signal: "NEUTRAL",
        reason: "<img src=x onerror=alert(1)>",
        indicators: { ema200: 123456.12345 },
      },
    },
    stale: false,
    candle_close: 1793232000000,
    calculated: 1793232000000,
  };
  await page.route("**/api/**", (route) => {
    const p = new URL(route.request().url()).pathname;
    return route.fulfill({
      json: p.endsWith("status")
        ? { stale: false, version: "test" }
        : p.endsWith("markets")
          ? {
              snapshot_utc: "TESTFIXTURE",
              assets: ["BTC/EUR", "ETH/EUR", "SOL/EUR", "NEAR/EUR"].map(
                (symbol) => ({
                  symbol,
                  classification: "NEUTRAL",
                  timeframes: Object.fromEntries(
                    ["15m", "1h", "4h", "1d"].map((tf) => [tf, frame]),
                  ),
                }),
              ),
            }
          : [],
    });
  });
  await page.goto("/");
  await expect(page.locator(".frame")).toHaveCount(16);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator("#analysis img")).toHaveCount(0);
  await expect(page.locator("#analysis")).toContainText(
    "<img src=x onerror=alert(1)>",
  );
  await page.screenshot({
    path: "test-results/dashboard-" + test.info().project.name + ".png",
    fullPage: true,
  });
});

test("fresh heartbeat and old single-job success never imply complete MTF release", async ({
  page,
}) => {
  await page.route("**/api/**", (route) => {
    const p = new URL(route.request().url()).pathname;
    return route.fulfill({
      json: p.endsWith("status")
        ? {
            stale: false,
            heartbeat: { status: "BLOCKED" },
            last_success: { finished: 1793232000000 },
          }
        : p.endsWith("markets")
          ? { assets: [], snapshot_utc: "fixture" }
          : p.endsWith("gaps")
            ? [
                {
                  symbol: "BTC/EUR",
                  timeframe: "15m",
                  missing_count: 1,
                  first_close: 1793232000000,
                  last_close: 1793232000000,
                  observed: 1793232900000,
                },
              ]
            : [],
    });
  });
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText(
    "MTF BLOCKIERT / UNVOLLSTÄNDIG",
  );
  await expect(page.locator("#status")).toContainText("kein Gesamterfolg");
  await expect(page.locator("#runs")).toContainText("MISSED");
});
