import { env } from "cloudflare:test";
import { it, expect, vi } from "vitest";
import type { Env } from "../src/types";
import { tick, handle } from "../src/index";
import { candleInsert } from "../src/candles";
import { analyse, FRAMES, Frame, SYMBOLS } from "../src/mtf";
import {
  storageState,
  WARN_BYTES,
  STOP_BYTES,
  WRITE_HEADROOM,
  diagnostics,
  errorClass,
  instrument,
} from "../src/monitoring";
const e = env as unknown as Env,
  now = Date.UTC(2026, 9, 30);
function bars(tf: Frame) {
  const d = FRAMES[tf],
    close = Math.floor(now / d) * d;
  return Array.from({ length: 720 }, (_, i) => [
    close - (720 - i) * d,
    100,
    101,
    99,
    100,
    10,
  ]);
}
const exchange: typeof fetch = async (input) => {
  const u = new URL(String(input));
  return u.pathname.endsWith("AssetPairs")
    ? Response.json({
        error: [],
        result: {
          P: {
            status: "online",
            quote: "ZEUR",
            wsname: u.searchParams.get("pair")!.replace("EUR", "/EUR"),
          },
        },
      })
    : Response.json({
        error: [],
        result: {
          P: bars(
            (Object.keys(FRAMES) as Frame[]).find(
              (t) =>
                FRAMES[t] === Number(u.searchParams.get("interval")) * 60000,
            )!,
          ).map((r) => [r[0] / 1000, ...r.slice(1, 5), 100, r[5], 1]),
        },
      });
};
async function n(table: string) {
  return (await e.DB.prepare(`SELECT COUNT(*) n FROM ${table}`).first<any>()).n;
}
// Only replace the platform metadata, never add an application bypass.
function sized(bytes: unknown): Env {
  const db = new Proxy(e.DB, {
    get(db, key) {
      if (key === "prepare")
        return (sql: string) => {
          const s = db.prepare(sql);
          if (!sql.startsWith("SELECT id FROM storage_guard")) return s;
          return new Proxy(s, {
            get(target, k) {
              if (k === "all")
                return async () => {
                  const r = await target.all();
                  return { ...r, meta: { ...r.meta, size_after: bytes } };
                };
              const v = Reflect.get(target, k);
              return typeof v === "function" ? v.bind(target) : v;
            },
          });
        };
      const v = Reflect.get(db, key);
      return typeof v === "function" ? v.bind(db) : v;
    },
  });
  return { ...e, DB: db };
}
it.each([undefined, null, NaN, Infinity, -1, 0, "1000"])(
  "unknown size %s cannot authorize a write",
  async (size) => {
    expect(storageState(size)).toBe("UNKNOWN");
    const fetcher = vi.fn(exchange);
    await tick(sized(size), now, fetcher, now);
    expect(fetcher).not.toHaveBeenCalled();
    expect(await n("raw_candles")).toBe(0);
  },
);
it("uses decimal MB and conservative headroom", () => {
  expect(storageState(WARN_BYTES - 1)).toBe("OK");
  expect(storageState(WARN_BYTES)).toBe("WARN");
  expect(storageState(STOP_BYTES - WRITE_HEADROOM)).toBe("STOP");
  expect(storageState(STOP_BYTES)).toBe("STOP");
});
it.each([STOP_BYTES, STOP_BYTES + 1])(
  "stop at %s preserves audit and readable analysis",
  async (size) => {
    await tick(e, now, exchange, now);
    const before = await Promise.all(
      ["raw_candles", "runs", "analyses", "coverage_gaps"].map(n),
    );
    const fetcher = vi.fn(exchange);
    await tick(sized(size), now, fetcher, now);
    expect(fetcher).not.toHaveBeenCalled();
    expect(
      await Promise.all(
        ["raw_candles", "runs", "analyses", "coverage_gaps"].map(n),
      ),
    ).toEqual(before);
    const d = await diagnostics(sized(size), now);
    expect(d.storage.state).toBe("STOP");
    expect(d.windows).toHaveLength(16);
    expect(d.missing_windows).toBe(15);
  },
);
it("warning processes bounded unit without inventing CPU", async () => {
  await tick(sized(WARN_BYTES), now, exchange, now);
  const d = await diagnostics(sized(WARN_BYTES + 1000), now);
  expect(d.storage.state).toBe("WARN");
  expect(d.cpu_ms).toBeNull();
  expect(d.free_tier_verified).toBe(false);
  expect(await n("raw_candles")).toBe(720);
});
it("all 16 normalized windows retain exact indicator parity and idempotency", async () => {
  await e.DB.prepare("UPDATE storage_guard SET owner='test',lease_until=?")
    .bind(Date.now() + 60000)
    .run();
  for (const symbol of SYMBOLS)
    for (const tf of Object.keys(FRAMES) as Frame[]) {
      const raw = bars(tf);
      await candleInsert(e.DB, symbol, tf, raw, now, "test", Date.now()).run();
      await candleInsert(e.DB, symbol, tf, raw, now, "test", Date.now()).run();
      const stored = await e.DB.prepare(
        "SELECT payload FROM raw_candles WHERE symbol=? AND timeframe=? ORDER BY open_utc",
      )
        .bind(symbol, tf)
        .all<{ payload: string }>();
      expect(
        analyse(
          stored.results.map((r) => JSON.parse(r.payload)),
          tf,
          now,
        ),
      ).toEqual(analyse(raw, tf, now));
    }
  expect(await n("raw_candles")).toBe(16 * 720);
});
it("revised history rolls back publication without changing earlier evidence", async () => {
  await tick(e, now, exchange, now);
  const raw = bars("15m");
  raw[0][4] = 100.5;
  await e.DB.prepare("UPDATE storage_guard SET owner='test',lease_until=?")
    .bind(Date.now() + 60000)
    .run();
  await expect(
    e.DB.batch([
      candleInsert(e.DB, "BTC/EUR", "15m", raw, now, "test", Date.now()),
      e.DB.prepare(
        "INSERT INTO runs(id,scheduled,started,status) VALUES('partial',0,0,'OK')",
      ),
    ]),
  ).rejects.toThrow("CANDLE_CONFLICT");
  expect(await n("runs")).toBe(1);
  expect(await n("analyses")).toBe(1);
  expect(await n("raw_candles")).toBe(720);
});
it("late transaction failure rolls back; dead lease recovers; old owner cannot write", async () => {
  await e.DB.prepare(
    "UPDATE storage_guard SET owner='dead',lease_until=0",
  ).run();
  await tick(e, now, exchange, now);
  expect(await n("analyses")).toBe(1);
  await e.DB.prepare("UPDATE storage_guard SET owner='test',lease_until=?")
    .bind(Date.now() + 60000)
    .run();
  await expect(
    e.DB.batch([
      candleInsert(
        e.DB,
        "ETH/EUR",
        "15m",
        bars("15m"),
        now,
        "test",
        Date.now(),
      ),
      e.DB.prepare("INSERT INTO storage_guard(id) VALUES(2)"),
    ]),
  ).rejects.toThrow();
  await candleInsert(
    e.DB,
    "ETH/EUR",
    "15m",
    bars("15m"),
    now,
    "old-owner",
    Date.now(),
  ).run();
  expect(await n("raw_candles")).toBe(720);
});
it("partial migration fails closed, without clearing legacy history", async () => {
  await e.DB.prepare("DROP TABLE raw_candles").run();
  await tick(e, now, exchange, now);
  expect(await n("analyses")).toBe(0);
  expect(
    (await e.DB.prepare("SELECT status FROM runs").first<any>()).status,
  ).toBe("ERROR");
  await e.DB.prepare("DROP TABLE storage_guard").run();
  await tick(e, now, exchange, now);
  expect(await n("runs")).toBe(1);
  expect((await diagnostics(e, now)).storage.state).toBe("UNKNOWN");
});
it("429 and arbitrary dependency strings cannot leak secrets", async () => {
  const spy = vi.spyOn(console, "error");
  await tick(
    e,
    now,
    async () => new Response("private-secret", { status: 429 }),
    now,
  );
  expect(
    (await e.DB.prepare("SELECT error FROM runs").first<any>()).error,
  ).toBe("KRAKEN_RATE_LIMIT");
  expect(JSON.stringify(spy.mock.calls)).not.toContain("private-secret");
  spy.mockRestore();
  expect(errorClass(Error("token=private-secret"))).toBe("DEPENDENCY_FAILURE");
});
it("query budget reserves five calls; metadata is actual D1 data", async () => {
  const tracked = instrument(e.DB);
  for (let i = 0; i < 45; i++) await tracked.db.prepare("SELECT 1").all();
  await expect(tracked.db.prepare("SELECT 1").all()).rejects.toThrow(
    "D1_INVOCATION_BUDGET",
  );
  expect(tracked.costs.api_calls).toBe(45);
  expect(tracked.costs.complete).toBe(true);
});
it("diagnostics require auth and reveal no private account data", async () => {
  const auth = { ...e, AUTH_USER: "owner", AUTH_PASSWORD: "x".repeat(40) };
  expect(
    (await handle(new Request("https://example.test/api/diagnostics"), auth))
      .status,
  ).toBe(401);
  const r = await handle(
    new Request("https://example.test/api/diagnostics", {
      headers: {
        Authorization: "Basic " + btoa("owner:" + auth.AUTH_PASSWORD),
      },
    }),
    auth,
  );
  expect(r.status).toBe(200);
  const body = await r.text();
  expect(body).not.toContain(auth.AUTH_PASSWORD);
  expect(body).not.toContain("account_bundles");
});
it("30 daily collisions preserve all 16 rolling 720-bar indicator results", async () => {
  await e.DB.prepare("UPDATE storage_guard SET owner='model',lease_until=?")
    .bind(Date.now() + 300000)
    .run();
  for (let day = 0; day < 30; day++) {
    const at = now + day * 86400000;
    for (const symbol of SYMBOLS)
      for (const tf of Object.keys(FRAMES) as Frame[]) {
        const d = FRAMES[tf],
          close = Math.floor(at / d) * d;
        const raw = Array.from({ length: 720 }, (_, i) => {
          const ts = close - (720 - i) * d,
            c = 100 + Math.sin(ts / d / 13) * 2;
          return [ts, c, c + 1, c - 1, c, 10];
        });
        await candleInsert(
          e.DB,
          symbol,
          tf,
          raw,
          at,
          "model",
          Date.now(),
        ).run();
        const stored = await e.DB.prepare(
          "SELECT payload FROM raw_candles WHERE symbol=? AND timeframe=? ORDER BY open_utc DESC LIMIT 720",
        )
          .bind(symbol, tf)
          .all<{ payload: string }>();
        expect(
          analyse(
            stored.results.reverse().map((r) => JSON.parse(r.payload)),
            tf,
            at,
          ),
        ).toEqual(analyse(raw, tf, at));
      }
  }
}, 120000);
it("cold 720-bar unit remains within measured local D1 invocation budget", async () => {
  const spy = vi.spyOn(console, "log");
  await tick(e, now, exchange, now);
  const report = spy.mock.calls
    .map((c) => {
      try {
        return JSON.parse(String(c[0]));
      } catch {
        return {};
      }
    })
    .find((r) => r.event === "invocation");
  spy.mockRestore();
  expect(report.d1.api_calls).toBeLessThan(45);
  expect(report.d1.rows_written).toBeLessThan(800);
  expect(report.d1.rows_read).toBeLessThan(5000);
  expect(report.d1.complete).toBe(true);
  console.log(
    JSON.stringify({ benchmark: "local-720-bar", d1: report.d1, cpu_ms: null }),
  );
});
it("Kraken reports API rate limits over HTTP 200 without logging the body", async () => {
  await tick(
    e,
    now,
    async () =>
      Response.json({ error: ["EAPI:Rate limit exceeded private-value"] }),
    now,
  );
  expect(
    (await e.DB.prepare("SELECT error FROM runs").first<any>()).error,
  ).toBe("KRAKEN_RATE_LIMIT");
});
it("an invalidated publication fence rolls back even an earlier candle insert", async () => {
  await e.DB.prepare("UPDATE storage_guard SET owner='old',lease_until=?")
    .bind(Date.now() + 60000)
    .run();
  await expect(
    e.DB.batch([
      candleInsert(e.DB, "BTC/EUR", "15m", bars("15m"), now, "old", Date.now()),
      e.DB.prepare(
        "INSERT INTO storage_guard(id) SELECT 2 WHERE NOT EXISTS(SELECT 1 FROM storage_guard WHERE id=1 AND owner='replacement')",
      ),
    ]),
  ).rejects.toThrow();
  expect(await n("raw_candles")).toBe(0);
  expect(await n("analyses")).toBe(0);
});
