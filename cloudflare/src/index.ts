import { localAccountPreview, readAccounts } from "./accounts";
import { cutoff, FRAMES, Frame, SYMBOLS, summarize } from "./mtf";
import type { Env } from "./types";
import { authorized } from "./auth";
import { tick } from "./scheduler";
import { diagnostics, instrument } from "./monitoring";
export { authorized, tick };
export type { Env };
export const VERSION = "2.0.0-phase-a";
function secure(r: Response) {
  const out = new Response(r.body, r);
  for (const [k, v] of Object.entries({
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy":
      "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
  }))
    out.headers.set(k, v);
  return out;
}
async function serve(r: Request, e: Env) {
  if (!(await authorized(r, e)))
    return secure(
      new Response("Anmeldung erforderlich", {
        status: 401,
        headers: {
          "WWW-Authenticate":
            'Basic realm="Krypto Master privat", charset="UTF-8"',
        },
      }),
    );
  if (r.method !== "GET")
    return secure(new Response("Nur lesend", { status: 405 }));
  const path = new URL(r.url).pathname,
    now = Date.now();
  try {
    if (path === "/api/diagnostics")
      return secure(Response.json(await diagnostics(e, now)));
    if (path === "/api/status") {
      const last = await e.DB.prepare(
        "SELECT scheduled,started,finished,status,symbol,timeframe,candle_close,elapsed_ms FROM runs ORDER BY scheduled DESC LIMIT 1",
      ).first<{ scheduled: number }>();
      const success = await e.DB.prepare(
        "SELECT scheduled,finished,status,symbol,timeframe,candle_close FROM runs WHERE status='OK' ORDER BY finished DESC LIMIT 1",
      ).first();
      return secure(
        Response.json({
          version: VERSION,
          build_id: e.CF_VERSION_METADATA?.id ?? null,
          mode: "BEOBACHTUNG",
          trading: false,
          heartbeat: last,
          last_success: success,
          stale: !last || now - last.scheduled > 180000,
          free_tier_verified: false,
          accounts_access: localAccountPreview(r, e)
            ? "LOCAL_PREVIEW"
            : "DISABLED_PENDING_AUTH_HARDENING",
          mtf_release: "SEE_PER_WINDOW_QUALITY",
        }),
      );
    }
    if (path === "/api/markets" || path === "/api/mtf") {
      const rows = await e.DB.prepare(
        `WITH pairs(symbol,timeframe) AS (VALUES ${SYMBOLS.flatMap((s) => Object.keys(FRAMES).map((tf) => `('${s}','${tf}')`)).join(",")}) SELECT a.* FROM pairs p JOIN analyses a ON a.symbol=p.symbol AND a.timeframe=p.timeframe AND a.candle_close=(SELECT candle_close FROM analyses WHERE symbol=p.symbol AND timeframe=p.timeframe ORDER BY candle_close DESC LIMIT 1)`,
      ).all<{
        symbol: string;
        timeframe: Frame;
        candle_close: number;
        calculated: number;
        payload: string;
      }>();
      const assets = SYMBOLS.map((symbol) => {
        const frames = Object.fromEntries(
          Object.keys(FRAMES).map((tf) => {
            const row = rows.results.find(
                (x) => x.symbol === symbol && x.timeframe === tf,
              ),
              fresh = row && row.candle_close === cutoff(tf as Frame, now),
              data = row
                ? JSON.parse(row.payload)
                : {
                    classification: "BLOCKIERT",
                    quality: { status: "BLOCKIERT", reason: "Noch kein Lauf" },
                    agents: {},
                  };
            return [
              tf,
              {
                ...data,
                classification: fresh ? data.classification : "BLOCKIERT",
                stale: !fresh,
                calculated: row?.calculated ?? null,
                candle_close: row?.candle_close ?? null,
              },
            ];
          }),
        );
        return {
          symbol,
          timeframes: frames,
          classification: summarize(frames),
        };
      });
      return secure(
        Response.json({ snapshot_utc: new Date(now).toISOString(), assets }),
      );
    }
    if (path === "/api/runs" || path === "/api/history") {
      const table = path === "/api/runs" ? "runs" : "analyses",
        order = path === "/api/runs" ? "scheduled" : "calculated";
      return secure(
        Response.json(
          (
            await e.DB.prepare(
              `SELECT * FROM ${table} ORDER BY ${order} DESC LIMIT 100`,
            ).all()
          ).results,
        ),
      );
    }
    if (path === "/api/accounts")
      return secure(
        Response.json(localAccountPreview(r, e) ? await readAccounts(e) : []),
      );
    if (path === "/api/gaps")
      return secure(
        Response.json(
          (
            await e.DB.prepare(
              "SELECT *, 'MISSED' AS status FROM coverage_gaps ORDER BY observed DESC LIMIT 100",
            ).all()
          ).results,
        ),
      );
    if (path.startsWith("/api/"))
      return secure(new Response("Nicht vorhanden", { status: 404 }));
    return secure(await e.ASSETS.fetch(r));
  } catch {
    return secure(
      Response.json(
        { error: "Datenbank/Verbindung gestört; Anzeige gesperrt" },
        { status: 503 },
      ),
    );
  }
}
export default {
  fetch: handle,
  scheduled(event: ScheduledController, e: Env, ctx: ExecutionContext) {
    ctx.waitUntil(tick(e, event.scheduledTime));
  },
};

export async function handle(r: Request, e: Env) {
  const tracked = instrument(e.DB),
    started = Date.now();
  const response = await serve(r, { ...e, DB: tracked.db });
  console.log(
    JSON.stringify({
      event: "http",
      status: response.status,
      d1: tracked.costs,
      cpu_ms: null,
      elapsed_ms: Date.now() - started,
    }),
  );
  return response;
}
