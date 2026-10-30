-- Additive only: legacy batches, signals, runs, gaps and accounts are untouched.
CREATE TABLE storage_guard (
 id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT, lease_until INTEGER NOT NULL DEFAULT 0,
 measured_bytes INTEGER, measured_at INTEGER, previous_bytes INTEGER, previous_at INTEGER
);
INSERT INTO storage_guard(id) VALUES(1);
CREATE TABLE raw_candles (
 symbol TEXT NOT NULL, timeframe TEXT NOT NULL,
 open_utc INTEGER NOT NULL, payload TEXT NOT NULL CHECK(json_valid(payload)),
 PRIMARY KEY(symbol,timeframe,open_utc)
) WITHOUT ROWID;
-- Closed candles are immutable. Revised upstream history blocks publication,
-- rather than silently rewriting the evidence for an earlier signal.
CREATE TRIGGER raw_candle_conflict BEFORE INSERT ON raw_candles
WHEN EXISTS(SELECT 1 FROM raw_candles WHERE symbol=NEW.symbol AND timeframe=NEW.timeframe
 AND open_utc=NEW.open_utc AND payload<>NEW.payload)
BEGIN SELECT RAISE(ABORT,'CANDLE_CONFLICT'); END;
CREATE INDEX coverage_gaps_observed ON coverage_gaps(observed DESC);
