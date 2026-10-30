import { analyse, cutoff, FRAMES, Frame, kraken, SYMBOLS } from "./mtf";
import type { Env } from "./types";
import { candleInsert } from "./candles";
import { errorClass, instrument, storageProbe } from "./monitoring";
// Journal expired windows since the first observed tick, including outage ranges.
// The cursor comparison and inserts share one D1 transaction; concurrent observers
// cannot double-count a range or move the cursor backwards.
async function journalGaps(e: Env, now: number) {
  await e.DB.prepare("INSERT OR IGNORE INTO scheduler_state VALUES(1,?)")
    .bind(now)
    .run();
  const previous = (await e.DB.prepare(
    "SELECT observed FROM scheduler_state WHERE id=1",
  ).first<{ observed: number }>())!.observed;
  if (now <= previous) return;
  const statements: D1PreparedStatement[] = [];
  for (const tf of Object.keys(FRAMES) as Frame[]) {
    const first = cutoff(tf, previous),
      last = cutoff(tf, now) - FRAMES[tf];
    if (last < first) continue;
    for (const symbol of SYMBOLS) {
      const count = (last - first) / FRAMES[tf] + 1;
      statements.push(
        e.DB.prepare(
          `INSERT OR IGNORE INTO coverage_gaps SELECT ?,?,?,?,?-COUNT(*),? FROM jobs WHERE symbol=? AND timeframe=? AND candle_close BETWEEN ? AND ? AND status='OK' HAVING ?-COUNT(*)>0 AND (SELECT observed FROM scheduler_state WHERE id=1)=?`,
        ).bind(
          symbol,
          tf,
          first,
          last,
          count,
          now,
          symbol,
          tf,
          first,
          last,
          count,
          previous,
        ),
      );
    }
  }
  statements.push(
    e.DB.prepare(
      "UPDATE scheduler_state SET observed=? WHERE id=1 AND observed=?",
    ).bind(now, previous),
  );
  await e.DB.batch(statements);
}
async function runTick(
  e: Env,
  scheduled: number,
  fetcher: typeof fetch = fetch,
  now = Date.now(),
  storageOwner: string,
) {
  const id = crypto.randomUUID(),
    start = Date.now();
  await e.DB.prepare(
    "INSERT INTO runs(id,scheduled,started,status) VALUES(?,?,?,?)",
  )
    .bind(id, scheduled, now, "RUNNING")
    .run();
  try {
    await journalGaps(e, now);
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
        attempts: number;
      }>();
    const units = Object.keys(FRAMES).flatMap((tf) =>
      SYMBOLS.map((symbol) => ({
        symbol,
        tf: tf as Frame,
        close: cutoff(tf as Frame, now),
      })),
    );
    const candidates = units
      .map((u) => ({
        ...u,
        job: jobs.results.find(
          (j) =>
            j.symbol === u.symbol &&
            j.timeframe === u.tf &&
            j.candle_close === u.close,
        ),
      }))
      .filter(
        (u) =>
          !u.job ||
          (u.job.status !== "OK" &&
            u.job.lease_until <= now &&
            u.job.attempts < 2),
      );
    // Earliest deadline first; first attempts win ties. At most two attempts per
    // combination/window keep permanently failing 15m markets from starving 1h/4h/1d.
    candidates.sort(
      (a, b) =>
        a.close + FRAMES[a.tf] - (b.close + FRAMES[b.tf]) ||
        (a.job?.attempts ?? 0) - (b.job?.attempts ?? 0) ||
        (a.job?.lease_until ?? 0) - (b.job?.lease_until ?? 0),
    );
    const unit = candidates[0];
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
      `INSERT INTO jobs(symbol,timeframe,candle_close,owner,lease_until,status,attempts) VALUES(?,?,?,?,?,'RUNNING',1) ON CONFLICT(symbol,timeframe,candle_close) DO UPDATE SET owner=excluded.owner,lease_until=excluded.lease_until,status='RUNNING',attempts=jobs.attempts+1 WHERE jobs.status!='OK' AND jobs.lease_until<=? AND jobs.attempts<2`,
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
      result.quality.reason = errorClass(err);
      result.reasons = [errorClass(err)];
    }
    const status = result.quality.status === "OK" ? "OK" : "BLOCKED";
    const latest = await storageProbe(e.DB);
    if (latest.state === "STOP" || latest.state === "UNKNOWN")
      throw Error("STORAGE_STOP");
    const lease = await e.DB.prepare(
      "SELECT owner FROM storage_guard WHERE id=1 AND owner=? AND lease_until>?",
    )
      .bind(storageOwner, Date.now())
      .first();
    if (!lease) throw Error("STORAGE_LEASE_EXPIRED");
    await e.DB.batch([
      // id=2 violates the singleton CHECK and rolls back the whole batch if
      // either lease was replaced between the preflight read and this commit.
      e.DB.prepare(
        `INSERT INTO storage_guard(id) SELECT 2 WHERE NOT EXISTS(
        SELECT 1 FROM storage_guard WHERE id=1 AND owner=? AND lease_until>?)
        OR NOT EXISTS(SELECT 1 FROM jobs WHERE symbol=? AND timeframe=?
          AND candle_close=? AND owner=? AND status='RUNNING')`,
      ).bind(storageOwner, Date.now(), symbol, tf, close, id),
      ...(status === "OK"
        ? [candleInsert(e.DB, symbol, tf, raw, now, storageOwner, Date.now())]
        : []),
      ...(status === "OK"
        ? [
            e.DB.prepare(
              `INSERT INTO analyses SELECT ?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM jobs WHERE symbol=? AND timeframe=? AND candle_close=? AND owner=?) AND EXISTS(SELECT 1 FROM storage_guard WHERE id=1 AND owner=? AND lease_until>?) ON CONFLICT(symbol,timeframe,candle_close) DO NOTHING`,
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
              storageOwner,
              Date.now(),
            ),
          ]
        : []),
      e.DB.prepare(
        "UPDATE jobs SET status=?,lease_until=? WHERE symbol=? AND timeframe=? AND candle_close=? AND owner=?",
      ).bind(status, now + 60000, symbol, tf, close, id),
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
        error_class: status === "OK" ? null : result.quality.reason,
      }),
    );
  } catch (err) {
    await e.DB.prepare(
      "UPDATE runs SET status='ERROR',finished=?,error=?,elapsed_ms=? WHERE id=?",
    )
      .bind(Date.now(), errorClass(err), Date.now() - start, id)
      .run();
    console.error(JSON.stringify({ id, error: errorClass(err) }));
  }
}

// One raw-data writer at a time across isolates. A crashed invocation expires;
// the lease is checked again in the atomic publication transaction.
export async function tick(
  e: Env,
  scheduled: number,
  fetcher: typeof fetch = fetch,
  now = Date.now(),
) {
  const tracked = instrument(e.DB),
    db = tracked.db,
    owner = crypto.randomUUID();
  let acquired = false,
    gate = "UNKNOWN";
  const started = Date.now();
  try {
    const claim = await db
      .prepare(
        "UPDATE storage_guard SET owner=?,lease_until=? WHERE id=1 AND lease_until<=?",
      )
      .bind(owner, Date.now() + 60000, Date.now())
      .run();
    if (!claim.meta.changes) {
      gate = "BUSY";
      return;
    }
    acquired = true;
    const probe = await storageProbe(db);
    gate = probe.state;
    if (gate === "UNKNOWN" || gate === "STOP") return;
    await db
      .prepare(
        `UPDATE storage_guard SET previous_bytes=measured_bytes,previous_at=measured_at,
      measured_bytes=?,measured_at=? WHERE id=1 AND owner=?`,
      )
      .bind(probe.bytes, now, owner)
      .run();
    await runTick({ ...e, DB: db }, scheduled, fetcher, now, owner);
  } catch (err) {
    console.error(
      JSON.stringify({
        event: "storage_guard",
        error: errorClass(err),
        state: gate,
      }),
    );
  } finally {
    if (acquired) {
      try {
        await db
          .prepare(
            "UPDATE storage_guard SET owner=NULL,lease_until=0 WHERE id=1 AND owner=?",
          )
          .bind(owner)
          .run();
      } catch {
        /* Crash recovery via lease expiry; no unsafe fallback writes. */
      }
    }
    console.log(
      JSON.stringify({
        event: "invocation",
        storage_state: gate,
        d1: tracked.costs,
        cpu_ms: null,
        elapsed_ms: Date.now() - started,
        daily_quota_remaining: null,
      }),
    );
  }
}
