CREATE TABLE scheduler_state (
 id INTEGER PRIMARY KEY CHECK(id=1), observed INTEGER NOT NULL
);
-- Compact explicit coverage gaps, not fabricated historical analyses.
CREATE TABLE coverage_gaps (
 symbol TEXT NOT NULL, timeframe TEXT NOT NULL,
 first_close INTEGER NOT NULL, last_close INTEGER NOT NULL,
 missing_count INTEGER NOT NULL CHECK(missing_count>0), observed INTEGER NOT NULL,
 PRIMARY KEY(symbol,timeframe,first_close,last_close)
);
-- The pair is ONE immutable row: one SQL statement is atomic on D1.
-- Legacy account_snapshots is retained but no longer consumed by the application.
CREATE TABLE account_bundles (
 id TEXT PRIMARY KEY CHECK(id='paper-readonly-v1'),
 imported_utc TEXT NOT NULL,
 bundle_sha256 TEXT NOT NULL CHECK(length(bundle_sha256)=64),
 payload TEXT NOT NULL CHECK(COALESCE(json_valid(payload) AND json_array_length(payload)=2
  AND json_extract(payload,'$[0].account')='master7'
  AND json_extract(payload,'$[1].account')='atr25'
  AND length(json_extract(payload,'$[0].source_sha256'))=64
  AND length(json_extract(payload,'$[1].source_sha256'))=64
  AND json_valid(json_extract(payload,'$[0].payload'))
  AND json_valid(json_extract(payload,'$[1].payload')),0))
);
-- A failing 15m market may not consume every minute forever.
ALTER TABLE jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 1;
