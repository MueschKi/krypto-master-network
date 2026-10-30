import { quality, Frame } from "./mtf";
// One JSON parameter keeps 720 bars below D1's 100-parameter limit. SQL writes
// only previously unseen closed bars; the trigger rejects changed history.
export function candleInsert(
  db: D1Database,
  symbol: string,
  tf: Frame,
  raw: unknown,
  now: number,
  owner: string,
  clock: number,
) {
  const rows = quality(raw, tf, now);
  return db
    .prepare(
      `INSERT INTO raw_candles(symbol,timeframe,open_utc,payload)
    SELECT ?,?,json_extract(value,'$[0]'),value FROM json_each(?)
    WHERE EXISTS(SELECT 1 FROM storage_guard WHERE id=1 AND owner=? AND lease_until>?)
    ON CONFLICT(symbol,timeframe,open_utc) DO NOTHING`,
    )
    .bind(symbol, tf, JSON.stringify(rows), owner, clock);
}
