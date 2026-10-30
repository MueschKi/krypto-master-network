export interface Env {
  DB: D1Database;
  CF_VERSION_METADATA?: { id: string; tag?: string; timestamp?: string };
  ASSETS: Fetcher;
  ENABLE_LOCAL_ACCOUNT_PREVIEW?: string;
  AUTH_USER?: string;
  AUTH_PASSWORD?: string;
}
