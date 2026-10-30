export const FRAMES = {
  "15m": 900000,
  "1h": 3600000,
  "4h": 14400000,
  "1d": 86400000,
} as const;
export type Frame = keyof typeof FRAMES;
export const SYMBOLS = ["BTC/EUR", "ETH/EUR", "SOL/EUR", "NEAR/EUR"] as const;
export type Candle = [number, number, number, number, number, number];
export function cutoff(tf: Frame, now: number) {
  return Math.floor(now / FRAMES[tf]) * FRAMES[tf];
}
export function quality(raw: unknown, tf: Frame, now: number): Candle[] {
  if (!Array.isArray(raw) || !raw.length || raw.length > 720)
    throw Error("KEINE_DATEN / ungültige Anzahl");
  const duration = FRAMES[tf];
  let previous = -1;
  const closed: Candle[] = [];
  for (const row of raw) {
    if (!Array.isArray(row) || row.length !== 6) throw Error("OHLCV-Format");
    const [ts, o, h, l, c, v] = row;
    if (!Number.isFinite(ts) || ts < 0 || ts % duration || ts <= previous)
      throw Error("UTC-Raster / doppelte oder unsortierte Zeitstempel");
    previous = ts;
    if (ts + duration > now) continue;
    if (
      !row.every((x) => typeof x === "number" && Number.isFinite(x)) ||
      Math.min(o, h, l, c) <= 0 ||
      v < 0 ||
      h < Math.max(o, c, l) ||
      l > Math.min(o, c, h)
    )
      throw Error("Unplausible OHLCV-Werte");
    if (closed.length && ts - closed[closed.length - 1][0] !== duration)
      throw Error("Datenlücke");
    closed.push(row as Candle);
  }
  if (closed.length < 250) throw Error("Zu wenig abgeschlossene Kerzen: <250");
  if (closed.at(-1)![0] + duration !== cutoff(tf, now))
    throw Error("Neueste abgeschlossene Kerze fehlt / veraltet");
  return closed;
}
function ema(values: number[], alpha: number) {
  let value = values[0];
  return values.map(
    (x, i) => (value = i ? (1 - alpha) * value + alpha * x : x),
  );
}
export function analyse(raw: unknown, tf: Frame, now: number) {
  try {
    const rows = quality(raw, tf, now),
      c = rows.map((r) => r[4]),
      last = c.at(-1)!;
    const end = (v: number[]) => v.at(-1)!;
    const trendValues = Object.fromEntries(
      [20, 50, 200].map((n) => ["ema" + n, end(ema(c, 2 / (n + 1)))]),
    );
    const { ema20: a, ema50: b, ema200: d } = trendValues;
    const trend =
      last > a && a > b && b > d
        ? "POSITIV"
        : last < a && a < b && b < d
          ? "NEGATIV"
          : "NEUTRAL";
    const delta = c.slice(1).map((v, i) => v - c[i]);
    const gain = end(
        ema(
          delta.map((x) => Math.max(0, x)),
          1 / 14,
        ),
      ),
      loss = end(
        ema(
          delta.map((x) => Math.max(0, -x)),
          1 / 14,
        ),
      );
    const rsi =
      gain === 0 && loss === 0
        ? 50
        : loss === 0
          ? 100
          : 100 - 100 / (1 + gain / loss);
    const e12 = ema(c, 2 / 13),
      e26 = ema(c, 2 / 27),
      macd = e12.map((x, i) => x - e26[i]);
    const line = end(macd),
      signal = end(ema(macd, 2 / 10)),
      histogram = line - signal;
    const momentum =
      rsi > 50 && histogram > 0
        ? "POSITIV"
        : rsi < 50 && histogram < 0
          ? "NEGATIV"
          : "NEUTRAL";
    const atr = end(
      ema(
        rows.map((r, i) =>
          Math.max(
            r[2] - r[3],
            i ? Math.abs(r[2] - c[i - 1]) : 0,
            i ? Math.abs(r[3] - c[i - 1]) : 0,
          ),
        ),
        1 / 14,
      ),
    );
    const volatility = atr / last > 0.1 ? "BLOCKIERT" : "NEUTRAL";
    return {
      classification:
        volatility === "BLOCKIERT"
          ? "BLOCKIERT"
          : trend === momentum
            ? trend
            : "NEUTRAL",
      quality: {
        status: "OK",
        reason: "Lückenlos, plausibel, aktuell und vollständig abgeschlossen",
        closed_count: rows.length,
        latest_close_utc: new Date(rows.at(-1)![0] + FRAMES[tf]).toISOString(),
      },
      agents: {
        trend: {
          signal: trend,
          indicators: trendValues,
          reason:
            "Schluss > EMA20 > EMA50 > EMA200; umgekehrt NEGATIV; sonst NEUTRAL.",
        },
        momentum: {
          signal: momentum,
          indicators: {
            rsi14: rsi,
            macd: line,
            macd_signal: signal,
            macd_histogram: histogram,
          },
          reason:
            "RSI > 50 und Histogramm > 0: POSITIV; beide darunter NEGATIV.",
        },
        volatility: {
          signal: volatility,
          indicators: { atr14: atr, atr14_fraction: atr / last },
          reason: "ATR14 / Schluss > 10 % blockiert.",
        },
      },
      reasons: [
        `Trend=${trend}, Momentum=${momentum}, Volatilität=${volatility}. Übereinstimmung erforderlich; Veto hat Vorrang.`,
      ],
    };
  } catch (e) {
    return {
      classification: "BLOCKIERT",
      quality: { status: "BLOCKIERT", reason: String(e) },
      agents: {},
      reasons: [String(e)],
    };
  }
}
export function summarize(frames: Record<string, { classification: string }>) {
  const s = Object.values(frames).map((x) => x.classification);
  return s.length !== 4 || s.includes("BLOCKIERT")
    ? "BLOCKIERT"
    : s.every((x) => x === "POSITIV")
      ? "POSITIV"
      : s.every((x) => x === "NEGATIV")
        ? "NEGATIV"
        : "NEUTRAL";
}
export async function kraken(
  symbol: string,
  tf: Frame,
  fetcher: typeof fetch = fetch,
): Promise<Candle[]> {
  const pairs: Record<string, string> = {
    "BTC/EUR": "XBTEUR",
    "ETH/EUR": "ETHEUR",
    "SOL/EUR": "SOLEUR",
    "NEAR/EUR": "NEAREUR",
  };
  if (!pairs[symbol]) throw Error("Unbekanntes Symbol");
  const marketResponse = await fetcher(
    `https://api.kraken.com/0/public/AssetPairs?pair=${pairs[symbol]}`,
    { signal: AbortSignal.timeout(15000) },
  );
  if (!marketResponse.ok)
    throw Error(`Kraken Marktstatus HTTP ${marketResponse.status}`);
  const markets = (await marketResponse.json()) as {
    error?: unknown[];
    result?: Record<
      string,
      { wsname?: string; status?: string; quote?: string }
    >;
  };
  const market = markets.result && Object.values(markets.result);
  if (
    !Array.isArray(markets.error) ||
    markets.error.length ||
    !market ||
    market.length !== 1 ||
    market[0].status !== "online" ||
    market[0].quote !== "ZEUR" ||
    market[0].wsname !== (symbol === "BTC/EUR" ? "XBT/EUR" : symbol)
  )
    throw Error("Kraken Markt fehlt / nicht online / falsche Quote");
  const response = await fetcher(
    `https://api.kraken.com/0/public/OHLC?pair=${pairs[symbol]}&interval=${FRAMES[tf] / 60000}`,
    { signal: AbortSignal.timeout(15000) },
  );
  if (!response.ok) throw Error(`Kraken HTTP ${response.status}`);
  const body = (await response.json()) as {
    error?: unknown[];
    result?: Record<string, unknown>;
  };
  if (!Array.isArray(body.error) || body.error.length || !body.result)
    throw Error("Kraken Fehlerantwort");
  const keys = Object.keys(body.result).filter((k) => k !== "last");
  const rows = body.result[keys[0]];
  if (keys.length !== 1 || !Array.isArray(rows) || rows.length > 721)
    throw Error("Kraken OHLC-Format");
  // Kraken can return 720 finalized bars PLUS the running bar. Match ccxt limit=720.
  return rows.slice(-720).map((r: unknown) => {
    if (
      !Array.isArray(r) ||
      r.length !== 8 ||
      r
        .slice(0, 7)
        .some(
          (x) =>
            x === null || x === "" || !["number", "string"].includes(typeof x),
        )
    )
      throw Error("Kraken Kerzenformat");
    return [
      Number(r[0]) * 1000,
      Number(r[1]),
      Number(r[2]),
      Number(r[3]),
      Number(r[4]),
      Number(r[6]),
    ] as Candle;
  });
}
