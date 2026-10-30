import { env } from "cloudflare:test";
import { it, expect } from "vitest";
import { tick, Env } from "../src/index";
import { FRAMES, Frame, SYMBOLS, cutoff } from "../src/mtf";
const e = env as unknown as Env,
  minute = 60000,
  midnight = Date.UTC(2026, 9, 30);
function exchange(at: number, lag = false): typeof fetch {
  return async (input) => {
    const u = new URL(String(input));
    if (u.pathname.endsWith("AssetPairs"))
      return Response.json({
        error: [],
        result: {
          PAIR: {
            status: "online",
            quote: "ZEUR",
            wsname: u.searchParams.get("pair")!.replace("EUR", "/EUR"),
          },
        },
      });
    const duration = Number(u.searchParams.get("interval")) * minute;
    const close =
      Math.floor(at / duration) * duration -
      (lag && duration === FRAMES["15m"] ? duration : 0);
    return Response.json({
      error: [],
      result: {
        PAIR: Array.from(
          { length: lag && duration === FRAMES["15m"] ? 300 : 301 },
          (_, i) => [
            (close - (300 - i) * duration) / 1000,
            "100",
            "101",
            "99",
            "100",
            "100",
            "10",
            1,
          ],
        ),
      },
    });
  };
}
async function count(tf: Frame, close: number) {
  return (
    await e.DB.prepare(
      "SELECT COUNT(*) n FROM jobs WHERE timeframe=? AND candle_close=? AND status='OK'",
    )
      .bind(tf, close)
      .first<any>()
  ).n;
}
it.each([0, 4, 12])(
  "advancing UTC collision at %sh completes every new combination and both 15m closes",
  async (hour) => {
    const start = midnight + hour * 3600000;
    // First observer establishes coverage; no invented pre-start completion.
    for (let i = -1; i <= 20; i++) {
      const at = start + i * minute;
      await tick(e, at, exchange(at), at);
    }
    for (const tf of Object.keys(FRAMES) as Frame[])
      expect(await count(tf, cutoff(tf, start))).toBe(4);
    expect(await count("15m", start + 15 * minute)).toBe(4);
    expect(
      (
        await e.DB.prepare(
          "SELECT COUNT(*) n FROM coverage_gaps WHERE first_close>=?",
        )
          .bind(start)
          .first<any>()
      ).n,
    ).toBe(0);
    const runs = await e.DB.prepare(
      "SELECT candle_close,started,timeframe FROM runs WHERE status='OK' AND candle_close>=?",
    )
      .bind(start)
      .all<any>();
    for (const r of runs.results)
      expect(r.started).toBeLessThan(
        r.candle_close + FRAMES[r.timeframe as Frame],
      );
  },
);
it("two delayed ticks still finish the midnight set before their deadlines", async () => {
  for (let i = 0; i <= 23; i++) {
    if (i === 1 || i === 2) continue;
    const at = midnight + i * minute;
    await tick(e, at - 2 * minute, exchange(at), at);
  }
  for (const tf of Object.keys(FRAMES) as Frame[])
    expect(await count(tf, midnight)).toBe(4);
  expect(await count("15m", midnight + 15 * minute)).toBe(4);
  expect(
    (await e.DB.prepare("SELECT COUNT(*) n FROM coverage_gaps").first<any>()).n,
  ).toBe(0);
});
it("API lag across close produces explicit MISSED coverage, not historical fills", async () => {
  for (let i = 0; i <= 20; i++) {
    const at = midnight + i * minute;
    await tick(e, at, exchange(at, i < 15), at);
  }
  expect(await count("15m", midnight)).toBe(0);
  expect(await count("15m", midnight + 15 * minute)).toBe(4);
  const gaps = await e.DB.prepare(
    "SELECT * FROM coverage_gaps WHERE timeframe='15m' AND first_close=?",
  )
    .bind(midnight)
    .all<any>();
  expect(gaps.results).toHaveLength(4);
  expect(gaps.results.every((r) => r.missing_count === 1)).toBe(true);
});
it("outage ranges are bounded, durable and idempotent across observers", async () => {
  await tick(e, midnight, exchange(midnight), midnight);
  const later = midnight + 3 * 3600000;
  await Promise.all([
    tick(e, later, exchange(later), later),
    tick(e, later, exchange(later), later),
  ]);
  const rows = await e.DB.prepare(
    "SELECT * FROM coverage_gaps WHERE timeframe='15m'",
  ).all<any>();
  expect(rows.results).toHaveLength(4);
  expect(rows.results.reduce((n, r) => n + r.missing_count, 0)).toBe(47); // 12*4, one actual success
});
it("brief boundary API lag retries before less urgent daily work", async () => {
  for (let i = 0; i <= 20; i++) {
    const at = midnight + i * minute;
    await tick(e, at, exchange(at, i === 0), at);
  }
  expect(await count("15m", midnight)).toBe(4);
  expect(
    (
      await e.DB.prepare(
        "SELECT COUNT(*) n FROM coverage_gaps WHERE first_close=?",
      )
        .bind(midnight)
        .first<any>()
    ).n,
  ).toBe(0);
});
it("permanent 15m faults have bounded retries and do not starve longer windows", async () => {
  for (let i = 0; i <= 60; i++) {
    const at = midnight + i * minute;
    await tick(e, at, exchange(at, true), at);
  }
  for (const tf of ["1h", "4h", "1d"] as Frame[])
    expect(await count(tf, midnight)).toBe(4);
  const attempts = await e.DB.prepare(
    "SELECT MAX(attempts) n FROM jobs WHERE timeframe='15m'",
  ).first<any>();
  expect(attempts.n).toBe(2);
});
