import { describe, it, expect } from "vitest";
import {
  analyse,
  quality,
  cutoff,
  FRAMES,
  Frame,
  kraken,
  summarize,
} from "../src/mtf";
import cases from "./reference.generated.json";
describe("Python parity (80 deterministic cases)", () => {
  for (const c of cases)
    it(c.symbol + " " + c.timeframe + " " + c.name, () => {
      const out = analyse(c.raw, c.timeframe as Frame, c.now);
      expect(out.classification).toBe(c.expected.classification);
      expect(out.quality.status).toBe(c.expected.quality.status);
      for (const [name, a] of Object.entries(c.expected.agents)) {
        const actual = (out.agents as any)[name];
        expect(actual.signal).toBe(a.signal);
        for (const [key, value] of Object.entries(a.indicators))
          expect(Math.abs(actual.indicators[key] - value)).toBeLessThanOrEqual(
            1e-10 * Math.max(1, Math.abs(value)),
          );
      }
    });
});
const c = cases[0],
  tf = c.timeframe as Frame;
it.each([
  "empty",
  "duplicate",
  "unsorted",
  "gap",
  "nan",
  "ohlc",
  "stale",
  "grid",
  "short",
])("blocks bad data %s", (kind) => {
  const rows = c.raw.map((r) => [...r]);
  if (kind === "empty") rows.length = 0;
  if (kind === "short") rows.splice(0, 500);
  if (kind === "duplicate") rows[1][0] = rows[0][0];
  if (kind === "unsorted") rows.reverse();
  if (kind === "gap") rows.splice(2, 1);
  if (kind === "nan") rows[3][4] = NaN;
  if (kind === "ohlc") rows[3][2] = 0;
  if (kind === "stale") rows.pop();
  if (kind === "grid") rows[1][0]++;
  expect(analyse(rows, tf, c.now).classification).toBe("BLOCKIERT");
});
it("excludes running candle", () => {
  const rows = [...c.raw, [c.now, 1, 2, 1, 1, 1]];
  expect(quality(rows, tf, c.now).length).toBe(c.raw.length);
});
it("UTC boundaries", () => {
  for (const [tf, d] of Object.entries(FRAMES)) {
    expect(cutoff(tf as Frame, c.now + d - 1)).toBe(c.now);
    expect(cutoff(tf as Frame, c.now + d)).toBe(c.now + d);
  }
});
it("cross-window veto", () =>
  expect(summarize({ a: { classification: "POSITIV" } })).toBe("BLOCKIERT"));
it.each([
  new Response("{}", { status: 429 }),
  Response.json({ error: ["EGeneral:bad"] }),
  Response.json({ error: [], result: { X: [[1]] } }),
])("blocks Kraken malformed replies", async (response) => {
  await expect(
    kraken("BTC/EUR", "15m", async () => response),
  ).rejects.toThrow();
});
it("network disconnection", async () => {
  await expect(
    kraken("BTC/EUR", "15m", async () => {
      throw Error("offline");
    }),
  ).rejects.toThrow("offline");
});

it("reports numerical parity envelope", () => {
  let absolute = 0,
    relative = 0;
  for (const c of cases) {
    const result = analyse(c.raw, c.timeframe as Frame, c.now);
    for (const [name, a] of Object.entries(c.expected.agents))
      for (const [key, value] of Object.entries(a.indicators)) {
        const diff = Math.abs(
          (result.agents as any)[name].indicators[key] - value,
        );
        absolute = Math.max(absolute, diff);
        relative = Math.max(relative, diff / Math.max(1, Math.abs(value)));
      }
  }
  console.log(
    JSON.stringify({
      cases: cases.length,
      max_absolute: absolute,
      max_scaled_relative: relative,
      tolerance: 1e-10,
    }),
  );
  expect(relative).toBeLessThan(1e-10);
});
it("inactive or non-EUR market blocks before OHLC retrieval", async () => {
  let calls = 0;
  await expect(
    kraken("BTC/EUR", "1d", async () => {
      calls++;
      return Response.json({
        error: [],
        result: {
          PAIR: { status: "cancel_only", quote: "ZEUR", wsname: "XBT/EUR" },
        },
      });
    }),
  ).rejects.toThrow("nicht online");
  expect(calls).toBe(1);
});
