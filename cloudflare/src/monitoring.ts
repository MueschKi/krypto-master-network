import type { Env } from "./types";
import { cutoff, FRAMES, Frame, SYMBOLS } from "./mtf";
export const WARN_BYTES = 250_000_000;
export const STOP_BYTES = 350_000_000;
// Reserve for one bounded transaction + concurrent HTTP/operational overhead.
export const WRITE_HEADROOM = 2_000_000;
export function storageState(bytes: unknown) {
  if (typeof bytes !== "number" || !Number.isSafeInteger(bytes) || bytes <= 0)
    return "UNKNOWN" as const;
  return bytes >= STOP_BYTES - WRITE_HEADROOM
    ? ("STOP" as const)
    : bytes >= WARN_BYTES
      ? ("WARN" as const)
      : ("OK" as const);
}
export function errorClass(err: unknown) {
  const message = err instanceof Error ? err.message : "";
  if (/429|rate limit|throttl/i.test(message)) return "KRAKEN_RATE_LIMIT";
  if (/STORAGE_STOP/.test(message)) return "STORAGE_STOP";
  if (/STORAGE_LEASE/.test(message)) return "STORAGE_LEASE_EXPIRED";
  if (/D1_INVOCATION_BUDGET/.test(message)) return "D1_INVOCATION_BUDGET";
  if (/CANDLE_CONFLICT/.test(message)) return "CANDLE_CONFLICT";
  if (/timeout|abort/i.test(message)) return "TIMEOUT";
  if (/Kraken.*HTTP 5\d\d/.test(message)) return "KRAKEN_SERVER";
  if (/Kraken.*HTTP/.test(message)) return "KRAKEN_HTTP";
  if (/Kraken/.test(message)) return "KRAKEN_RESPONSE";
  if (/VERSPAETET/.test(message)) return "LATE_TICK";
  return "DEPENDENCY_FAILURE";
}
export function instrument(db: D1Database) {
  const costs = {
    api_calls: 0,
    statements: 0,
    rows_read: 0,
    rows_written: 0,
    complete: true,
  };
  function call() {
    if (costs.api_calls >= 45) throw Error("D1_INVOCATION_BUDGET");
    costs.api_calls++;
  }
  function record(results: D1Result[]) {
    for (const r of results) {
      if (
        !Number.isFinite(r.meta?.rows_read) ||
        !Number.isFinite(r.meta?.rows_written)
      )
        costs.complete = false;
      costs.rows_read += r.meta?.rows_read ?? 0;
      costs.rows_written += r.meta?.rows_written ?? 0;
    }
  }
  function statement(s: D1PreparedStatement): D1PreparedStatement {
    return new Proxy(s, {
      get(target, key) {
        if (key === "bind")
          return (...args: unknown[]) => statement(target.bind(...args));
        if (key === "all" || key === "run")
          return async () => {
            call();
            costs.statements++;
            try {
              const r = await target[key]();
              record([r]);
              return r;
            } catch (err) {
              costs.complete = false;
              throw err;
            }
          };
        if (key === "first")
          return async (column?: string) => {
            call();
            costs.statements++;
            try {
              const r = await target.all<Record<string, unknown>>();
              record([r]);
              const first = r.results[0];
              return column ? (first?.[column] ?? null) : (first ?? null);
            } catch (err) {
              costs.complete = false;
              throw err;
            }
          };
        const v = Reflect.get(target, key);
        return typeof v === "function" ? v.bind(target) : v;
      },
    });
  }
  const tracked = new Proxy(db, {
    get(target, key) {
      if (key === "prepare")
        return (sql: string) => statement(target.prepare(sql));
      if (key === "batch")
        return async (s: D1PreparedStatement[]) => {
          call();
          costs.statements += s.length;
          try {
            const r = await target.batch(s);
            record(r);
            return r;
          } catch (err) {
            costs.complete = false;
            throw err;
          }
        };
      const v = Reflect.get(target, key);
      return typeof v === "function" ? v.bind(target) : v;
    },
  });
  return { db: tracked, costs };
}
export async function storageProbe(db: D1Database) {
  // Cloudflare documents meta.size_after in bytes. Do not substitute walltime,
  // estimated payload lengths, PRAGMA support or a previous in-memory sample.
  const r = await db.prepare("SELECT id FROM storage_guard WHERE id=1").all();
  if (r.results.length !== 1) throw Error("STORAGE_SCHEMA_INCOMPLETE");
  return { bytes: r.meta.size_after, state: storageState(r.meta.size_after) };
}
export async function diagnostics(e: Env, now: number) {
  const tracked = instrument(e.DB),
    db = tracked.db;
  let storage: Record<string, unknown> = {
    state: "UNKNOWN",
    bytes: null,
    growth_bytes_per_day: null,
  };
  try {
    const probe = await storageProbe(db);
    const sample = await db
      .prepare(
        "SELECT measured_bytes,measured_at,previous_bytes,previous_at FROM storage_guard WHERE id=1",
      )
      .first<any>();
    const dt = sample?.measured_at - sample?.previous_at;
    storage = {
      state: probe.state,
      bytes: probe.state === "UNKNOWN" ? null : probe.bytes,
      source: "D1.meta.size_after",
      warn_bytes: WARN_BYTES,
      stop_bytes: STOP_BYTES,
      write_headroom_bytes: WRITE_HEADROOM,
      measured_at: now,
      trend_sampled_at: sample?.measured_at ?? null,
      growth_bytes_per_day:
        dt > 0 && Number.isFinite(sample.previous_bytes)
          ? ((sample.measured_bytes - sample.previous_bytes) * 86400000) / dt
          : null,
    };
  } catch {
    /* Partial migration or unavailable metadata: no fictitious green. */
  }
  const pairs = SYMBOLS.flatMap((s) =>
    Object.keys(FRAMES).map((tf) => `('${s}','${tf}')`),
  ).join(",");
  const rows = await db
    .prepare(
      `WITH pairs(symbol,timeframe) AS (VALUES ${pairs})
    SELECT a.symbol,a.timeframe,a.candle_close,a.payload FROM pairs p JOIN analyses a
    ON a.symbol=p.symbol AND a.timeframe=p.timeframe AND a.candle_close=
    (SELECT MAX(b.candle_close) FROM analyses b WHERE b.symbol=p.symbol AND b.timeframe=p.timeframe)`,
    )
    .all<{
      symbol: string;
      timeframe: Frame;
      candle_close: number;
      payload: string;
    }>();
  const windows = SYMBOLS.flatMap((symbol) =>
    (Object.keys(FRAMES) as Frame[]).map((timeframe) => {
      const row = rows.results.find(
        (r) => r.symbol === symbol && r.timeframe === timeframe,
      );
      let ok = false;
      try {
        ok = JSON.parse(row?.payload ?? "{}").quality?.status === "OK";
      } catch {
        /* Block invalid stored JSON. */
      }
      return {
        symbol,
        timeframe,
        missing: !row,
        stale: !row || row.candle_close !== cutoff(timeframe, now),
        quality: ok ? "OK" : "BLOCKED",
      };
    }),
  );
  return {
    storage,
    windows,
    missing_windows: windows.filter((w) => w.missing).length,
    blocked_or_stale: windows.filter((w) => w.stale || w.quality !== "OK")
      .length,
    d1: tracked.costs,
    cpu_ms: null,
    daily_quota_remaining: null,
    free_tier_verified: false,
    pruning_enabled: false,
  };
}
