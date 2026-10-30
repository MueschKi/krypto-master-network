import type { Env } from "./types";
export async function authorized(r: Request, e: Env) {
  const u = new URL(r.url);
  if (
    u.protocol !== "https:" &&
    !["localhost", "127.0.0.1"].includes(u.hostname)
  )
    return false;
  if (!e.AUTH_USER || !e.AUTH_PASSWORD || e.AUTH_PASSWORD.length < 32)
    return false;
  const hash = (s: string) =>
    crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  const [a, b] = await Promise.all([
    hash(r.headers.get("Authorization") ?? ""),
    hash("Basic " + btoa(e.AUTH_USER + ":" + e.AUTH_PASSWORD)),
  ]);
  return (
    new Uint8Array(a).reduce((n, x, i) => n | (x ^ new Uint8Array(b)[i]), 0) ===
    0
  );
}
