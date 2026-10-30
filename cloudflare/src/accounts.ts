import type { Env } from "./types";
export function localAccountPreview(request: Request, env: Env) {
  return (
    env.ENABLE_LOCAL_ACCOUNT_PREVIEW === "true" &&
    !request.cf &&
    ["localhost", "127.0.0.1"].includes(new URL(request.url).hostname)
  );
}
async function sha256(value: string) {
  return Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)),
    ),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
}
export async function readAccounts(env: Env) {
  const row = await env.DB.prepare(
    "SELECT * FROM account_bundles WHERE id='paper-readonly-v1'",
  ).first<{ imported_utc: string; bundle_sha256: string; payload: string }>();
  if (!row) return [];
  if ((await sha256(row.payload)) !== row.bundle_sha256)
    throw Error("Ungültiger Paar-Hash");
  const accounts = JSON.parse(row.payload);
  if (
    !Array.isArray(accounts) ||
    accounts.length !== 2 ||
    accounts[0].account !== "master7" ||
    accounts[1].account !== "atr25"
  )
    throw Error("Unvollständiges Kontopaar");
  for (const a of accounts) {
    if (
      typeof a.payload !== "string" ||
      (await sha256(a.payload)) !== a.source_sha256
    )
      throw Error("Ungültiger Quell-Hash");
    JSON.parse(a.payload);
  }
  return accounts.map((a) => ({ ...a, imported_utc: row.imported_utc }));
}
