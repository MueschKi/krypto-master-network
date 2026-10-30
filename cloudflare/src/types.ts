export interface Env {
  DB: D1Database;
  ASSETS: Fetcher;
  ENABLE_LOCAL_ACCOUNT_PREVIEW?: string;
  AUTH_USER?: string;
  AUTH_PASSWORD?: string;
}
