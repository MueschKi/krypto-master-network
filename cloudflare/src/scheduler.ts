import { analyse, cutoff, FRAMES, Frame, kraken, SYMBOLS } from "./mtf";
import type { Env } from "./types";
export async function tick(
  e: Env,
  scheduled: number,
  fetcher: typeof fetch = fetch,
  now = Date.now(),
) {
  const id = crypto.randomUUID(),
    start = Date.now();
  await e.DB.prepare(
    "INSERT INTO runs(id,scheduled,started,status) VALUES(?,?,?,?)",
  )
    .bind(id, scheduled, now, "RUNNING")
    .run();
  try {
    if (scheduled > now + 60000 || now - scheduled > 300000)
      throw Error("VERSPAETET: Takt nicht nachgerechnet");
    const jobs = await e.DB.prepare("SELECT * FROM jobs WHERE candle_close>=?")
      .bind(cutoff("1d", now))
      .all<{
        symbol: string;
        timeframe: Frame;
        candle_close: number;
        lease_until: number;
        status: string;
      }>();
    const units = Object.keys(FRAMES)
      .reverse()
      .flatMap((tf) =>
        SYMBOLS.map((symbol) => ({
          symbol,
          tf: tf as Frame,
          close: cutoff(tf as Frame, now),
        })),
      );
    const unit = units.find(
      (u) =>
        !jobs.results.some(
          (j) =>
            j.symbol === u.symbol &&
            j.timeframe === u.tf &&
            j.candle_close === u.close &&
            (j.status === "OK" || j.lease_until > now),
        ),
    );
    if (!unit) {
      await e.DB.prepare(
        "UPDATE runs SET status='IDLE',finished=?,elapsed_ms=? WHERE id=?",
      )
        .bind(Date.now(), Date.now() - start, id)
        .run();
      return;
    }
    const { symbol, tf, close } = unit;
    const claim = await e.DB.prepare(
      `INSERT INTO jobs VALUES(?,?,?,?,?,'RUNNING') ON CONFLICT(symbol,timeframe,candle_close) DO UPDATE SET owner=excluded.owner,lease_until=excluded.lease_until,status='RUNNING' WHERE jobs.status!='OK' AND jobs.lease_until<=?`,
    )
      .bind(symbol, tf, close, id, now + 300000, now)
      .run();
    if (!claim.meta.changes) {
      await e.DB.prepare(
        "UPDATE runs SET status='DUPLICATE',finished=? WHERE id=?",
      )
        .bind(Date.now(), id)
        .run();
      return;
    }
    await e.DB.prepare(
      "UPDATE runs SET symbol=?,timeframe=?,candle_close=? WHERE id=?",
    )
      .bind(symbol, tf, close, id)
      .run();
    let result,
      raw: unknown = null;
    try {
      raw = await kraken(symbol, tf, fetcher);
      result = analyse(raw, tf, now);
    } catch (err) {
      result = analyse(null, tf, now);
      result.quality.reason = String(err);
      result.reasons = [String(err)];
    }
    const status = result.quality.status === "OK" ? "OK" : "BLOCKED";
    await e.DB.batch([
      e.DB.prepare(
        `INSERT INTO candle_batches SELECT ?,?,?,?,? WHERE EXISTS(SELECT 1 FROM jobs WHERE symbol=? AND timeframe=? AND candle_close=? AND owner=?) ON CONFLICT(symbol,timeframe,candle_close) DO UPDATE SET fetched=excluded.fetched,payload=excluded.payload`,
      ).bind(
        symbol,
        tf,
        close,
        now,
        JSON.stringify(raw),
        symbol,
        tf,
        close,
        id,
      ),
      e.DB.prepare(
        `INSERT INTO analyses SELECT ?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM jobs WHERE symbol=? AND timeframe=? AND candle_close=? AND owner=?) ON CONFLICT(symbol,timeframe,candle_close) DO UPDATE SET calculated=excluded.calculated,run_id=excluded.run_id,payload=excluded.payload`,
      ).bind(
        symbol,
        tf,
        close,
        now,
        id,
        JSON.stringify(result),
        symbol,
        tf,
        close,
        id,
      ),
      e.DB.prepare(
        "UPDATE jobs SET status=?,lease_until=? WHERE symbol=? AND timeframe=? AND candle_close=? AND owner=?",
      ).bind(status, now + 1800000, symbol, tf, close, id),
      e.DB.prepare(
        "UPDATE runs SET status=?,finished=?,error=?,elapsed_ms=? WHERE id=?",
      ).bind(
        status,
        Date.now(),
        status === "OK" ? null : result.quality.reason,
        Date.now() - start,
        id,
      ),
    ]);
    console.log(
      JSON.stringify({
        id,
        symbol,
        tf,
        status,
        elapsed_ms: Date.now() - start,
        cpu_ms: null,
      }),
    );
  } catch (err) {
    await e.DB.prepare(
      "UPDATE runs SET status='ERROR',finished=?,error=?,elapsed_ms=? WHERE id=?",
    )
      .bind(Date.now(), String(err).slice(0, 400), Date.now() - start, id)
      .run();
    console.error(JSON.stringify({ id, error: String(err) }));
  }
}
