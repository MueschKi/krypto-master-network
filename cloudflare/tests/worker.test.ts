import { env } from "cloudflare:test";
import { it, expect } from "vitest";
import { handle, tick, authorized, Env } from "../src/index";
import { FRAMES } from "../src/mtf";
const e = env as unknown as Env;
const now = 1793232000000;
const auth = { ...e, AUTH_USER: "owner", AUTH_PASSWORD: "x".repeat(40) };
const request = (path: string, method = "GET") =>
  new Request("https://example.test" + path, {
    method,
    headers: { Authorization: "Basic " + btoa("owner:" + auth.AUTH_PASSWORD) },
  });
const valid: typeof fetch = async (input) => {
  const url = new URL(String(input));
  if (url.pathname.endsWith("AssetPairs")) {
    const pair = url.searchParams.get("pair")!;
    return Response.json({
      error: [],
      result: {
        PAIR: {
          status: "online",
          quote: "ZEUR",
          wsname: pair.replace("EUR", "/EUR"),
        },
      },
    });
  }
  const tf =
    Number(new URL(String(input)).searchParams.get("interval")) * 60000;
  return Response.json({
    error: [],
    result: {
      PAIR: Array.from({ length: 300 }, (_, i) => [
        ((Math.floor(now / tf) - 300 + i) * tf) / 1000,
        "100",
        "101",
        "99",
        "100",
        "100",
        "10",
        1,
      ]),
    },
  });
};
it("denies UI, portfolio, control and assets without authentication", async () => {
  for (const path of ["/", "/app.js", "/api/accounts", "/api/control"])
    expect(
      (await handle(new Request("https://example.test" + path), e)).status,
    ).toBe(401);
});
it("fails closed for short passwords and insecure transport", async () => {
  expect(
    await authorized(request("/"), { ...auth, AUTH_PASSWORD: "short" }),
  ).toBe(false);
  expect(await authorized(new Request("http://example.test"), auth)).toBe(
    false,
  );
});
it("read-only, no-store API and no control endpoints", async () => {
  expect((await handle(request("/api/accounts", "POST"), auth)).status).toBe(
    405,
  );
  const r = await handle(request("/api/accounts"), auth);
  expect(r.status).toBe(200);
  expect(r.headers.get("Cache-Control")).toBe("no-store");
  expect((await handle(request("/api/control"), auth)).status).toBe(404);
});
it("persists all 16 units, duplicates do not republish", async () => {
  for (let i = 0; i < 17; i++) await tick(e, now, valid, now);
  expect(
    (await e.DB.prepare("SELECT COUNT(*) n FROM analyses").first<any>()).n,
  ).toBe(16);
  expect(
    (
      await e.DB.prepare(
        "SELECT COUNT(*) n FROM runs WHERE status='IDLE'",
      ).first<any>()
    ).n,
  ).toBe(1);
  for (const tf of Object.keys(FRAMES))
    expect(
      (
        await e.DB.prepare("SELECT COUNT(*) n FROM analyses WHERE timeframe=?")
          .bind(tf)
          .first<any>()
      ).n,
    ).toBe(4);
});
it("concurrent duplicate claims are safe", async () => {
  await Promise.all([tick(e, now, valid, now), tick(e, now, valid, now)]);
  expect(
    (await e.DB.prepare("SELECT COUNT(*) n FROM analyses").first<any>()).n,
  ).toBe(1);
});
it("late events are logged, not replayed", async () => {
  await tick(e, now - 360000, valid, now);
  expect(
    (await e.DB.prepare("SELECT status FROM runs").first<any>()).status,
  ).toBe("ERROR");
  expect(
    (await e.DB.prepare("SELECT COUNT(*) n FROM analyses").first<any>()).n,
  ).toBe(0);
});
it("network failure persisted, cooldown then successful retry", async () => {
  for (let i = 0; i < 16; i++) await tick(e, now, valid, now);
  await e.DB.prepare(
    "DELETE FROM jobs WHERE symbol='BTC/EUR' AND timeframe='15m'",
  ).run();
  await tick(
    e,
    now,
    async () => {
      throw Error("offline");
    },
    now,
  );
  expect(
    (
      await e.DB.prepare(
        "SELECT status FROM jobs WHERE symbol='BTC/EUR' AND timeframe='15m'",
      ).first<any>()
    ).status,
  ).toBe("BLOCKED");
  await e.DB.prepare(
    "UPDATE jobs SET lease_until=0 WHERE status='BLOCKED'",
  ).run();
  await tick(e, now, valid, now);
  expect(
    (
      await e.DB.prepare(
        "SELECT status FROM jobs WHERE symbol='BTC/EUR' AND timeframe='15m'",
      ).first<any>()
    ).status,
  ).toBe("OK");
});
it("stale market never gets a positive classification", async () => {
  await tick(e, now, valid, now);
  const r = await handle(request("/api/markets"), auth);
  const data = (await r.json()) as any;
  expect(data.assets.every((a: any) => a.classification === "BLOCKIERT")).toBe(
    true,
  );
});
it("D1 transaction rolls back on invalid account import", async () => {
  await expect(
    e.DB.batch([
      e.DB.prepare(
        "INSERT INTO account_snapshots VALUES('master7','utc','sha','{}')",
      ),
      e.DB.prepare(
        "INSERT INTO account_snapshots VALUES('invalid','utc','sha','{}')",
      ),
    ]),
  ).rejects.toThrow();
  expect(
    (
      await e.DB.prepare(
        "SELECT COUNT(*) n FROM account_snapshots",
      ).first<any>()
    ).n,
  ).toBe(0);
});
it("scheduled handler runs via waitUntil independently of browser", async () => {
  const {
    createScheduledController,
    createExecutionContext,
    waitOnExecutionContext,
  } = await import("cloudflare:test");
  const { default: worker } = await import("../src/index");
  const ctx = createExecutionContext();
  worker.scheduled(
    createScheduledController({
      scheduledTime: Date.now() - 360000,
      cron: "* * * * *",
    }),
    e,
    ctx,
  );
  await waitOnExecutionContext(ctx);
  expect(
    (await e.DB.prepare("SELECT status FROM runs").first<any>()).status,
  ).toBe("ERROR");
});
it("persists raw candles and calculation atomically", async () => {
  await tick(e, now, valid, now);
  const bars = await e.DB.prepare(
    "SELECT payload FROM raw_candles ORDER BY open_utc",
  ).all<any>();
  expect(bars.results).toHaveLength(300);
  expect(
    (await e.DB.prepare("SELECT COUNT(*) n FROM candle_batches").first<any>())
      .n,
  ).toBe(0);
  expect(
    (await e.DB.prepare("SELECT COUNT(*) n FROM analyses").first<any>()).n,
  ).toBe(1);
});
it("authenticated static UI is served through the same guard", async () => {
  const r = await handle(request("/"), auth);
  expect(r.status).toBe(200);
  expect(await r.text()).toContain("Krypto Master Network");
  expect(r.headers.get("Cache-Control")).toBe("no-store");
});
it("database failure returns 503 without data", async () => {
  const r = await handle(request("/api/status"), {
    ...auth,
    DB: {
      prepare() {
        throw Error("database disconnected");
      },
    } as unknown as D1Database,
  });
  expect(r.status).toBe(503);
  expect(await r.text()).toContain("gesperrt");
});
it("expired claim is recoverable", async () => {
  for (let i = 0; i < 16; i++) await tick(e, now, valid, now);
  await e.DB.prepare(
    "UPDATE jobs SET owner='dead-worker',status='RUNNING',lease_until=0 WHERE symbol='BTC/EUR' AND timeframe='15m'",
  ).run();
  await tick(e, now, valid, now);
  const job = await e.DB.prepare(
    "SELECT * FROM jobs WHERE symbol='BTC/EUR' AND timeframe='15m'",
  ).first<any>();
  expect(job.owner).not.toBe("dead-worker");
  expect(job.status).toBe("OK");
});
it("exposes the non-secret Cloudflare build version without asserting live quotas", async () => {
  const r = await handle(request("/api/status"), {
    ...auth,
    CF_VERSION_METADATA: { id: "12345678-1234-4234-8234-123456789abc" },
  });
  const body = (await r.json()) as any;
  expect(body.build_id).toBe("12345678-1234-4234-8234-123456789abc");
  expect(body.free_tier_verified).toBe(false);
});
