-- No trading ledger or writable account engine in Phase A.
CREATE TABLE runs (
 id TEXT PRIMARY KEY, scheduled INTEGER NOT NULL, started INTEGER NOT NULL,
 finished INTEGER, status TEXT NOT NULL, symbol TEXT, timeframe TEXT,
 candle_close INTEGER, error TEXT, elapsed_ms INTEGER
);
CREATE INDEX runs_scheduled ON runs(scheduled DESC);
CREATE TABLE analyses (
 symbol TEXT NOT NULL, timeframe TEXT NOT NULL, candle_close INTEGER NOT NULL,
 calculated INTEGER NOT NULL, run_id TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(symbol,timeframe,candle_close)
);
CREATE TABLE jobs (
 symbol TEXT NOT NULL, timeframe TEXT NOT NULL, candle_close INTEGER NOT NULL,
 owner TEXT NOT NULL, lease_until INTEGER NOT NULL, status TEXT NOT NULL,
 PRIMARY KEY(symbol,timeframe,candle_close)
);
-- Explicit operator-imported, immutable read-only snapshot; not authoritative.
CREATE TABLE account_snapshots (
 account TEXT PRIMARY KEY CHECK(account IN ('master7','atr25')),
 imported_utc TEXT NOT NULL, source_sha256 TEXT NOT NULL, payload TEXT NOT NULL
);

CREATE INDEX jobs_close ON jobs(candle_close);
CREATE INDEX runs_status ON runs(status,finished DESC);
CREATE TABLE candle_batches (
 symbol TEXT NOT NULL, timeframe TEXT NOT NULL,candle_close INTEGER NOT NULL,
 fetched INTEGER NOT NULL,payload TEXT NOT NULL,
 PRIMARY KEY(symbol,timeframe,candle_close)
);

CREATE INDEX analyses_calculated ON analyses(calculated DESC);
