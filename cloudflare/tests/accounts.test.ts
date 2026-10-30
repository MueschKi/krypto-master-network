import { env } from "cloudflare:test";
import { it, expect } from "vitest";
import { handle, Env } from "../src/index";
import { readAccounts } from "../src/accounts";
import fixture from "./import.generated.json";
const e = env as unknown as Env;
it("generated Python import is one D1 statement, validates hashes and cannot overwrite on retry", async () => {
  expect(fixture.sql).not.toMatch(/BEGIN|COMMIT|REPLACE|UPDATE/);
  await e.DB.prepare(fixture.sql).run();
  const before = await readAccounts(e);
  expect(before.map((a) => a.account)).toEqual(["master7", "atr25"]);
  await expect(e.DB.prepare(fixture.sql).run()).rejects.toThrow();
  expect(await readAccounts(e)).toEqual(before);
});
it("malformed partial pair is rejected with no published account", async () => {
  const damaged = fixture.sql.replace("atr25", "other");
  await expect(e.DB.prepare(damaged).run()).rejects.toThrow();
  expect(await readAccounts(e)).toEqual([]);
});
it("legacy partial import is never shown as a valid pair", async () => {
  await e.DB.prepare(
    "INSERT INTO account_snapshots VALUES('master7','utc','sha','{}')",
  ).run();
  expect(await readAccounts(e)).toEqual([]);
});
it("tampered source/pair hash fails closed", async () => {
  await e.DB.prepare(fixture.sql).run();
  await e.DB.prepare("UPDATE account_bundles SET bundle_sha256=?")
    .bind("0".repeat(64))
    .run();
  await expect(readAccounts(e)).rejects.toThrow("Hash");
});
it("public personal account access stays disabled, including when local flag is accidentally enabled", async () => {
  await e.DB.prepare(fixture.sql).run();
  const auth = {
    ...e,
    AUTH_USER: "owner",
    AUTH_PASSWORD: "x".repeat(40),
    ENABLE_LOCAL_ACCOUNT_PREVIEW: "true",
  };
  const headers = {
    Authorization: "Basic " + btoa("owner:" + auth.AUTH_PASSWORD),
  };
  expect(
    await (
      await handle(
        new Request("https://public.workers.dev/api/accounts", { headers }),
        auth,
      )
    ).json(),
  ).toEqual([]);
  const local = await handle(
    new Request("http://localhost/api/accounts", { headers }),
    auth,
  );
  expect(((await local.json()) as any[]).length).toBe(2);
  const forged = new Request("https://localhost/api/accounts", {
    headers,
    cf: { colo: "TEST" },
  });
  expect(await (await handle(forged, auth)).json()).toEqual([]);
});
it("valid outer hash cannot hide a mismatched original source hash", async () => {
  await e.DB.prepare(fixture.sql).run();
  const row = await e.DB.prepare(
    "SELECT payload FROM account_bundles",
  ).first<any>();
  const accounts = JSON.parse(row.payload);
  accounts[1].source_sha256 = "0".repeat(64);
  const payload = JSON.stringify(accounts);
  const hash = Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(payload)),
    ),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
  await e.DB.prepare("UPDATE account_bundles SET payload=?,bundle_sha256=?")
    .bind(payload, hash)
    .run();
  await expect(readAccounts(e)).rejects.toThrow("Quell-Hash");
});
it("named pair without both payloads and hashes is rejected", async () => {
  await expect(
    e.DB.prepare(
      "INSERT INTO account_bundles VALUES('paper-readonly-v1','utc',?,?)",
    )
      .bind(
        "0".repeat(64),
        JSON.stringify([{ account: "master7" }, { account: "atr25" }]),
      )
      .run(),
  ).rejects.toThrow();
  expect(await readAccounts(e)).toEqual([]);
});
