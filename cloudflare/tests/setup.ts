import { env, applyD1Migrations, reset } from "cloudflare:test";
import { beforeEach } from "vitest";
beforeEach(async () => {
  await reset();
  await applyD1Migrations(env.DB, env.TEST_MIGRATIONS);
});
